from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd


@dataclass
class MacroInputs:
    total_donations_y1: float
    donor_continuation_rate: float
    base_cost_y1: float
    margin: float
    cost_growth: float
    donation_shock: float = 0.0
    cost_shock: float = 0.0


def _safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b not in (0, None) else 0.0


def build_macro_forecast(inputs: MacroInputs) -> Dict[str, Any]:
    """
    Donations logic:
    - Year 1 Donations = total_donations_y1
    - Year 2 Donations = Year 1 Donations * donor_continuation_rate
    - Year 3 Donations = Year 1 Donations * donor_continuation_rate
      (excludes any new donors in Years 2 and 3)

    Cost logic:
    - Year 1 Cost = base_cost_y1 * (1 + margin)
    - Year 2 Cost = base_cost_y1 * cost_growth
    - Year 3 Cost = base_cost_y1 * cost_growth
    """

    d1 = float(inputs.total_donations_y1)
    cont = max(0.0, min(1.0, float(inputs.donor_continuation_rate)))

    donations1 = d1
    donations2 = d1 * cont
    donations3 = d1 * cont

    donation_mult = 1.0 + float(inputs.donation_shock)
    donations1 *= donation_mult
    donations2 *= donation_mult
    donations3 *= donation_mult

    c = float(inputs.base_cost_y1)
    m = max(0.0, float(inputs.margin))
    g = max(0.0, float(inputs.cost_growth))

    cost1 = c * (1.0 + m)
    cost2 = c * g
    cost3 = c * g

    cost_mult = 1.0 + float(inputs.cost_shock)
    cost1 *= cost_mult
    cost2 *= cost_mult
    cost3 *= cost_mult

    df = pd.DataFrame({
        "Year": ["Year 1", "Year 2", "Year 3"],
        "Donations": [donations1, donations2, donations3],
        "Cost": [cost1, cost2, cost3],
    })
    df["Net"] = df["Donations"] - df["Cost"]
    df["ROI Multiple"] = df.apply(lambda r: _safe_div(r["Donations"], r["Cost"]), axis=1)
    df["ROI %"] = df["ROI Multiple"] - 1.0

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

    recommendations = []

    if cont < 0.40:
        recommendations.append("Donor continuation is relatively low. Improving retention of Year 1 donors would materially strengthen 3-year donations.")
    elif cont < 0.60:
        recommendations.append("Donor continuation is moderate. Small improvements in retention could produce a meaningful gain in long-term donations.")
    else:
        recommendations.append("Donor continuation is strong. The focus should be on sustaining donor relationships and protecting renewal rates.")

    if roi_multiple_3yr < 1.0:
        recommendations.append("The model shows costs exceed donations over the 3-year horizon. Review Year 1 margin and donor continuation assumptions.")
    elif roi_multiple_3yr < 2.0:
        recommendations.append("The model shows a positive but moderate return. Tighter cost discipline or stronger donor continuation would improve the result.")
    else:
        recommendations.append("The model shows a strong return across the 3-year horizon. Maintaining donor continuation and cost discipline will be important.")

    return {
        "forecast_df": df,
        "kpis": kpis,
        "recommendations": recommendations,
    }
