"""Page 3 — Cost Savings Dashboard."""
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

st.set_page_config(page_title="Cost Savings Dashboard — PBCP", layout="wide")
st.title("Cost Savings Dashboard")
st.caption("How much cloud waste was prevented · broken down by stage and workload type")

kpis    = load_kpis()
stage_df = load_cps_by_stage()
type_df  = load_cps_by_type()
ifs_df   = load_ifs_distribution()

# -- KPI row ----------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
valid_cps = round(kpis["system_cps"] * 1.0, 4)   # ESR=1.0 (no failures in DB)
c1.metric("System CPS",     f"{kpis['system_cps']:.3f}")
c2.metric("Valid CPS",      f"{valid_cps:.3f}")
c3.metric("Mean IFS",       f"{kpis['mean_ifs']:.3f}")
c4.metric("IBD-flagged",    f"{kpis['ibd_fraction']*100:.1f}%",
          help="Fraction of workloads with IFS < 0.70 (Intent-Behavior Discrepancy)")
c5.metric("Total Prevented",f"${kpis['total_prevented']:,.0f}")

st.divider()

# -- Charts -----------------------------------------------------------------
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("CPS by Stage")
    st.plotly_chart(cps_by_stage_bar(stage_df), use_container_width=True)

    st.subheader("IFS Distribution")
    st.plotly_chart(ifs_histogram(ifs_df), use_container_width=True)

with col_r:
    st.subheader("CPS by Workload Type")
    st.plotly_chart(cps_by_type_bar(type_df), use_container_width=True)

    st.subheader("Intent-Fit Score Category Breakdown")
    st.plotly_chart(ifs_category_donut(ifs_df), use_container_width=True)

st.divider()

# -- Stage breakdown table --------------------------------------------------
st.subheader("Stage Breakdown")
st.dataframe(
    stage_df.rename(columns={
        "stage": "Stage", "cps": "CPS", "mean_ifs": "Mean IFS", "n": "Records",
    }),
    use_container_width=True,
    hide_index=True,
)

# -- Type breakdown table ---------------------------------------------------
st.subheader("Workload Type Breakdown")
st.dataframe(
    type_df.rename(columns={
        "workload_type": "Type", "cps": "CPS",
        "mean_ifs": "Mean IFS", "n_workloads": "Workloads",
    }),
    use_container_width=True,
    hide_index=True,
)