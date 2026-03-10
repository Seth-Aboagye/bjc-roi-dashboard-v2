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
    macro_revenue_allocation_chart,
    macro_scenario_comparison_chart,
    macro_roi_sensitivity_heatmap,
)


def macro_interpretation(model: dict, assumptions: dict) -> str:
    k = model.get("kpis", {}) or {}
    f = model.get("forecast_df")

    total_rev = float(k.get("Total Revenue (3yr)", 0.0))
    total_cost = float(k.get("Total Cost (3yr)", 0.0))
    total_net = float(k.get("Total Net (3yr)", 0.0))
    roi_mult = float(k.get("ROI Multiple (3yr)", 0.0))
    roi_pct = float(k.get("ROI % (3yr)", roi_mult - 1.0))
    c_per_1 = float(k.get("Cost per $1 (3yr)", 0.0))

    # Budget note
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

    y1_real = assumptions.get("Year 1 Realization Rate", None)
    carry = assumptions.get("Carryover Factor", None)
    margin = assumptions.get("Development Margin (Y1 only)", None)
    cg = assumptions.get("Cost Growth Add-on (Y2 & Y3)", None)

    lines = []
    lines.append(
        f"This Macro View is a **strategic planning allocation**: it spreads the current-year fundraising pool "
        f"across the current year and the next two years to support budgeting and operational planning."
    )
    lines.append(
        f"Over the 3-year horizon, the model projects **${total_rev:,.0f}** in planned revenue allocation against "
        f"**${total_cost:,.0f}** in modeled cost, resulting in a net of **${total_net:,.0f}**."
    )
    lines.append(
        f"That corresponds to an overall **ROI of {roi_mult:.2f}x** (approximately **{roi_pct*100:,.1f}%**) "
        f"and a **cost per $1 of ${c_per_1:.2f}**."
    )

    a_bits = []
    if y1_real is not None:
        a_bits.append(f"Year 1 realization = **{float(y1_real):.0%}**")
    if carry is not None:
        a_bits.append(f"Carryover factor = **{float(carry):.0%}**")
    if margin is not None:
        a_bits.append(f"Development margin (Y1 only) = **{float(margin):.0%}**")
    if cg is not None:
        a_bits.append(f"Cost growth add-on (Y2 & Y3) = **{float(cg):.0%} of base cost per year**")
    if a_bits:
        lines.append("Key assumptions: " + "; ".join(a_bits) + ".")

    if budget_note:
        lines.append(budget_note)

    if roi_mult < 1.0:
        lines.append("This scenario indicates costs exceed the allocated 3-year revenue impact; consider lowering Year-1 margin, improving allocation assumptions, or tightening cost growth.")
    elif roi_mult < 2.0:
        lines.append("This scenario indicates a positive but moderate return; efficiency gains and disciplined cost growth would strengthen net impact.")
    else:
        lines.append("This scenario indicates strong returns; the priority becomes maintaining discipline as the organization scales activities.")

    return "\n\n".join(lines)


def _build_sensitivity_pivot(base_inputs: MacroInputs) -> pd.DataFrame:
    """
    Build ROI Multiple heatmap across Carryover Factor (rows) and Cost Growth (cols).
    Keeps everything else fixed.
    """
    carry_vals = [round(x, 2) for x in [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]]
    cg_vals = [round(x, 2) for x in [0.00, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20]]

    rows = []
    for carry in carry_vals:
        for cg in cg_vals:
            test_inputs = MacroInputs(
                total_raised_y1=base_inputs.total_raised_y1,
                year1_realization=base_inputs.year1_realization,
                carryover_factor=carry,
                base_cost_y1=base_inputs.base_cost_y1,
                margin=base_inputs.margin,
                cost_growth=cg,
                revenue_shock=base_inputs.revenue_shock,
                cost_shock=base_inputs.cost_shock,
            )
            m = build_macro_forecast(test_inputs)
            roi = float(m["kpis"].get("ROI Multiple (3yr)", 0.0))
            rows.append({"Carryover": carry, "CostGrowth": cg, "ROI": roi})

    df = pd.DataFrame(rows)
    pivot = df.pivot(index="Carryover", columns="CostGrowth", values="ROI").sort_index()
    return pivot


