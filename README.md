# MedSure Vision Backend

MedSure Vision is an AI-assisted medicine packaging screening & verification platform backend.

## Features
- **Multi-Layer Screening Engine**: Image Quality Gate, OCR Field Extraction (RapidFuzz), Barcode & GS1 Payload Parser, Visual Anomaly & Cosine Embedding Similarity, Authenticity & Serial Trail Verification.
- **Safety Verdict Bands**: `low_risk`, `needs_verification`, `high_suspicion`, `insufficient_quality`.
- **Privacy & Security**: HMAC-SHA256 salted hashing for serials/batches, 2-decimal rounded location coordinates, device history deletion.
- **Receiving Mode**: Batch receiving sessions, intra-lot outlier detection, registry state updates, PDF/CSV export.
- **ReportLab PDF Reports**: Professional downloadable verification reports.

## Quick Start
```bash
./run.sh
```
Or manually:
```bash
pip install -r requirements.txt
python scripts/seed_db.py
uvicorn backend.app.main:app --port 8000
```

## Running Tests
```bash
pytest tests/
```
