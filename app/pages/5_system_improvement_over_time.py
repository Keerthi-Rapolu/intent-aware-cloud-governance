"""Page 5 — System Improvement Over Time."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.data_loader import load_convergence
from components.charts import convergence_line

st.set_page_config(page_title="System Improvement Over Time — PBCP", layout="wide")
st.title("System Improvement Over Time")
st.caption("The system learns from past jobs and gets better at preventing waste with each batch")

df = load_convergence()

if df.empty:
    st.warning("results/exp6_convergence.csv not found. Run Exp 6 first: "
               "`python experiments/exp6_phase3_convergence.py`")
    st.stop()

# -- KPIs -------------------------------------------------------------------
full_col   = "full_pbcp_cps_mean"
no3_col    = "no_phase3_cps_mean"
peak_full  = df[full_col].max()
peak_no3   = df[no3_col].max()
peak_gen   = int(df.loc[df[full_col].idxmax(), "generation"])
improvement = round(peak_full / peak_no3, 1) if peak_no3 > 0 else float("inf")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Peak Full PBCP CPS",    f"{peak_full:.3f}", f"gen {peak_gen}")
c2.metric("Peak No Phase 3 CPS",   f"{peak_no3:.3f}")
c3.metric("Improvement vs. baseline", f"{improvement:.1f}x")
c4.metric("Seeds",                 "5  (42–46)")

st.divider()

# -- Chart ------------------------------------------------------------------
st.subheader("CPS Convergence Across Generations")
st.plotly_chart(convergence_line(df), use_container_width=True)

st.caption(
    "Vertical dashed lines separate pre-provision (gens 0–3), runtime (gens 4–7), "
    "and baseline-only (gens 8–9) record types. "
    "Shaded bands show ±95% CI across 5 seeds."
)

st.divider()

# -- Generation slider ------------------------------------------------------
st.subheader("Per-Generation Detail")
gen = st.slider("Select generation", min_value=0, max_value=9, value=5)
row = df[df["generation"] == gen].iloc[0]

cols = st.columns(4)
scenarios = [
    ("Full PBCP",       "full_pbcp"),
    ("No Phase 3",      "no_phase3"),
    ("Policy-only",     "policy_only"),
    ("Embedding-only",  "embedding_only"),
]
for col, (label, key) in zip(cols, scenarios):
    mean = row.get(f"{key}_cps_mean", 0.0)
    std  = row.get(f"{key}_cps_std",  0.0)
    col.metric(label, f"{mean:.3f}", f"±{std:.3f} std")

st.divider()

# -- Raw table --------------------------------------------------------------
with st.expander("Raw convergence data"):
    display = df.copy()
    # Round all float columns
    float_cols = [c for c in display.columns if c != "generation"]
    display[float_cols] = display[float_cols].round(4)
    st.dataframe(display, use_container_width=True, hide_index=True)