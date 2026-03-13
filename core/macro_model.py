from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class MacroInputs:
    # Donations logic
    total_donations_y1: float
    donor_continuation_rate: float   # e.g. 0.40 means 40% of Year 1 donations in Year 2 and again in Year 3

    # Cost logic
    base_cost_y1: float
    margin: float                    # applied only in Year 1
    cost_growth: float               # applied as add-on in Year 2 and Year 3

    # Scenario shocks
    donation_shock: float = 0.0
    cost_shock: float = 0.0


def _safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b not in (0, None) else 0.0


def build_macro_forecast(
    inputs: MacroInputs,
    budget_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    3-year donations planning model

    Donations:
    - Year 1 = current-year donations
    - Year 2 = Year 1 donations * donor continuation rate
    - Year 3 = Year 1 donations * donor continuation rate
      (This excludes new donors in Years 2 and 3)

    Costs:
    - Year 1 = base cost + margin
    - Year 2 = cost growth % of base cost
    - Year 3 = cost growth % of base cost
    """

    # ---------------------------
    # Donations
    # ---------------------------
    D1 = float(inputs.total_donations_y1)
    cont = max(0.0, min(1.0, float(inputs.donor_continuation_rate)))

    donations1 = D1
    donations2 = D1 * cont
    donations3 = D1 * cont

    donation_mult = 1.0 + float(inputs.donation_shock)
    donations1 *= donation_mult
    donations2 *= donation_mult
    donations3 *= donation_mult

    # ---------------------------
    # Costs
    # ---------------------------
    C = float(inputs.base_cost_y1)
    m = max(0.0, float(inputs.margin))
    g = max(0.0, float(inputs.cost_growth))

    cost1 = C * (1.0 + m)
    cost2 = C * g
    cost3 = C * g

    cost_mult = 1.0 + float(inputs.cost_shock)
    cost1 *= cost_mult
    cost2 *= cost_mult
    cost3 *= cost_mult

    # ---------------------------
    # Forecast table
    # ---------------------------
    df = pd.DataFrame({
        "Year": ["Year 1", "Year 2", "Year 3"],
        "Donations": [donations1, donations2, donations3],
        "Cost": [cost1, cost2, cost3],
    })
    df["Net"] = df["Donations"] - df["Cost"]
    df["ROI Multiple"] = df.apply(lambda r: _safe_div(r["Donations"], r["Cost"]), axis=1)
    df["ROI %"] = df["ROI Multiple"] - 1.0

    # ---------------------------
    # KPIs
    # ---------------------------
    total_don = float(df["Donations"].sum())
    total_cost = float(df["Cost"].sum())
    total_net = float(df["Net"].sum())
    roi_multiple_3yr = _safe_div(total_don, total_cost)
    roi_pct_3yr = roi_multiple_3yr - 1.0
    cost_per_1 = _safe_div(total_cost, total_don)

    kpis = {
        "Total Donations (3yr)": total_don,
        "Total Cost (3yr)": total_cost,
        "Total Net (3yr)": total_net,
        "ROI Multiple (3yr)": roi_multiple_3yr,
        "ROI % (3yr)": roi_pct_3yr,
        "Cost per $1 (3yr)": cost_per_1,
    }

    # ---------------------------
    # Recommendations
    # ---------------------------
    recs = []
    recs.append(
        f"Donations are modeled so that Year 2 equals {cont:.0%} of Year 1 donations and Year 3 also equals {cont:.0%} of Year 1 donations, excluding any new donors in Years 2 and 3."
    )

    if roi_multiple_3yr < 1.0:
        recs.append("Overall ROI is below 1.0x; review donor continuation assumptions, Year 1 development margin, and cost discipline.")
    elif roi_multiple_3yr < 2.0:
        recs.append("Overall ROI is positive but moderate; improving donor continuation or tightening cost assumptions would strengthen net impact.")
    else:
        recs.append("Overall ROI is strong; the focus should be on sustaining donor continuation while maintaining cost discipline.")

    # Budget intentionally removed
    budget_out = None

    return {
        "forecast_df": df,
        "kpis": kpis,
        "budget_df": budget_out,
        "recommendations": recs,
    }
2) core/charts.py

Rep
