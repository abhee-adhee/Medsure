import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import ScanRecord
from backend.app.schemas import ScanResponse, ScansListResponse, DeleteScansResponse
from backend.reports.pdf import generate_pdf_report

router = APIRouter(tags=["Scans"])

def build_scan_response_from_model(rec: ScanRecord) -> ScanResponse:
    return ScanResponse(
        id=rec.id,
        timestamp=rec.timestamp.isoformat() + "Z",
        verdict=rec.verdict,
        verdict_label=rec.verdict_label,
        confidence=rec.confidence,
        confidence_note=rec.confidence_note or "",
        disclaimer=rec.disclaimer or "Screening only. This does not confirm authenticity.",
        reasons=json.loads(rec.reasons_json or "[]"),
        checked=json.loads(rec.checked_json or "[]"),
        not_checked=json.loads(rec.not_checked_json or "[]"),
        fields=json.loads(rec.fields_json or "{}"),
        code_data=json.loads(rec.code_data_json or "{}"),
        quality=json.loads(rec.quality_json or "{}"),
        visual=json.loads(rec.visual_json or "{}"),
        authenticity=json.loads(rec.authenticity_json or "{}"),
        simulated_flags=json.loads(rec.simulated_flags_json or "{}")
    )

@router.get("/scans", response_model=ScansListResponse)
async def list_scans(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
):
    query = db.query(ScanRecord)
    if x_device_token:
        query = query.filter(ScanRecord.device_token == x_device_token)
    
    total = query.count()
    records = query.order_by(ScanRecord.timestamp.desc()).offset(offset).limit(limit).all()
    
    scans_list = [build_scan_response_from_model(r) for r in records]
    return ScansListResponse(scans=scans_list, total=total)


@router.get("/scans/{id}", response_model=ScanResponse)
async def get_scan(id: str, db: Session = Depends(get_db)):
    rec = db.query(ScanRecord).filter(ScanRecord.id == id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Scan record not found.")
    return build_scan_response_from_model(rec)


@router.get("/scans/{id}/report.pdf")
async def get_scan_pdf(id: str, db: Session = Depends(get_db)):
    rec = db.query(ScanRecord).filter(ScanRecord.id == id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Scan record not found.")
    
    scan_resp = build_scan_response_from_model(rec)
    pdf_data = generate_pdf_report(scan_resp.model_dump())
    
    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=medsure_report_{id}.pdf"}
    )


@router.delete("/scans", response_model=DeleteScansResponse)
async def delete_device_scans(
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
):
    if not x_device_token:
        raise HTTPException(status_code=400, detail="X-Device-Token header is required to delete device history.")
    
    scans = db.query(ScanRecord).filter(ScanRecord.device_token == x_device_token).all()
    deleted_count = len(scans)
    for s in scans:
        db.delete(s)
    db.commit()

    return DeleteScansResponse(
        message="Scan history for device deleted successfully.",
        deleted_count=deleted_count
    )
