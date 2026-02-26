import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# =========================
# MICRO VIEW CHARTS (EXISTING)
# =========================
def line_trend(d: pd.DataFrame, c: pd.DataFrame):
    d_m = d.groupby("month")["amount"].sum().reset_index().rename(columns={"amount": "raised"})
    c_m = c.groupby("month")["cost_amount"].sum().reset_index().rename(columns={"cost_amount": "costs"})
    m = pd.merge(d_m, c_m, on="month", how="outer").fillna(0).sort_values("month")
    m["net"] = m["raised"] - m["costs"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m["month"], y=m["raised"], mode="lines+markers", name="Raised"))
    fig.add_trace(go.Scatter(x=m["month"], y=m["costs"], mode="lines+markers", name="Costs"))
    fig.add_trace(go.Scatter(x=m["month"], y=m["net"], mode="lines+markers", name="Net"))
    fig.update_layout(title="Monthly Trend: Raised vs Costs vs Net", xaxis_title="Month", yaxis_title="USD")
    return fig

def bar_compare(rollup: pd.DataFrame, group_col: str):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=rollup[group_col], y=rollup["raised"], name="Raised"))
    fig.add_trace(go.Bar(x=rollup[group_col], y=rollup["costs"], name="Costs"))
    fig.update_layout(
        barmode="group",
        title=f"Raised vs Costs by {group_col}",
        xaxis_title=group_col,
        yaxis_title="USD"
    )
    return fig

def waterfall_net(kpis: dict):
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative", "relative", "total"],
        x=["Raised", "Costs", "Net"],
        y=[kpis["total_raised"], -kpis["total_costs"], kpis["net_raised"]],
        connector={"line": {"dash": "dot"}}
    ))
    fig.update_layout(title="Waterfall: Raised → Costs → Net", yaxis_title="USD")
    return fig

def donor_mix_pie(d: pd.DataFrame):
    s = d.groupby("donor_segment")["amount"].sum().reset_index()
    fig = px.pie(s, values="amount", names="donor_segment", title="Donations by Donor Segment")
    return fig


# =========================
# MACRO VIEW CHARTS (NEW)
# Expected columns for forecast_df:
#   year (or Year), raised (or Revenue), cost (or Cost), net (or Net), roi (or ROI)
# These functions are flexible: they will work with either naming style.
# =========================

