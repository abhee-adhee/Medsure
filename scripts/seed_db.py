import sys
import json
import datetime
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.db import engine, SessionLocal, Base
from backend.app.models import AlertRecord, RegistryRecord, ScanRecord, BatchReportRecord, ReceivingSessionRecord
from backend.app.config import DATA_DIR
from backend.app.pipeline.authenticity import hash_salted

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed Alerts
        alerts_file = DATA_DIR / "alerts.json"
        if alerts_file.exists():
            with open(alerts_file, "r", encoding="utf-8") as f:
                alerts_data = json.load(f)
            for a in alerts_data:
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

        # Seed Registry Records
        sample_serials = [
            ("08901234567890", "AMX2026B1", "2027-01-10", "SN9876543210", "registered"),
            ("08909876543210", "PCM2026A1", "2026-12-31", "SN1122334455", "registered"),
            ("08905555444333", "MET2025C3", "2026-11-15", "SN9988776655", "recalled"),
            ("08901111222333", "AZT2026D1", "2027-06-30", "SNBLOCKED001", "blocked")
        ]

        for gtin, batch, exp, serial, status in sample_serials:
            s_hash = hash_salted(serial)
            existing = db.query(RegistryRecord).filter(RegistryRecord.serial_hash == s_hash).first()
            if not existing:
                reg = RegistryRecord(
                    serial_hash=s_hash,
                    gtin=gtin,
                    batch_number=batch,
                    expiry_date=exp,
                    status=status
                )
                db.add(reg)

        db.commit()
        print("Database seeded successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
