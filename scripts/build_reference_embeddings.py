import sys
import os
import json
import cv2
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.config import DATA_DIR
from backend.app.pipeline.visual import get_image_embedding

def build_embeddings():
    ref_dir = DATA_DIR / "reference_images"
    ref_dir.mkdir(parents=True, exist_ok=True)
    
    embeddings = {}
    for img_path in ref_dir.glob("*.jpg"):
        img = cv2.imread(str(img_path))
        if img is not None:
            emb = get_image_embedding(img)
            if emb is not None:
                embeddings[img_path.name] = emb.tolist()
    
    out_file = ref_dir / "embeddings.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(embeddings, f, indent=2)
    print(f"Reference embeddings built: {len(embeddings)} files processed.")

if __name__ == "__main__":
    build_embeddings()
