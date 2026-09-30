import io
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_pdf_report(scan_data: dict) -> bytes:
    """
    Generates PDF report bytes for a given scan response dictionary using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1E3A8A'))
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#1E40AF'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14)
    alert_style = ParagraphStyle('AlertStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#991B1B'))

    # Header
    story.append(Paragraph("MedSure Vision - Verification Screening Report", title_style))
    story.append(Spacer(1, 10))

    # Meta Table
    scan_id = scan_data.get("id", "N/A")
    ts = scan_data.get("timestamp", "N/A")
    verdict_label = scan_data.get("verdict_label", scan_data.get("verdict", "N/A"))
    
    meta_data = [
        [Paragraph("<b>Scan ID:</b>", body_style), Paragraph(scan_id, body_style)],
        [Paragraph("<b>Timestamp:</b>", body_style), Paragraph(ts, body_style)],
        [Paragraph("<b>Verdict:</b>", body_style), Paragraph(f"<b>{verdict_label}</b>", body_style)],
        [Paragraph("<b>Confidence:</b>", body_style), Paragraph(f"{scan_data.get('confidence', 0)}%", body_style)]
    ]
    meta_table = Table(meta_data, colWidths=[100, 400])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB'))
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Fields Table
    story.append(Paragraph("Extracted Product Information", heading_style))
    story.append(Spacer(1, 5))
    fields = scan_data.get("fields", {})
    field_rows = [
        [Paragraph("<b>Field</b>", body_style), Paragraph("<b>Value</b>", body_style)],
        [Paragraph("Medicine Name", body_style), Paragraph(fields.get("medicine_name") or "Unverified", body_style)],
        [Paragraph("Strength / Form", body_style), Paragraph(f"{fields.get('strength') or ''} {fields.get('form') or ''}".strip() or "N/A", body_style)],
        [Paragraph("Batch Number", body_style), Paragraph(fields.get("batch_number") or "Unverified", body_style)],
        [Paragraph("Expiry Date", body_style), Paragraph(fields.get("expiry_date") or "Unverified", body_style)],
        [Paragraph("Manufacturer", body_style), Paragraph(fields.get("manufacturer") or "N/A", body_style)]
    ]
    fields_table = Table(field_rows, colWidths=[150, 350])
    fields_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#DBEAFE')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1'))
    ]))
    story.append(fields_table)
    story.append(Spacer(1, 15))

    # Barcode Cross Check
    story.append(Paragraph("Code Payload Cross-Check", heading_style))
    story.append(Spacer(1, 5))
    code_data = scan_data.get("code_data", {})
    cross = code_data.get("cross_check", {})
    code_rows = [
        [Paragraph("<b>Check Point</b>", body_style), Paragraph("<b>Status</b>", body_style)],
        [Paragraph("Code Type", body_style), Paragraph(code_data.get("type") or "N/A", body_style)],
        [Paragraph("GTIN Payload", body_style), Paragraph(code_data.get("gtin") or "N/A", body_style)],
        [Paragraph("Batch Cross-Check", body_style), Paragraph(cross.get("batch_match", "not_comparable"), body_style)],
        [Paragraph("Expiry Cross-Check", body_style), Paragraph(cross.get("expiry_match", "not_comparable"), body_style)]
    ]
    code_table = Table(code_rows, colWidths=[150, 350])
    code_table.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0'))
    ]))
    story.append(code_table)
    story.append(Spacer(1, 15))

    # Reasons & Evidence
    story.append(Paragraph("Findings & Reasons", heading_style))
    story.append(Spacer(1, 5))
    reasons = scan_data.get("reasons", [])
    if not reasons:
        story.append(Paragraph("No risk factors identified.", body_style))
    else:
        for r in reasons:
            story.append(Paragraph(f"• {r}", alert_style if "mismatch" in r.lower() or "alert" in r.lower() or "invalid" in r.lower() else body_style))
    story.append(Spacer(1, 10))

    # Checked / Not Checked
    checked_str = ", ".join(scan_data.get("checked", []))
    not_checked_str = ", ".join(scan_data.get("not_checked", [])) or "None"
    story.append(Paragraph(f"<b>Layers Checked:</b> {checked_str}", body_style))
    story.append(Paragraph(f"<b>Layers Not Checked:</b> {not_checked_str}", body_style))
    story.append(Spacer(1, 15))

    # Heatmap Image if present
    visual = scan_data.get("visual", {})
    heatmap_url = visual.get("heatmap_url")
    if heatmap_url and heatmap_url.startswith("/static/"):
        rel_path = heatmap_url.replace("/static/", "backend/static/")
        full_hpath = Path(rel_path)
        if full_hpath.exists():
            story.append(Paragraph("Visual Anomaly Heatmap", heading_style))
            story.append(Spacer(1, 5))
            try:
                img = RLImage(str(full_hpath), width=200, height=200)
                story.append(img)
                story.append(Spacer(1, 15))
            except Exception:
                pass

    # Next Steps & Disclaimer
    story.append(Paragraph("Recommended Next Steps", heading_style))
    story.append(Spacer(1, 5))
    verdict = scan_data.get("verdict")
    if verdict == "low_risk":
        story.append(Paragraph("Product packaging exhibits standard features. Maintain standard distribution procedures.", body_style))
    elif verdict == "high_suspicion":
        story.append(Paragraph("High suspicion detected. Quarantine batch and contact regional drug regulatory officer immediately.", alert_style))
    else:
        story.append(Paragraph("Inspect physical packaging closely, verify supplier invoice, and perform secondary manual inspection.", body_style))

    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Notice:</b> Simulated registry & alert data may be used in evaluation.", body_style))
    disclaimer = scan_data.get("disclaimer", "Screening only. This does not confirm authenticity.")
    story.append(Paragraph(f"<b>Disclaimer:</b> {disclaimer}", alert_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
