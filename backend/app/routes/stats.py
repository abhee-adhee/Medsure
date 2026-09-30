import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import ScanRecord, AlertRecord, ReceivingSessionRecord
from backend.app.schemas import StatsResponse, HealthResponse
from backend.app.pipeline.authenticity import STATIC_ALERTS

router = APIRouter(tags=["Stats & Health"])

@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    scans = db.query(ScanRecord).all()
    total_scans = len(scans)

    counts = {
        "low_risk": 0,
        "needs_verification": 0,
        "high_suspicion": 0,
        "insufficient_quality": 0
    }
    for s in scans:
        if s.verdict in counts:
            counts[s.verdict] += 1

    db_alerts_count = db.query(AlertRecord).count()
    active_alerts = db_alerts_count + len(STATIC_ALERTS)

    receiving_count = db.query(ReceivingSessionRecord).count()

    return StatsResponse(
        total_scans=total_scans,
        verdict_counts=counts,
        active_alerts=active_alerts,
        receiving_sessions=receiving_count
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    now_str = datetime.datetime.utcnow().isoformat() + "Z"
    return HealthResponse(status="ok", timestamp=now_str, version="1.0.0")
