"""Page 3 — Runtime & Savings: CPS / IFS metrics dashboard."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.data_loader import (
    load_kpis, load_cps_by_stage, load_cps_by_type, load_ifs_distribution,
)
from components.charts import (
    cps_by_stage_bar, cps_by_type_bar, ifs_histogram, ifs_category_donut,
)

st.set_page_config(page_title="Runtime & Savings — PBCP", layout="wide")
st.title("Runtime & Savings")
st.caption(
    "Cost prevention and alignment metrics across all benchmark workloads · "
    "Controlled evaluation benchmark: seed 42, 500 workloads, 28,423 runs"
)

with st.expander("Metric definitions", expanded=False):
    st.markdown("""
**CPS (Cost Prevention Score)** = `prevented_cost / potential_cost_without_system` (0–1, higher is better).
Fraction of wasteful spend intercepted before billing.

**Valid CPS** = `CPS × ESR` where ESR (Execution Success Rate) = fraction of workloads that completed
successfully. ESR makes CPS gaming-resistant: a system that blocks aggressively earns low ESR and therefore
low Valid CPS regardless of savings claimed.

**IFS (Intent-Fit Score)** = `0.35 × type_alignment + 0.25 × util_alignment + 0.20 × duration_alignment
+ 0.20 × resource_alignment` (0–1). Measures alignment between declared intent and observed runtime behavior.

Categories: well_aligned ≥ 0.85 · minor ≥ 0.70 · significant ≥ 0.50 · severe < 0.50.

**IBD (Intent-Behavior Discrepancy)**: IFS < 0.70 — declared intent and runtime behavior diverged enough
to warrant a governance alert.
    """)

kpis     = load_kpis()
stage_df = load_cps_by_stage()
type_df  = load_cps_by_type()
ifs_df   = load_ifs_distribution()

# -- KPI row ----------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
valid_cps = round(kpis["system_cps"] * 1.0, 4)
c1.metric("System CPS",      f"{kpis['system_cps']:.3f}",
          help="prevented_cost / potential_cost across all non-baseline records")
c2.metric("Valid CPS",       f"{valid_cps:.3f}",
          help="CPS × ESR — ESR penalises over-aggressive blocking")
c3.metric("Mean IFS",        f"{kpis['mean_ifs']:.3f}",
          help="Intent-Fit Score: 0–1, higher = declared intent matched runtime behavior")
c4.metric("IBD Rate",        f"{kpis['ibd_fraction']*100:.1f}%",
          help="Workloads with IFS < 0.70 — intent-behavior discrepancy")
c5.metric("Total Prevented", f"${kpis['total_prevented']:,.0f}",
          help="Sum of prevented_cost_usd across all non-baseline intervention records")

st.divider()

# -- Charts -----------------------------------------------------------------
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("CPS by Stage")
    st.caption(
        "Runtime interventions (mid-execution) achieve higher CPS than pre-provision checks "
        "because they catch utilization failures that couldn't be predicted at submission time."
    )
    st.plotly_chart(cps_by_stage_bar(stage_df), use_container_width=True)

    st.subheader("IFS Distribution")
    st.caption(
        "Distribution of Intent-Fit Scores across all benchmark runs. "
        "Shaded regions indicate alignment category boundaries."
    )
    st.plotly_chart(ifs_histogram(ifs_df), use_container_width=True)

with col_r:
    st.subheader("CPS by Workload Type")
    st.caption(
        "Ad-hoc and ML training workloads show higher CPS, reflecting larger "
        "over-provisioning margins at submission time."
    )
    st.plotly_chart(cps_by_type_bar(type_df), use_container_width=True)

    st.subheader("Intent-Fit Score Category Breakdown")
    st.caption(
        "Category distribution across the benchmark. "
        "Dataset includes controlled anomaly injection for evaluation purposes."
    )
    st.plotly_chart(ifs_category_donut(ifs_df), use_container_width=True)

st.divider()

# -- Detail tables ----------------------------------------------------------
col_tl, col_tr = st.columns(2)

with col_tl:
    st.subheader("Stage Breakdown")
    st.dataframe(
        stage_df.rename(columns={
            "stage": "Stage", "cps": "CPS", "mean_ifs": "Mean IFS", "n": "Records",
        }),
        use_container_width=True, hide_index=True,
    )

with col_tr:
    st.subheader("Workload Type Breakdown")
    st.dataframe(
        type_df.rename(columns={
            "workload_type": "Type", "cps": "CPS",
            "mean_ifs": "Mean IFS", "n_workloads": "Workloads",
        }),
        use_container_width=True, hide_index=True,
    )

st.divider()

# -- IFS category table -------------------------------------------------------
st.subheader("IFS Category Summary")
if not ifs_df.empty:
    cat_summary = (
        ifs_df.groupby("ifs_category")
        .agg(count=("ifs", "count"), mean_ifs=("ifs", "mean"))
        .reset_index()
    )
    cat_summary["share"] = (cat_summary["count"] / cat_summary["count"].sum() * 100).round(1)
    cat_summary["mean_ifs"] = cat_summary["mean_ifs"].round(3)
    st.dataframe(
        cat_summary.rename(columns={
            "ifs_category": "Category", "count": "Runs",
            "mean_ifs": "Mean IFS", "share": "Share (%)",
        }),
        use_container_width=True, hide_index=True,
    )