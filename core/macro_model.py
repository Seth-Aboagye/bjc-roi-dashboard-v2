from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

def _safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b not in (0, None) else 0.0

@dataclass
class MacroInputs:
    total_raised_y1: float
    base_cost_y1: float
    retention: float = 0.60
    revenue_method: str = "prior"   # "prior" is Katie’s model
    revenue_shock: float = 0.0

    margin: float = 0.20
    cost_growth: float = 0.05
    cost_shock: float = 0.0

    # NEW: Katie update
    acquisition_cost_year1_only: bool = True

def _build_revenue_series(total_raised_y1: float, retention: float, method: str, revenue_shock: float) -> list[float]:
    """
    Revenue impact (macro):
    - prior (Katie): Y2 = retention * Y1, Y3 = retention * Y2
    - remaining: Y2 = retention * remaining_after_Y1, Y3 = retention * remaining_after_Y2
      (Note: if remaining_after_Y1 is 0, revenues will be 0)
    """
    y1 = float(total_raised_y1)
    method = (method or "prior").strip().lower()

    if method == "remaining":
        remaining = max(y1 - y1, 0.0)  # after taking 100% in year 1, remaining becomes 0 by definition
        y2 = retention * remaining
        remaining2 = max(remaining - y2, 0.0)
        y3 = retention * remaining2
    else:
        # default / Katie model
        y2 = retention * y1
        y3 = retention * y2

    # Apply revenue shock to Y2/Y3 (not Y1) to model environment changes
    y2 = y2 * (1.0 + revenue_shock)
    y3 = y3 * (1.0 + revenue_shock)

    return [y1, y2, y3]

def _build_cost_series(
    base_cost_y1: float,
    margin: float,
    cost_growth: float,
    cost_shock: float,
    acquisition_cost_year1_only: bool
) -> list[float]:
    """
    Cost (macro):
    - If acquisition_cost_year1_only=True (Katie):
        Year 1 cost = base_cost * (1 + margin)   (full acquisition effort + development margin)
        Years 2–3 cost = ONLY the margin portion (stewardship/development), grown by cost_growth
            Y2 = (base_cost * margin) * (1+cost_growth)
            Y3 = (base_cost * margin) * (1+cost_growth)^2
      Then apply cost_shock to Y2/Y3.
    - Else (legacy macro):
        Costs grow on the full cost base each year:
            Y1 = base_cost*(1+margin)
            Y2 = Y1*(1+cost_growth)
            Y3 = Y2*(1+cost_growth)
      Then apply cost_shock to Y2/Y3.
    """
    base_cost_y1 = float(base_cost_y1)
    margin = float(margin)
    cost_growth = float(cost_growth)
    cost_shock = float(cost_shock)

    y1 = base_cost_y1 * (1.0 + margin)

    if acquisition_cost_year1_only:
        stewardship_base = base_cost_y1 * margin  # only “margin” portion continues
        y2 = stewardship_base * (1.0 + cost_growth)
        y3 = stewardship_base * ((1.0 + cost_growth) ** 2)
    else:
        y2 = y1 * (1.0 + cost_growth)
        y3 = y2 * (1.0 + cost_growth)

    # Apply cost shock to ongoing years only
    y2 = y2 * (1.0 + cost_shock)
    y3 = y3 * (1.0 + cost_shock)

    return [y1, y2, y3]

def build_macro_forecast(inputs: MacroInputs, budget_df: pd.DataFrame | None = None) -> dict:
    years = ["Year 1", "Year 2", "Year 3"]

    revenue = _build_revenue_series(
        total_raised_y1=inputs.total_raised_y1,
        retention=inputs.retention,
        method=inputs.revenue_method,
        revenue_shock=inputs.revenue_shock,
    )

    cost = _build_cost_series(
        base_cost_y1=inputs.base_cost_y1,
        margin=inputs.margin,
        cost_growth=inputs.cost_growth,
        cost_shock=inputs.cost_shock,
        acquisition_cost_year1_only=inputs.acquisition_cost_year1_only,
    )

    df = pd.DataFrame({"Year": years, "Revenue": revenue, "Cost": cost})
    df["Net"] = df["Revenue"] - df["Cost"]

    # ROI multiple per year (Revenue / Cost)
    df["ROI Multiple"] = df.apply(lambda r: _safe_div(r["Revenue"], r["Cost"]), axis=1)
    df["ROI %"] = df["ROI Multiple"] - 1.0

    total_rev = float(df["Revenue"].sum())
    total_cost = float(df["Cost"].sum())
    total_net = float(df["Net"].sum())
    roi_mult = _safe_div(total_rev, total_cost)

    kpis = {
        "Total Revenue (3yr)": total_rev,
        "Total Cost (3yr)": total_cost,
        "Total Net (3yr)": total_net,
        "ROI Multiple (3yr)": roi_mult,
        "ROI % (3yr)": roi_mult - 1.0,
        # IMPORTANT: always include cost per $1 to prevent KeyError
        "Cost per $1 (3yr)": _safe_div(total_cost, total_rev),
    }

    # Budget compare (optional)
    budget_out = None
    if budget_df is not None and len(budget_df) > 0:
        b = budget_df.copy()
        b.columns = [str(c).strip() for c in b.columns]

        # Expect Year, Budget Revenue, Budget Cost (but tolerate common variants)
        col_year = next((c for c in b.columns if c.lower() == "year"), None)
        col_brev = next((c for c in b.columns if c.lower() in ("budget revenue", "budget_revenue", "revenue_budget")), None)
        col_bcost = next((c for c in b.columns if c.lower() in ("budget cost", "budget_cost", "cost_budget")), None)

        if col_year and col_brev and col_bcost:
            b = b[[col_year, col_brev, col_bcost]].rename(
                columns={col_year: "Year", col_brev: "Budget Revenue", col_bcost: "Budget Cost"}
            )
            # merge forecast
            m = pd.merge(b, df[["Year", "Revenue", "Cost", "Net"]], on="Year", how="left").fillna(0)
            m["Budget Net"] = m["Budget Revenue"] - m["Budget Cost"]

            m["Revenue Var"] = m["Revenue"] - m["Budget Revenue"]
            m["Cost Var"] = m["Cost"] - m["Budget Cost"]
            m["Net Var"] = m["Net"] - m["Budget Net"]
            budget_out = m

    # Recommendations (simple, readable)
    recs = []
    if kpis["ROI Multiple (3yr)"] < 1.0:
        recs.append("Overall ROI is below 1.0x (costs exceed returns). Re-check retention, reduce acquisition cost, or focus more on high-yield donor segments.")
    elif kpis["ROI Multiple (3yr)"] < 2.0:
        recs.append("ROI is positive but moderate. Improving retention and controlling ongoing stewardship cost would materially improve net resources.")
    else:
        recs.append("ROI is strong. Consider scaling the strategies producing the highest retained revenue while monitoring cost growth assumptions.")

    if inputs.revenue_method == "remaining":
        recs.append("Revenue Method is set to 'remaining'. If Year 2 and Year 3 show $0, switch to 'prior' to model 60% of prior-year retained revenue (Katie’s approach).")

    return {
        "forecast_df": df,
        "kpis": kpis,
        "budget_df": budget_out,
        "recommendations": recs,
    }
