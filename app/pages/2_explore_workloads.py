"""Page 2 — Explore Workloads."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from components.data_loader import load_workloads

st.set_page_config(page_title="Explore Workloads — PBCP", layout="wide")
st.title("Explore Workloads")
st.caption("500 synthetic workloads · seed 42 · IACG v2.0")

df = load_workloads()

# -- Filters ----------------------------------------------------------------
st.sidebar.header("Filters")

types = st.sidebar.multiselect(
    "Workload type", sorted(df["workload_type"].unique()),
    default=sorted(df["workload_type"].unique()),
)
teams = st.sidebar.multiselect(
    "Team", sorted(df["team"].unique()),
    default=sorted(df["team"].unique()),
)
envs = st.sidebar.multiselect(
    "Environment", sorted(df["environment"].unique()),
    default=sorted(df["environment"].unique()),
)
over_prov = st.sidebar.checkbox("Over-provisioned only (OPF ≥ 1.5)", value=False)
mismatch  = st.sidebar.checkbox("Type-mismatch only", value=False)

filt = df[
    df["workload_type"].isin(types) &
    df["team"].isin(teams) &
    df["environment"].isin(envs)
]
if over_prov:
    filt = filt[filt["is_over_provisioned"]]
if mismatch:
    filt = filt[filt["type_mismatch"]]

# -- Summary stats ----------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Workloads", len(filt))
c2.metric("Over-provisioned",
          f"{filt['is_over_provisioned'].sum()} ({filt['is_over_provisioned'].mean()*100:.0f}%)")
c3.metric("Type mismatches",
          f"{filt['type_mismatch'].sum()} ({filt['type_mismatch'].mean()*100:.0f}%)")
c4.metric("Avg expected duration",
          f"{filt['expected_h'].mean():.1f} h" if len(filt) else "—")

st.divider()

# -- Table ------------------------------------------------------------------
display_cols = [
    "workload_name", "workload_type", "team", "environment", "priority",
    "expected_h", "node_count", "opf", "is_over_provisioned",
    "type_mismatch", "use_spot", "instance_type",
]
st.dataframe(
    filt[display_cols].rename(columns={
        "workload_name": "Name", "workload_type": "Type", "team": "Team",
        "environment": "Env", "priority": "Priority", "expected_h": "Exp. h",
        "node_count": "Nodes", "opf": "OPF", "is_over_provisioned": "Over-prov",
        "type_mismatch": "Mismatch", "use_spot": "Spot", "instance_type": "Instance",
    }),
    use_container_width=True,
    height=420,
)

# -- Row detail -------------------------------------------------------------
st.divider()
st.subheader("Row Detail")
selected_name = st.selectbox(
    "Select a workload to inspect",
    options=filt["workload_name"].tolist(),
    index=0,
)
if selected_name:
    row = filt[filt["workload_name"] == selected_name].iloc[0]
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"**Description:** {row['description']}")
        st.markdown(f"**Type:** {row['workload_type']} | **Team:** {row['team']} | **Priority:** {row['priority']}")
        st.markdown(f"**Environment:** {row['environment']} | **Spot:** {row['use_spot']}")
    with col_r:
        st.markdown(f"**Nodes:** {row['node_count']} | **Instance:** {row['instance_type']}")
        st.markdown(f"**OPF:** {row['opf']:.2f} | **Over-provisioned:** {row['is_over_provisioned']}")
        st.markdown(f"**Type mismatch:** {row['type_mismatch']} | **PII:** {row['pii_signal']}")