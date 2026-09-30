import datetime
from typing import Tuple, List, Dict, Any
from backend.app.schemas import QualityResult, FieldsResult, CodeData, VisualResult, AuthenticityResult
from backend.app.pipeline.gs1 import validate_gtin

def evaluate_decision_rules(
    quality: QualityResult,
    fields: FieldsResult,
    code_data: CodeData,
    visual: VisualResult,
    authenticity: AuthenticityResult,
    layers_executed: List[str]
) -> Tuple[str, float, List[str]]:
    """
    Applies MedSure hard rules, soft scoring, and safety decision logic.
    Returns (verdict, score, reasons).
    """
    reasons: List[str] = []
    hard_high = False
    warning_triggered = False
    soft_score = 0.0

    # 1. Quality Check Gate
    if not quality.passed:
        return "insufficient_quality", 0.0, ["Quality gate failed. Please adjust lighting and camera angle."]

    # 2. Hard High Rules
    # Invalid GTIN
    if code_data.gtin:
        if not validate_gtin(code_data.gtin):
            hard_high = True
            reasons.append("Invalid GTIN check digit detected in code payload.")
    
    # Batch / Expiry mismatch
    if code_data.cross_check.batch_match == "mismatch":
        hard_high = True
        reasons.append("Printed batch number does not match barcode payload.")
    
    if code_data.cross_check.expiry_match == "mismatch":
        hard_high = True
        reasons.append("Printed expiry date does not match barcode payload.")

    # Exact alert match
    if authenticity.alert_matched and authenticity.alert_details and authenticity.alert_details.risk_level == "high_suspicion":
        hard_high = True
        reasons.append(f"Exact drug alert matched: {authenticity.alert_details.description}")

    # Blocked / Recalled registry status
    if authenticity.serial_status in ("blocked", "recalled"):
        hard_high = True
        reasons.append(f"Serial number is flagged as {authenticity.serial_status} in registry.")

    # Strong clone signal
    if authenticity.impossible_travel:
        hard_high = True
        reasons.append("Impossible travel detected: serial scanned in different locations simultaneously.")

    # 3. Warning Triggers (needs_verification)
    if authenticity.alert_matched and authenticity.alert_details and authenticity.alert_details.risk_level == "needs_verification":
        warning_triggered = True
        reasons.append(f"Partial drug alert matched for medicine/batch.")

    # Expiry check
    if fields.expiry_date:
        try:
            exp_d = datetime.datetime.strptime(fields.expiry_date, "%Y-%m-%d").date()
            if exp_d < datetime.date.today():
                warning_triggered = True
                reasons.append("Medicine package is past its printed expiry date.")
        except Exception:
            pass

    # Soft Scoring
    if visual.similarity_score < 0.75:
        soft_score += 20.0
        reasons.append("Packaging visual similarity is lower than reference baseline.")

    if visual.anomaly_detected:
        soft_score += 20.0
        reasons.append("Visual anomaly detected on package surface.")

    if not fields.medicine_name or not fields.batch_number:
        soft_score += 10.0
        reasons.append("Key packaging text fields could not be clearly identified.")

    if authenticity.scan_count > 3:
        soft_score += 15.0
        reasons.append(f"Unusual scan activity: serial scanned {authenticity.scan_count} times.")

    if code_data.type == "UNKNOWN" or not code_data.raw_payload:
        reasons.append("Barcode/QR code absent or unreadable.")

    # 4. Final Verdict Logic
    if hard_high or soft_score >= 51.0:
        verdict = "high_suspicion"
    elif warning_triggered or soft_score >= 21.0 or len(layers_executed) < 3:
        verdict = "needs_verification"
    else:
        # Mandatory Rule: Never return low_risk unless OCR + code + visual all ran.
        required_layers = {"ocr", "code", "visual"}
        if required_layers.issubset(set(layers_executed)):
            verdict = "low_risk"
            if not reasons:
                reasons.append("All verified layers match expected patterns.")
        else:
            verdict = "needs_verification"
            reasons.append("Insufficient layer verification to confirm low risk.")

    return verdict, soft_score, reasons
