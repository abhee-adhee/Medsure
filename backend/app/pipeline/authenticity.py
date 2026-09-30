import hmac
import hashlib
import datetime
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from backend.app.config import HMAC_SALT, DATA_DIR
from backend.app.models import RegistryRecord, AlertRecord, ScanRecord, BatchReportRecord
from backend.app.schemas import AuthenticityResult, AlertDetails

logger = logging.getLogger(__name__)

# Load static alerts.json if DB is empty
STATIC_ALERTS: List[Dict[str, Any]] = []

def load_static_alerts():
    global STATIC_ALERTS
    al_file = DATA_DIR / "alerts.json"
    if al_file.exists():
        try:
            with open(al_file, "r", encoding="utf-8") as f:
                STATIC_ALERTS = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load alerts.json: {e}")

load_static_alerts()

def hash_salted(value: str) -> str:
    """
    Computes HMAC-SHA256 salted hash for sensitive strings (serial / batch numbers).
    """
    if not value:
        return ""
    key = HMAC_SALT.encode("utf-8")
    msg = value.strip().upper().encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def round_coordinates(lat: Optional[float], lng: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    """
    Privacy requirement: Store district-level coordinates only; round lat/lng to 2 decimals.
    """
    r_lat = round(lat, 2) if lat is not None else None
    r_lng = round(lng, 2) if lng is not None else None
    return r_lat, r_lng

def check_alert_match(
    db: Session,
    medicine_name: Optional[str],
    batch_number: Optional[str],
    expiry_date: Optional[str]
) -> Tuple[bool, Optional[AlertDetails], str]:
    """
    Checks for exact or partial alert matches.
    IMPORTANT: A batch number alone must NEVER match an alert.
    Exact: name + batch + expiry -> exact match
    Partial: name + batch -> partial match
    """
    if not batch_number or not medicine_name:
        return False, None, "none"

    m_name = medicine_name.strip().upper()
    b_num = batch_number.strip().upper()

    # Query DB alerts first
    db_alerts = db.query(AlertRecord).all()
    alerts_to_check = []
    for a in db_alerts:
        alerts_to_check.append({
            "id": a.id,
            "medicine_name": a.medicine_name,
            "batch_number": a.batch_number,
            "expiry_date": a.expiry_date,
            "risk_level": a.risk_level,
            "description": a.description
        })
    # Add static alerts
    for sa in STATIC_ALERTS:
        if not any(a["id"] == sa["id"] for a in alerts_to_check):
            alerts_to_check.append(sa)

    exact_found = None
    partial_found = None

    for a in alerts_to_check:
        a_name = a["medicine_name"].strip().upper()
        a_batch = a["batch_number"].strip().upper()
        a_exp = a.get("expiry_date")

        if a_name in m_name or m_name in a_name:
            if a_batch == b_num:
                if expiry_date and a_exp and expiry_date.strip() == a_exp.strip():
                    exact_found = a
                    break
                else:
                    partial_found = a

    if exact_found:
        details = AlertDetails(
            id=exact_found["id"],
            medicine_name=exact_found["medicine_name"],
            batch_number=exact_found["batch_number"],
            expiry_date=exact_found.get("expiry_date"),
            risk_level=exact_found.get("risk_level", "high_suspicion"),
            description=exact_found.get("description", "Active drug alert matched.")
        )
        return True, details, "exact"

    if partial_found:
        details = AlertDetails(
            id=partial_found["id"],
            medicine_name=partial_found["medicine_name"],
            batch_number=partial_found["batch_number"],
            expiry_date=partial_found.get("expiry_date"),
            risk_level="needs_verification",
            description=partial_found.get("description", "Partial alert match found for medicine and batch.")
        )
        return True, details, "partial"

    return False, None, "none"

def evaluate_authenticity(
    db: Session,
    medicine_name: Optional[str],
    batch_number: Optional[str],
    expiry_date: Optional[str],
    serial_number: Optional[str],
    device_token: Optional[str],
    lat: Optional[float],
    lng: Optional[float]
) -> AuthenticityResult:
    """
    Evaluates serial status, alert matches, clone signals, impossible travel, and community status.
    """
    result = AuthenticityResult()

    # 1. Alert Matching
    alert_matched, alert_details, alert_type = check_alert_match(db, medicine_name, batch_number, expiry_date)
    result.alert_matched = alert_matched
    result.alert_details = alert_details

    # 2. Serial & Registry Analysis
    s_hash = hash_salted(serial_number) if serial_number else None
    if s_hash:
        reg = db.query(RegistryRecord).filter(RegistryRecord.serial_hash == s_hash).first()
        if reg:
            result.serial_status = reg.status
        else:
            result.serial_status = "registered"  # Default simulated registry assumption

        # Scan count & Clone Signals
        previous_scans = db.query(ScanRecord).filter(ScanRecord.serial_hash == s_hash).all()
        result.scan_count = len(previous_scans) + 1

        # Impossible Travel Detection
        if previous_scans and lat is not None and lng is not None:
            for past in previous_scans:
                if past.lat is not None and past.lng is not None:
                    # Distances > 5.0 lat/lng diff within 1 hour -> impossible travel
                    lat_diff = abs(past.lat - lat)
                    lng_diff = abs(past.lng - lng)
                    time_diff = (datetime.datetime.utcnow() - past.timestamp).total_seconds()
                    if (lat_diff > 3.0 or lng_diff > 3.0) and time_diff < 3600:
                        result.impossible_travel = True
                        break
    else:
        result.serial_status = "unverified"
        result.scan_count = 1

    # 3. Community Batch Status (Same-device exclusion, 5-device threshold)
    b_hash = hash_salted(batch_number) if batch_number else None
    if b_hash:
        reports = db.query(BatchReportRecord).filter(BatchReportRecord.batch_hash == b_hash).all()
        unique_devices = set(r.device_token for r in reports if r.device_token)
        if len(unique_devices) >= 5:
            result.community_status = "flagged"
        elif len(unique_devices) >= 2:
            result.community_status = "suspicious"
        else:
            result.community_status = "normal"

    return result
