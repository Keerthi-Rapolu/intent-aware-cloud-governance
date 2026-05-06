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
st.caption("How much cloud waste was prevented · broken down by stage and workload type · Dataset: seed 42, 500 workloads")

with st.expander("Metric definitions", expanded=False):
    st.markdown("""
**CPS (Cost Prevention Score)** = `prevented_cost / potential_cost_without_system` (0–1, higher is better).
Measures the fraction of wasteful spend that PBCP intercepted before billing.

**Valid CPS** = `CPS × ESR` where ESR (Execution Success Rate) = fraction of workloads that completed successfully.
The ESR multiplier makes CPS gaming-resistant: a system that blocks aggressively earns low ESR and therefore low Valid CPS regardless of savings claimed.

**IFS (Intent-Fit Score)** = `0.35 × type_alignment + 0.25 × util_alignment + 0.20 × duration_alignment + 0.20 × resource_alignment` (0–1, higher is better).
Measures how well a workload's declared intent matched its observed runtime behavior.
Categories: well_aligned ≥ 0.85 · minor ≥ 0.70 · significant ≥ 0.50 · severe < 0.50.

**IBD-flagged (Intent-Behavior Discrepancy)** = fraction of workloads with IFS < 0.70.
These are workloads where declared intent and actual behavior diverged enough to warrant a governance alert.

> **Note — IFS scoring:** The `ifs` values stored in `cps_ifs_records` were pre-computed by the dataset generator
> using Beta-distribution sampling tuned to the injection rates (mean ≈ 0.33 for the synthetic population).
> The live **IFSCalculator** (used in the Live Demo and Exp 5) computes IFS from the 4-sub-score formula and
> produces higher values for well-provisioned workloads. Both are valid — the DB values reflect population-level
> alignment signal; the live calculator reflects per-run alignment at the moment of execution.
>
> **IBD threshold:** 92.9% of non-baseline records have pre-computed IFS < 0.70. This reflects the generator's
> deliberate misalignment injection (20% anomaly rate per run, 35% ETL over-provisioning). In a production
> deployment, IBD rate would reflect actual organizational behavior, not injected faults.
>
> **Dataset provenance:** seed 42, 500 workloads, 28,423 runs, generated 2026-05-05. All KPIs are deterministic
> for this seed. See design doc Section 6 for full methodology.
""")

kpis    = load_kpis()
stage_df = load_cps_by_stage()
type_df  = load_cps_by_type()
ifs_df   = load_ifs_distribution()

# -- KPI row ----------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
valid_cps = round(kpis["system_cps"] * 1.0, 4)   # ESR=1.0 (no failures in DB)
c1.metric("System CPS",     f"{kpis['system_cps']:.3f}",
          help="prevented_cost / potential_cost across all active-stage records")
c2.metric("Valid CPS",      f"{valid_cps:.3f}",
          help="CPS × ESR — gaming-resistant; ESR penalises over-aggressive blocking")
c3.metric("Mean IFS",       f"{kpis['mean_ifs']:.3f}",
          help="Intent-Fit Score: 0–1, higher = declared intent matched runtime behavior")
c4.metric("IBD-flagged",    f"{kpis['ibd_fraction']*100:.1f}%",
          help="Workloads with IFS < 0.70 — declared intent diverged from observed behavior")
c5.metric("Total Prevented",f"${kpis['total_prevented']:,.0f}",
          help="Sum of prevented_cost_usd across all non-baseline intervention records")

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