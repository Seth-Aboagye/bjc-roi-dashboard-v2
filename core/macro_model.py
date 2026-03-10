from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class MacroInputs:
    # Revenue allocation model
    total_raised_y1: float
    year1_realization: float          # e.g. 0.40
    carryover_factor: float           # e.g. 0.60

    # Cost model
    base_cost_y1: float               # BJC total cost in current year
    margin: float                     # development margin, Year 1 only
    cost_growth: float                # add-on % of base cost for Y2 and Y3

    # Scenario shocks
    revenue_shock: float = 0.0
    cost_shock: float = 0.0


def _safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b not in (0, None) else 0.0


def build_macro_forecast(
    inputs: MacroInputs,
    budget_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Strategic planning model:
    - Revenue: spreads the current-year fundraising pool across Y1-Y3
    - Cost:
        Y1 = base cost + development margin
        Y2 = cost growth component only (% of base cost)
        Y3 = cost growth component only (% of base cost)
    """

    # ---------------------------
    # Revenue allocation
    # ---------------------------
    R = float(inputs.total_raised_y1)
    r1 = max(0.0, min(1.0, float(inputs.year1_realization)))
    k = max(0.0, min(1.0, float(inputs.carryover_factor)))

    rev1 = R * r1
    remaining_after_y1 = R - rev1
    rev2 = remaining_after_y1 * k
    remaining_after_y2 = remaining_after_y1 - rev2
    rev3 = remaining_after_y2 * k

    revenue_mult = 1.0 + float(inputs.revenue_shock)
    rev1 *= revenue_mult
    rev2 *= revenue_mult
    rev3 *= revenue_mult

    # ---------------------------
    # Cost structure
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
        "Revenue": [rev1, rev2, rev3],
        "Cost": [cost1, cost2, cost3],
    })
    df["Net"] = df["Revenue"] - df["Cost"]
    df["ROI Multiple"] = df.apply(lambda r: _safe_div(r["Revenue"], r["Cost"]), axis=1)
    df["ROI %"] = df["ROI Multiple"] - 1.0

    # ---------------------------
    # KPIs
    # ---------------------------
    total_rev = float(df["Revenue"].sum())
    total_cost = float(df["Cost"].sum())
    total_net = float(df["Net"].sum())
    roi_multiple_3yr = _safe_div(total_rev, total_cost)
    roi_pct_3yr = roi_multiple_3yr - 1.0
    cost_per_1 = _safe_div(total_cost, total_rev)

    kpis = {
        "Total Revenue (3yr)": total_rev,
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

    unrealized = max(0.0, (R * revenue_mult) - total_rev)
    recs.append(
        f"Revenue is allocated across three years for planning. Approximate unrealized amount after Year 3 is ${unrealized:,.0f}."
    )

    if roi_multiple_3yr < 1.0:
        recs.append("Overall ROI is below 1.0x; review Year 1 development margin, realization assumptions, and cost discipline.")
    elif roi_multiple_3yr < 2.0:
        recs.append("Overall ROI is positive but moderate; improving realization and tightening cost assumptions would strengthen net impact.")
    else:
        recs.append("Overall ROI is strong; focus on maintaining cost discipline while maximizing strategic allocation.")

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
        br_col = _pick("Budget Revenue", "BudgetRevenue", "budget_revenue", "revenue_budget")
        bc_col = _pick("Budget Cost", "BudgetCost", "budget_cost", "cost_budget")

        if year_col and br_col and bc_col:
            merged = pd.merge(
                df,
                b[[year_col, br_col, bc_col]].rename(
                    columns={
                        year_col: "Year",
                        br_col: "Budget Revenue",
                        bc_col: "Budget Cost",
                    }
                ),
                on="Year",
                how="left"
            )
            merged["Revenue Var"] = merged["Revenue"] - merged["Budget Revenue"]
            merged["Cost Var"] = merged["Cost"] - merged["Budget Cost"]
            merged["Net Var"] = merged["Net"] - (merged["Budget Revenue"] - merged["Budget Cost"])
            budget_out = merged

    return {
        "forecast_df": df,
        "kpis": kpis,
        "budget_df": budget_out,
        "recommendations": recs,
    }