def macro_view():
    st.header("Macro 3-Year Strategic View (Investment Forecasting + Budget Comparison)")
    st.caption(
        "Strategic planning tool: allocate the current-year fundraising pool across the current year and the next two years. "
        "This is a rolling approach—update inputs each year based on actual results and new expectations."
    )

    # Presets
    st.subheader("Scenario Presets")
    preset = st.selectbox("Preset", ["Base", "Conservative", "Optimistic", "Custom"], index=0)

    # Defaults
    year1_realization = 0.40
    carryover = 0.60
    margin = 0.20
    cost_growth = 0.05
    revenue_shock = 0.00
    cost_shock = 0.00

    if preset == "Conservative":
        year1_realization = 0.30
        carryover = 0.50
        margin = 0.25
        cost_growth = 0.08
        revenue_shock = -0.03
        cost_shock = +0.03
    elif preset == "Optimistic":
        year1_realization = 0.50
        carryover = 0.70
        margin = 0.15
        cost_growth = 0.03
        revenue_shock = +0.03
        cost_shock = 0.00

    colA, colB = st.columns(2)
    total_raised = colA.number_input(
        "Total Raised (Current Year Pool)",
        min_value=0.0,
        value=250000.0,
        step=5000.0
    )
    base_cost = colB.number_input(
        "Base Cost (BJC Total Cost in Current Year)",
        min_value=0.0,
        value=150000.0,
        step=5000.0
    )

    st.subheader("Adjustable Assumptions (update anytime)")
    c1, c2, c3, c4, c5 = st.columns(5)
    year1_realization = c1.slider("Year 1 Realization Rate", 0.0, 1.0, float(year1_realization), 0.05)
    carryover = c2.slider("Carryover Factor (of remaining)", 0.0, 1.0, float(carryover), 0.05)
    margin = c3.slider("Development Margin (Year 1 only)", 0.0, 0.50, float(margin), 0.01)
    cost_growth = c4.slider("Cost Growth Add-on (Y2 & Y3, % of base cost)", 0.0, 0.25, float(cost_growth), 0.01)
    revenue_shock = c5.slider("Revenue Shock (applies to all years)", -0.30, 0.30, float(revenue_shock), 0.01)

    with st.expander("Advanced"):
        cost_shock = st.slider("Cost Shock (applies to all years)", -0.30, 0.30, float(cost_shock), 0.01)

    inputs = MacroInputs(
        total_raised_y1=float(total_raised),
        year1_realization=float(year1_realization),
        carryover_factor=float(carryover),
        base_cost_y1=float(base_cost),
        margin=float(margin),
        cost_growth=float(cost_growth),
        revenue_shock=float(revenue_shock),
        cost_shock=float(cost_shock),
    )

    # Budget upload
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

    # Base model
    model = build_macro_forecast(inputs, budget_df=budget_df)
    k = model["kpis"]

    # KPIs (safe keys already ensured by macro_model)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Revenue (3yr)", f"${float(k['Total Revenue (3yr)']):,.0f}")
    k2.metric("Total Cost (3yr)", f"${float(k['Total Cost (3yr)']):,.0f}")
    k3.metric("Total Net (3yr)", f"${float(k['Total Net (3yr)']):,.0f}")
    k4.metric("ROI Multiple (3yr)", f"{float(k['ROI Multiple (3yr)']):.2f}x")
    k5.metric("Cost per $1 (3yr)", f"${float(k['Cost per $1 (3yr)']):.2f}")

    # Tabs
    st.divider()
    t1, t2, t3 = st.tabs(["Charts", "Interpretation", "Budget & Variance"])

    assumptions = {
        "Total Raised (Year 1 Pool)": total_raised,
        "Base Cost (Year 1)": base_cost,
        "Year 1 Realization Rate": year1_realization,
        "Carryover Factor": carryover,
        "Development Margin (Y1 only)": margin,
        "Cost Growth Add-on (Y2 & Y3)": cost_growth,
        "Revenue Shock": revenue_shock,
        "Cost Shock": cost_shock,
        "Preset": preset,
    }

    # Scenario models for comparison (simple +/- adjustments)
    conservative_inputs = MacroInputs(
        total_raised_y1=inputs.total_raised_y1,
        year1_realization=max(inputs.year1_realization - 0.10, 0.0),
        carryover_factor=max(inputs.carryover_factor - 0.10, 0.0),
        base_cost_y1=inputs.base_cost_y1,
        margin=min(inputs.margin + 0.05, 0.50),
        cost_growth=min(inputs.cost_growth + 0.03, 0.25),
        revenue_shock=-0.03,
        cost_shock=+0.03,
    )
    optimistic_inputs = MacroInputs(
        total_raised_y1=inputs.total_raised_y1,
        year1_realization=min(inputs.year1_realization + 0.10, 1.0),
        carryover_factor=min(inputs.carryover_factor + 0.10, 1.0),
        base_cost_y1=inputs.base_cost_y1,
        margin=max(inputs.margin - 0.05, 0.0),
        cost_growth=max(inputs.cost_growth - 0.02, 0.0),
        revenue_shock=+0.03,
        cost_shock=0.00,
    )
    conservative_model = build_macro_forecast(conservative_inputs)
    optimistic_model = build_macro_forecast(optimistic_inputs)

    scenarios_df = pd.DataFrame([
        {
            "Scenario": "Conservative",
            "Total Revenue": conservative_model["kpis"]["Total Revenue (3yr)"],
            "Total Cost": conservative_model["kpis"]["Total Cost (3yr)"],
            "Net": conservative_model["kpis"]["Total Net (3yr)"],
            "ROI Multiple": conservative_model["kpis"]["ROI Multiple (3yr)"],
        },
        {
            "Scenario": "Base",
            "Total Revenue": model["kpis"]["Total Revenue (3yr)"],
            "Total Cost": model["kpis"]["Total Cost (3yr)"],
            "Net": model["kpis"]["Total Net (3yr)"],
            "ROI Multiple": model["kpis"]["ROI Multiple (3yr)"],
        },
        {
            "Scenario": "Optimistic",
            "Total Revenue": optimistic_model["kpis"]["Total Revenue (3yr)"],
            "Total Cost": optimistic_model["kpis"]["Total Cost (3yr)"],
            "Net": optimistic_model["kpis"]["Total Net (3yr)"],
            "ROI Multiple": optimistic_model["kpis"]["ROI Multiple (3yr)"],
        },
    ])

    with t1:
        st.subheader("Revenue Allocation (Strategic Planning)")
        st.plotly_chart(macro_revenue_allocation_chart(model["forecast_df"]), use_container_width=True)

        st.subheader("Scenario Comparison")
        st.plotly_chart(macro_scenario_comparison_chart(scenarios_df), use_container_width=True)
        st.dataframe(scenarios_df, use_container_width=True)

        st.subheader("ROI Sensitivity Map")
        pivot = _build_sensitivity_pivot(inputs)
        st.plotly_chart(
            macro_roi_sensitivity_heatmap(pivot, "ROI Sensitivity (3yr): Carryover Factor vs Cost Growth"),
            use_container_width=True
        )
        st.caption("This heatmap shows how ROI changes when carryover and cost growth assumptions shift.")

        st.subheader("Forecast Trend & ROI by Year")
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

    # Downloads
    st.divider()
    st.subheader("Download Reports")

    excel_out = io.BytesIO()
    with pd.ExcelWriter(excel_out, engine="xlsxwriter") as writer:
        pd.DataFrame([assumptions]).to_excel(writer, sheet_name="Assumptions", index=False)
        pd.DataFrame([model["kpis"]]).to_excel(writer, sheet_name="KPIs", index=False)
        model["forecast_df"].to_excel(writer, sheet_name="Forecast", index=False)
        scenarios_df.to_excel(writer, sheet_name="Scenarios", index=False)
        pivot.reset_index().to_excel(writer, sheet_name="Sensitivity", index=False)
        if model.get("budget_df") is not None:
            model["budget_df"].to_excel(writer, sheet_name="Budget_Compare", index=False)

        pd.DataFrame([{"Interpretation": macro_interpretation(model, assumptions)}]).to_excel(
            writer, sheet_name="Interpretation", index=False
        )

    st.download_button(
        "Download Excel (Macro Forecast + Scenarios + Sensitivity)",
        data=excel_out.getvalue(),
        file_name="bjc_macro_forecast_scenarios_sensitivity.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    pdf_bytes = build_macro_pdf(
        title="BJC 3-Year Strategic Planning Forecast (Macro View)",
        kpis=model["kpis"],
        assumptions=assumptions,
        recs=model.get("recommendations", []),
        forecast_df=model["forecast_df"],
    )
    st.download_button(
        "Download PDF (Executive Summary)",
        data=pdf_bytes,
        file_name="bjc_macro_forecast_summary.pdf",
        mime="application/pdf",
    )