def _col(df: pd.DataFrame, *candidates: str) -> str:
    """Return the first column name found in df from candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of these columns found: {candidates}. Available: {list(df.columns)}")

def macro_3yr_trend_line(forecast_df: pd.DataFrame):
    year_col = _col(forecast_df, "year", "Year")
    raised_col = _col(forecast_df, "raised", "Revenue", "Raised")
    cost_col = _col(forecast_df, "cost", "Cost", "Costs")
    net_col = _col(forecast_df, "net", "Net")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=forecast_df[year_col], y=forecast_df[raised_col], mode="lines+markers", name="Raised"))
    fig.add_trace(go.Scatter(x=forecast_df[year_col], y=forecast_df[cost_col], mode="lines+markers", name="Cost"))
    fig.add_trace(go.Scatter(x=forecast_df[year_col], y=forecast_df[net_col], mode="lines+markers", name="Net"))
    fig.update_layout(title="3-Year Forecast: Raised vs Cost vs Net", xaxis_title="Year", yaxis_title="USD")
    return fig

def macro_roi_bar(forecast_df: pd.DataFrame):
    year_col = _col(forecast_df, "year", "Year")
    roi_col = _col(forecast_df, "roi", "ROI", "ROI %", "ROI Multiple")

    # If ROI is stored as a fraction (0.25), show %; if it's a multiple (1.25x), show multiple.
    vals = forecast_df[roi_col].astype(float)
    is_fraction = vals.max() <= 1.0  # heuristic
    y = vals * 100.0 if is_fraction else vals
    y_label = "ROI (%)" if is_fraction else "ROI (Multiple)"

    fig = go.Figure()
    fig.add_trace(go.Bar(x=forecast_df[year_col], y=y, name=y_label))
    fig.update_layout(title=f"3-Year Forecast {y_label}", xaxis_title="Year", yaxis_title=y_label)
    return fig

def macro_cost_per_dollar_bar(forecast_df: pd.DataFrame):
    year_col = _col(forecast_df, "year", "Year")
    cpd_col = _col(forecast_df, "cost_per_1", "Cost per $1", "Cost per $1 Raised", "Cost per $1 (3yr)", "Cost per $1")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=forecast_df[year_col], y=forecast_df[cpd_col], name="Cost per $1"))
    fig.update_layout(title="Cost Efficiency: Cost per $1 Raised (by Year)", xaxis_title="Year", yaxis_title="USD")
    return fig

def macro_budget_vs_forecast_bar(budget_compare_df: pd.DataFrame):
    """
    budget_compare_df expected columns (from macro_model merge):
      Year, Budget Revenue, Budget Cost, Revenue, Cost
    Also supports:
      year, budget_raised, budget_cost, raised, cost
    """
    year_col = _col(budget_compare_df, "Year", "year")
    # revenue
    bud_rev = _col(budget_compare_df, "Budget Revenue", "budget_raised", "budget_revenue")
    fc_rev = _col(budget_compare_df, "Revenue", "raised", "Forecast Revenue", "forecast_revenue")
    # cost
    bud_cost = _col(budget_compare_df, "Budget Cost", "budget_cost")
    fc_cost = _col(budget_compare_df, "Cost", "cost", "Forecast Cost", "forecast_cost")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=budget_compare_df[year_col], y=budget_compare_df[bud_rev], name="Budget Revenue"))
    fig.add_trace(go.Bar(x=budget_compare_df[year_col], y=budget_compare_df[fc_rev], name="Forecast Revenue"))
    fig.add_trace(go.Bar(x=budget_compare_df[year_col], y=budget_compare_df[bud_cost], name="Budget Cost"))
    fig.add_trace(go.Bar(x=budget_compare_df[year_col], y=budget_compare_df[fc_cost], name="Forecast Cost"))
    fig.update_layout(
        title="Budget vs Forecast (Revenue & Cost)",
        barmode="group",
        xaxis_title="Year",
        yaxis_title="USD"
    )
    return fig

def macro_variance_bars(budget_compare_df: pd.DataFrame):
    """
    budget_compare_df expected columns:
      Year, Revenue Var, Cost Var, Net Var
    """
    year_col = _col(budget_compare_df, "Year", "year")
    rev_var = _col(budget_compare_df, "Revenue Var", "revenue_var")
    cost_var = _col(budget_compare_df, "Cost Var", "cost_var")
    net_var = _col(budget_compare_df, "Net Var", "net_var")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=budget_compare_df[year_col], y=budget_compare_df[rev_var], name="Revenue Var"))
    fig.add_trace(go.Bar(x=budget_compare_df[year_col], y=budget_compare_df[cost_var], name="Cost Var"))
    fig.add_trace(go.Bar(x=budget_compare_df[year_col], y=budget_compare_df[net_var], name="Net Var"))
    fig.update_layout(
        title="Variance vs Budget (Forecast - Budget)",
        barmode="group",
        xaxis_title="Year",
        yaxis_title="USD"
    )
    return fig

def macro_sensitivity_heatmap(retention_values, cost_growth_values, base_inputs: dict, compute_forecast_fn):
    """
    Heatmap of Year 3 ROI (%) for scenario planning.

    - retention_values: e.g. [0.4, 0.5, 0.6, 0.7, 0.8]
    - cost_growth_values: e.g. [0.00, 0.05, 0.10, 0.15, 0.20]
    - base_inputs: dict of other assumptions
    - compute_forecast_fn: function(inputs_dict) -> forecast_df with columns year/roi
    """
    z = []
    for r in retention_values:
        row = []
        for g in cost_growth_values:
            inputs = dict(base_inputs)
            inputs["retention_multiplier"] = r
            inputs["cost_growth_pct"] = g

            f = compute_forecast_fn(inputs)
            year_col = _col(f, "year", "Year")
            roi_col = _col(f, "roi", "ROI", "ROI %", "ROI Multiple")

            # take last year ROI
            last_year = f[year_col].iloc[-1]
            y3_roi = float(f.loc[f[year_col] == last_year, roi_col].iloc[0])

            # assume fraction -> convert to %
            if y3_roi <= 1.0:
                y3_roi = y3_roi * 100.0

            row.append(y3_roi)
        z.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=[f"{int(g*100)}%" for g in cost_growth_values],
        y=[f"{int(r*100)}%" for r in retention_values],
        colorbar=dict(title="Year 3 ROI (%)")
    ))
    fig.update_layout(
        title="Sensitivity: Year 3 ROI vs Retention & Cost Growth",
        xaxis_title="Cost Growth",
        yaxis_title="Retention"
    )
    return fig