import pandas as pd
import streamlit as st
from datetime import datetime
import traceback

from core.utils import normalize_columns, ensure_datetime, segment_donors_basic, month_floor
from core.metrics import compute_kpis, compute_rollups
from core.charts import line_trend, bar_compare, waterfall_net, donor_mix_pie

macro_view = None
macro_import_error = None

try:
    from core.macro_view import macro_view
except Exception:
    macro_import_error = traceback.format_exc()

st.set_page_config(page_title="BJC Fundraising ROI Dashboard", layout="wide")
st.title("BJC Fundraising ROI Dashboard")
st.caption("Switch between operational tracking (Micro) and 3-year strategic planning (Macro).")

mode = st.sidebar.radio(
    "View Mode",
    ["Micro View (Operational Tracking)", "Macro 3-Year Strategic View"],
    index=0
)

DISABLE_WORD_EXPORT = False


def guide_tab():
    st.header("Guide")

    guide_micro, guide_macro = st.tabs(["Guide: Micro View", "Guide: Macro View"])

    with guide_micro:
        st.subheader("Purpose of Micro View")
        st.markdown(
            """
Micro View is the operational tracking side of the dashboard.

It analyzes actual donations and costs for a selected period and helps answer:
- How much did we raise?
- How much did it cost?
- What was the net result?
- Which campaign codes performed best?
- Which channels performed best?
- Are donations coming from new donors or returning donors?
"""
        )

        st.subheader("1) Upload Data (CSV)")
        st.markdown(
            """
### Donations CSV
Contains actual donation transactions.

### Costs CSV
Contains fundraising-related costs.

The dashboard standardizes uploaded fields so they can be analyzed consistently.
"""
        )

        st.subheader("2) Filters")
        st.markdown(
            """
### Date Range
Limits analysis to a selected period.

### Channel
Filters by fundraising source or method.

### Campaign Code
Filters by source code / campaign identifier.

### Donor Segment
Splits donors into New and Returning.
"""
        )

        st.subheader("3) KPI Summary Row")
        st.markdown(
            r"""
### Total Raised
\[
\text{Total Raised} = \sum \text{Donation Amount}
\]

### Total Costs
\[
\text{Total Costs} = \sum \text{Cost Amount}
\]

### Net Raised
\[
\text{Net Raised} = \text{Total Raised} - \text{Total Costs}
\]

### ROI
\[
\text{ROI} = \frac{\text{Net Raised}}{\text{Total Costs}}
\]

### Cost to Raise \$1
\[
\text{Cost to Raise \$1} = \frac{\text{Total Costs}}{\text{Total Raised}}
\]
"""
        )

        st.subheader("4) Interactive Charts")
        st.markdown(
            """
### Trend
Shows monthly Raised, Costs, and Net, plus a waterfall summary.

### Compare Campaigns
Compares campaign codes and includes the Top N slider.

### Compare Channels
Compares performance by channel.

### Donor Mix
Shows donation distribution between new and returning donors.
"""
        )

        st.subheader("5) Generate Reports")
        st.markdown(
            """
### Excel Report
Exports filtered results to Excel.

### Word Report
Exports a written summary report.
"""
        )

    with guide_macro:
        st.subheader("Purpose of Macro View")
        st.markdown(
            """
Macro View is the strategic planning side of the dashboard.

It assumes:
- Year 1 donations are known
- Year 2 donations are a percentage of Year 1 donations from retained donors
- Year 3 donations are a percentage of Year 2 donations from retained donors
- cost follows a Year 1 margin and compounded cost growth in Years 2 and 3
- cost growth can increase or decrease
"""
        )

        st.subheader("1) Inputs")
        st.markdown(
            r"""
### Total Donations (Year 1)
This is the Year 1 donation base.

### Base Cost (Year 1)
This is the Year 1 cost base.

### Donor Continuation Rate
\[
\text{Year 2 Donations} = \text{Year 1 Donations} \times \text{Donor Continuation Rate}
\]

\[
\text{Year 3 Donations} = \text{Year 2 Donations} \times \text{Donor Continuation Rate}
\]

### Development Margin (Year 1 only)
\[
\text{Year 1 Cost} = \text{Base Cost} \times (1 + \text{Margin})
\]

### Cost Growth Add-on (Years 2 and 3)
\[
\text{Year 2 Cost} = \text{Year 1 Cost} \times (1 + \text{Cost Growth})
\]

\[
\text{Year 3 Cost} = \text{Year 2 Cost} \times (1 + \text{Cost Growth})
\]

A negative cost growth value means cost reduction in Years 2 and 3.
"""
        )

        st.subheader("2) KPI Summary Row")
        st.markdown(
            r"""
### Total Donations (3yr)
Sum of Year 1, Year 2, and Year 3 donations.

### Total Cost (3yr)
Sum of Year 1, Year 2, and Year 3 cost.

### Total Net (3yr)
\[
\text{Total Donations} - \text{Total Cost}
\]

### ROI Multiple (3yr)
\[
\frac{\text{Total Donations}}{\text{Total Cost}}
\]

### Cost per \$1 (3yr)
\[
\frac{\text{Total Cost}}{\text{Total Donations}}
\]
"""
        )

        st.subheader("3) Charts")
        st.markdown(
            """
### Donations Allocation Across 3 Years
Shows the share of 3-year donations by year.

### Year-by-Year Comparison
Compares Donations, Cost, and Net by year.

### ROI Sensitivity Map
Shows how ROI changes when donor continuation and cost growth change. Because continuation compounds year to year, improvements in retention can significantly increase long-term donations.

### Forecast Trend & ROI by Year
Shows Donations, Cost, Net, and ROI by year.

### Forecast Table
Shows the exact yearly figures.
"""
        )

        st.subheader("4) Interpretation")
        st.markdown(
            """
Provides written analysis of total donations, total cost, total net, ROI, assumptions, and recommendations.
"""
        )

        st.subheader("5) Download Reports")
        st.markdown(
            """
### Excel Report
Exports assumptions, KPIs, forecast, sensitivity, and interpretation.

### PDF Report
Exports a concise executive summary.
"""
        )


