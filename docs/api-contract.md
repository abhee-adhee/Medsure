# MedSure Vision API Contract

Base URL: `http://localhost:8000`

## Headers
- `X-Device-Token`: (optional string) Device identifier for rate-limiting and user-specific history.

## Standard Error Response Format
HTTP 4xx / 5xx responses return JSON:
```json
{
  "detail": "Error message description",
  "error_code": "INVALID_INPUT",
  "status": 400
}
```

## Endpoints

### 1. `POST /scan`
- **Request**: Multipart Form Data (`image` file, optional `lat` float, optional `lng` float)
- **Response**:
```json
{
  "id": "scan_12345678",
  "timestamp": "2026-09-30T18:50:00Z",
  "verdict": "low_risk",
  "verdict_label": "Low Risk",
  "confidence": 85.0,
  "confidence_note": "All 3 core analysis layers evaluated with consistent results.",
  "disclaimer": "Screening only. This does not confirm authenticity.",
  "reasons": ["OCR fields match package database.", "Code payload cross-check passed."],
  "checked": ["quality", "ocr", "code", "visual", "authenticity"],
  "not_checked": [],
  "fields": {
    "medicine_name": "Amoxicillin",
    "strength": "500mg",
    "form": "Capsule",
    "batch_number": "AMX2026B1",
    "manufacture_date": "2025-01-10",
    "expiry_date": "2027-01-10",
    "manufacturer": "PharmaCorp"
  },
  "code_data": {
    "type": "GS1_QR",
    "raw_payload": "(01)08901234567890(10)AMX2026B1(17)270110(21)SN9876543210",
    "gtin": "08901234567890",
    "batch": "AMX2026B1",
    "expiry": "2027-01-10",
    "serial": "SN9876543210",
    "cross_check": {
      "name_match": "match",
      "batch_match": "match",
      "expiry_match": "match",
      "overall": "match"
    }
  },
  "quality": {
    "passed": true,
    "score": 90.0,
    "metrics": {
      "blur": 250.0,
      "brightness": 120.0,
      "glare_ratio": 0.005,
      "contrast": 50.0,
      "resolution_min": 800
    },
    "tips": []
  },
  "visual": {
    "similarity_score": 0.92,
    "anomaly_detected": false,
    "heatmap_url": null,
    "suspicious_boxes": []
  },
  "authenticity": {
    "alert_matched": false,
    "alert_details": null,
    "serial_status": "registered",
    "scan_count": 1,
    "impossible_travel": false,
    "community_status": "normal"
  },
  "simulated_flags": {
    "registry_simulated": true,
    "demo_case": false,
    "alerts_simulated": true
  }
}
```

### 2. `POST /scan/manual`
- **Request JSON**:
```json
{
  "medicine_name": "Amoxicillin",
  "batch_number": "AMX2026B1",
  "expiry_date": "2027-01-10",
  "gtin": "08901234567890",
  "serial": "SN9876543210",
  "lat": 12.97,
  "lng": 77.59
}
```
- **Response**: Same scan result object as `POST /scan`.

### 3. `GET /demo/{case_id}`
- **Response**: Scan result object preconfigured for the given case ID (`genuine`, `expiry_tampered`, `logo_shifted`, `clone_code`, `alert_match`, `blurry`).

### 4. `GET /scans`
- **Query**: `limit` (default 20), `offset` (default 0)
- **Header**: `X-Device-Token`
- **Response**:
```json
{
  "scans": [ /* list of scan summaries or full scan objects */ ],
  "total": 10
}
```

### 5. `GET /scans/{id}`
- **Response**: Full scan result object for scan ID.

### 6. `GET /scans/{id}/report.pdf`
- **Response**: `application/pdf` binary download.

### 7. `GET /alerts`
- **Response**:
```json
{
  "alerts": [
    {
      "id": "alert_001",
      "medicine_name": "Amoxicillin",
      "batch_number": "AMX2026B1",
      "expiry_date": "2027-01-10",
      "risk_level": "high_suspicion",
      "description": "Counterfeit batch reported in region.",
      "issued_at": "2026-08-01T00:00:00Z"
    }
  ]
}
```

