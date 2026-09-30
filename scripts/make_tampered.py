import sys
import cv2
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.config import DATA_DIR

def make_tampered_samples():
    demo_dir = DATA_DIR / "demo_cases"
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    # Create synthetic baseline packaging image (explicitly synthetic)
    img = np.ones((400, 600, 3), dtype=np.uint8) * 240
    cv2.putText(img, "SYNTHETIC TEST SAMPLE - MedSure", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 100, 0), 2)
    cv2.putText(img, "Amoxicillin 500mg", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(img, "Batch: AMX2026B1", (30, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(img, "EXP: 2027-01-10", (30, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)

    cv2.imwrite(str(demo_dir / "synthetic_genuine_pack.png"), img)

    # Tampered image (shifted logo / text)
    t_img = img.copy()
    cv2.rectangle(t_img, (30, 100), (450, 140), (240, 240, 240), -1)
    cv2.putText(t_img, "Amoxicillin 500mg", (60, 135), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 180), 2)
    cv2.imwrite(str(demo_dir / "synthetic_tampered_pack.png"), t_img)

    print("Synthetic packaging samples created.")

if __name__ == "__main__":
    make_tampered_samples()
