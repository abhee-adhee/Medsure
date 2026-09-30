import cv2
import numpy as np
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PYZBAR_AVAILABLE = False
PYLIBDMTX_AVAILABLE = False

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except Exception as e:
    logger.warning(f"pyzbar unavailable: {e}")

try:
    from pylibdmtx import pylibdmtx
    PYLIBDMTX_AVAILABLE = True
except Exception as e:
    logger.warning(f"pylibdmtx unavailable: {e}")

def decode_codes(image: np.ndarray) -> Dict[str, Any]:
    """
    Decodes QR, DataMatrix, or linear barcodes from input image.
    Uses pyzbar, pylibdmtx, and OpenCV QRDetector fallback.
    """
    if image is None or image.size == 0:
        return {"type": "UNKNOWN", "raw_payload": None}

    # 1. pyzbar (QR & Barcodes)
    if PYZBAR_AVAILABLE:
        try:
            decoded_objects = pyzbar.decode(image)
            for obj in decoded_objects:
                payload = obj.data.decode("utf-8", errors="ignore")
                if payload:
                    code_type = obj.type
                    if "QR" in code_type.upper():
                        return {"type": "GS1_QR" if payload.startswith("]") or "(01)" in payload else "QR", "raw_payload": payload}
                    return {"type": "LINEAR_BARCODE", "raw_payload": payload}
        except Exception as ex:
            logger.warning(f"pyzbar decode error: {ex}")

    # 2. pylibdmtx (DataMatrix)
    if PYLIBDMTX_AVAILABLE:
        try:
            dmtx_objs = pylibdmtx.decode(image)
            for obj in dmtx_objs:
                payload = obj.data.decode("utf-8", errors="ignore")
                if payload:
                    return {"type": "DATA_MATRIX", "raw_payload": payload}
        except Exception as ex:
            logger.warning(f"pylibdmtx decode error: {ex}")

    # 3. OpenCV QRCodeDetector fallback
    try:
        detector = cv2.QRCodeDetector()
        val, points, _ = detector.detectAndDecode(image)
        if val:
            return {"type": "GS1_QR" if val.startswith("]") or "(01)" in val else "QR", "raw_payload": val}
    except Exception as ex:
        logger.warning(f"OpenCV QRDetector fallback error: {ex}")

    return {"type": "UNKNOWN", "raw_payload": None}
