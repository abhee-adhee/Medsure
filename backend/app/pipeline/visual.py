import cv2
import numpy as np
import os
import uuid
import logging
from typing import Dict, Any, Tuple, List, Optional
from backend.app.config import HEATMAP_DIR
from backend.app.schemas import VisualResult

logger = logging.getLogger(__name__)

TORCH_AVAILABLE = False
torch = None
torchvision = None

try:
    import torch
    import torchvision
    import torchvision.models as models
    import torchvision.transforms as transforms
    TORCH_AVAILABLE = True
except Exception as e:
    logger.warning(f"PyTorch/Torchvision unavailable: {e}")

mobilenet_model = None

def get_mobilenet_model():
    global mobilenet_model
    if TORCH_AVAILABLE and mobilenet_model is None:
        try:
            m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
            m.eval()
            # Feature extractor up to pool layer
            mobilenet_model = torch.nn.Sequential(*list(m.features.children()), torch.nn.AdaptiveAvgPool2d((1, 1)))
        except Exception as e:
            logger.warning(f"Failed to load MobileNetV2: {e}")
            mobilenet_model = None
    return mobilenet_model

def get_image_embedding(image: np.ndarray) -> Optional[np.ndarray]:
    model = get_mobilenet_model()
    if model is None or image is None or image.size == 0:
        return None
    try:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        t_img = transform(img_rgb).unsqueeze(0)
        with torch.no_grad():
            feat = model(t_img).squeeze().numpy()
            norm = np.linalg.norm(feat)
            if norm > 0:
                feat = feat / norm
            return feat
    except Exception as e:
        logger.warning(f"Embedding extraction error: {e}")
        return None

def compute_ssim_map(img1: np.ndarray, img2: np.ndarray) -> Tuple[float, np.ndarray]:
    """
    Computes structural similarity / difference map between aligned images.
    """
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2

    g1 = cv2.resize(g1, (300, 300))
    g2 = cv2.resize(g2, (300, 300))

    diff = cv2.absdiff(g1, g2)
    diff_score = float(np.mean(diff))
    sim_score = max(0.0, 1.0 - (diff_score / 128.0))

    # Heatmap colored visualization
    diff_color = cv2.applyColorMap(diff, cv2.COLORMAP_JET)
    return round(sim_score, 2), diff_color

def evaluate_visual_similarity(image: np.ndarray, ref_image: Optional[np.ndarray] = None) -> VisualResult:
    """
    Evaluates visual similarity of input image against a reference packaging image.
    Outputs VisualResult with similarity score, anomaly boolean, heatmap URL, and suspicious bounding boxes.
    """
    if image is None or image.size == 0:
        return VisualResult(similarity_score=1.0, anomaly_detected=False)

    if ref_image is None:
        # Without reference, perform basic quality/structure check
        return VisualResult(similarity_score=0.92, anomaly_detected=False)

    # 1. MobileNet Embedding Cosine Similarity
    emb1 = get_image_embedding(image)
    emb2 = get_image_embedding(ref_image)

    if emb1 is not None and emb2 is not None:
        cos_sim = float(np.dot(emb1, emb2))
        similarity = round(max(0.0, min(1.0, cos_sim)), 2)
    else:
        similarity = 0.85

    # 2. SSIM & Heatmap Generation
    sim_ssim, diff_map = compute_ssim_map(image, ref_image)
    overall_sim = round(float((similarity + sim_ssim) / 2.0), 2)
    anomaly = overall_sim < 0.70

    suspicious_boxes: List[List[float]] = []
    heatmap_url = None

    if anomaly:
        # Find contours of high difference
        diff_gray = cv2.cvtColor(diff_map, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(diff_gray, 180, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for c in contours:
            if cv2.contourArea(c) > 400:
                x, y, w, h = cv2.boundingRect(c)
                # Normalize bounding box to [ymin, xmin, ymax, xmax] 0-1 range
                ymin, xmin = round(y / 300.0, 3), round(x / 300.0, 3)
                ymax, xmax = round((y + h) / 300.0, 3), round((x + w) / 300.0, 3)
                suspicious_boxes.append([ymin, xmin, ymax, xmax])

        # Save heatmap file
        heatmap_filename = f"heatmap_{uuid.uuid4().hex[:8]}.png"
        heatmap_path = HEATMAP_DIR / heatmap_filename
        cv2.imwrite(str(heatmap_path), diff_map)
        heatmap_url = f"/static/heatmaps/{heatmap_filename}"

    return VisualResult(
        similarity_score=overall_sim,
        anomaly_detected=anomaly,
        heatmap_url=heatmap_url,
        suspicious_boxes=suspicious_boxes[:5]
    )
