from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

@dataclass
class MacroInputs:
    total_raised_y1: float
    base_cost_y1: float
    retention: float                # e.g., 0.60
    revenue_method: str             # "remaining" or "prior"
    revenue_shock: float            # e.g., -0.10 to +0.10
    margin: float                   # e.g., 0.20
    cost_growth: float              # e.g., 0.05
    cost_shock: float               # e.g., -0.05 to +0.05
    acquisition_cost_year1_only: bool = True  # Katie update


def build_macro_forecast(inputs: MacroInputs, budget_df: pd.DataFrame | None = None) -> dict:
    # -----------------------
    # Revenue projection
    # -----------------------
    # Apply shock to Year 1 starting revenue
    y1_rev = max(inputs.total_raised_y1 * (1.0 + inputs.revenue_shock), 0.0)

    # Year 2 and Year 3 revenue
    if inputs.revenue_method == "prior":
        y2_rev = max(y1_rev * inputs.retention, 0.0)
        y3_rev = max(y2_rev * inputs.retention, 0.0)
    else:
        # remaining = retention applied to remaining balance
        # remaining after Year 1
        rem_after_y1 = max(inputs.total_raised_y1 - y1_rev, 0.0)
        y2_rev = max(rem_after_y1 * inputs.retention, 0.0)

        # remaining after Year 2
        rem_after_y2 = max(rem_after_y1 - y2_rev, 0.0)
        y3_rev = max(rem_after_y2 * inputs.retention, 0.0)

    # -----------------------
    # Cost projection
    # -----------------------
    # Base cost Year 1 (acquisition year)
    y1_cost_base = inputs.base_cost_y1 * (1.0 + inputs.cost_shock)
    y1_cost = y1_cost_base * (1.0 + inputs.margin)

    if inputs.acquisition_cost_year1_only:
        # Ongoing stewardship cost = Year1 base cost * growth only (no re-acquisition)
        y2_cost_base = inputs.base_cost_y1 * (1.0 + inputs.cost_growth) * (1.0 + inputs.cost_shock)
        y3_cost_base = inputs.base_cost_y1 * ((1.0 + inputs.cost_growth) ** 2) * (1.0 + inputs.cost_shock)
    else:
        # If not using Katie’s rule, costs compound from prior year totals
        y2_cost_base = y1_cost_base * (1.0 + inputs.cost_growth)
        y3_cost_base = y2_cost_base * (1.0 + inputs.cost_growth)

    y2_cost = y2_cost_base * (1.0 + inputs.margin)
    y3_cost = y3_cost_base * (1.0 + inputs.margin)

    forecast_df = pd.DataFrame(
        {
            "Year": ["Year 1", "Year 2", "Year 3"],
            "Revenue": [y1_rev, y2_rev, y3_rev],
            "Cost": [y1_cost, y2_cost, y3_cost],
        }
    )
    forecast_df["Net"] = forecast_df["Revenue"] - forecast_df["Cost"]
    forecast_df["ROI Multiple"] = forecast_df.apply(
        lambda r: (r["Revenue"] / r["Cost"]) if r["Cost"] else 0.0, axis=1
    )
    forecast_df["ROI %"] = forecast_df["ROI Multiple"] - 1.0

    # 3-year KPIs
    total_rev = float(forecast_df["Revenue"].sum())
    total_cost = float(forecast_df["Cost"].sum())
    total_net = float(forecast_df["Net"].sum())
    roi_mult = (total_rev / total_cost) if total_cost else 0.0
    cost_per_1 = (total_cost / total_rev) if total_rev else 0.0

    kpis = {
        "Total Revenue (3yr)": total_rev,
        "Total Cost (3yr)": total_cost,
        "Total Net (3yr)": total_net,
        "ROI Multiple (3yr)": roi_mult,
        "ROI % (3yr)": roi_mult - 1.0,
        "Cost per $1 (3yr)": cost_per_1,
    }

    # Budget compare (optional)
    out_budget = None
    if budget_df is not None and len(budget_df) > 0:
        # Expect columns: Year, Revenue, Cost (budget)
        b = budget_df.copy()
        b.columns = [str(c).strip() for c in b.columns]
        b = b.rename(columns={"Budget Revenue": "Revenue", "Budget Cost": "Cost"})
        merged = pd.merge(b, forecast_df, on="Year", how="left", suffixes=("_Budget", "_Forecast"))

        # Variances
        merged["Revenue Var"] = merged["Revenue_Forecast"] - merged["Revenue_Budget"]
        merged["Cost Var"] = merged["Cost_Forecast"] - merged["Cost_Budget"]
        merged["Net_Budget"] = merged["Revenue_Budget"] - merged["Cost_Budget"]
        merged["Net_Forecast"] = merged["Revenue_Forecast"] - merged["Cost_Forecast"]
        merged["Net Var"] = merged["Net_Forecast"] - merged["Net_Budget"]

        out_budget = merged

    # Recommendations (simple starter rules)
    recs = []
    if kpis["ROI Multiple (3yr)"] < 1.0:
        recs.append("ROI is below 1.0x across 3 years. Consider focusing on higher-yield channels and improving retention while tightening cost growth.")
    if inputs.retention < 0.60:
        recs.append("Retention assumption is relatively low. Consider stronger stewardship strategy or validate donor repeat patterns.")
    if inputs.cost_growth > 0.10:
        recs.append("Cost growth is high. Consider budget controls or reallocating effort to lower-cost fundraising activities.")
    if not recs:
        recs.append("Scenario appears healthy. Consider scaling what works while monitoring retention sensitivity and cost growth.")

    return {
        "forecast_df": forecast_df,
        "kpis": kpis,
        "budget_df": out_budget,
        "recommendations": recs,
    }
