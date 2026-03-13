from __future__ import annotations
import streamlit as st
import pandas as pd
import io

from .macro_model import MacroInputs, build_macro_forecast
from .reports_pdf import build_macro_pdf

from .charts import (
    macro_3yr_trend_line,
    macro_roi_bar,
    macro_donations_allocation_chart,
    macro_scenario_comparison_chart,
    macro_roi_sensitivity_heatmap,
)


def macro_interpretation(model: dict, assumptions: dict) -> str:
    k = model.get("kpis", {}) or {}

    total_don = float(k.get("Total Donations (3yr)", 0.0))
    total_cost = float(k.get("Total Cost (3yr)", 0.0))
    total_net = float(k.get("Total Net (3yr)", 0.0))
    roi_mult = float(k.get("ROI Multiple (3yr)", 0.0))
    roi_pct = float(k.get("ROI % (3yr)", roi_mult - 1.0))
    c_per_1 = float(k.get("Cost per $1 (3yr)", 0.0))

    lines = []
    lines.append(
        "This Macro View is a strategic planning tool. It assumes that a percentage of current-year donors "
        "will continue donating in the next two years."
    )
    lines.append(
        f"Over the 3-year horizon, the model projects **${total_don:,.0f}** in donations against "
        f"**${total_cost:,.0f}** in modeled cost, resulting in a net of **${total_net:,.0f}**."
    )
    lines.append(
        f"That corresponds to an overall **ROI of {roi_mult:.2f}x** "
        f"(approximately **{roi_pct*100:,.1f}%**) and a **cost per $1 of ${c_per_1:.2f}**."
    )
    lines.append(
        f"Key assumptions include **Donor Continuation Rate = {float(assumptions['Donor Continuation Rate']):.0%}**, "
        f"**Development Margin (Year 1 only) = {float(assumptions['Development Margin (Y1 only)']):.0%}**, and "
        f"**Cost Growth Add-on (Years 2 and 3) = {float(assumptions['Cost Growth Add-on (Y2 & Y3)']):.0%} of base cost per year**."
    )

    return "\n\n".join(lines)


def _build_sensitivity_pivot(base_inputs: MacroInputs) -> pd.DataFrame:
    continuation_vals = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
    cg_vals = [0.00, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20]

    rows = []
    for cont in continuation_vals:
        for cg in cg_vals:
            test_inputs = MacroInputs(
                total_donations_y1=base_inputs.total_donations_y1,
                donor_continuation_rate=cont,
                base_cost_y1=base_inputs.base_cost_y1,
                margin=base_inputs.margin,
                cost_growth=cg,
                donation_shock=base_inputs.donation_shock,
                cost_shock=base_inputs.cost_shock,
            )
            m = build_macro_forecast(test_inputs)
            roi = float(m["kpis"].get("ROI Multiple (3yr)", 0.0))
            rows.append({"Continuation": cont, "CostGrowth": cg, "ROI": roi})

    df = pd.DataFrame(rows)
    return df.pivot(index="Continuation", columns="CostGrowth", values="ROI").sort_index()


