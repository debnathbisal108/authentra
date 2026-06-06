from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Color palette
DARK = colors.HexColor("#0f172a")
PRIMARY = colors.HexColor("#0ea5e9")
SUCCESS = colors.HexColor("#22c55e")
WARNING = colors.HexColor("#f59e0b")
DANGER = colors.HexColor("#ef4444")
LIGHT_BG = colors.HexColor("#f8fafc")
BORDER = colors.HexColor("#e2e8f0")
TEXT = colors.HexColor("#374151")
MUTED = colors.HexColor("#9ca3af")


def risk_color(level: str) -> colors.Color:
    return {
        "low": SUCCESS,
        "moderate": WARNING,
        "high": DANGER,
        "critical": colors.HexColor("#7f1d1d"),
    }.get(str(level).lower(), MUTED)


def verdict_color(verdict: str) -> colors.Color:
    return {
        "clear": SUCCESS,
        "review_required": WARNING,
        "reject": DANGER,
    }.get(str(verdict).lower() if verdict else "", MUTED)


def generate_verification_report(
    candidate: dict,
    employment_records: list,
    education_records: list,
    fraud_flags: list,
    risk_score: dict,
    organization_name: str,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    h1 = ParagraphStyle("h1", parent=styles["Normal"], fontSize=22, textColor=DARK,
                         fontName="Helvetica-Bold", spaceBefore=0, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Normal"], fontSize=14, textColor=DARK,
                         fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=styles["Normal"], fontSize=11, textColor=TEXT,
                         fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, textColor=TEXT,
                           leading=16, spaceBefore=4, spaceAfter=4)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=MUTED, leading=12)
    
    elements = []

    # ── Header ─────────────────────────────────────────────────────────────────
    elements.append(Paragraph("AUTHENTRA AI", ParagraphStyle(
        "logo", parent=styles["Normal"], fontSize=10, textColor=PRIMARY,
        fontName="Helvetica-Bold", spaceAfter=4
    )))
    elements.append(Paragraph("Background Verification Report", h1))
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=12))
    
    # Header table
    now = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
    verdict = (risk_score.get("final_verdict") or "PENDING").upper().replace("_", " ")
    verdict_val = (risk_score.get("final_verdict") or "").lower()
    v_color = verdict_color(verdict_val)
    
    header_data = [
        [
            Paragraph(f"<b>Candidate:</b> {candidate.get('full_name', 'Unknown')}", body),
            Paragraph(f"<b>Report Date:</b> {now}", body),
        ],
        [
            Paragraph(f"<b>Organization:</b> {organization_name}", body),
            Paragraph(f"<b>Status:</b> <font color='#{v_color.hexval()[2:]}'>● {verdict}</font>", body),
        ],
    ]
    header_table = Table(header_data, colWidths=[9 * cm, 9 * cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 1, BORDER),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # ── Risk Score Banner ──────────────────────────────────────────────────────
    score = risk_score.get("total_score", 0)
    risk_level = (risk_score.get("risk_level") or "unknown").upper()
    rl_color = risk_color(risk_score.get("risk_level", ""))
    
    score_data = [[
        Paragraph(f"<font size='28'><b>{int(score)}</b></font><font size='10'>/100</font>", 
                  ParagraphStyle("sc", parent=styles["Normal"], textColor=rl_color, fontName="Helvetica-Bold")),
        Paragraph(f"<b>RISK LEVEL: {risk_level}</b>", 
                  ParagraphStyle("rl", parent=styles["Normal"], fontSize=14, textColor=rl_color, fontName="Helvetica-Bold")),
        Paragraph(f"<b>VERDICT: {verdict}</b>",
                  ParagraphStyle("vd", parent=styles["Normal"], fontSize=14, textColor=v_color, fontName="Helvetica-Bold")),
    ]]
    score_table = Table(score_data, colWidths=[4 * cm, 7 * cm, 7 * cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("ROUNDEDCORNERS", [6], ),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 16))

    # ── Executive Summary ─────────────────────────────────────────────────────
    elements.append(Paragraph("1. Executive Summary", h2))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
    
    summary_text = risk_score.get("ai_recommendation") or "Verification process completed."
    elements.append(Paragraph(summary_text, body))
    
    explanation = risk_score.get("explanation")
    if explanation:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Risk Analysis:</b> {explanation}", body))

    # ── Candidate Profile ─────────────────────────────────────────────────────
    elements.append(Paragraph("2. Candidate Profile", h2))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
    
    profile_data = [
        ["Full Name", candidate.get("full_name", "—")],
        ["Email", candidate.get("email", "—")],
        ["Phone", candidate.get("phone", "—")],
        ["LinkedIn", candidate.get("linkedin_url", "—")],
        ["Skills", ", ".join(candidate.get("skills", [])) or "—"],
    ]
    profile_table = Table(profile_data, colWidths=[4 * cm, 14 * cm])
    profile_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, colors.white]),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    elements.append(profile_table)

    # ── Employment History ─────────────────────────────────────────────────────
    elements.append(Paragraph("3. Employment Verification", h2))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
    
    if employment_records:
        emp_data = [["Company", "Title", "Dates", "Status"]]
        for emp in employment_records:
            status = str(emp.get("verification_status", "pending")).upper()
            dates = f"{emp.get('start_date', '?')} – {emp.get('end_date', 'Present') if not emp.get('is_current') else 'Present'}"
            emp_data.append([
                emp.get("company_name", "—"),
                emp.get("job_title", "—"),
                dates,
                status,
            ])
        emp_table = Table(emp_data, colWidths=[5 * cm, 4 * cm, 5 * cm, 4 * cm])
        emp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 1, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ]))
        elements.append(emp_table)
    else:
        elements.append(Paragraph("No employment records found.", body))

    # ── Education ─────────────────────────────────────────────────────────────
    elements.append(Paragraph("4. Education Verification", h2))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
    
    if education_records:
        edu_data = [["Institution", "Degree", "Years", "Status"]]
        for edu in education_records:
            years = f"{edu.get('start_year', '?')} – {edu.get('end_year', '?')}"
            edu_data.append([
                edu.get("institution_name", "—"),
                f"{edu.get('degree', '')} {edu.get('field_of_study', '')}".strip() or "—",
                years,
                str(edu.get("verification_status", "pending")).upper(),
            ])
        edu_table = Table(edu_data, colWidths=[6 * cm, 5 * cm, 3 * cm, 4 * cm])
        edu_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 1, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ]))
        elements.append(edu_table)
    else:
        elements.append(Paragraph("No education records found.", body))

    # ── Fraud Flags ───────────────────────────────────────────────────────────
    elements.append(Paragraph("5. Fraud & Anomaly Detection", h2))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
    
    if fraud_flags:
        for flag in fraud_flags:
            sev = str(flag.get("severity", "low")).upper()
            sev_color = {"LOW": WARNING, "MEDIUM": WARNING, "HIGH": DANGER, "CRITICAL": DANGER}.get(sev, MUTED)
            elements.append(Paragraph(
                f"<b>[{sev}]</b> {flag.get('flag_type', '').replace('_', ' ')} — {flag.get('description', '')}",
                ParagraphStyle("flag", parent=body, textColor=sev_color if sev in ("HIGH", "CRITICAL") else TEXT)
            ))
    else:
        elements.append(Paragraph("✓ No fraud indicators detected.", 
                                   ParagraphStyle("ok", parent=body, textColor=SUCCESS)))

    # ── Score Breakdown ───────────────────────────────────────────────────────
    elements.append(Paragraph("6. Risk Score Breakdown", h2))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
    
    score_breakdown = [
        ["Category", "Score", "Weight"],
        ["Employment Verification", f"{int(risk_score.get('employment_score', 0))}/100", "35%"],
        ["Education Verification", f"{int(risk_score.get('education_score', 0))}/100", "25%"],
        ["Fraud & Anomaly Detection", f"{int(risk_score.get('fraud_score', 0))}/100", "25%"],
        ["Public Records Check", f"{int(risk_score.get('public_check_score', 0))}/100", "15%"],
        ["TOTAL RISK SCORE", f"{int(risk_score.get('total_score', 0))}/100", "100%"],
    ]
    sb_table = Table(score_breakdown, colWidths=[10 * cm, 4 * cm, 4 * cm])
    sb_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BG),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT_BG]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    elements.append(sb_table)

    # ── Footer ─────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 24))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"This report was generated by Authentra AI on {now}. "
        "This report is confidential and intended solely for the hiring organization. "
        "All verifications are based on available data and should be considered alongside other evaluation criteria.",
        small
    ))

    doc.build(elements)
    return buffer.getvalue()
