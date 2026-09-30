import cv2
import numpy as np
from typing import Dict, Any, Tuple, List
from backend.app.schemas import QualityResult, QualityMetrics

def evaluate_quality(image: np.ndarray) -> QualityResult:
    """
    Evaluates image quality based on blur, brightness, glare, contrast, and resolution.
    Returns QualityResult schema.
    """
    if image is None or image.size == 0:
        return QualityResult(
            passed=False,
            score=0.0,
            metrics=QualityMetrics(blur=0.0, brightness=0.0, glare_ratio=1.0, contrast=0.0, resolution_min=0),
            tips=["Hold steady", "Move closer"]
        )

    h, w = image.shape[:2]
    resolution_min = min(h, w)

    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        brightness = float(np.mean(hsv[:, :, 2]))
    else:
        gray = image
        brightness = float(np.mean(gray))

    # Blur: Variance of Laplacian
    blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Glare ratio: pixels >= 250
    glare_pixels = np.sum(gray >= 250)
    glare_ratio = float(glare_pixels / (h * w))

    # Contrast: standard deviation of grayscale
    contrast_std = float(np.std(gray))

    tips: List[str] = []
    passed = True

    if resolution_min < 300:
        tips.append("Move closer")
        passed = False
    
    if blur_var < 80.0:
        tips.append("Hold steady")
        passed = False

    if glare_ratio > 0.15:
        tips.append("Reduce glare, tilt the pack")
        passed = False

    if brightness < 40.0:
        tips.append("More light needed")
        passed = False

    # Score out of 100
    res_score = min(1.0, resolution_min / 600.0) * 20.0
    blur_score = min(1.0, blur_var / 250.0) * 30.0
    bright_score = (1.0 - min(1.0, abs(brightness - 128.0) / 128.0)) * 20.0
    glare_score = (1.0 - min(1.0, glare_ratio / 0.10)) * 15.0
    contrast_score = min(1.0, contrast_std / 50.0) * 15.0

    score = round(float(res_score + blur_score + bright_score + glare_score + contrast_score), 1)
    if not passed:
        score = min(score, 45.0)

    metrics = QualityMetrics(
        blur=round(blur_var, 2),
        brightness=round(brightness, 2),
        glare_ratio=round(glare_ratio, 4),
        contrast=round(contrast_std, 2),
        resolution_min=resolution_min
    )

    return QualityResult(
        passed=passed,
        score=score,
        metrics=metrics,
        tips=tips
    )
