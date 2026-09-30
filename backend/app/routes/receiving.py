import csv
import io
import json
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import ReceivingSessionRecord, ScanRecord, RegistryRecord
from backend.app.schemas import (
    ReceivingSessionCreate, ReceivingSessionResponse, ReceivingScanResponse,
    ReceivingSessionSummary, ReceivingSessionAcceptResponse, ManualScanRequest, ScanResponse
)
from backend.app.pipeline.fusion import process_scan_image
from backend.app.routes.scans import build_scan_response_from_model
from backend.reports.pdf import generate_pdf_report

router = APIRouter(prefix="/receiving", tags=["Receiving"])

@router.post("/sessions", response_model=ReceivingSessionResponse)
async def create_receiving_session(req: ReceivingSessionCreate, db: Session = Depends(get_db)):
    sess = ReceivingSessionRecord(
        supplier_name=req.supplier_name,
        invoice_number=req.invoice_number
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)

    return ReceivingSessionResponse(
        id=sess.id,
        supplier_name=sess.supplier_name,
        invoice_number=sess.invoice_number,
        created_at=sess.created_at.isoformat() + "Z",
        status=sess.status,
        total_scans=0
    )


@router.post("/sessions/{id}/scan", response_model=ReceivingScanResponse)
async def scan_receiving_item(
    id: str,
    image: Optional[UploadFile] = File(None),
    manual_data_str: Optional[str] = Form(None),
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
):
    sess = db.query(ReceivingSessionRecord).filter(ReceivingSessionRecord.id == id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Receiving session not found.")

    image_bytes = None
    if image:
        image_bytes = await image.read()

    m_data = json.loads(manual_data_str) if manual_data_str else None

    scan_resp, serial_hash, batch_hash = process_scan_image(
        db=db,
        image_bytes=image_bytes,
        device_token=x_device_token,
        manual_data=m_data
    )

    existing_scans = db.query(ScanRecord).filter(ScanRecord.receiving_session_id == id).all()
    session_index = len(existing_scans) + 1

    rec = ScanRecord(
        id=scan_resp.id,
        device_token=x_device_token,
        verdict=scan_resp.verdict,
        verdict_label=scan_resp.verdict_label,
        confidence=scan_resp.confidence,
        confidence_note=scan_resp.confidence_note,
        disclaimer=scan_resp.disclaimer,
        reasons_json=json.dumps(scan_resp.reasons),
        checked_json=json.dumps(scan_resp.checked),
        not_checked_json=json.dumps(scan_resp.not_checked),
        fields_json=scan_resp.fields.model_dump_json(),
        code_data_json=scan_resp.code_data.model_dump_json(),
        quality_json=scan_resp.quality.model_dump_json(),
        visual_json=scan_resp.visual.model_dump_json(),
        authenticity_json=scan_resp.authenticity.model_dump_json(),
        simulated_flags_json=scan_resp.simulated_flags.model_dump_json(),
        serial_hash=serial_hash,
        batch_hash=batch_hash,
        receiving_session_id=id
    )
    db.add(rec)
    db.commit()

    outlier = scan_resp.verdict in ("high_suspicion", "needs_verification")

    return ReceivingScanResponse(
        session_id=id,
        scan_id=scan_resp.id,
        item_result=scan_resp,
        session_scan_index=session_index,
        outlier_warning=outlier
    )


@router.get("/sessions/{id}/summary", response_model=ReceivingSessionSummary)
async def get_receiving_summary(id: str, db: Session = Depends(get_db)):
    sess = db.query(ReceivingSessionRecord).filter(ReceivingSessionRecord.id == id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Receiving session not found.")

    scans = db.query(ScanRecord).filter(ScanRecord.receiving_session_id == id).all()
    scan_responses = [build_scan_response_from_model(s) for s in scans]

    low_c = sum(1 for s in scan_responses if s.verdict == "low_risk")
    needs_c = sum(1 for s in scan_responses if s.verdict == "needs_verification")
    high_c = sum(1 for s in scan_responses if s.verdict == "high_suspicion")
    qual_c = sum(1 for s in scan_responses if s.verdict == "insufficient_quality")

    outliers = [s.id for s in scan_responses if s.verdict in ("high_suspicion", "needs_verification")]

    return ReceivingSessionSummary(
        id=sess.id,
        supplier_name=sess.supplier_name,
        invoice_number=sess.invoice_number,
        status=sess.status,
        total_scanned=len(scans),
        low_risk_count=low_c,
        needs_verification_count=needs_c,
        high_suspicion_count=high_c,
        insufficient_quality_count=qual_c,
        outliers=outliers,
        scans=scan_responses
    )


@router.post("/sessions/{id}/accept", response_model=ReceivingSessionAcceptResponse)
async def accept_receiving_session(id: str, db: Session = Depends(get_db)):
    sess = db.query(ReceivingSessionRecord).filter(ReceivingSessionRecord.id == id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Receiving session not found.")

    sess.status = "accepted"
    sess.accepted_at = datetime.datetime.utcnow()

    scans = db.query(ScanRecord).filter(ScanRecord.receiving_session_id == id).all()
    reg_count = 0
    for s in scans:
        if s.serial_hash:
            reg = db.query(RegistryRecord).filter(RegistryRecord.serial_hash == s.serial_hash).first()
            if not reg:
                reg = RegistryRecord(
                    serial_hash=s.serial_hash,
                    gtin=json.loads(s.code_data_json).get("gtin"),
                    batch_number=json.loads(s.fields_json).get("batch_number"),
                    expiry_date=json.loads(s.fields_json).get("expiry_date"),
                    status="registered"
                )
                db.add(reg)
            else:
                reg.status = "registered"
            reg_count += 1

    db.commit()

    return ReceivingSessionAcceptResponse(
        id=id,
        status="accepted",
        accepted_at=sess.accepted_at.isoformat() + "Z",
        registered_items_count=reg_count
    )


@router.get("/sessions/{id}/export")
async def export_receiving_session(id: str, format: str = Query("csv"), db: Session = Depends(get_db)):
    sess = db.query(ReceivingSessionRecord).filter(ReceivingSessionRecord.id == id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Receiving session not found.")

    scans = db.query(ScanRecord).filter(ScanRecord.receiving_session_id == id).all()
    scan_responses = [build_scan_response_from_model(s) for s in scans]

    if format.lower() == "pdf":
        summary_dict = {
            "id": f"Receiving_Session_{sess.id}",
            "timestamp": sess.created_at.isoformat() + "Z",
            "verdict_label": f"Receiving Session Report ({sess.supplier_name})",
            "confidence": 100.0,
            "fields": {
                "medicine_name": f"Supplier: {sess.supplier_name}",
                "batch_number": f"Invoice: {sess.invoice_number}",
                "strength": f"Total Scanned: {len(scans)}",
                "form": f"Status: {sess.status}"
            },
            "reasons": [f"Scan {s.id}: {s.verdict_label} - {s.fields.medicine_name or 'N/A'}" for s in scan_responses],
            "checked": ["receiving", "intra_lot_consistency", "outlier_detection"],
            "not_checked": [],
            "disclaimer": "Screening only. This does not confirm authenticity."
        }
        pdf_bytes = generate_pdf_report(summary_dict)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=receiving_session_{id}.pdf"}
        )
    else:  # CSV format
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Scan ID", "Timestamp", "Medicine Name", "Batch Number", "Expiry Date", "Verdict", "Confidence"])
        for s in scan_responses:
            writer.writerow([
                s.id,
                s.timestamp,
                s.fields.medicine_name or "",
                s.fields.batch_number or "",
                s.fields.expiry_date or "",
                s.verdict,
                s.confidence
            ])
        csv_data = output.getvalue()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=receiving_session_{id}.csv"}
        )
