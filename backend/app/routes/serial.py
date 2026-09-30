from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import ScanRecord, RegistryRecord
from backend.app.schemas import SerialTrailResponse, SerialTrailScan

router = APIRouter(tags=["Serial"])

@router.get("/serial/{hash}/trail", response_model=SerialTrailResponse)
async def get_serial_trail(hash: str, db: Session = Depends(get_db)):
    scans = db.query(ScanRecord).filter(ScanRecord.serial_hash == hash).order_by(ScanRecord.timestamp.asc()).all()
    reg = db.query(RegistryRecord).filter(RegistryRecord.serial_hash == hash).first()
    
    status = reg.status if reg else ("registered" if scans else "unverified")
    scan_count = len(scans)
    
    first_scanned = scans[0].timestamp.isoformat() + "Z" if scans else None
    last_scanned = scans[-1].timestamp.isoformat() + "Z" if scans else None
    
    trail_scans: List[SerialTrailScan] = []
    impossible_travel = False
    
    for idx, s in enumerate(scans):
        loc = {"lat": s.lat, "lng": s.lng} if (s.lat is not None and s.lng is not None) else None
        trail_scans.append(
            SerialTrailScan(
                timestamp=s.timestamp.isoformat() + "Z",
                location=loc,
                verdict=s.verdict
            )
        )
        if idx > 0 and loc:
            prev = scans[idx-1]
            if prev.lat is not None and prev.lng is not None:
                lat_d = abs(prev.lat - s.lat)
                lng_d = abs(prev.lng - s.lng)
                t_d = (s.timestamp - prev.timestamp).total_seconds()
                if (lat_d > 3.0 or lng_d > 3.0) and t_d < 3600:
                    impossible_travel = True

    return SerialTrailResponse(
        serial_hash=hash,
        status=status,
        scan_count=scan_count,
        first_scanned=first_scanned,
        last_scanned=last_scanned,
        scans=trail_scans,
        impossible_travel_detected=impossible_travel
    )
