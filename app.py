import pandas as pd
import streamlit as st
from datetime import datetime
import traceback

# Micro dependencies
from core.utils import normalize_columns, ensure_datetime, segment_donors_basic, month_floor
from core.metrics import compute_kpis, compute_rollups
from core.charts import line_trend, bar_compare, waterfall_net, donor_mix_pie

# Macro view import with real error capture
macro_view = None
macro_import_error = None

try:
    from core.macro_view import macro_view
except Exception:
    macro_import_error = traceback.format_exc()


st.set_page_config(page_title="BJC Fundraising ROI Dashboard", layout="wide")
st.title("BJC Fundraising ROI Dashboard")
st.caption("Switch between operational tracking (Micro) and 3-year strategic planning (Macro).")

# Toggle: Micro vs Macro
mode = st.sidebar.radio(
    "View Mode",
    ["Micro View (Operational Tracking)", "Macro 3-Year Strategic View"],
    index=0
)

DISABLE_WORD_EXPORT = False


# ======================================================================
# GUIDE TAB
# ======================================================================
def guide_tab():
    st.header("Guide")

    guide_micro, guide_macro = st.tabs(["Guide: Micro View", "Guide: Macro View"])

    with guide_micro:
        st.subheader("Purpose of Micro View")
        st.markdown(
            """
Micro View is the **operational tracking** side of the dashboard.  
It is designed to analyze actual donations and actual fundraising-related costs for a selected period.

It helps answer questions such as:
- How much did we raise?
- How much did it cost?
- What was the net result?
- Which campaign codes performed best?
- Which channels performed best?
- Are donations coming more from new donors or returning donors?
"""
        )

        st.subheader("1) Upload Data (CSV)")
        st.markdown(
            """
This section is in the sidebar.

You upload:
1. **Donations CSV**
2. **Costs CSV**

### Donations CSV
This file should contain actual donation transactions.

Common fields include:
- Date Received
- Amount
- VANID
- Source Code
- Payment Method
- Contact Name
- Contribution ID
- Designation
- Remaining Amount
- Financial Batch

The dashboard maps common donation field names into a standard structure.

### Costs CSV
This file should contain fundraising-related cost entries.

Common fields include:
- date
- cost_amount
- campaign_code
- channel
- cost_type

This file is used to compare funds raised against the costs incurred in generating those funds.
"""
        )

        st.subheader("2) Filters")
        st.markdown(
            """
This section is also in the sidebar.

The filters determine which records are included in the KPIs, charts, and reports.

### Date Range
Limits the analysis to a selected time window.

Use this to review:
- a month
- a quarter
- a campaign period
- a year

### Channel
Filters by fundraising source or method.

Examples may include:
- Email
- Event
- Online
- Mail
- Payment Method, if no separate channel field exists

Use this to understand which source or method performed best.

### Campaign Code
Filters by source code / appeal code / campaign identifier.

Use this to compare:
- different fundraising appeals
- different source codes
- different initiatives

### Donor Segment
Splits donors into:
- **New**
- **Returning**

This is based on the donor’s first appearance in the uploaded dataset.

Use this to understand whether performance is driven more by donor acquisition or existing donor relationships.
"""
        )

        st.subheader("3) KPI Summary Row")
        st.markdown(
            r"""
At the top of Micro View you will see five KPI cards.

### Total Raised
Sum of filtered donations.

\[
\text{Total Raised} = \sum \text{Donation Amount}
\]

### Total Costs
Sum of filtered costs.

\[
\text{Total Costs} = \sum \text{Cost Amount}
\]

### Net Raised
Difference between raised funds and costs.

\[
\text{Net Raised} = \text{Total Raised} - \text{Total Costs}
\]

### ROI
Shows return relative to cost.

\[
\text{ROI} = \frac{\text{Net Raised}}{\text{Total Costs}}
\]

### Cost to Raise \$1
Shows how much it costs to generate one dollar.

\[
\text{Cost to Raise \$1} = \frac{\text{Total Costs}}{\text{Total Raised}}
\]

Interpretation:
- lower cost to raise $1 is generally better
- higher ROI is generally better
"""
        )

        st.subheader("4) Interactive Charts")
        st.markdown(
            """
Micro View contains four chart tabs.

### Trend
This tab shows how fundraising changes over time.

It includes:
- **Monthly Trend line chart** for Raised, Costs, and Net
- **Waterfall chart** showing Raised → Costs → Net

Use this to identify:
- strong months
- weak months
- periods where costs increased
- whether fundraising performance is improving or declining over time

### Compare Campaigns
This tab compares campaign/source codes.

It includes:
- a **Top N slider**
- a campaign-level performance table
- a bar chart comparing Raised vs Costs by campaign code

#### Top N (by Raised)
This slider controls how many campaign codes are shown.

Examples:
- 5 = top 5 campaign codes by donations raised
- 15 = top 15 campaign codes
- 50 = top 50 campaign codes

Use this when you want to focus only on the largest contributors.

### Compare Channels
This tab compares channels or fundraising methods.

It includes:
- a channel-level table
- a bar chart comparing Raised vs Costs by channel

Use this to determine:
- which channel raises the most
- which channel is most efficient
- which channel is costing too much relative to what it brings in

### Donor Mix
This tab shows a pie chart of donations by donor segment.

It answers:
- how much of giving is coming from new donors
- how much is coming from returning donors
"""
        )

        st.subheader("5) Generate Reports")
        st.markdown(
            """
Micro View supports report exports.

### Report Title
Lets you choose the title for the exported report.

### Interpretation / Notes
Lets you add comments or context.

### Download Excel Report
Exports the filtered Micro View results into Excel.

Useful for:
- further analysis
- finance review
- sharing detailed figures

### Download Word Report
Exports a written report with results and notes.

Useful for:
- leadership summaries
- meeting notes
- written documentation
"""
        )

        st.subheader("6) Preview Section")
        st.markdown(
            """
At the bottom of Micro View there is a preview section.

It shows the first 200 rows of:
- filtered donations
- filtered costs

This helps validate:
- that uploads worked correctly
- that filters are working correctly
- that the right fields were mapped

If available, it can also display optional donation fields such as:
- contribution_id
- contact_name
- designation
- payment_method
- remaining_amount
- financial_batch
"""
        )

    with guide_macro:
        st.subheader("Purpose of Macro View")
        st.markdown(
            """
Macro View is the **strategic planning** side of the dashboard.

It is not meant to track individual transactions.  
Instead, it uses high-level assumptions to model how current-year donations may translate into donations and costs over a 3-year planning horizon.

It helps answer questions such as:
- If we receive this level of donations in the current year, what might that mean over the next two years?
- If some donors continue giving, how much value could that create over 3 years?
- How much would it cost over that same horizon?
- What changes under conservative, base, optimistic, or custom assumptions?
"""
        )

        st.subheader("1) Scenario Presets")
        st.markdown(
            """
Macro View begins with a scenario preset selector.

### Base
This is the neutral planning case.

Use it when:
- you want a normal or expected case
- you want a baseline planning view

### Conservative
This is the downside case.

It generally assumes:
- lower donor continuation
- higher cost burden
- weaker donation outcome

Use it for:
- downside planning
- stress testing

### Optimistic
This is the upside case.

It generally assumes:
- stronger donor continuation
- lower cost pressure
- stronger donation outcome

Use it for:
- growth planning
- upside testing

### Custom
This lets leadership set assumptions manually.

Use it when:
- you want to test a specific scenario
- you want assumptions that differ from the preset cases
"""
        )

        st.subheader("2) Input Fields")
        st.markdown(
            """
### Total Donations (Current Year)
This is the current-year donation amount used as the starting point for the model.

The macro model assumes that some percentage of these same donors may continue donating in Years 2 and 3.

### Base Cost (BJC Total Cost in Current Year)
This is the current-year base organizational cost used in the macro model.

It acts as the cost base for:
- Year 1 full cost calculation
- Year 2 cost add-on
- Year 3 cost add-on
"""
        )

        st.subheader("3) Adjustable Assumptions")
        st.markdown(
            r"""
These are the main planning levers in Macro View.

### Donor Continuation Rate
This is the percentage of current-year donors assumed to continue donating in later years.

Formulas:

\[
\text{Year 2 Donations} = \text{Year 1 Donations} \times \text{Donor Continuation Rate}
\]

\[
\text{Year 3 Donations} = \text{Year 2 Donations} \times \text{Donor Continuation Rate}
\]

Higher continuation:
- increases future donations
- improves net impact
- improves ROI

Lower continuation:
- reduces future donations
- weakens ROI

### Development Margin (Year 1 only)
This is the additional Year 1 cost for development effort.

\[
\text{Year 1 Cost} = \text{Base Cost} \times (1 + \text{Margin})
\]

Higher margin:
- raises Year 1 cost
- reduces Year 1 net
- reduces total ROI

### Cost Growth Add-on (Y2 & Y3)
This is the cost add-on used for Years 2 and 3.

\[
\text{Year 2 Cost} = \text{Base Cost} \times \text{Cost Growth}
\]

\[
\text{Year 3 Cost} = \text{Base Cost} \times \text{Cost Growth}
\]

Higher cost growth:
- increases future cost burden
- reduces ROI

### Donation Shock
Applies an upward or downward adjustment to donations.

\[
\text{Donations} \times (1 + \text{Donation Shock})
\]

Positive shock:
- raises donations

Negative shock:
- lowers donations

This is useful for testing:
- changing fundraising conditions
- external environment pressure
- stronger or weaker donor response

### Cost Shock
Applies an upward or downward adjustment to costs.

\[
\text{Cost} \times (1 + \text{Cost Shock})
\]

Positive shock:
- raises costs

Negative shock:
- lowers costs
"""
        )

        st.subheader("4) KPI Summary Row")
        st.markdown(
            r"""
Macro View shows five KPI cards.

### Total Donations (3yr)
Sum of Year 1, Year 2, and Year 3 donations.

### Total Cost (3yr)
Sum of Year 1, Year 2, and Year 3 modeled cost.

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

        st.subheader("5) Charts Tab")
        st.markdown(
            """
The Charts tab contains the main strategic visuals.

### Donations Forecast Across 3 Years
Shows how donations evolve across the 3-year planning horizon.

Use this to explain:
- current-year donation starting point
- Year 2 continuation effect
- Year 3 continuation effect

### Scenario Comparison
Compares:
- Conservative
- Base
- Optimistic

Shows:
- Total Donations
- Total Cost
- Net
- ROI Multiple

Use this to explain downside risk, expected case, and upside potential.

### ROI Sensitivity Map
This heatmap shows how ROI changes when:
- donor continuation changes
- cost growth changes

Use this to identify:
- which assumptions matter most
- where risk is concentrated
- where ROI improves meaningfully

### Forecast Trend & ROI by Year
Shows:
- Donations
- Cost
- Net
- ROI by year

Use this to understand:
- whether value is front-loaded or future-loaded
- whether costs fall sharply after Year 1
- whether ROI improves over time

### Forecast Table
Shows the exact numbers behind the charts.

Use this for:
- validation
- presentations
- export support
"""
        )

        st.subheader("6) Interpretation Tab")
        st.markdown(
            """
This tab provides written interpretation of the Macro model.

It summarizes:
- total donations
- total cost
- total net
- ROI
- key assumptions

It also shows model recommendations.

Use this tab when:
- presenting to leadership
- creating written summaries
- documenting assumptions and implications
"""
        )

        st.subheader("7) Download Reports")
        st.markdown(
            """
Macro View supports:

### Excel Download
Includes:
- assumptions
- KPI summary
- forecast table
- scenario table
- sensitivity table
- interpretation

### PDF Download
Provides a concise executive-style summary of the Macro view.
"""
        )

        st.subheader("8) Practical Interpretation of Macro View")
        st.markdown(
            """
Macro View is meant for planning, not transaction reconciliation.

It should be explained as:
- a strategic estimate
- a scenario-based forward planning tool
- a way to translate current-year donations into a 3-year planning conversation

It is most useful when leadership wants to ask:
- what happens if donor continuation changes?
- what happens if cost growth changes?
- what is our expected 3-year return under different cases?
"""
        )


# ======================================================================
# MICRO VIEW
# ======================================================================
def micro_view():
    st.subheader("Micro View (Operational Tracking)")
    st.caption("Upload donations + cost CSV files to compute ROI, explore trends, and generate reports.")

    # Sidebar uploads
    st.sidebar.header("1) Upload Data (CSV)")
    donations_file = st.sidebar.file_uploader("Donations CSV (EveryAction export)", type=["csv"], key="don_csv")
    costs_file = st.sidebar.file_uploader("Costs CSV (your template)", type=["csv"], key="cost_csv")

    with st.expander("Required columns + common aliases"):
        st.markdown("""
**Donations CSV required fields:**
- `date` (GiftDate, ContributionDate, Date Received)
- `amount` (Amount, ContributionAmount, GiftAmount)
- `donor_id` (VANID, PersonID, DonorID)
- `campaign_code` (AppealCode, Campaign, Source Code, FundraisingCode)
- `channel` (Channel, Source, Medium, Payment Method)

**Costs CSV required fields:**
- `date` (ExpenseDate, PaidDate)
- `cost_amount` (Amount, Expense, Cost)
- `campaign_code` (optional but recommended; can be blank -> UNMAPPED)
- `channel` (recommended; can be blank -> UNMAPPED)
- `cost_type` (Direct, Labor, Overhead) (optional; default Direct)
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

        optional_cols = [
            "contribution_id", "contact_name", "designation",
            "payment_method", "remaining_amount", "financial_batch"
        ]
        present_optional = [c for c in optional_cols if c in d.columns]
        if present_optional:
            st.write("Donation extra fields (if available in upload)")
            st.dataframe(d[present_optional].head(200), use_container_width=True)

        st.write("Costs (filtered)")
        st.dataframe(c.head(200), use_container_width=True)


# ======================================================================
# ROUTER
# ======================================================================
tabs = st.tabs(["Guide", "Dashboard"])

with tabs[0]:
    guide_tab()

with tabs[1]:
    if mode.startswith("Micro"):
        micro_view()
    else:
        st.subheader("Macro 3-Year Strategic View (Donations Forecasting)")
        if macro_view is None:
            st.error("Macro view failed to load.")
            if macro_import_error:
                st.code(macro_import_error)
        else:
            macro_view()
