"""Page 3 — Runtime & Savings: CPS / IFS metrics."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.data_loader import (
    load_kpis, load_cps_by_stage, load_cps_by_type,
    load_ifs_distribution,
)
from components.charts import (
    cps_by_stage_bar, cps_by_type_bar, ifs_histogram, ifs_category_donut,
)
from components.sidebar import render as render_sidebar

st.set_page_config(page_title="Runtime & Savings — PBCP", layout="wide")
render_sidebar()
st.title("Runtime & Savings")
st.markdown(
    "How much did PBCP save, and did the workloads keep their promises? "
    "CPS tracks the money; **IFS (Intent-Fit Score)**, Sreeja's metric, tracks whether each job's runtime matched its declared intent."
)
st.caption(
    "Cost prevention and alignment metrics across the controlled evaluation benchmark · "
    "seed 42 · 500 workloads · 28,423 runs"
)

st.markdown("""
<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;">
  <span class="badge badge-sim">Controlled Benchmark</span>
  <span class="badge badge-price">Published Cloud Pricing</span>
  <span class="badge badge-warn">Controlled Anomaly Injection</span>
</div>
""", unsafe_allow_html=True)

with st.expander("Metric definitions", expanded=False):
    st.markdown("""
**CPS (Cost Prevention Score)** = `prevented_cost / potential_cost_without_system` (0–1).
Fraction of wasteful spend intercepted before billing.

**Valid CPS** = `CPS × ESR`. ESR (Execution Success Rate) penalizes over-aggressive blocking to
prevent gaming: a system that blocks every submission achieves CPS = 1 but ESR ≈ 0.

**IFS (Intent-Fit Score)** — cosine similarity between intent and behavior embeddings.
Sub-scores shown are interpretable components of the embedding-based calculation.

**IBD (Intent-Behavior Discrepancy)**: IFS < 0.65 triggers anomaly detection and root-cause attribution.

Note: Benchmark includes controlled anomaly injection to evaluate governance effectiveness
under realistic cloud waste scenarios. IBD rates reflect injected fault rates, not production baselines.
    """)

kpis     = load_kpis()
stage_df = load_cps_by_stage()
type_df  = load_cps_by_type()
ifs_df   = load_ifs_distribution()

# -- KPI row -------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
valid_cps = round(kpis["system_cps"] * 1.0, 4)
c1.metric("System CPS",      f"{kpis['system_cps']:.3f}",
          help="prevented_cost / potential_cost across all non-baseline records")
c2.metric("Valid CPS",       f"{valid_cps:.3f}",
          help="CPS × ESR — ESR penalises over-aggressive blocking")
c3.metric("Mean IFS",        f"{kpis['mean_ifs']:.3f}",
          help="Intent-Fit Score mean across benchmark (controlled injection included)")
c4.metric("IBD Rate",        f"{kpis['ibd_fraction']*100:.0f}%",
          help="Workloads with IFS < 0.65 — includes controlled anomaly injection")
c5.metric("Total Prevented", f"${kpis['total_prevented']:,.0f}",
          help="Sum of prevented_cost_usd across all non-baseline intervention records")

st.caption(
    "Benchmark includes controlled anomaly injection to evaluate governance "
    "effectiveness under realistic cloud waste scenarios."
)

st.divider()

# -- Charts -------------------------------------------------------------------
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("CPS by Stage")
    st.caption(
        "Runtime interventions achieve higher CPS because they catch utilization failures "
        "that cannot be fully predicted at submission time."
    )
    st.plotly_chart(cps_by_stage_bar(stage_df), use_container_width=True)

    st.subheader("IFS Distribution")
    st.caption(
        "Distribution across all benchmark runs. Shaded regions indicate alignment "
        "category boundaries. Includes controlled anomaly injection."
    )
    st.plotly_chart(ifs_histogram(ifs_df), use_container_width=True)

with col_r:
    st.subheader("CPS by Workload Type")
    st.caption(
        "Ad-hoc and ML training workloads show higher CPS, reflecting larger "
        "over-provisioning margins at submission time."
    )
    st.plotly_chart(cps_by_type_bar(type_df), use_container_width=True)

    st.subheader("Intent-Fit Score — Category Breakdown")
    st.caption(
        "Category distribution across the benchmark population. "
        "Controlled anomaly injection is used to evaluate detection sensitivity."
    )
    st.plotly_chart(ifs_category_donut(ifs_df), use_container_width=True)

st.divider()

# -- Detail tables ------------------------------------------------------------
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

# -- IFS Category Summary -----------------------------------------------------
st.subheader("IFS Category Summary")
st.caption(
    "Alignment category distribution across the full benchmark. "
    "Benchmark includes controlled anomaly injection to evaluate governance "
    "effectiveness under realistic cloud waste scenarios."
)
if not ifs_df.empty:
    cat_summary = (
        ifs_df.groupby("ifs_category")
        .agg(count=("ifs", "count"), mean_ifs=("ifs", "mean"))
        .reset_index()
    )
    cat_summary["share_%"] = (cat_summary["count"] / cat_summary["count"].sum() * 100).round(1)
    cat_summary["mean_ifs"] = cat_summary["mean_ifs"].round(3)
    st.dataframe(
        cat_summary.rename(columns={
            "ifs_category": "Category", "count": "Runs",
            "mean_ifs": "Mean IFS", "share_%": "Share (%)",
        }),
        use_container_width=True, hide_index=True,
    )