def micro_view():
    st.subheader("Micro View (Operational Tracking)")
    st.caption("Upload donations + cost CSV files to compute ROI, explore trends, and generate reports.")

    st.sidebar.header("1) Upload Data (CSV)")
    donations_file = st.sidebar.file_uploader("Donations CSV (EveryAction export)", type=["csv"], key="don_csv")
    costs_file = st.sidebar.file_uploader("Costs CSV (your template)", type=["csv"], key="cost_csv")

    with st.expander("Required columns + common aliases"):
        st.markdown("""
**Donations CSV required fields:**
- `date`
- `amount`
- `donor_id`
- `campaign_code`
- `channel`

**Costs CSV required fields:**
- `date`
- `cost_amount`
- `campaign_code`
- `channel`
- `cost_type`
""")

    if not donations_file or not costs_file:
        st.info("Upload both **Donations CSV** and **Costs CSV** to begin.")
        st.stop()

    donations_raw = pd.read_csv(donations_file)
    costs_raw = pd.read_csv(costs_file)

    donations_df = normalize_columns(donations_raw, kind="donations")
    costs_df = normalize_columns(costs_raw, kind="costs")

    donations_df = ensure_datetime(donations_df, "date")
    costs_df = ensure_datetime(costs_df, "date")

    donations_df = segment_donors_basic(donations_df)
    donations_df["month"] = donations_df["date"].apply(month_floor)
    costs_df["month"] = costs_df["date"].apply(month_floor)

    st.sidebar.markdown("---")
    st.sidebar.header("2) Filters")

    min_date = min(donations_df["date"].min(), costs_df["date"].min())
    max_date = max(donations_df["date"].max(), costs_df["date"].max())

    date_range = st.sidebar.date_input(
        "Date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date()
    )

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_dt = pd.to_datetime(date_range[0])
        end_dt = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    else:
        start_dt = pd.to_datetime(date_range)
        end_dt = start_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    channels = sorted(set(donations_df["channel"].dropna().unique()).union(set(costs_df["channel"].dropna().unique())))
    campaigns = sorted(set(donations_df["campaign_code"].dropna().unique()).union(set(costs_df["campaign_code"].dropna().unique())))
    segments = sorted(donations_df["donor_segment"].dropna().unique())

    sel_channels = st.sidebar.multiselect("Channel", options=channels, default=channels)
    sel_campaigns = st.sidebar.multiselect("Campaign code", options=campaigns, default=campaigns)
    sel_segments = st.sidebar.multiselect("Donor segment", options=segments, default=segments)

    d = donations_df[
        (donations_df["date"] >= start_dt) & (donations_df["date"] <= end_dt) &
        (donations_df["channel"].isin(sel_channels)) &
        (donations_df["campaign_code"].isin(sel_campaigns)) &
        (donations_df["donor_segment"].isin(sel_segments))
    ].copy()

    c = costs_df[
        (costs_df["date"] >= start_dt) & (costs_df["date"] <= end_dt) &
        (costs_df["channel"].isin(sel_channels)) &
        (costs_df["campaign_code"].isin(sel_campaigns))
    ].copy()

    kpis = compute_kpis(d, c)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Raised", f"${kpis['total_raised']:,.0f}")
    k2.metric("Total Costs", f"${kpis['total_costs']:,.0f}")
    k3.metric("Net Raised", f"${kpis['net_raised']:,.0f}")
    k4.metric("ROI", f"{kpis['roi']*100:,.1f}%")
    k5.metric("Cost to Raise $1", f"${kpis['cost_to_raise_1']:,.2f}")

    st.markdown("---")
    st.subheader("Interactive Charts")

    tab1, tab2, tab3, tab4 = st.tabs(["Trend", "Compare Campaigns", "Compare Channels", "Donor Mix"])

    with tab1:
        st.plotly_chart(line_trend(d, c), use_container_width=True)
        st.plotly_chart(waterfall_net(kpis), use_container_width=True)

    with tab2:
        roll = compute_rollups(d, c, by="campaign_code")
        top_n = st.slider("Top N (by Raised)", 5, 50, 15)
        roll_top = roll.sort_values("raised", ascending=False).head(top_n)
        st.dataframe(roll_top, use_container_width=True)
        st.plotly_chart(bar_compare(roll_top, group_col="campaign_code"), use_container_width=True)

    with tab3:
        roll = compute_rollups(d, c, by="channel").sort_values("raised", ascending=False)
        st.dataframe(roll, use_container_width=True)
        st.plotly_chart(bar_compare(roll, group_col="channel"), use_container_width=True)

    with tab4:
        st.plotly_chart(donor_mix_pie(d), use_container_width=True)

    st.markdown("---")
    st.subheader("Generate Reports")

    report_title = st.text_input("Report title", value="BJC Fundraising ROI Report")
    notes = st.text_area("Interpretation / Notes (optional)", value="")

    payload = {
        "title": report_title,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "filters": {
            "start": str(start_dt.date()),
            "end": str(end_dt.date()),
            "channels": sel_channels,
            "campaigns": sel_campaigns,
            "segments": sel_segments
        },
        "kpis": kpis,
    }

    from core.reports_excel import build_excel_report

    colx, colw = st.columns(2)

    with colx:
        xlsx_bytes = build_excel_report(d, c, payload)
        st.download_button(
            "Download Excel report",
            data=xlsx_bytes,
            file_name="bjc_roi_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with colw:
        if DISABLE_WORD_EXPORT:
            st.info("Word export disabled in this environment.")
        else:
            from core.reports_word import build_word_report
            docx_bytes = build_word_report(d, c, payload, notes=notes)
            st.download_button(
                "Download Word report",
                data=docx_bytes,
                file_name="bjc_roi_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    st.markdown("---")
    with st.expander("Preview (first 200 rows)"):
        st.write("Donations (filtered)")
        st.dataframe(d.head(200), use_container_width=True)
        st.write("Costs (filtered)")
        st.dataframe(c.head(200), use_container_width=True)


tabs = st.tabs(["Guide", "Dashboard"])

with tabs[0]:
    guide_tab()

with tabs[1]:
    if mode.startswith("Micro"):
        micro_view()
    else:
        if macro_view is None:
            st.error("Macro view failed to load.")
            if macro_import_error:
                st.code(macro_import_error)
        else:
            macro_view()