def macro_view():
    st.header("Macro 3-Year Strategic View (Donations Forecasting)")
    st.caption(
        "Strategic planning tool: assumes a percentage of current-year donors will continue donating in Years 2 and 3."
    )

    st.subheader("Scenario Presets")
    preset = st.selectbox("Preset", ["Base", "Conservative", "Optimistic", "Custom"], index=0)

    donor_continuation = 0.40
    margin = 0.20
    cost_growth = 0.05
    donation_shock = 0.00
    cost_shock = 0.00

    if preset == "Conservative":
        donor_continuation = 0.30
        margin = 0.25
        cost_growth = 0.08
        donation_shock = -0.03
        cost_shock = 0.03
    elif preset == "Optimistic":
        donor_continuation = 0.50
        margin = 0.15
        cost_growth = 0.03
        donation_shock = 0.03
        cost_shock = 0.00

    colA, colB = st.columns(2)
    total_donations = colA.number_input("Total Donations (Current Year)", min_value=0.0, value=250000.0, step=5000.0)
    base_cost = colB.number_input("Base Cost (BJC Total Cost in Current Year)", min_value=0.0, value=150000.0, step=5000.0)

    st.subheader("Adjustable Assumptions (update anytime)")
    c1, c2, c3, c4 = st.columns(4)
    donor_continuation = c1.slider("Donor Continuation Rate", 0.0, 1.0, float(donor_continuation), 0.05)
    margin = c2.slider("Development Margin (Year 1 only)", 0.0, 0.50, float(margin), 0.01)
    cost_growth = c3.slider("Cost Growth Add-on (Y2 & Y3, % of base cost)", 0.0, 0.25, float(cost_growth), 0.01)
    donation_shock = c4.slider("Donation Shock (applies to all years)", -0.30, 0.30, float(donation_shock), 0.01)

    with st.expander("Advanced"):
        cost_shock = st.slider("Cost Shock (applies to all years)", -0.30, 0.30, float(cost_shock), 0.01)

    inputs = MacroInputs(
        total_donations_y1=float(total_donations),
        donor_continuation_rate=float(donor_continuation),
        base_cost_y1=float(base_cost),
        margin=float(margin),
        cost_growth=float(cost_growth),
        donation_shock=float(donation_shock),
        cost_shock=float(cost_shock),
    )

    model = build_macro_forecast(inputs)
    k = model["kpis"]

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Donations (3yr)", f"${float(k['Total Donations (3yr)']):,.0f}")
    k2.metric("Total Cost (3yr)", f"${float(k['Total Cost (3yr)']):,.0f}")
    k3.metric("Total Net (3yr)", f"${float(k['Total Net (3yr)']):,.0f}")
    k4.metric("ROI Multiple (3yr)", f"{float(k['ROI Multiple (3yr)']):.2f}x")
    k5.metric("Cost per $1 (3yr)", f"${float(k['Cost per $1 (3yr)']):.2f}")

    st.divider()
    t1, t2 = st.tabs(["Charts", "Interpretation"])

    assumptions = {
        "Total Donations (Year 1)": total_donations,
        "Base Cost (Year 1)": base_cost,
        "Donor Continuation Rate": donor_continuation,
        "Development Margin (Y1 only)": margin,
        "Cost Growth Add-on (Y2 & Y3)": cost_growth,
        "Donation Shock": donation_shock,
        "Cost Shock": cost_shock,
        "Preset": preset,
    }

    conservative_inputs = MacroInputs(
        total_donations_y1=inputs.total_donations_y1,
        donor_continuation_rate=max(inputs.donor_continuation_rate - 0.10, 0.0),
        base_cost_y1=inputs.base_cost_y1,
        margin=min(inputs.margin + 0.05, 0.50),
        cost_growth=min(inputs.cost_growth + 0.03, 0.25),
        donation_shock=-0.03,
        cost_shock=0.03,
    )
    optimistic_inputs = MacroInputs(
        total_donations_y1=inputs.total_donations_y1,
        donor_continuation_rate=min(inputs.donor_continuation_rate + 0.10, 1.0),
        base_cost_y1=inputs.base_cost_y1,
        margin=max(inputs.margin - 0.05, 0.0),
        cost_growth=max(inputs.cost_growth - 0.02, 0.0),
        donation_shock=0.03,
        cost_shock=0.00,
    )

    conservative_model = build_macro_forecast(conservative_inputs)
    optimistic_model = build_macro_forecast(optimistic_inputs)

    scenarios_df = pd.DataFrame([
        {
            "Scenario": "Conservative",
            "Total Donations": conservative_model["kpis"]["Total Donations (3yr)"],
            "Total Cost": conservative_model["kpis"]["Total Cost (3yr)"],
            "Net": conservative_model["kpis"]["Total Net (3yr)"],
            "ROI Multiple": conservative_model["kpis"]["ROI Multiple (3yr)"],
        },
        {
            "Scenario": "Base",
            "Total Donations": model["kpis"]["Total Donations (3yr)"],
            "Total Cost": model["kpis"]["Total Cost (3yr)"],
            "Net": model["kpis"]["Total Net (3yr)"],
            "ROI Multiple": model["kpis"]["ROI Multiple (3yr)"],
        },
        {
            "Scenario": "Optimistic",
            "Total Donations": optimistic_model["kpis"]["Total Donations (3yr)"],
            "Total Cost": optimistic_model["kpis"]["Total Cost (3yr)"],
            "Net": optimistic_model["kpis"]["Total Net (3yr)"],
            "ROI Multiple": optimistic_model["kpis"]["ROI Multiple (3yr)"],
        },
    ])

    with t1:
        st.subheader("Donations Forecast Across 3 Years")
        st.plotly_chart(macro_donations_allocation_chart(model["forecast_df"]), use_container_width=True)

        st.subheader("Scenario Comparison")
        st.plotly_chart(macro_scenario_comparison_chart(scenarios_df), use_container_width=True)
        st.dataframe(scenarios_df, use_container_width=True)

        st.subheader("ROI Sensitivity Map")
        pivot = _build_sensitivity_pivot(inputs)
        st.plotly_chart(
            macro_roi_sensitivity_heatmap(pivot, "ROI Sensitivity (3yr): Donor Continuation vs Cost Growth"),
            use_container_width=True
        )
        st.caption("This heatmap shows how ROI changes when donor continuation and cost growth assumptions shift.")

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

    st.divider()
    st.subheader("Download Reports")

    excel_out = io.BytesIO()
    with pd.ExcelWriter(excel_out, engine="xlsxwriter") as writer:
        pd.DataFrame([assumptions]).to_excel(writer, sheet_name="Assumptions", index=False)
        pd.DataFrame([model["kpis"]]).to_excel(writer, sheet_name="KPIs", index=False)
        model["forecast_df"].to_excel(writer, sheet_name="Forecast", index=False)
        scenarios_df.to_excel(writer, sheet_name="Scenarios", index=False)
        pivot.reset_index().to_excel(writer, sheet_name="Sensitivity", index=False)

        pd.DataFrame([{"Interpretation": macro_interpretation(model, assumptions)}]).to_excel(
            writer, sheet_name="Interpretation", index=False
        )

    st.download_button(
        "Download Excel (Macro Forecast + Scenarios + Sensitivity)",
        data=excel_out.getvalue(),
        file_name="bjc_macro_donations_forecast.xlsx",
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
        file_name="bjc_macro_donations_summary.pdf",
        mime="application/pdf",
    )
