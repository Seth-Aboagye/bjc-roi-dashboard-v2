from __future__ import annotations
import streamlit as st
import pandas as pd
import io

from .macro_model import MacroInputs, build_macro_forecast
from .budget_templates import budget_template_excel
from .reports_pdf import build_macro_pdf

from .charts import (
    macro_3yr_trend_line,
    macro_roi_bar,
    macro_budget_vs_forecast_bar,
    macro_variance_bars,
)

def macro_interpretation(model: dict, assumptions: dict) -> str:
    k = model.get("kpis", {}) or {}
    f = model.get("forecast_df")

    total_rev = float(k.get("Total Revenue (3yr)", 0.0))
    total_cost = float(k.get("Total Cost (3yr)", 0.0))
    total_net = float(k.get("Total Net (3yr)", 0.0))
    roi_mult = float(k.get("ROI Multiple (3yr)", 0.0))
    roi_pct = float(k.get("ROI % (3yr)", max(roi_mult - 1.0, 0.0)))
    c_per_1 = float(k.get("Cost per $1 (3yr)", 0.0))

    improving = declining = False
    if f is not None and "ROI %" in f.columns and len(f) >= 2:
        improving = float(f["ROI %"].iloc[-1]) > float(f["ROI %"].iloc[0])
        declining = float(f["ROI %"].iloc[-1]) < float(f["ROI %"].iloc[0])

    budget_note = ""
    b = model.get("budget_df")
    if b is not None and all(col in b.columns for col in ["Revenue Var", "Cost Var", "Net Var"]):
        rev_var = float(b["Revenue Var"].sum())
        cost_var = float(b["Cost Var"].sum())
        net_var = float(b["Net Var"].sum())
        def _fmt(x: float) -> str:
            sign = "+" if x >= 0 else "-"
            return f"{sign}${abs(x):,.0f}"
        budget_note = (
            f"Against the uploaded budget, the 3-year forecast shows "
            f"**Revenue variance {_fmt(rev_var)}**, **Cost variance {_fmt(cost_var)}**, "
            f"and **Net variance {_fmt(net_var)}** (Forecast − Budget)."
        )

    lines = []
    lines.append(
        f"Over the 3-year horizon, the model projects **${total_rev:,.0f}** in revenue impact against "
        f"**${total_cost:,.0f}** in modeled fundraising/development cost, resulting in a net of "
        f"**${total_net:,.0f}**."
    )
    lines.append(
        f"That corresponds to an overall **ROI of {roi_mult:.2f}x** (approximately **{roi_pct*100:,.1f}%**) "
        f"and a **cost to raise $1 of ${c_per_1:.2f}**."
    )

    if improving:
        lines.append("ROI **improves over time**, suggesting retained/repeat value outweighs modeled cost growth.")
    elif declining:
        lines.append("ROI **declines over time**, suggesting cost growth or weaker retention is outpacing retained revenue.")
    else:
        lines.append("ROI appears **relatively stable across the 3 years** under current assumptions.")

    if assumptions.get("Acquisition Cost Year 1 Only", False):
        lines.append(
            "Costs assume **Year 1 includes acquisition effort**, while **Years 2–3 reflect lower ongoing stewardship cost**, "
            "adjusted by the selected cost growth and any cost shock."
        )

    if budget_note:
        lines.append(budget_note)

    return "\n\n".join(lines)

