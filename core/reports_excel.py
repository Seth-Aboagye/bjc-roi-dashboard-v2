import io
import pandas as pd
from core.metrics import compute_rollups

def build_excel_report(d: pd.DataFrame, c: pd.DataFrame, payload: dict) -> bytes:
    out = io.BytesIO()

    roll_campaign = compute_rollups(d, c, by="campaign_code").sort_values("raised", ascending=False)
    roll_channel = compute_rollups(d, c, by="channel").sort_values("raised", ascending=False)

    kpis = pd.DataFrame([payload["kpis"]])
    filters = pd.DataFrame([{
        "start": payload["filters"]["start"],
        "end": payload["filters"]["end"],
        "channels": ", ".join(payload["filters"]["channels"]),
        "campaigns": ", ".join(payload["filters"]["campaigns"]),
        "segments": ", ".join(payload["filters"]["segments"]),
    }])

    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        filters.to_excel(writer, sheet_name="Filters", index=False)
        kpis.to_excel(writer, sheet_name="KPIs", index=False)
        roll_campaign.to_excel(writer, sheet_name="By Campaign", index=False)
        roll_channel.to_excel(writer, sheet_name="By Channel", index=False)
        d.to_excel(writer, sheet_name="Donations (Filtered)", index=False)
        c.to_excel(writer, sheet_name="Costs (Filtered)", index=False)

    return out.getvalue()
