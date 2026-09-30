import pytest
import datetime
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db import Base, get_db
from backend.app.models import ScanRecord, ReceivingSessionRecord, RegistryRecord, AlertRecord, BatchReportRecord
from backend.app.pipeline.gs1 import (
    calculate_gtin_check_digit, validate_gtin, parse_gs1_date,
    parse_code_payload, cross_check_printed_vs_code
)
from backend.app.pipeline.quality import evaluate_quality
from backend.app.pipeline.authenticity import (
    hash_salted, round_coordinates, check_alert_match
)
from backend.app.pipeline.rules import evaluate_decision_rules
from backend.app.schemas import (
    QualityResult, QualityMetrics, FieldsResult, CodeData, VisualResult, AuthenticityResult
)

# Setup shared in-memory database with StaticPool so all connections share state
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables on the shared test engine
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# 1. Test GTIN Check Digit & Validation
def test_gtin_check_digit():
    assert calculate_gtin_check_digit("08901234567890") == 0
    assert validate_gtin("08901234567890") is True
    assert validate_gtin("08901234567891") is False
    assert validate_gtin("12345") is False

# 2. Test GS1 Date Parsing & Robustness
def test_gs1_date_parsing():
    assert parse_gs1_date("270110") == "2027-01-10"
    assert parse_gs1_date("261231") == "2026-12-31"
    assert parse_gs1_date("invalid") is None
    assert parse_gs1_date("999999") is None

# 3. Test GS1 Payload Parsing & Bracket Format
def test_gs1_payload_parsing():
    payload = "(01)08901234567890(10)AMX2026B1(17)270110(21)SN9876543210"
    res = parse_code_payload(payload)
    assert res.gtin == "08901234567890"
    assert res.batch == "AMX2026B1"
    assert res.expiry == "2027-01-10"
    assert res.serial == "SN9876543210"

# 4. Test Custom MEDSURE Format Parsing
def test_medsure_custom_format():
    payload = "MEDSURE|08901234567890|AMX2026B1|270110|SN9876543210|Amoxicillin"
    res = parse_code_payload(payload)
    assert res.gtin == "08901234567890"
    assert res.batch == "AMX2026B1"
    assert res.type == "MEDSURE_FORMAT"

# 5. Test Quality Gate Evaluation
def test_quality_gate():
    blank = np.zeros((100, 100, 3), dtype=np.uint8)
    q_res = evaluate_quality(blank)
    assert q_res.passed is False

    good_img = np.random.randint(0, 255, (800, 800, 3), dtype=np.uint8)
    q_res2 = evaluate_quality(good_img)
    assert q_res2.metrics.resolution_min == 800

# 6. Test Decision Engine Truth Table & Safety Rules
def test_decision_truth_table():
    q_pass = QualityResult(passed=True, score=90, metrics=QualityMetrics(blur=200, brightness=120, glare_ratio=0, contrast=50, resolution_min=800))
    fields = FieldsResult(medicine_name="Amoxicillin", batch_number="B1", expiry_date="2027-01-10")
    code = CodeData(gtin="08901234567890", batch="B1", expiry="2027-01-10")
    vis = VisualResult(similarity_score=0.95, anomaly_detected=False)
    auth = AuthenticityResult()
    layers = ["quality", "ocr", "code", "visual", "authenticity"]

    verdict, score, reasons = evaluate_decision_rules(q_pass, fields, code, vis, auth, layers)
    assert verdict == "low_risk"

    q_fail = QualityResult(passed=False, score=20, metrics=QualityMetrics())
    verdict_q, _, _ = evaluate_decision_rules(q_fail, fields, code, vis, auth, layers)
    assert verdict_q == "insufficient_quality"

    code_mismatch = CodeData(gtin="08901234567890", batch="DIFFERENT_BATCH")
    code_mismatch.cross_check.batch_match = "mismatch"
    verdict_m, _, reasons_m = evaluate_decision_rules(q_pass, fields, code_mismatch, vis, auth, layers)
    assert verdict_m == "high_suspicion"

# 7. Test Batch-Only Alert Rejection & Exact Match
def test_alert_matching_rules():
    db = TestingSessionLocal()
    matched, details, match_type = check_alert_match(db, medicine_name=None, batch_number="AMX2026BAD", expiry_date="2027-01-10")
    assert matched is False

    matched_p, details_p, match_type_p = check_alert_match(db, medicine_name="Amoxicillin", batch_number="AMX2026BAD", expiry_date="2029-01-01")
    assert matched_p is True
    assert match_type_p == "partial"

    matched_e, details_e, match_type_e = check_alert_match(db, medicine_name="Amoxicillin", batch_number="AMX2026BAD", expiry_date="2027-01-10")
    assert matched_e is True
    assert match_type_e == "exact"
    db.close()

# 8. Test Privacy & Coordinate Rounding
def test_privacy_coordinate_rounding():
    r_lat, r_lng = round_coordinates(12.97345, 77.59123)
    assert r_lat == 12.97
    assert r_lng == 77.59
    assert hash_salted("SN123") == hash_salted("SN123")

# 9. Test Endpoint: Health Check
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

# 10. Test Endpoint: Manual Scan
def test_manual_scan_endpoint():
    payload = {
        "medicine_name": "Amoxicillin",
        "batch_number": "AMX2026B1",
        "expiry_date": "2027-01-10",
        "gtin": "08901234567890",
        "serial": "SN9876543210"
    }
    response = client.post("/scan/manual", json=payload, headers={"X-Device-Token": "dev_test_123"})
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] in ("low_risk", "needs_verification", "high_suspicion")

# 11. Test Endpoint: Demo Case
def test_demo_cases():
    resp = client.get("/demo/genuine")
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "low_risk"

    resp_alert = client.get("/demo/alert_match")
    assert resp_alert.status_code == 200

# 12. Test Endpoint: Receiving Session Flow & Acceptance
def test_receiving_session_flow():
    create_resp = client.post("/receiving/sessions", json={"supplier_name": "TestSupplier", "invoice_number": "INV-1001"})
    assert create_resp.status_code == 200
    sess_id = create_resp.json()["id"]

    sum_resp = client.get(f"/receiving/sessions/{sess_id}/summary")
    assert sum_resp.status_code == 200

    acc_resp = client.post(f"/receiving/sessions/{sess_id}/accept")
    assert acc_resp.status_code == 200
    assert acc_resp.json()["status"] == "accepted"

# 13. Test Endpoint: Delete Device Scans
def test_delete_scans():
    client.post("/scan/manual", json={"medicine_name": "Paracetamol"}, headers={"X-Device-Token": "del_dev_99"})
    
    del_resp = client.delete("/scans", headers={"X-Device-Token": "del_dev_99"})
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted_count"] >= 1
