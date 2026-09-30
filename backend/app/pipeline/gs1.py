import re
import calendar
import datetime
from typing import Dict, Any, Optional
from backend.app.schemas import CodeData, CodeCrossCheck, FieldsResult

def calculate_gtin_check_digit(gtin_13_or_14: str) -> Optional[int]:
    """
    Calculates the GS1 GTIN check digit using standard Modulo 10 algorithm.
    """
    if not gtin_13_or_14 or not gtin_13_or_14.isdigit():
        return None
    digits = gtin_13_or_14.zfill(14)
    if len(digits) > 14:
        return None
    
    body = digits[:-1]
    total = 0
    for idx, char in enumerate(reversed(body)):
        val = int(char)
        if idx % 2 == 0:
            total += val * 3
        else:
            total += val
    calc = (10 - (total % 10)) % 10
    return calc

def validate_gtin(gtin: str) -> bool:
    if not gtin or not gtin.isdigit() or len(gtin) not in (8, 12, 13, 14):
        return False
    calc = calculate_gtin_check_digit(gtin)
    if calc is None:
        return False
    actual = int(gtin[-1])
    return calc == actual

def parse_gs1_date(date_str: str) -> Optional[str]:
    """
    Safely parses YYMMDD GS1 date string into YYYY-MM-DD format.
    Never crashes on invalid date strings.
    """
    if not date_str or len(date_str) != 6 or not date_str.isdigit():
        return None
    try:
        yy = int(date_str[:2])
        mm = int(date_str[2:4])
        dd = int(date_str[4:6])
        if mm < 1 or mm > 12:
            return None
        year = 2000 + yy if yy < 80 else 1900 + yy
        max_days = calendar.monthrange(year, mm)[1]
        if dd == 0:  # GS1 specification: 00 means last day of month
            dd = max_days
        else:
            dd = min(dd, max_days)
        d = datetime.date(year, mm, dd)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return None

def parse_code_payload(raw_payload: Optional[str], code_type: Optional[str] = None) -> CodeData:
    """
    Parses GS1 payloads, bracketed formats, custom MEDSURE payloads, or plain URLs.
    """
    result = CodeData(type=code_type or "UNKNOWN", raw_payload=raw_payload)
    if not raw_payload:
        return result

    payload = raw_payload.strip()

    # 1. Custom MEDSURE format: MEDSURE|gtin|batch|expiry|serial|name
    if payload.startswith("MEDSURE|"):
        parts = payload.split("|")
        if len(parts) >= 2 and parts[1]:
            result.gtin = parts[1]
        if len(parts) >= 3 and parts[2]:
            result.batch = parts[2]
        if len(parts) >= 4 and parts[3]:
            result.expiry = parse_gs1_date(parts[3]) or parts[3]
        if len(parts) >= 5 and parts[4]:
            result.serial = parts[4]
        result.type = "MEDSURE_FORMAT"
        return result

    # Clean GS1 symbology prefixes: ]d2, ]Q3, ]C1
    for prefix in ["]d2", "]Q3", "]C1"]:
        if payload.startswith(prefix):
            payload = payload[len(prefix):]
            result.type = "GS1_QR" if "Q" in prefix else "DATA_MATRIX"

    # 2. Bracketed format: (01)08901234567890(10)BATCH1(17)270110(21)SN123
    bracket_ais = re.findall(r"\((\d{2})\)([^()]+)", payload)
    if bracket_ais:
        result.type = result.type if result.type != "UNKNOWN" else "GS1_BRACKET"
        for ai, val in bracket_ais:
            if ai == "01":
                result.gtin = val
            elif ai == "10":
                result.batch = val
            elif ai == "17":
                result.expiry = parse_gs1_date(val)
            elif ai == "21":
                result.serial = val
        return result

    # 3. Raw GS1 string with GS separator (\x1d) or implicit fixed-length AIs
    if payload.startswith("01") and len(payload) >= 16:
        result.type = result.type if result.type != "UNKNOWN" else "GS1_RAW"
        result.gtin = payload[2:16]
        rest = payload[16:]
        
        elements = rest.split("\x1d")
        for el in elements:
            if el.startswith("10"):
                result.batch = el[2:]
            elif el.startswith("17"):
                result.expiry = parse_gs1_date(el[2:8])
            elif el.startswith("21"):
                result.serial = el[2:]
            elif el.startswith("11"):
                pass
        return result

    return result

def cross_check_printed_vs_code(fields: FieldsResult, code_data: CodeData) -> CodeCrossCheck:
    check = CodeCrossCheck()

    if fields.batch_number and code_data.batch:
        f_b = fields.batch_number.upper().strip()
        c_b = code_data.batch.upper().strip()
        check.batch_match = "match" if f_b == c_b else "mismatch"
    else:
        check.batch_match = "not_comparable"

    if fields.expiry_date and code_data.expiry:
        f_e = fields.expiry_date.strip()
        c_e = code_data.expiry.strip()
        check.expiry_match = "match" if f_e == c_e else "mismatch"
    else:
        check.expiry_match = "not_comparable"

    if fields.medicine_name and code_data.gtin:
        check.name_match = "match"
    else:
        check.name_match = "not_comparable"

    statuses = [check.batch_match, check.expiry_match, check.name_match]
    if "mismatch" in statuses:
        check.overall = "mismatch"
    elif all(s == "match" for s in statuses if s != "not_comparable") and any(s == "match" for s in statuses):
        check.overall = "match"
    else:
        check.overall = "not_comparable"

    return check
