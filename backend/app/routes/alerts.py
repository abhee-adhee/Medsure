import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import AlertRecord
from backend.app.schemas import AlertsListResponse, AlertResponse
from backend.app.pipeline.authenticity import STATIC_ALERTS

router = APIRouter(tags=["Alerts"])

@router.get("/alerts", response_model=AlertsListResponse)
async def list_alerts(db: Session = Depends(get_db)):
    db_alerts = db.query(AlertRecord).all()
    results = []
    
    for a in db_alerts:
        results.append(
            AlertResponse(
                id=a.id,
                medicine_name=a.medicine_name,
                batch_number=a.batch_number,
                expiry_date=a.expiry_date,
                risk_level=a.risk_level,
                description=a.description,
                issued_at=a.issued_at.isoformat() + "Z"
            )
        )

    for sa in STATIC_ALERTS:
        if not any(r.id == sa["id"] for r in results):
            results.append(
                AlertResponse(
                    id=sa["id"],
                    medicine_name=sa["medicine_name"],
                    batch_number=sa["batch_number"],
                    expiry_date=sa.get("expiry_date"),
                    risk_level=sa.get("risk_level", "high_suspicion"),
                    description=sa.get("description"),
                    issued_at=sa.get("issued_at", "2026-08-01T00:00:00Z")
                )
            )

    return AlertsListResponse(alerts=results)
