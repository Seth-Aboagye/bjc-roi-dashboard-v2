from __future__ import annotations
import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def build_macro_pdf(title: str, kpis: dict, assumptions: dict, recs: list[str], forecast_df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    y = h - 60

    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, y, title)

    y -= 28
    c.setFont("Helvetica", 11)
    for k in ["Total Revenue (3yr)", "Total Cost (3yr)", "Total Net (3yr)"]:
        c.drawString(50, y, f"{k}: ${kpis[k]:,.2f}")
        y -= 16
    c.drawString(50, y, f"ROI Multiple (3yr): {kpis['ROI Multiple (3yr)']:.2f}x")
    y -= 16
    c.drawString(50, y, f"ROI % (3yr): {kpis['ROI % (3yr)']*100:.1f}%")
    y -= 16
    c.drawString(50, y, f"Cost per $1 (3yr): ${kpis['Cost per $1 (3yr)']:.2f}")

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Assumptions")
    y -= 16
    c.setFont("Helvetica", 10)
    for k, v in assumptions.items():
        c.drawString(60, y, f"{k}: {v}")
        y -= 14
        if y < 80:
            c.showPage()
            y = h - 60

    y -= 8
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Recommendations")
    y -= 16
    c.setFont("Helvetica", 10)
    for r in recs:
        c.drawString(60, y, f"• {r[:110]}")
        y -= 14
        if y < 80:
            c.showPage()
            y = h - 60

    c.showPage()
    c.save()
    return buf.getvalue()