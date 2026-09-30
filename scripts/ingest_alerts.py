import sys
import json
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.db import SessionLocal
from backend.app.models import AlertRecord
from backend.app.config import DATA_DIR

def ingest_alerts():
    db = SessionLocal()
    try:
        alerts_file = DATA_DIR / "alerts.json"
        if not alerts_file.exists():
            print("alerts.json file not found.")
            return

        with open(alerts_file, "r", encoding="utf-8") as f:
            alerts = json.load(f)

        count = 0
        for a in alerts:
            existing = db.query(AlertRecord).filter(AlertRecord.id == a["id"]).first()
            if not existing:
                rec = AlertRecord(
                    id=a["id"],
                    medicine_name=a["medicine_name"],
                    batch_number=a["batch_number"],
                    expiry_date=a.get("expiry_date"),
                    risk_level=a.get("risk_level", "high_suspicion"),
                    description=a.get("description"),
                    issued_at=datetime.datetime.utcnow()
                )
                db.add(rec)
                count += 1

        db.commit()
        print(f"Ingested {count} new alert records into DB.")
    finally:
        db.close()

if __name__ == "__main__":
    ingest_alerts()
