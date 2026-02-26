from __future__ import annotations
import pandas as pd
import io

def budget_template_excel() -> bytes:
    df = pd.DataFrame({
        "Year": ["Year 1", "Year 2", "Year 3"],
        "Budget Revenue": [250000, 150000, 60000],
        "Budget Cost": [180000, 190000, 200000],
    })
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Budget", index=False)
    return out.getvalue()