def macro_view():
    st.header("Macro 3-Year Strategic View (Investment Forecasting + Budget Comparison)")
    st.caption("Adjust assumptions for changing economic/business conditions and compare forecast to budget.")

    st.subheader("Scenario Presets")
    preset = st.selectbox("Preset", ["Base", "Conservative", "Optimistic", "Custom"], index=0)

    retention = 0.60
    margin = 0.20
    cost_growth = 0.05
    revenue_shock = 0.00
    cost_shock = 0.00

    if preset == "Conservative":
        retention = 0.50
        revenue_shock = -0.10
        cost_growth = 0.08
        cost_shock = +0.05
    elif preset == "Optimistic":
        retention = 0.70
        revenue_shock = +0.05
        cost_growth = 0.03
        cost_shock = 0.00

    colA, colB, colC = st.columns(3)
    total_raised = colA.number_input("Total Raised (Year 1)", min_value=0.0, value=250000.0, step=5000.0)
    base_cost = colB.number_input("Base Cost (Year 1)", min_value=0.0, value=150000.0, step=5000.0)

    # IMPORTANT: default to Katie model
    method = colC.selectbox(
        "Revenue Method",
        ["prior", "remaining"],
        index=0,
        help="prior = 60% of prior year (Katie). remaining = 60% of remaining after Year 1 (often becomes $0)."
    )

    st.subheader("Adjustable Assumptions (update anytime)")
    c1, c2, c3, c4, c5 = st.columns(5)
    retention = c1.slider("Retention", 0.0, 1.0, float(retention), 0.05)
    margin = c2.slider("Margin", 0.0, 0.50, float(margin), 0.01)
    cost_growth = c3.slider("Cost Growth", 0.0, 0.25, float(cost_growth), 0.01)
    revenue_shock = c4.slider("Revenue Shock", -0.30, 0.30, float(revenue_shock), 0.01)
    cost_shock = c5.slider("Cost Shock", -0.30, 0.30, float(cost_shock), 0.01)

    st.subheader("Cost Structure (Macro)")
    acq_only = st.checkbox(
        "Apply Base Cost only in Year 1 (Years 2–3 use ongoing stewardship cost only, adjusted by Cost Growth)",
        value=True
    )

    inputs = MacroInputs(
        total_raised_y1=float(total_raised),
        base_cost_y1=float(base_cost),
        retention=float(retention),
        revenue_method=str(method),
        revenue_shock=float(revenue_shock),
        margin=float(margin),
        cost_growth=float(cost_growth),
        cost_shock=float(cost_shock),
        acquisition_cost_year1_only=bool(acq_only),
    )

    st.divider()
    st.subheader("Budget Comparison (optional)")
    st.download_button(
        "Download Budget Template (Excel)",
        data=budget_template_excel(),
        file_name="bjc_budget_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    budget_file = st.file_uploader("Upload Budget (Excel or CSV)", type=["xlsx", "csv"])
    budget_df = None
    if budget_file is not None:
        if budget_file.name.lower().endswith(".csv"):
            budget_df = pd.read_csv(budget_file)
        else:
            budget_df = pd.read_excel(budget_file)
        budget_df.columns = [str(c).strip() for c in budget_df.columns]

    model = build_macro_forecast(inputs, budget_df=budget_df)
    k = model.get("kpis", {}) or {}

    # SAFE KPI rendering (no KeyError)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Revenue (3yr)", f"${float(k.get('Total Revenue (3yr)', 0.0)):,.0f}")
    k2.metric("Total Cost (3yr)", f"${float(k.get('Total Cost (3yr)', 0.0)):,.0f}")
    k3.metric("Total Net (3yr)", f"${float(k.get('Total Net (3yr)', 0.0)):,.0f}")
    k4.metric("ROI Multiple (3yr)", f"{float(k.get('ROI Multiple (3yr)', 0.0)):.2f}x")
    k5.metric("Cost per $1 (3yr)", f"${float(k.get('Cost per $1 (3yr)', 0.0)):.2f}")

    st.divider()
    t1, t2, t3 = st.tabs(["Charts", "Interpretation", "Budget & Variance"])

    assumptions = {
        "Total Raised (Y1)": total_raised,
        "Base Cost (Y1)": base_cost,
        "Retention": retention,
        "Revenue Method": method,
        "Revenue Shock": revenue_shock,
        "Margin": margin,
        "Cost Growth": cost_growth,
        "Cost Shock": cost_shock,
        "Preset": preset,
        "Acquisition Cost Year 1 Only": bool(acq_only),
    }

    with t1:
        st.subheader("Charts")
        st.plotly_chart(macro_3yr_trend_line(model["forecast_df"]), use_container_width=True)
        st.plotly_chart(macro_roi_bar(model["forecast_df"]), use_container_width=True)
        st.caption("Forecast table")
        st.dataframe(model["forecast_df"], use_container_width=True)

    with t2:
        st.subheader("Interpretation")
        st.markdown(macro_interpretation(model, assumptions))
        st.subheader("Model Recommendations")
        for r in model.get("recommendations", []):
            st.write(f"• {r}")

    with t3:
        if model.get("budget_df") is None:
            st.info("Upload a budget file to enable Budget vs Forecast and variance charts.")
        else:
            b = model["budget_df"]
            st.subheader("Budget vs Forecast")
            st.plotly_chart(macro_budget_vs_forecast_bar(b), use_container_width=True)
            st.subheader("Variance vs Budget (Forecast - Budget)")
            st.plotly_chart(macro_variance_bars(b), use_container_width=True)
            st.caption("Budget comparison table")
            st.dataframe(b, use_container_width=True)

    st.divider()
    st.subheader("Download Reports")

    excel_out = io.BytesIO()
    with pd.ExcelWriter(excel_out, engine="xlsxwriter") as writer:
        pd.DataFrame([assumptions]).to_excel(writer, sheet_name="Assumptions", index=False)
        pd.DataFrame([model["kpis"]]).to_excel(writer, sheet_name="KPIs", index=False)
        model["forecast_df"].to_excel(writer, sheet_name="Forecast", index=False)
        if model.get("budget_df") is not None:
            model["budget_df"].to_excel(writer, sheet_name="Budget_Compare", index=False)
        pd.DataFrame([{"Interpretation": macro_interpretation(model, assumptions)}]).to_excel(
            writer, sheet_name="Interpretation", index=False
        )

    st.download_button(
        "Download Excel (Macro Forecast + Budget Compare)",
        data=excel_out.getvalue(),
        file_name="bjc_macro_forecast_budget.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    pdf_bytes = build_macro_pdf(
        title="BJC 3-Year Development Investment Forecast (Macro View)",
        kpis=model["kpis"],
        assumptions=assumptions,
        recs=model["recommendations"],
        forecast_df=model["forecast_df"],
    )
    st.download_button(
        "Download PDF (Executive Summary)",
        data=pdf_bytes,
        file_name="bjc_macro_forecast_summary.pdf",
        mime="application/pdf",
    )