### 8. `GET /serial/{hash}/trail`
- **Response**:
```json
{
  "serial_hash": "a1b2c3d4...",
  "status": "registered",
  "scan_count": 3,
  "first_scanned": "2026-09-01T10:00:00Z",
  "last_scanned": "2026-09-30T18:50:00Z",
  "scans": [
    {
      "timestamp": "2026-09-30T18:50:00Z",
      "location": {"lat": 12.97, "lng": 77.59},
      "verdict": "low_risk"
    }
  ],
  "impossible_travel_detected": false
}
```

### 9. `GET /batch/{hash}/status`
- **Response**:
```json
{
  "batch_hash": "e5f6g7h8...",
  "batch_number": "AMX2026B1",
  "total_scans": 15,
  "suspicious_count": 0,
  "community_reports_count": 0,
  "unique_devices_reported": 0,
  "status": "normal",
  "notice": "A flagged batch does not mean every pack is fake."
}
```

### 10. `POST /batch-report`
- **Request JSON**:
```json
{
  "batch_number": "AMX2026B1",
  "medicine_name": "Amoxicillin",
  "reason": "Suspicious packaging print quality",
  "lat": 12.97,
  "lng": 77.59
}
```
- **Response**:
```json
{
  "message": "Report submitted successfully.",
  "batch_hash": "e5f6g7h8...",
  "status": "received"
}
```

### 11. `POST /receiving/sessions`
- **Request JSON**:
```json
{
  "supplier_name": "MedDistributor Inc",
  "invoice_number": "INV-2026-99"
}
```
- **Response**:
```json
{
  "id": "rec_12345",
  "supplier_name": "MedDistributor Inc",
  "invoice_number": "INV-2026-99",
  "created_at": "2026-09-30T18:50:00Z",
  "status": "active",
  "total_scans": 0
}
```

### 12. `POST /receiving/sessions/{id}/scan`
- **Request**: Multipart Form Data (`image` file) OR JSON body for manual scan
- **Response**:
```json
{
  "session_id": "rec_12345",
  "scan_id": "scan_67890",
  "item_result": { /* scan object */ },
  "session_scan_index": 1,
  "outlier_warning": false
}
```

### 13. `GET /receiving/sessions/{id}/summary`
- **Response**:
```json
{
  "id": "rec_12345",
  "supplier_name": "MedDistributor Inc",
  "invoice_number": "INV-2026-99",
  "status": "active",
  "total_scanned": 5,
  "low_risk_count": 5,
  "needs_verification_count": 0,
  "high_suspicion_count": 0,
  "insufficient_quality_count": 0,
  "outliers": [],
  "scans": [ /* list of scans in session */ ]
}
```

### 14. `POST /receiving/sessions/{id}/accept`
- **Response**:
```json
{
  "id": "rec_12345",
  "status": "accepted",
  "accepted_at": "2026-09-30T19:00:00Z",
  "registered_items_count": 5
}
```

### 15. `GET /receiving/sessions/{id}/export`
- **Query**: `format` (`csv` or `pdf`, default `csv`)
- **Response**: File download stream (`text/csv` or `application/pdf`).

### 16. `GET /stats`
- **Response**:
```json
{
  "total_scans": 120,
  "verdict_counts": {
    "low_risk": 95,
    "needs_verification": 18,
    "high_suspicion": 5,
    "insufficient_quality": 2
  },
  "active_alerts": 2,
  "receiving_sessions": 4
}
```

### 17. `DELETE /scans`
- **Header**: `X-Device-Token`
- **Response**:
```json
{
  "message": "Scan history for device deleted successfully.",
  "deleted_count": 10
}
```

### 18. `GET /health`
- **Response**:
```json
{
  "status": "ok",
  "timestamp": "2026-09-30T18:50:00Z",
  "version": "1.0.0"
}
```
