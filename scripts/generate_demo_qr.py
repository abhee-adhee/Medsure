import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.config import DATA_DIR

def generate_demo_qr():
    demo_dir = DATA_DIR / "demo_cases"
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    payloads = {
        "gs1_qr_genuine.txt": "(01)08901234567890(10)AMX2026B1(17)270110(21)SN9876543210",
        "gs1_qr_alert.txt": "(01)08901234567890(10)AMX2026BAD(17)270110(21)SN9876543210",
        "medsure_format.txt": "MEDSURE|08901234567890|AMX2026B1|270110|SN9876543210|Amoxicillin"
    }

    for name, payload in payloads.items():
        with open(demo_dir / name, "w", encoding="utf-8") as f:
            f.write(payload)
            
    print(f"Generated {len(payloads)} demo QR payload files in demo_cases.")

if __name__ == "__main__":
    generate_demo_qr()
