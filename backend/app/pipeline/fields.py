import re
import json
import datetime
import logging
from typing import Dict, Any, Optional, List
from rapidfuzz import process, fuzz
from backend.app.config import DATA_DIR
from backend.app.schemas import FieldsResult

logger = logging.getLogger(__name__)

# Load medicines reference database
MEDICINES_DB: List[Dict[str, Any]] = []

def load_medicines():
    global MEDICINES_DB
    med_file = DATA_DIR / "medicines.json"
    if med_file.exists():
        try:
            with open(med_file, "r", encoding="utf-8") as f:
                MEDICINES_DB = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load medicines.json: {e}")
            MEDICINES_DB = []

load_medicines()

def parse_date_safe(date_str: str) -> Optional[str]:
    """
    Exception-safe date parser converting various date strings to YYYY-MM-DD.
    """
    if not date_str:
        return None
    cleaned = date_str.strip()
    
    # Common formats: YYMMDD, YYYY-MM-DD, DD/MM/YYYY, MM/YYYY, EXP: 01/2027
    patterns = [
        (r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", "%Y-%m-%d"),
        (r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", "%d-%m-%Y"),
        (r"(\d{1,2})[-/.](\d{4})", "%m-%Y"),
        (r"^(\d{2})(\d{2})(\d{2})$", "%y%m%d")
    ]

    for pattern, fmt in patterns:
        m = re.search(pattern, cleaned)
        if m:
            try:
                if fmt == "%y%m%d":
                    d = datetime.datetime.strptime(m.group(0), "%y%m%d").date()
                    return d.strftime("%Y-%m-%d")
                elif fmt == "%m-%Y":
                    m_val, y_val = int(m.group(1)), int(m.group(2))
                    d = datetime.date(y_val, m_val, 1)
                    return d.strftime("%Y-%m-%d")
                elif fmt == "%d-%m-%Y":
                    d_val, m_val, y_val = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    d = datetime.date(y_val, m_val, d_val)
                    return d.strftime("%Y-%m-%d")
                elif fmt == "%Y-%m-%d":
                    y_val, m_val, d_val = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    d = datetime.date(y_val, m_val, d_val)
                    return d.strftime("%Y-%m-%d")
            except Exception:
                pass
    return None

def extract_fields_from_ocr(ocr_text: str) -> FieldsResult:
    """
    Extracts medicine name, strength, form, batch, dates, manufacturer from OCR text,
    matching against medicines database using RapidFuzz.
    """
    fields = FieldsResult()
    if not ocr_text:
        return fields

    text_upper = ocr_text.upper()

    # 1. Match Medicine Name via RapidFuzz
    known_names = [m["medicine_name"] for m in MEDICINES_DB]
    if known_names:
        match = process.extractOne(ocr_text, known_names, scorer=fuzz.partial_ratio)
        if match and match[1] >= 65:
            fields.medicine_name = match[0]
            # Find DB entry
            matched_med = next((m for m in MEDICINES_DB if m["medicine_name"] == match[0]), None)
            if matched_med:
                fields.strength = matched_med.get("strength")
                fields.form = matched_med.get("form")
                fields.manufacturer = matched_med.get("manufacturer")

    # Fallback strength / form extraction using regex
    if not fields.strength:
        str_m = re.search(r"(\d+\s*(mg|g|ml|mcg))", ocr_text, re.IGNORECASE)
        if str_m:
            fields.strength = str_m.group(1).replace(" ", "")

    if not fields.form:
        if "TABLET" in text_upper or "TAB" in text_upper:
            fields.form = "Tablet"
        elif "CAPSULE" in text_upper or "CAP" in text_upper:
            fields.form = "Capsule"
        elif "SYRUP" in text_upper:
            fields.form = "Syrup"
        elif "INJECTION" in text_upper:
            fields.form = "Injection"

    # 2. Extract Batch Number
    batch_m = re.search(r"(?:B\.?N\.?|BATCH|LOT)[:\s]*([A-Z0-9\-]+)", text_upper)
    if batch_m:
        fields.batch_number = batch_m.group(1)
    else:
        # Standalone alphanumeric batch candidate pattern
        b_cands = re.findall(r"\b([A-Z]{3}\d{4}[A-Z0-9]+)\b", text_upper)
        if b_cands:
            fields.batch_number = b_cands[0]

    # 3. Extract Expiry & Manufacture Dates
    exp_m = re.search(r"(?:EXP|EXPIRY|EXP\.DATE)[:\s]*([0-9\/\-\.]+)", text_upper)
    if exp_m:
        fields.expiry_date = parse_date_safe(exp_m.group(1))

    mfg_m = re.search(r"(?:MFG|MFD|MFG\.DATE)[:\s]*([0-9\/\-\.]+)", text_upper)
    if mfg_m:
        fields.manufacture_date = parse_date_safe(mfg_m.group(1))

    return fields
