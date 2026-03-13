from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class MacroInputs:
    # Donations logic
    total_donations_y1: float
    donor_continuation_rate: float   # e.g. 0.40 means 40% of Y1 donors donate again in Y2 and Y3

    # Cost logic
    base_cost_y1: float
    margin: float                    # Development margin, Year 1 only
    cost_growth: float               # Add-on % of base cost for Y2 and Y3

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
    Macro strategic planning model

    Donations:
    - Year 1 = current-year donations input
    - Year 2 = Year 1 * donor continuation rate
    - Year 3 = Year 2 * donor continuation rate

    Cost:
    - Year 1 = base cost + development margin
    - Year 2 = cost growth add-on only (% of base cost)
    - Year 3 = cost growth add-on only (% of base cost)
    """

    # ---------------------------
    # Donations
    # ---------------------------
    D1 = float(inputs.total_donations_y1)
    cont = max(0.0, min(1.0, float(inputs.donor_continuation_rate)))

    donations1 = D1
    donations2 = D1 * cont
    donations3 = donations2 * cont

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
        f"Donations are modeled such that the Year 2 amount equals {cont:.0%} of Year 1 donations, "
        f"and Year 3 equals {cont:.0%} of Year 2 donations."
    )

    if roi_multiple_3yr < 1.0:
        recs.append("Overall ROI is below 1.0x; review Year 1 development margin, donor continuation assumptions, and cost discipline.")
    elif roi_multiple_3yr < 2.0:
        recs.append("Overall ROI is positive but moderate; improving donor continuation and tightening cost assumptions would strengthen net impact.")
    else:
        recs.append("Overall ROI is strong; focus on sustaining donor continuation while maintaining cost discipline.")

    # ---------------------------
    # Budget comparison
    # ---------------------------
    budget_out = None
    if budget_df is not None and len(budget_df) > 0:
        b = budget_df.copy()
        b.columns = [str(c).strip() for c in b.columns]

        colmap = {c.lower(): c for c in b.columns}

        def _pick(*names):
            for n in names:
                if n.lower() in colmap:
                    return colmap[n.lower()]
            return None

        year_col = _pick("Year", "year")
        bd_col = _pick("Budget Donations", "BudgetDonations", "budget_donations", "donations_budget", "Budget Revenue", "BudgetRevenue", "budget_revenue")
        bc_col = _pick("Budget Cost", "BudgetCost", "budget_cost", "cost_budget")

        if year_col and bd_col and bc_col:
            merged = pd.merge(
                df,
                b[[year_col, bd_col, bc_col]].rename(
                    columns={
                        year_col: "Year",
                        bd_col: "Budget Donations",
                        bc_col: "Budget Cost",
                    }
                ),
                on="Year",
                how="left"
            )
            merged["Donations Var"] = merged["Donations"] - merged["Budget Donations"]
            merged["Cost Var"] = merged["Cost"] - merged["Budget Cost"]
            merged["Net Var"] = merged["Net"] - (merged["Budget Donations"] - merged["Budget Cost"])
            budget_out = merged

    return {
        "forecast_df": df,
        "kpis": kpis,
        "budget_df": budget_out,
        "recommendations": recs,
    }
