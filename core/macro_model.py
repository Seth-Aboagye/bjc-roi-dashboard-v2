from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

def safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if float(b) != 0 else 0.0

@dataclass
class MacroInputs:
    # Year-1 baseline
    total_raised_y1: float
    base_cost_y1: float

    # Revenue assumptions
    retention: float = 0.60                 # 60%
    revenue_method: str = "remaining"       # "remaining" or "prior"
    revenue_shock: float = 0.00             # -0.20 to +0.20 (economic scenario adjustment)

    # Cost assumptions
    margin: float = 0.20                    # 20% dev margin
    cost_growth: float = 0.05               # 5% annual growth on base cost
    cost_shock: float = 0.00                # -0.20 to +0.20 (economic scenario adjustment)

def forecast_revenue_3yr(total_raised_y1: float, retention: float, method: str, shock: float) -> pd.Series:
    """
    method:
      - "remaining": Y2 = r * remaining; Y3 = r * remaining_after_Y2
      - "prior":     Y2 = r * Y1; Y3 = r * Y2
    shock: applies uniformly to Y2 and Y3 (and can apply to Y1 too if you want; here we keep Y1 at 100%)
    """
    y1 = float(total_raised_y1)

    if method == "prior":
        y2 = retention * y1
        y3 = retention * y2
    else:
        remaining = y1
        y2 = retention * remaining
        remaining = remaining - y2
        y3 = retention * remaining

    # Apply economic/business scenario shock to projected years (optional policy)
    y2 = y2 * (1.0 + shock)
    y3 = y3 * (1.0 + shock)

    return pd.Series([y1, y2, y3], index=["Year 1", "Year 2", "Year 3"], name="Revenue")

def forecast_cost_3yr(base_cost_y1: float, margin: float, cost_growth: float, shock: float) -> pd.Series:
    """
    Cost model requested:
      Year 1 = base_cost * (1 + margin)
      Year 2 = base_cost*(1+growth) * (1+margin)
      Year 3 = base_cost*(1+growth)^2 * (1+margin)
    shock: applies to Y2 and Y3 (optional), or to all years—here we apply to all for simplicity.
    """
    c0 = float(base_cost_y1)

    y1 = c0 * (1.0 + margin)
    y2 = (c0 * (1.0 + cost_growth)) * (1.0 + margin)
    y3 = (c0 * (1.0 + cost_growth) ** 2) * (1.0 + margin)

    # Apply cost shock (inflation, wage pressure, etc.)
    y1 = y1 * (1.0 + shock)
    y2 = y2 * (1.0 + shock)
    y3 = y3 * (1.0 + shock)

    return pd.Series([y1, y2, y3], index=["Year 1", "Year 2", "Year 3"], name="Cost")

def build_macro_forecast(inputs: MacroInputs, budget_df: pd.DataFrame | None = None) -> dict:
    revenue = forecast_revenue_3yr(
        inputs.total_raised_y1, inputs.retention, inputs.revenue_method, inputs.revenue_shock
    )
    cost = forecast_cost_3yr(
        inputs.base_cost_y1, inputs.margin, inputs.cost_growth, inputs.cost_shock
    )

    df = pd.DataFrame({"Year": revenue.index, "Revenue": revenue.values, "Cost": cost.values})
    df["Net"] = df["Revenue"] - df["Cost"]
    df["ROI Multiple"] = df.apply(lambda r: safe_div(r["Revenue"], r["Cost"]), axis=1)
    df["ROI %"] = df.apply(lambda r: safe_div(r["Revenue"] - r["Cost"], r["Cost"]), axis=1)
    df["Cost per $1"] = df.apply(lambda r: safe_div(r["Cost"], r["Revenue"]), axis=1)

    # 3-year totals
    total_rev = float(df["Revenue"].sum())
    total_cost = float(df["Cost"].sum())
    total_net = total_rev - total_cost

    kpis = {
        "Total Revenue (3yr)": total_rev,
        "Total Cost (3yr)": total_cost,
        "Total Net (3yr)": total_net,
        "ROI Multiple (3yr)": safe_div(total_rev, total_cost),
        "ROI % (3yr)": safe_div(total_net, total_cost),
        "Cost per $1 (3yr)": safe_div(total_cost, total_rev),
    }

    # Budget integration (optional)
    budget_out = None
    if budget_df is not None and len(budget_df) > 0:
        # Expect columns: Year, Budget Revenue, Budget Cost
        b = budget_df.copy()
        b["Year"] = b["Year"].astype(str)
        merged = df.merge(b, on="Year", how="left")
        merged["Revenue Var"] = merged["Revenue"] - merged["Budget Revenue"]
        merged["Cost Var"] = merged["Cost"] - merged["Budget Cost"]
        merged["Budget Net"] = merged["Budget Revenue"] - merged["Budget Cost"]
        merged["Net Var"] = merged["Net"] - merged["Budget Net"]
        budget_out = merged

    # Recommendations (simple, practical rules)
    recs = []
    if total_cost <= 0:
        recs.append("Enter a Base Cost greater than 0 to compute ROI.")
    else:
        roi_mult = kpis["ROI Multiple (3yr)"]
        c_per_1 = kpis["Cost per $1 (3yr)"]

        if roi_mult < 1.0:
            recs.append("3-year ROI multiple is below 1.0x (costs exceed projected revenue impact). Consider reducing development margin, lowering cost growth, or focusing on higher-yield fundraising activities (e.g., major donors).")
        elif roi_mult < 2.0:
            recs.append("3-year ROI is positive but moderate. Prioritize segments/campaigns with lower cost per $1 raised, and test a conservative scenario for planning.")
        else:
            recs.append("3-year ROI looks strong under current assumptions. Consider scaling the most effective development activities while monitoring cost growth and retention sensitivity.")

        if c_per_1 > 0.50:
            recs.append("Cost per $1 raised is relatively high. Consider shifting effort toward major donor engagement or channels with higher efficiency.")

    recs.append("Use scenario presets (Base / Conservative / Optimistic) to support budgeting and strategic planning conversations.")

    return {"forecast_df": df, "kpis": kpis, "budget_df": budget_out, "recommendations": recs}