from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import datetime

class QualityMetrics(BaseModel):
    blur: float = 0.0
    brightness: float = 0.0
    glare_ratio: float = 0.0
    contrast: float = 0.0
    resolution_min: int = 0

class QualityResult(BaseModel):
    passed: bool
    score: float
    metrics: QualityMetrics
    tips: List[str] = []

class CodeCrossCheck(BaseModel):
    name_match: str = "not_comparable"  # match, mismatch, not_comparable
    batch_match: str = "not_comparable"
    expiry_match: str = "not_comparable"
    overall: str = "not_comparable"

class CodeData(BaseModel):
    type: Optional[str] = None  # GS1_QR, DATA_MATRIX, LINEAR_BARCODE, UNKNOWN
    raw_payload: Optional[str] = None
    gtin: Optional[str] = None
    batch: Optional[str] = None
    expiry: Optional[str] = None
    serial: Optional[str] = None
    cross_check: CodeCrossCheck = Field(default_factory=CodeCrossCheck)

class FieldsResult(BaseModel):
    medicine_name: Optional[str] = None
    strength: Optional[str] = None
    form: Optional[str] = None
    batch_number: Optional[str] = None
    manufacture_date: Optional[str] = None
    expiry_date: Optional[str] = None
    manufacturer: Optional[str] = None

class VisualResult(BaseModel):
    similarity_score: float = 1.0
    anomaly_detected: bool = False
    heatmap_url: Optional[str] = None
    suspicious_boxes: List[List[float]] = []

class AlertDetails(BaseModel):
    id: str
    medicine_name: str
    batch_number: str
    expiry_date: Optional[str] = None
    risk_level: str
    description: Optional[str] = None

class AuthenticityResult(BaseModel):
    alert_matched: bool = False
    alert_details: Optional[AlertDetails] = None
    serial_status: str = "registered"  # registered, unverified, blocked, recalled, consumed
    scan_count: int = 1
    impossible_travel: bool = False
    community_status: str = "normal"  # normal, flagged, suspicious

class SimulatedFlags(BaseModel):
    registry_simulated: bool = True
    demo_case: bool = False
    alerts_simulated: bool = True

class ScanResponse(BaseModel):
    id: str
    timestamp: str
    verdict: str  # low_risk, needs_verification, high_suspicion, insufficient_quality
    verdict_label: str
    confidence: float
    confidence_note: str
    disclaimer: str = "Screening only. This does not confirm authenticity."
    reasons: List[str] = []
    checked: List[str] = []
    not_checked: List[str] = []
    fields: FieldsResult = Field(default_factory=FieldsResult)
    code_data: CodeData = Field(default_factory=CodeData)
    quality: QualityResult
    visual: VisualResult = Field(default_factory=VisualResult)
    authenticity: AuthenticityResult = Field(default_factory=AuthenticityResult)
    simulated_flags: SimulatedFlags = Field(default_factory=SimulatedFlags)

class ScansListResponse(BaseModel):
    scans: List[ScanResponse]
    total: int

class ManualScanRequest(BaseModel):
    medicine_name: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    gtin: Optional[str] = None
    serial: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class BatchReportRequest(BaseModel):
    batch_number: str
    medicine_name: Optional[str] = None
    reason: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class BatchReportResponse(BaseModel):
    message: str
    batch_hash: str
    status: str = "received"

class ReceivingSessionCreate(BaseModel):
    supplier_name: str
    invoice_number: str

class ReceivingSessionResponse(BaseModel):
    id: str
    supplier_name: str
    invoice_number: str
    created_at: str
    status: str
    total_scans: int = 0

class ReceivingScanResponse(BaseModel):
    session_id: str
    scan_id: str
    item_result: ScanResponse
    session_scan_index: int
    outlier_warning: bool = False

class ReceivingSessionSummary(BaseModel):
    id: str
    supplier_name: str
    invoice_number: str
    status: str
    total_scanned: int
    low_risk_count: int
    needs_verification_count: int
    high_suspicion_count: int
    insufficient_quality_count: int
    outliers: List[str] = []
    scans: List[ScanResponse] = []

class ReceivingSessionAcceptResponse(BaseModel):
    id: str
    status: str = "accepted"
    accepted_at: str
    registered_items_count: int

class SerialTrailScan(BaseModel):
    timestamp: str
    location: Optional[Dict[str, float]] = None
    verdict: str

class SerialTrailResponse(BaseModel):
    serial_hash: str
    status: str
    scan_count: int
    first_scanned: Optional[str] = None
    last_scanned: Optional[str] = None
    scans: List[SerialTrailScan] = []
    impossible_travel_detected: bool = False

class BatchStatusResponse(BaseModel):
    batch_hash: str
    batch_number: str
    total_scans: int
    suspicious_count: int
    community_reports_count: int
    unique_devices_reported: int
    status: str  # normal, suspicious, flagged
    notice: str = "A flagged batch does not mean every pack is fake."

class AlertResponse(BaseModel):
    id: str
    medicine_name: str
    batch_number: str
    expiry_date: Optional[str] = None
    risk_level: str
    description: Optional[str] = None
    issued_at: str

class AlertsListResponse(BaseModel):
    alerts: List[AlertResponse]

class StatsResponse(BaseModel):
    total_scans: int
    verdict_counts: Dict[str, int]
    active_alerts: int
    receiving_sessions: int

class DeleteScansResponse(BaseModel):
    message: str
    deleted_count: int

class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str
    version: str = "1.0.0"
