import cv2
import numpy as np
import logging
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

# Try importing EasyOCR and pytesseract
EASYOCR_AVAILABLE = False
PYTESSERACT_AVAILABLE = False

try:
    import easyocr
    easyocr_reader = easyocr.Reader(['en'], gpu=False)
    EASYOCR_AVAILABLE = True
except Exception as e:
    logger.warning(f"EasyOCR unavailable: {e}")
    easyocr_reader = None

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except Exception as e:
    logger.warning(f"pytesseract unavailable: {e}")

def preprocess_image(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Applies CLAHE, adaptive thresholding, and deskewing to optimize OCR.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Adaptive Threshold
    adaptive = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Deskew estimation
    coords = np.column_stack(np.where(adaptive > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 0.5 and abs(angle) < 45:
            (h, w) = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            enhanced = cv2.warpAffine(enhanced, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            adaptive = cv2.warpAffine(adaptive, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return enhanced, adaptive

def perform_ocr(image: np.ndarray) -> Dict[str, Any]:
    """
    Runs OCR pipeline returning merged text, raw outputs, and confidence metric.
    """
    if image is None or image.size == 0:
        return {"text": "", "confidence": 0.0, "disagreement": False, "sources": []}

    enhanced, adaptive = preprocess_image(image)
    texts_found: List[str] = []
    sources: List[str] = []
    confs: List[float] = []

    # 1. EasyOCR
    if EASYOCR_AVAILABLE and easyocr_reader is not None:
        try:
            results = easyocr_reader.readtext(enhanced)
            easy_texts = [res[1] for res in results if res[2] > 0.2]
            if easy_texts:
                texts_found.append(" ".join(easy_texts))
                avg_c = float(np.mean([res[2] for res in results])) if results else 0.5
                confs.append(avg_c)
                sources.append("easyocr")
        except Exception as ex:
            logger.warning(f"EasyOCR run failed: {ex}")

    # 2. PyTesseract
    if PYTESSERACT_AVAILABLE:
        try:
            tess_text = pytesseract.image_to_string(enhanced, config="--psm 6")
            cleaned_tess = tess_text.strip()
            if cleaned_tess:
                texts_found.append(cleaned_tess)
                confs.append(0.7)
                sources.append("tesseract")
        except Exception as ex:
            logger.warning(f"Tesseract run failed: {ex}")

    if not texts_found:
        # Fallback text extraction using simple contours/heuristics if OCR engines fail
        merged_text = ""
        final_conf = 0.0
        disagreement = False
    else:
        merged_text = " \n ".join(texts_found)
        final_conf = float(np.mean(confs)) if confs else 0.5
        disagreement = len(texts_found) > 1 and abs(len(texts_found[0]) - len(texts_found[1])) > 15

    return {
        "text": merged_text,
        "confidence": round(final_conf, 2),
        "disagreement": disagreement,
        "sources": sources
    }
