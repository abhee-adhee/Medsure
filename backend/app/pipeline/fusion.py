import cv2
import datetime
import numpy as np
import uuid
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from backend.app.schemas import (
    ScanResponse, QualityResult, QualityMetrics, CodeData, FieldsResult, VisualResult,
    AuthenticityResult, SimulatedFlags, CodeCrossCheck
)
from backend.app.pipeline.quality import evaluate_quality
from backend.app.pipeline.ocr import perform_ocr
from backend.app.pipeline.fields import extract_fields_from_ocr
from backend.app.pipeline.codes import decode_codes
from backend.app.pipeline.gs1 import parse_code_payload, cross_check_printed_vs_code
from backend.app.pipeline.visual import evaluate_visual_similarity
from backend.app.pipeline.authenticity import evaluate_authenticity, round_coordinates, hash_salted
from backend.app.pipeline.rules import evaluate_decision_rules
from backend.app.pipeline.explain import generate_explanation

ALL_LAYERS = ["quality", "ocr", "code", "visual", "authenticity"]

def process_scan_image(
    db: Session,
    image_bytes: Optional[bytes] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    device_token: Optional[str] = None,
    manual_data: Optional[Dict[str, Any]] = None,
    ref_image: Optional[np.ndarray] = None
) -> Tuple[ScanResponse, str, str]:
    """
    Executes full multi-layer analysis pipeline and constructs standard ScanResponse.
    Returns (ScanResponse, serial_hash, batch_hash).
    """
    scan_id = f"scan_{uuid.uuid4().hex[:10]}"
    now_str = datetime.datetime.utcnow().isoformat() + "Z"
    r_lat, r_lng = round_coordinates(lat, lng)

    layers_executed = []

    # 1. Image Quality Layer
    if image_bytes is not None:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR) if len(image_bytes) > 0 else None
        if img is None:
            quality_res = QualityResult(
                passed=False,
                score=0.0,
                metrics=QualityMetrics(blur=0.0, brightness=0.0, glare_ratio=1.0, contrast=0.0, resolution_min=0),
                tips=["Corrupt or unreadable image file."]
            )
            layers_executed.append("quality")
        else:
            quality_res = evaluate_quality(img)
            layers_executed.append("quality")
    else:
        img = None
        # Manual entry mode
        quality_res = QualityResult(
            passed=True,
            score=100.0,
            metrics=QualityMetrics(blur=500.0, brightness=128.0, glare_ratio=0.0, contrast=60.0, resolution_min=1000),
            tips=[]
        )
        layers_executed.append("quality")

    # If quality failed, abort early per safety rules
    if not quality_res.passed:
        verdict_label, confidence, confidence_note, checked, not_checked = generate_explanation(
            verdict="insufficient_quality",
            reasons=quality_res.tips or ["Image quality insufficient."],
            layers_executed=layers_executed,
            all_possible_layers=ALL_LAYERS,
            quality_passed=False
        )
        response = ScanResponse(
            id=scan_id,
            timestamp=now_str,
            verdict="insufficient_quality",
            verdict_label=verdict_label,
            confidence=confidence,
            confidence_note=confidence_note,
            reasons=quality_res.tips or ["Image quality insufficient."],
            checked=checked,
            not_checked=not_checked,
            quality=quality_res,
            fields=FieldsResult(),
            code_data=CodeData(),
            visual=VisualResult(),
            authenticity=AuthenticityResult(),
            simulated_flags=SimulatedFlags()
        )
        return response, "", ""

    # 2. OCR & Field Extraction Layer
    if img is not None:
        ocr_res = perform_ocr(img)
        fields_res = extract_fields_from_ocr(ocr_res["text"])
        layers_executed.append("ocr")
    else:
        fields_res = FieldsResult()
        layers_executed.append("ocr")

    # Apply manual overrides if present
    if manual_data:
        if manual_data.get("medicine_name"):
            fields_res.medicine_name = manual_data["medicine_name"]
        if manual_data.get("batch_number"):
            fields_res.batch_number = manual_data["batch_number"]
        if manual_data.get("expiry_date"):
            fields_res.expiry_date = manual_data["expiry_date"]

    # 3. Barcode / Code Analysis Layer
    if img is not None:
        raw_code = decode_codes(img)
        code_data = parse_code_payload(raw_code.get("raw_payload"), raw_code.get("type"))
        layers_executed.append("code")
    else:
        code_data = CodeData()
        layers_executed.append("code")

    if manual_data:
        if manual_data.get("gtin"):
            code_data.gtin = manual_data["gtin"]
        if manual_data.get("serial"):
            code_data.serial = manual_data["serial"]

    # Cross-check printed fields vs code payload
    code_data.cross_check = cross_check_printed_vs_code(fields_res, code_data)

    # 4. Visual Analysis Layer
    if img is not None:
        visual_res = evaluate_visual_similarity(img, ref_image)
        layers_executed.append("visual")
    else:
        if manual_data and manual_data.get("visual_anomaly"):
            visual_res = VisualResult(similarity_score=0.55, anomaly_detected=True)
        else:
            visual_res = VisualResult(similarity_score=1.0, anomaly_detected=False)
        layers_executed.append("visual")

    # 5. Authenticity Layer
    auth_res = evaluate_authenticity(
        db=db,
        medicine_name=fields_res.medicine_name,
        batch_number=fields_res.batch_number or code_data.batch,
        expiry_date=fields_res.expiry_date or code_data.expiry,
        serial_number=code_data.serial,
        device_token=device_token,
        lat=r_lat,
        lng=r_lng
    )
    layers_executed.append("authenticity")

    # 6. Decision Rules Engine
    verdict, soft_score, reasons = evaluate_decision_rules(
        quality=quality_res,
        fields=fields_res,
        code_data=code_data,
        visual=visual_res,
        authenticity=auth_res,
        layers_executed=layers_executed
    )

    verdict_label, confidence, confidence_note, checked, not_checked = generate_explanation(
        verdict=verdict,
        reasons=reasons,
        layers_executed=layers_executed,
        all_possible_layers=ALL_LAYERS,
        quality_passed=True
    )

    s_hash = hash_salted(code_data.serial) if code_data.serial else ""
    b_hash = hash_salted(fields_res.batch_number or code_data.batch) if (fields_res.batch_number or code_data.batch) else ""

    response = ScanResponse(
        id=scan_id,
        timestamp=now_str,
        verdict=verdict,
        verdict_label=verdict_label,
        confidence=confidence,
        confidence_note=confidence_note,
        reasons=reasons,
        checked=checked,
        not_checked=not_checked,
        fields=fields_res,
        code_data=code_data,
        quality=quality_res,
        visual=visual_res,
        authenticity=auth_res,
        simulated_flags=SimulatedFlags()
    )

    return response, s_hash, b_hash
