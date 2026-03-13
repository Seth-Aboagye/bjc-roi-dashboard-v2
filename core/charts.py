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
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of these columns found: {candidates}. Available: {list(df.columns)}")


# =========================
# MACRO VIEW CHARTS
# =========================
def macro_3yr_trend_line(forecast_df: pd.DataFrame):
    year_col = _col(forecast_df, "Year", "year")
    donations_col = _col(forecast_df, "Donations", "donations")
    cost_col = _col(forecast_df, "Cost", "cost")
    net_col = _col(forecast_df, "Net", "net")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=forecast_df[year_col], y=forecast_df[donations_col],
        mode="lines+markers", name="Donations"
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
        title="3-Year Forecast: Donations vs Cost vs Net",
        xaxis_title="Year",
        yaxis_title="USD"
    )
    return fig


def macro_roi_bar(forecast_df: pd.DataFrame):
    year_col = _col(forecast_df, "Year", "year")

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


def macro_donations_allocation_chart(forecast_df: pd.DataFrame):
    year_col = _col(forecast_df, "Year", "year")
    donations_col = _col(forecast_df, "Donations", "donations")

    df = forecast_df[[year_col, donations_col]].copy()
    df.columns = ["Year", "Donations"]

    fig = px.pie(
        df,
        values="Donations",
        names="Year",
        title="Donations Forecast Across 3-Year Planning Horizon",
        hole=0.35,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def macro_scenario_comparison_chart(scenarios_df: pd.DataFrame):
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
                "Donor Continuation Rate: %{y:.2f}<br>"
                "ROI: %{z:.2f}x<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Cost Growth Add-on (as % of base cost)",
        yaxis_title="Donor Continuation Rate",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig
