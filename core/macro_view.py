from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd


@dataclass
class MacroInputs:
    total_donations_y1: float
    donor_continuation_rate: float
    base_cost_y1: float
    organizational_margin: float
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
    - Year 3 Donations = Year 2 Donations * donor_continuation_rate

    Cost logic:
    - Year 1 Cost = base_cost_y1 + (organizational_margin * base_cost_y1)
    - Year 2 Cost = cost_growth * Year 1 Cost
    - Year 3 Cost = cost_growth * (Year 1 Cost + Year 2 Cost)

    Negative cost growth is allowed to model cost reduction.
    """

    # Donations
    d1 = float(inputs.total_donations_y1)
    cont = max(0.0, min(1.0, float(inputs.donor_continuation_rate)))

    donations1 = d1
    donations2 = donations1 * cont
    donations3 = donations2 * cont

    donation_mult = 1.0 + float(inputs.donation_shock)
    donations1 *= donation_mult
    donations2 *= donation_mult
    donations3 *= donation_mult

    # Costs
    base_cost = float(inputs.base_cost_y1)
    org_margin = float(inputs.organizational_margin)
    growth = float(inputs.cost_growth)

    cost1 = base_cost + (org_margin * base_cost)
    cost2 = growth * cost1
    cost3 = growth * (cost1 + cost2)

    cost_mult = 1.0 + float(inputs.cost_shock)
    cost1 *= cost_mult
    cost2 *= cost_mult
    cost3 *= cost_mult

    # Forecast table
    df = pd.DataFrame({
        "Year": ["Year 1", "Year 2", "Year 3"],
        "Donations": [donations1, donations2, donations3],
        "Cost": [cost1, cost2, cost3],
    })

    df["Net"] = df["Donations"] - df["Cost"]
    df["ROI Multiple"] = df.apply(
        lambda r: _safe_div(r["Donations"], r["Cost"]) if r["Cost"] > 0 else 0.0,
        axis=1
    )
    df["ROI %"] = df["ROI Multiple"] - 1.0

    # KPI summary
    total_don = float(df["Donations"].sum())
    total_cost = float(df["Cost"].sum())
    total_net = float(df["Net"].sum())

    roi_multiple_3yr = _safe_div(total_don, total_cost) if total_cost > 0 else 0.0
    roi_pct_3yr = roi_multiple_3yr - 1.0
    cost_per_1 = _safe_div(total_cost, total_don) if total_don > 0 else 0.0

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
        recommendations.append(
            "Donor continuation is relatively low. Improving retention of Year 1 donors would materially strengthen 3-year donations."
        )
    elif cont < 0.60:
        recommendations.append(
            "Donor continuation is moderate. Small improvements in retention could produce meaningful gains in long-term donations."
        )
    else:
        recommendations.append(
            "Donor continuation is strong. Focus on sustaining donor relationships and protecting renewal rates."
        )

    recommendations.append(
        "The donation model assumes Year 2 comes from retained Year 1 donors, while Year 3 comes from retained Year 2 donors."
    )

    recommendations.append(
        "The cost model assumes Year 1 includes the full base cost plus organizational margin, Year 2 is a growth percentage of Year 1 cost, and Year 3 is a growth percentage of the combined Year 1 and Year 2 cost."
    )

    if growth < 0:
        recommendations.append(
            "Cost growth is negative, meaning the model assumes cost reduction in Years 2 and 3."
        )
    elif growth == 0:
        recommendations.append(
            "Cost growth is flat, so no additional Year 2 or Year 3 growth cost is assumed."
        )
    else:
        recommendations.append(
            "Positive cost growth adds incremental cost in Years 2 and 3 based on prior accumulated cost."
        )

    if roi_multiple_3yr < 1.0:
        recommendations.append(
            "The model shows costs exceed donations over the 3-year horizon. Review organizational margin, cost growth, and donor continuation assumptions."
        )
    elif roi_multiple_3yr < 2.0:
        recommendations.append(
            "The model shows a positive but moderate return. Tighter cost discipline or stronger donor continuation would improve the result."
        )
    else:
        recommendations.append(
            "The model shows a strong return across the 3-year horizon. Maintaining donor continuation and cost discipline will be important."
        )

    return {
        "forecast_df": df,
        "kpis": kpis,
        "recommendations": recommendations,
    }
