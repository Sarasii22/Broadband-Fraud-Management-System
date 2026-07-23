"""
Generates a downloadable PDF report summarizing fraud statistics for a
given time period. Built with reportlab so it runs fully server-side —
no browser print dialog, no missing styling, and it reuses the exact
same data that /stats/by-time already returns.
"""

import io
from datetime import datetime
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

FRAUD_RED = colors.HexColor("#c0392b")
NORMAL_GREEN = colors.HexColor("#1e8449")
REVIEW_AMBER = colors.HexColor("#b8860b")
BRAND_BLUE = colors.HexColor("#2f8bff")


def _format_dt(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _build_rule_chart(rule_breakdown: List[Dict]) -> Drawing:
    """
    Vertical bar chart: one bar per triggered rule, height = fraud
    percentage among the records where that rule fired.
    """
    # Limit to top 10 rules by volume so the chart stays readable.
    top_rules = rule_breakdown[:10]
    labels = [r["rule"].replace("_", " ") for r in top_rules]
    values = [r["fraud_percentage"] for r in top_rules]

    drawing = Drawing(480, 260)

    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 60
    chart.width = 400
    chart.height = 170
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.dx = -8
    chart.categoryAxis.labels.dy = -10
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 20
    chart.valueAxis.labelTextFormat = "%d%%"
    chart.bars[0].fillColor = BRAND_BLUE
    chart.barWidth = 10

    drawing.add(chart)
    return drawing


def build_pdf_report(
    start_time: datetime,
    end_time: datetime,
    total_records: int,
    fraud_count: int,
    normal_count: int,
    fraud_percentage: float,
    normal_percentage: float,
    records: List[Dict],
    rule_breakdown: List[Dict],
) -> bytes:
    """
    Returns raw PDF bytes. Caller is responsible for streaming/returning
    them in an HTTP response.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=20, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"], textColor=colors.grey, spaceAfter=16
    )
    section_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=18, spaceAfter=8
    )
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, leading=10)
    header_cell_style = ParagraphStyle(
        "HeaderCell", parent=styles["Normal"], fontSize=8, leading=10,
        textColor=colors.whitesmoke, fontName="Helvetica-Bold",
    )
    fraud_cell_style = ParagraphStyle(
        "FraudCell", parent=cell_style, textColor=FRAUD_RED, fontName="Helvetica-Bold"
    )
    normal_cell_style = ParagraphStyle(
        "NormalCell", parent=cell_style, textColor=NORMAL_GREEN, fontName="Helvetica-Bold"
    )

    story = []

    # ---------- Header ----------
    story.append(Paragraph("Broadband Fraud Detection Report", title_style))
    story.append(
        Paragraph(
            f"Period: {_format_dt(start_time)} &nbsp;&mdash;&nbsp; {_format_dt(end_time)}"
            f"<br/>Generated: {_format_dt(datetime.utcnow())} UTC",
            subtitle_style,
        )
    )

    # ---------- Summary table ----------
    story.append(Paragraph("Summary", section_style))

    summary_data = [
        ["Metric", "Value"],
        ["Total Records", str(total_records)],
        ["Fraud Count", str(fraud_count)],
        ["Normal Count", str(normal_count)],
        ["Fraud Percentage", f"{fraud_percentage}%"],
        ["Normal Percentage", f"{normal_percentage}%"],
    ]

    summary_table = Table(summary_data, colWidths=[7 * cm, 7 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Color the fraud/normal count rows for a quick visual cue
                ("TEXTCOLOR", (1, 2), (1, 2), FRAUD_RED),
                ("TEXTCOLOR", (1, 3), (1, 3), NORMAL_GREEN),
                ("TEXTCOLOR", (1, 4), (1, 4), FRAUD_RED),
                ("TEXTCOLOR", (1, 5), (1, 5), NORMAL_GREEN),
            ]
        )
    )
    story.append(summary_table)

    # ---------- Triggered rules vs fraud percentage chart ----------
    story.append(Paragraph("Triggered Rules vs Fraud Percentage", section_style))

    if not rule_breakdown:
        story.append(Paragraph("No rules were triggered in this time period.", styles["Normal"]))
    else:
        story.append(_build_rule_chart(rule_breakdown))
        story.append(Spacer(1, 10))

        rule_header = [
            Paragraph(h, header_cell_style)
            for h in ["Rule", "Times Triggered", "Fraud Count", "Fraud %"]
        ]
        rule_table_data = [rule_header]
        for r in rule_breakdown:
            rule_table_data.append(
                [
                    Paragraph(r["rule"].replace("_", " "), cell_style),
                    Paragraph(str(r["total"]), cell_style),
                    Paragraph(str(r["fraud_count"]), cell_style),
                    Paragraph(f"{r['fraud_percentage']:.2f}%", cell_style),
                ]
            )

        rule_table = Table(rule_table_data, colWidths=[6 * cm, 3 * cm, 3 * cm, 3 * cm])
        rule_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ]
            )
        )
        story.append(rule_table)

    # ---------- Records table ----------
    story.append(Paragraph("Detailed Records", section_style))

    if not records:
        story.append(Paragraph("No records found for this time period.", styles["Normal"]))
    else:
        header_row = [
            Paragraph(h, header_cell_style)
            for h in [
                "Customer ID", "Fraud Status", "Decision", "Final Score",
                "Rule Score", "ML Score", "Triggered Rules", "Scored At",
            ]
        ]
        table_data = [header_row]

        for r in records:
            triggered = r.get("triggered_rules") or []
            is_fraud = bool(r.get("is_fraud"))

            fraud_status_paragraph = Paragraph(
                "FRAUD" if is_fraud else "NOT FRAUD",
                fraud_cell_style if is_fraud else normal_cell_style,
            )

            table_data.append(
                [
                    Paragraph(str(r.get("subscriber_id", "")), cell_style),
                    fraud_status_paragraph,
                    Paragraph(str(r.get("decision", "")), cell_style),
                    Paragraph(f"{r.get('final_score', 0):.4f}", cell_style),
                    Paragraph(f"{r.get('rule_score', 0):.4f}", cell_style),
                    Paragraph(f"{r.get('ml_score', 0):.4f}", cell_style),
                    Paragraph(", ".join(triggered) if triggered else "None", cell_style),
                    Paragraph(_format_dt(r.get("created_at")), cell_style),
                ]
            )

        col_widths = [2.1 * cm, 1.7 * cm, 1.6 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 3.8 * cm, 2.5 * cm]
        records_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        row_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]

        # Color-code the Decision column per row (index 2) based on value
        for idx, r in enumerate(records, start=1):
            decision = str(r.get("decision", "")).upper()
            if decision == "BLOCK":
                row_styles.append(("TEXTCOLOR", (2, idx), (2, idx), FRAUD_RED))
            elif decision == "REVIEW":
                row_styles.append(("TEXTCOLOR", (2, idx), (2, idx), REVIEW_AMBER))
            else:
                row_styles.append(("TEXTCOLOR", (2, idx), (2, idx), NORMAL_GREEN))

        records_table.setStyle(TableStyle(row_styles))
        story.append(records_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()