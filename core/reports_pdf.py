from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def _money(x) -> str:
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return str(x)


def _pct(x) -> str:
    try:
        return f"{float(x) * 100:,.1f}%"
    except Exception:
        return str(x)


def build_macro_pdf(title: str, kpis: dict, assumptions: dict, recs: list, forecast_df) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))

    intro = (
        "This report summarizes the 3-year donations planning forecast. "
        "The model assumes that Year 2 donations are a percentage of Year 1 donations from retained donors, and Year 3 donations are a percentage of Year 2 donations from retained donors."
    )
    story.append(Paragraph(intro, styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("KPI Summary", styles["Heading2"]))
    kpi_rows = [
        ["Metric", "Value"],
        ["Total Donations (3yr)", _money(kpis.get("Total Donations (3yr)", 0))],
        ["Total Cost (3yr)", _money(kpis.get("Total Cost (3yr)", 0))],
        ["Total Net (3yr)", _money(kpis.get("Total Net (3yr)", 0))],
        ["ROI Multiple (3yr)", f"{float(kpis.get('ROI Multiple (3yr)', 0)):.2f}x"],
        ["ROI % (3yr)", _pct(kpis.get("ROI % (3yr)", 0))],
        ["Cost per $1 (3yr)", f"${float(kpis.get('Cost per $1 (3yr)', 0)):.2f}"],
    ]
    kpi_table = Table(kpi_rows, hAlign="LEFT")
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Assumptions", styles["Heading2"]))
    assumption_rows = [["Assumption", "Value"]]
    for k, v in assumptions.items():
        if isinstance(v, float):
            if "Rate" in k or "Shock" in k or "Margin" in k or "Growth" in k:
                val = _pct(v)
            else:
                val = str(v)
        else:
            val = str(v)
        assumption_rows.append([str(k), val])

    assumption_table = Table(assumption_rows, hAlign="LEFT")
    assumption_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(assumption_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("3-Year Forecast", styles["Heading2"]))
    forecast_rows = [["Year", "Donations", "Cost", "Net", "ROI Multiple"]]
    for _, row in forecast_df.iterrows():
        forecast_rows.append([
            str(row.get("Year", "")),
            _money(row.get("Donations", 0)),
            _money(row.get("Cost", 0)),
            _money(row.get("Net", 0)),
            f"{float(row.get('ROI Multiple', 0)):.2f}x",
        ])

    forecast_table = Table(forecast_rows, hAlign="LEFT")
    forecast_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(forecast_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommendations", styles["Heading2"]))
    for r in recs:
        story.append(Paragraph(f"• {r}", styles["BodyText"]))
        story.append(Spacer(1, 6))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
