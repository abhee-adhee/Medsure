import datetime
import uuid
from sqlalchemy import Column, String, Float, DateTime, Text, Integer, ForeignKey
from backend.app.db import Base

def generate_id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:12]}"

class ScanRecord(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=lambda: generate_id("scan_"))
    device_token = Column(String, index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    verdict = Column(String, nullable=False)
    verdict_label = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)
    confidence_note = Column(Text, nullable=True)
    disclaimer = Column(Text, default="Screening only. This does not confirm authenticity.")
    
    reasons_json = Column(Text, default="[]")
    checked_json = Column(Text, default="[]")
    not_checked_json = Column(Text, default="[]")
    fields_json = Column(Text, default="{}")
    code_data_json = Column(Text, default="{}")
    quality_json = Column(Text, default="{}")
    visual_json = Column(Text, default="{}")
    authenticity_json = Column(Text, default="{}")
    simulated_flags_json = Column(Text, default="{}")

    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    serial_hash = Column(String, index=True, nullable=True)
    batch_hash = Column(String, index=True, nullable=True)
    receiving_session_id = Column(String, ForeignKey("receiving_sessions.id"), nullable=True)


class BatchReportRecord(Base):
    __tablename__ = "batch_reports"

    id = Column(String, primary_key=True, default=lambda: generate_id("rep_"))
    device_token = Column(String, index=True, nullable=True)
    batch_number = Column(String, nullable=False)
    batch_hash = Column(String, index=True, nullable=False)
    medicine_name = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ReceivingSessionRecord(Base):
    __tablename__ = "receiving_sessions"

    id = Column(String, primary_key=True, default=lambda: generate_id("rec_"))
    supplier_name = Column(String, nullable=False)
    invoice_number = Column(String, nullable=False)
    status = Column(String, default="active")  # active, accepted
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)


class RegistryRecord(Base):
    __tablename__ = "registry"

    serial_hash = Column(String, primary_key=True)
    gtin = Column(String, nullable=True)
    batch_number = Column(String, nullable=True)
    expiry_date = Column(String, nullable=True)
    status = Column(String, default="registered")  # registered, recalled, consumed, blocked
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)


class AlertRecord(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: generate_id("alert_"))
    medicine_name = Column(String, nullable=False)
    batch_number = Column(String, nullable=False)
    expiry_date = Column(String, nullable=True)
    risk_level = Column(String, default="high_suspicion")
    description = Column(Text, nullable=True)
    issued_at = Column(DateTime, default=datetime.datetime.utcnow)
