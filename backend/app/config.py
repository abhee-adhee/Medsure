import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "backend" / "static"
HEATMAP_DIR = STATIC_DIR / "heatmaps"
DB_PATH = BASE_DIR / "medsure.db"

# Environment configuration
HMAC_SALT = os.environ.get("SALT", "medsure_default_secret_salt_2026")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Ensure directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "reference_images").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "demo_cases").mkdir(parents=True, exist_ok=True)
