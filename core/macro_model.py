from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import pandas as pd

from .utils import safe_div


@dataclass
class MacroInputs:
    total_raised_y1: float
    base_cost_y1: float
    retention: float                 # e.g., 0.60
    revenue_method: str              # "remaining" or "prior"
    revenue_shock: float             # e.g., -0.10 to +0.10
    margin: float                    # e.g., 0.20
    cost_growth: float               # e.g., 0.05
    cost_shock: float                # e.g., -0.05 to +0.05

    # NEW: acquisition cost is only in year 1
    acquisition_cost_year1_only: bool = True


def _build_revenue_series(y1_total: float, retention: float, method: str) -> list[float]:
    """
    Builds 3-year revenue series.
    - method="remaining": Y2 = retention * remaining after Y1; Y3 = retention * remaining after Y2
    - method="prior":     Y2 = retention * Y1; Y3 = retention * Y2
    """
    y1 = float(y1_total)

    if method == "prior":
        y2 = retention * y1
        y3 = retention * y2
        return [y1, y2, y3]

    # default: "remaining"
    remaining_after_y1 = max(y1_total - y1, 0.0)  # typically 0 in this simplified model
    # Note: If you interpret Y1 as "100% realized this year" and the rest is "unrealized future",
    # you should input total_raised_y1 as the *full pledge/expected* amount, not just cash received.
    y2 = retention * remaining_after_y1
    remaining_after_y2 = max(remaining_after_y1 - y2, 0.0)
    y3 = retention * remaining_after_y2
    return [y1, y2, y3]


def _apply_shock(values: list[float], shock: float) -> list[float]:
    """Applies a multiplicative shock: +10% => 1.10, -10% => 0.90."""
    mult = 1.0 + float(shock)
    return [v * mult for v in values]


def build_macro_forecast(inputs: MacroInputs, budget_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    # -----------------------
    # Revenue (3-year)
    # -----------------------
    revenue = _build_revenue_series(
        y1_total=inputs.total_raised_y1,
        retention=inputs.retention,
        method=inputs.revenue_method,
    )
    revenue = _apply_shock(revenue, inputs.revenue_shock)

    # -----------------------
    # Cost (3-year) — UPDATED LOGIC
    # -----------------------
    base = float(inputs.base_cost_y1)
    margin = float(inputs.margin)
    g = float(inputs.cost_growth)

    # Year 1: acquisition + overhead margin
    y1_cost = base + (base * margin)

    if inputs.acquisition_cost_year1_only:
        # Years 2–3: ONLY "maintenance/stewardship" (use margin portion), growing each year
        sustain_base = base * margin
        y2_cost = sustain_base * (1.0 + g)
        y3_cost = sustain_base * ((1.0 + g) ** 2)
        cost = [y1_cost, y2_cost, y3_cost]
    else:
        # Legacy behavior (if you ever want it): full cost continues and grows each year
        cost = [
            y1_cost,
            y1_cost * (1.0 + g),
            y1_cost * ((1.0 + g) ** 2),
        ]

    cost = _apply_shock(cost, inputs.cost_shock)

    # -----------------------
    # Forecast frame
    # -----------------------
    years = ["Year 1", "Year 2", "Year 3"]
    df = pd.DataFrame(
        {
            "Year": years,
            "Revenue": revenue,
            "Cost": cost,
        }
    )
    df["Net"] = df["Revenue"] - df["Cost"]
    df["ROI Multiple"] = df.apply(lambda r: safe_div(r["Revenue"], r["Cost"]) if r["Cost"] else 0.0, axis=1)

    # -----------------------
    # KPIs
    # -----------------------
    total_rev = float(df["Revenue"].sum())
    total_cost = float(df["Cost"].sum())
    total_net = float(df["Net"].sum())

    kpis = {
        "Total Revenue (3yr)": total_rev,
        "Total Cost (3yr)": total_cost,
        "Total Net (3yr)": total_net,
        "ROI Multiple (3yr)": safe_div(total_rev, total_cost),
        "Cost per $1 (3yr)": safe_div(total_cost, total_rev),
    }

    # -----------------------
    # Budget compare (optional)
    # Expected columns: Year, Revenue, Cost (budget)
    # -----------------------
    budget_out = None
    if budget_df is not None and len(budget_df) > 0:
        b = budget_df.copy()
        b.columns = [str(c).strip() for c in b.columns]

        # normalize year labels to match
        if "Year" in b.columns:
            b["Year"] = b["Year"].astype(str).str.strip()

        # merge forecast with budget
        merged = pd.merge(
            df[["Year", "Revenue", "Cost", "Net"]],
            b,
            on="Year",
            how="left",
            suffixes=("", "_Budget"),
        )

        # If budget has these columns
        if "Revenue_Budget" in merged.columns:
            merged["Revenue Var"] = merged["Revenue"] - merged["Revenue_Budget"]
        if "Cost_Budget" in merged.columns:
            merged["Cost Var"] = merged["Cost"] - merged["Cost_Budget"]
        if "Net_Budget" in merged.columns:
            merged["Net Var"] = merged["Net"] - merged["Net_Budget"]

        budget_out = merged

    # -----------------------
    # Recommendations (simple rules)
    # -----------------------
    recs: List[str] = []

    if kpis["ROI Multiple (3yr)"] < 1.0:
        recs.append("3-year ROI is below 1.0x — consider reducing Year 1 acquisition cost, improving retention, or rebalancing channels toward higher-return sources.")
    else:
        recs.append("3-year ROI is above 1.0x — strategy appears sustainable under current assumptions; consider scaling what’s working.")

    if inputs.retention < 0.55:
        recs.append("Retention is relatively low — stewardship strategies (recurring gifts, donor journeys, major-donor follow-up) may produce outsized improvements.")

    if inputs.cost_growth > 0.10:
        recs.append("Cost growth is high — consider tighter budget controls or shifting effort toward lower-cost fundraising mechanisms.")

    if inputs.revenue_shock < 0:
        recs.append("Revenue shock is negative — use Conservative scenario as a planning baseline and build a contingency plan.")

    if inputs.acquisition_cost_year1_only:
        recs.append("Model assumes Year 2–3 costs are primarily stewardship/maintenance (not full acquisition), aligned with donor retention strategy.")

    return {
        "forecast_df": df,
        "kpis": kpis,
        "budget_df": budget_out,
        "recommendations": recs,
    }
