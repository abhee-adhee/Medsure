#!/bin/bash
set -e

echo "Initializing MedSure Vision Backend..."

# Initialize DB & seed data
python scripts/seed_db.py
python scripts/ingest_alerts.py
python scripts/generate_demo_qr.py
python scripts/make_tampered.py

echo "Starting FastAPI server on port 8000..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
