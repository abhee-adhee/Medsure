from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import ScanRecord, BatchReportRecord
from backend.app.schemas import BatchStatusResponse, BatchReportRequest, BatchReportResponse
from backend.app.pipeline.authenticity import hash_salted, round_coordinates

router = APIRouter(tags=["Batch"])

@router.get("/batch/{hash}/status", response_model=BatchStatusResponse)
async def get_batch_status(hash: str, db: Session = Depends(get_db)):
    scans = db.query(ScanRecord).filter(ScanRecord.batch_hash == hash).all()
    reports = db.query(BatchReportRecord).filter(BatchReportRecord.batch_hash == hash).all()
    
    total_scans = len(scans)
    suspicious_count = sum(1 for s in scans if s.verdict in ("high_suspicion", "needs_verification"))
    
    reports_count = len(reports)
    unique_devices = set(r.device_token for r in reports if r.device_token)
    
    batch_num = reports[0].batch_number if reports else (scans[0].batch_hash[:8] if scans else hash[:8])
    
    if len(unique_devices) >= 5:
        status = "flagged"
    elif len(unique_devices) >= 2 or suspicious_count >= 3:
        status = "suspicious"
    else:
        status = "normal"

    return BatchStatusResponse(
        batch_hash=hash,
        batch_number=batch_num,
        total_scans=total_scans,
        suspicious_count=suspicious_count,
        community_reports_count=reports_count,
        unique_devices_reported=len(unique_devices),
        status=status,
        notice="A flagged batch does not mean every pack is fake."
    )


@router.post("/batch-report", response_model=BatchReportResponse)
async def create_batch_report(
    req: BatchReportRequest,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
):
    b_hash = hash_salted(req.batch_number)
    r_lat, r_lng = round_coordinates(req.lat, req.lng)
    
    rec = BatchReportRecord(
        device_token=x_device_token,
        batch_number=req.batch_number,
        batch_hash=b_hash,
        medicine_name=req.medicine_name,
        reason=req.reason,
        lat=r_lat,
        lng=r_lng
    )
    db.add(rec)
    db.commit()

    return BatchReportResponse(
        message="Report submitted successfully.",
        batch_hash=b_hash,
        status="received"
    )
