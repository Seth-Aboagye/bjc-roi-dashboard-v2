import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# =========================
# MICRO VIEW CHARTS
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
    fig.update_layout(
        title="Monthly Trend: Raised vs Costs vs Net",
        xaxis_title="Month",
        yaxis_title="USD"
    )
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
# MACRO VIEW HELPERS
# =========================
def _col(df: pd.DataFrame, *candidates: str) -> str:
    """Return the first column name found in df from candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of these columns found: {candidates}. Available: {list(df.columns)}")


# =========================
# MACRO VIEW CHARTS
# =========================
def macro_3yr_trend_line(forecast_df: pd.DataFrame):
    """
    Expects forecast_df with at least:
    Year, Revenue, Cost, Net
    """
    year_col = _col(forecast_df, "year", "Year")
    revenue_col = _col(forecast_df, "Revenue", "raised", "Raised")
    cost_col = _col(forecast_df, "Cost", "cost", "Costs")
    net_col = _col(forecast_df, "Net", "net")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=forecast_df[year_col], y=forecast_df[revenue_col],
        mode="lines+markers", name="Revenue"
    ))
    fig.add_trace(go.Scatter(
        x=forecast_df[year_col], y=forecast_df[cost_col],
        mode="lines+markers", name="Cost"
    ))
    fig.add_trace(go.Scatter(
        x=forecast_df[year_col], y=forecast_df[net_col],
        mode="lines+markers", name="Net"
    ))
    fig.update_layout(
        title="3-Year Forecast: Revenue vs Cost vs Net",
        xaxis_title="Year",
        yaxis_title="USD"
    )
    return fig


def macro_roi_bar(forecast_df: pd.DataFrame):
    """
    Shows ROI Multiple or ROI % by year, depending on available column.
    """
    year_col = _col(forecast_df, "year", "Year")

    if "ROI Multiple" in forecast_df.columns:
        y = forecast_df["ROI Multiple"].astype(float)
        y_label = "ROI Multiple"
    elif "ROI %" in forecast_df.columns:
        y = forecast_df["ROI %"].astype(float) * 100.0
        y_label = "ROI (%)"
    else:
        roi_col = _col(forecast_df, "ROI", "roi")
        vals = forecast_df[roi_col].astype(float)
        if vals.max() <= 1.0:
            y = vals * 100.0
            y_label = "ROI (%)"
        else:
            y = vals
            y_label = "ROI Multiple"

    fig = go.Figure()
    fig.add_trace(go.Bar(x=forecast_df[year_col], y=y, name=y_label))
    fig.update_layout(
        title=f"3-Year Forecast {y_label}",
        xaxis_title="Year",
        yaxis_title=y_label
    )
    return fig


def macro_cost_per_dollar_bar(forecast_df: pd.DataFrame):
    """
    Optional utility if you later add Cost per $1 by year to forecast_df.
    """
    year_col = _col(forecast_df, "year", "Year")
    cpd_col = _col(
        forecast_df,
        "cost_per_1", "Cost per $1", "Cost per $1 Raised", "Cost per $1 (3yr)"
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(x=forecast_df[year_col], y=forecast_df[cpd_col], name="Cost per $1"))
    fig.update_layout(
        title="Cost Efficiency: Cost per $1 by Year",
        xaxis_title="Year",
        yaxis_title="USD"
    )
    return fig


def macro_budget_vs_forecast_bar(budget_compare_df: pd.DataFrame):
    """
    Expected columns:
    - Year
    - Budget Revenue
    - Budget Cost
    - Revenue
    - Cost
    """
    year_col = _col(budget_compare_df, "Year", "year")
    bud_rev = _col(budget_compare_df, "Budget Revenue", "budget_revenue", "BudgetRevenue")
    fc_rev = _col(budget_compare_df, "Revenue", "revenue")
    bud_cost = _col(budget_compare_df, "Budget Cost", "budget_cost", "BudgetCost")
    fc_cost = _col(budget_compare_df, "Cost", "cost")

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
    Expected columns:
    - Year
    - Revenue Var
    - Cost Var
    - Net Var
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


def macro_revenue_allocation_chart(forecast_df: pd.DataFrame):
    """
    Shows how the current-year fundraising pool is allocated across 3 years.
    Expects columns: Year, Revenue
    """
    year_col = _col(forecast_df, "Year", "year")
    revenue_col = _col(forecast_df, "Revenue", "revenue", "Raised", "raised")

    df = forecast_df[[year_col, revenue_col]].copy()
    df.columns = ["Year", "Revenue"]

    fig = px.pie(
        df,
        values="Revenue",
        names="Year",
        title="Allocation of Current-Year Fundraising Across 3-Year Planning Horizon",
        hole=0.35,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def macro_scenario_comparison_chart(scenarios_df: pd.DataFrame):
    """
    scenarios_df expected columns:
    - Scenario
    - Net
    - optionally Total Revenue, Total Cost, ROI Multiple
    """
    fig = px.bar(
        scenarios_df,
        x="Scenario",
        y="Net",
        text="Net",
        title="Scenario Comparison (3-Year Net Impact)"
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig.update_layout(
        yaxis_title="USD",
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False
    )
    return fig


def macro_roi_sensitivity_heatmap(pivot: pd.DataFrame, title: str = "ROI Sensitivity Map") -> go.Figure:
    """
    Expects a pivot table where:
    - index = Carryover Factor
    - columns = Cost Growth
    - values = ROI Multiple
    """
    x = [float(c) for c in pivot.columns]
    y = [float(i) for i in pivot.index]
    z = pivot.values

    fig = go.Figure(
        data=go.Heatmap(
            x=x,
            y=y,
            z=z,
            colorbar=dict(title="ROI Multiple"),
            hovertemplate=(
                "Cost Growth: %{x:.2f}<br>"
                "Carryover: %{y:.2f}<br>"
                "ROI: %{z:.2f}x<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Cost Growth Add-on (as % of base cost)",
        yaxis_title="Carryover Factor (of remaining)",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig
