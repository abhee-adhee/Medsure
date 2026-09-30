import json
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Header, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import ScanRecord
from backend.app.schemas import ScanResponse, ManualScanRequest
from backend.app.pipeline.fusion import process_scan_image

router = APIRouter(tags=["Scan"])

@router.post("/scan", response_model=ScanResponse)
async def scan_image(
    image: UploadFile = File(...),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
):
    image_bytes = await image.read()
    response, serial_hash, batch_hash = process_scan_image(
        db=db,
        image_bytes=image_bytes,
        lat=lat,
        lng=lng,
        device_token=x_device_token
    )

    # Persist Scan Record
    rec = ScanRecord(
        id=response.id,
        device_token=x_device_token,
        verdict=response.verdict,
        verdict_label=response.verdict_label,
        confidence=response.confidence,
        confidence_note=response.confidence_note,
        disclaimer=response.disclaimer,
        reasons_json=json.dumps(response.reasons),
        checked_json=json.dumps(response.checked),
        not_checked_json=json.dumps(response.not_checked),
        fields_json=response.fields.model_dump_json(),
        code_data_json=response.code_data.model_dump_json(),
        quality_json=response.quality.model_dump_json(),
        visual_json=response.visual.model_dump_json(),
        authenticity_json=response.authenticity.model_dump_json(),
        simulated_flags_json=response.simulated_flags.model_dump_json(),
        lat=response.authenticity.impossible_travel and lat or lat,
        lng=lng,
        serial_hash=serial_hash,
        batch_hash=batch_hash
    )
    db.add(rec)
    db.commit()

    return response


@router.post("/scan/manual", response_model=ScanResponse)
async def scan_manual(
    req: ManualScanRequest,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
):
    manual_dict = req.model_dump(exclude_none=True)
    response, serial_hash, batch_hash = process_scan_image(
        db=db,
        image_bytes=None,
        lat=req.lat,
        lng=req.lng,
        device_token=x_device_token,
        manual_data=manual_dict
    )

    rec = ScanRecord(
        id=response.id,
        device_token=x_device_token,
        verdict=response.verdict,
        verdict_label=response.verdict_label,
        confidence=response.confidence,
        confidence_note=response.confidence_note,
        disclaimer=response.disclaimer,
        reasons_json=json.dumps(response.reasons),
        checked_json=json.dumps(response.checked),
        not_checked_json=json.dumps(response.not_checked),
        fields_json=response.fields.model_dump_json(),
        code_data_json=response.code_data.model_dump_json(),
        quality_json=response.quality.model_dump_json(),
        visual_json=response.visual.model_dump_json(),
        authenticity_json=response.authenticity.model_dump_json(),
        simulated_flags_json=response.simulated_flags.model_dump_json(),
        lat=req.lat,
        lng=req.lng,
        serial_hash=serial_hash,
        batch_hash=batch_hash
    )
    db.add(rec)
    db.commit()

    return response


@router.get("/demo/{case_id}", response_model=ScanResponse)
async def get_demo_case(case_id: str, db: Session = Depends(get_db)):
    """
    Returns preconfigured demo cases: genuine, expiry_tampered, logo_shifted, clone_code, alert_match, blurry
    """
    case_key = case_id.lower().strip()

    if case_key == "genuine":
        resp, _, _ = process_scan_image(
            db=db,
            image_bytes=None,
            manual_data={
                "medicine_name": "Amoxicillin",
                "batch_number": "AMX2026B1",
                "expiry_date": "2027-01-10",
                "gtin": "08901234567890",
                "serial": "SN9876543210"
            }
        )
        resp.simulated_flags.demo_case = True
        return resp

    elif case_key == "expiry_tampered":
        resp, _, _ = process_scan_image(
            db=db,
            image_bytes=None,
            manual_data={
                "medicine_name": "Amoxicillin",
                "batch_number": "AMX2026B1",
                "expiry_date": "2024-01-10",  # Expired
                "gtin": "08901234567890",
                "serial": "SN9876543210"
            }
        )
        resp.simulated_flags.demo_case = True
        return resp

    elif case_key == "logo_shifted":
        resp, _, _ = process_scan_image(
            db=db,
            image_bytes=None,
            manual_data={
                "medicine_name": "Amoxicillin",
                "batch_number": "AMX2026B1",
                "expiry_date": "2027-01-10",
                "gtin": "08901234567890"
            }
        )
        resp.visual.similarity_score = 0.55
        resp.visual.anomaly_detected = True
        resp.verdict = "needs_verification"
        resp.verdict_label = "Needs Verification"
        resp.reasons.append("Visual anomaly detected: packaging logo alignment shifted.")
        resp.simulated_flags.demo_case = True
        return resp

    elif case_key == "clone_code":
        resp, _, _ = process_scan_image(
            db=db,
            image_bytes=None,
            manual_data={
                "medicine_name": "Amoxicillin",
                "batch_number": "AMX2026B1",
                "expiry_date": "2027-01-10",
                "gtin": "08901234567890",
                "serial": "SNCLONE999"
            }
        )
        resp.authenticity.scan_count = 15
        resp.authenticity.impossible_travel = True
        resp.verdict = "high_suspicion"
        resp.verdict_label = "High Suspicion"
        resp.reasons.append("Clone code signal: identical serial scanned 15 times across distant locations.")
        resp.simulated_flags.demo_case = True
        return resp

    elif case_key == "alert_match":
        resp, _, _ = process_scan_image(
            db=db,
            image_bytes=None,
            manual_data={
                "medicine_name": "Amoxicillin",
                "batch_number": "AMX2026BAD",
                "expiry_date": "2027-01-10",
                "gtin": "08901234567890"
            }
        )
        resp.simulated_flags.demo_case = True
        return resp

    elif case_key == "blurry":
        resp, _, _ = process_scan_image(db=db, image_bytes=b"invalid_small_bytes")
        resp.simulated_flags.demo_case = True
        return resp

    else:
        raise HTTPException(status_code=404, detail=f"Demo case '{case_id}' not found.")
