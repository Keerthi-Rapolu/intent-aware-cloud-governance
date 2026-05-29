"""Page 5 — Paper: abstract, results summary, BibTeX, and links."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.sidebar import render as render_sidebar

st.set_page_config(page_title="Paper — PBCP", layout="wide")
render_sidebar()

# Research identity bar
st.markdown("""
<div style="font-size: 11px; font-weight: 500; letter-spacing: 0.05em;
            color: #0891B2; margin-bottom: 6px;">
  Cloud Systems Research &nbsp;·&nbsp; IACG v2.0
</div>
""", unsafe_allow_html=True)

st.title("PBCP: Pre-Billing Cost Prevention for Intent-Aware Cloud Governance")
st.markdown("Sreeja Katta &nbsp;·&nbsp; Keerthi Rapolu", unsafe_allow_html=True)

st.markdown("""
<div style="display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 20px 0;">
  <a href="https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance"
     target="_blank"
     style="background: #1A1A2E; color: #F9FAFB; padding: 5px 14px; border-radius: 6px;
            font-size: 12px; font-weight: 600; text-decoration: none;">
    GitHub
  </a>
  <a href="https://intent-aware-cloud-governance.streamlit.app/"
     target="_blank"
     style="background: #E11D48; color: #F9FAFB; padding: 5px 14px; border-radius: 6px;
            font-size: 12px; font-weight: 600; text-decoration: none;">
    Live Demo
  </a>
</div>
""", unsafe_allow_html=True)

st.divider()

# -- Abstract ------------------------------------------------------------------
st.subheader("Abstract")
st.markdown("""
Cloud governance systems usually detect waste only after resources have been provisioned,
used, and billed. This timing makes many optimizations economically reactive even when
post-execution diagnosis is accurate. We present **Pre-Billing Cost Prevention (PBCP)**,
an intent-aware governance framework that infers workload intent from natural-language
submissions, retrieves similar historical workloads, simulates likely utilization and cost
before execution, and applies decision-theoretic intervention before waste is incurred.

PBCP combines pre-billing prevention with runtime governance and policy learning, and
evaluates system behavior using Cost Prevention Score (CPS), Execution Success Rate (ESR),
and Intent-Fit Score (IFS). Across a controlled benchmark of 500 workloads and 28,423 runs,
PBCP achieves utilization MAE of 0.054 in simulation calibration, improves IFS-based
anomaly-detection F1 to 0.7608 versus 0.6054 for a CPU-threshold baseline, and reaches
peak CPS of 0.733 — a 56× improvement over the No Phase 3 baseline. These results suggest
that cloud governance benefits from moving intervention earlier in the execution lifecycle
rather than relying on post-billing recommendation alone.
""")

st.divider()

# -- Key results ---------------------------------------------------------------
st.subheader("Key Results")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Benchmark Workloads", "500", help="Controlled benchmark · seed 42")
c2.metric("Total Runs", "28,423", help="Runs across 6 workload classes")
c3.metric("Utilization MAE", "0.054", help="Exp 0 — simulation calibration")
c4.metric("IFS F1", "0.7608", help="Exp 3 — IBD anomaly detection (CPU-threshold baseline: 0.6054)")
c5.metric("Peak CPS", "0.733", help="Exp 6 — with policy learning (56× over No-Phase-3 baseline)")

st.divider()

# -- Experiments summary -------------------------------------------------------
st.subheader("Experiments")

exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    st.markdown("""
<div class="research-card">
  <div style="font-size: 12px; font-weight: 600; color: #0891B2; margin-bottom: 6px;">
    Exp 0 — Simulation Calibration
  </div>
  <div style="font-size: 13px; color: #374151;">
    Tests whether the pre-execution simulator is accurate enough to support
    governance decisions. Utilization MAE = <b>0.054</b>; cost rel-RMSE = 0.306.
    The error is below the threshold at which intervention becomes arbitrary.
  </div>
</div>

<div class="research-card">
  <div style="font-size: 12px; font-weight: 600; color: #0891B2; margin-bottom: 6px;">
    Exp 1 — Pre-Provision Intervention
  </div>
  <div style="font-size: 13px; color: #374151;">
    Showcase: PBCP reduces a 20-node ETL request to 10 nodes before billing begins,
    preventing $15.36 with CPS 0.500. The waste path is altered before the cluster
    is ever provisioned.
  </div>
</div>

<div class="research-card">
  <div style="font-size: 12px; font-weight: 600; color: #0891B2; margin-bottom: 6px;">
    Exp 2 — Runtime Governance
  </div>
  <div style="font-size: 13px; color: #374151;">
    Runtime intervention captures failure modes invisible before execution —
    idle persistence, underutilized ETL, runaway ML training.
    Runaway scenario: <b>$97.92 prevented</b>, CPS 0.667.
  </div>
</div>
""", unsafe_allow_html=True)

with exp_col2:
    st.markdown("""
<div class="research-card">
  <div style="font-size: 12px; font-weight: 600; color: #7C3AED; margin-bottom: 6px;">
    Exp 3 — IBD Anomaly Detection
  </div>
  <div style="font-size: 13px; color: #374151;">
    IFS-based detector vs. CPU-threshold baseline. IFS detector F1 = <b>0.7608</b>
    (recall improvement substantial). Semantic alignment captures divergence
    missed by single-metric thresholding.
  </div>
</div>

<div class="research-card">
  <div style="font-size: 12px; font-weight: 600; color: #15803D; margin-bottom: 6px;">
    Exp 5 — System Roll-Up
  </div>
  <div style="font-size: 13px; color: #374151;">
    System-level evaluation using CPS × ESR × IFS together.
    Valid CPS = <b>0.5585</b>, ESR = <b>0.9809</b>. Prevention remains high
    after penalizing over-aggressive interventions.
  </div>
</div>

<div class="research-card">
  <div style="font-size: 12px; font-weight: 600; color: #7C3AED; margin-bottom: 6px;">
    Exp 6 — Policy Learning Convergence
  </div>
  <div style="font-size: 13px; color: #374151;">
    Full PBCP reaches peak CPS = <b>0.733</b> vs. 0.013 for the No-Phase-3 baseline —
    a <b>56× improvement</b>. Policy learning, not just retrieval or static rules,
    drives the gain.
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# -- Contributions -------------------------------------------------------------
st.subheader("Contributions")
st.markdown("""
1. **Pre-billing governance architecture** — reframes cloud cost control as an early-intervention systems problem rather than post-billing reporting.
2. **Decision-theoretic intervention engine** — weighs predicted waste against governance action cost before execution begins.
3. **Intent-Behavior Discrepancy (IBD) framework** — operationalized through IFS, models divergence between workload intent and runtime behavior.
4. **Controlled evaluation benchmark** — 500 workloads, 28,423 runs measuring pre-billing prevention, runtime governance, anomaly detection, and policy learning under one governance-timing framework.
""")

st.divider()

# -- BibTeX --------------------------------------------------------------------
st.subheader("Citation")

bibtex = """@inproceedings{rapolu2025pbcp,
  title     = {PBCP: Pre-Billing Cost Prevention for Intent-Aware Cloud Governance},
  author    = {Katta, Sreeja and Rapolu, Keerthi},
  year      = {2025},
  note      = {Research prototype. Source: https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance}
}"""

st.code(bibtex, language="bibtex")

st.divider()

# -- Links ---------------------------------------------------------------------
st.subheader("Links")

lc1, lc2, lc3 = st.columns(3)

with lc1:
    st.markdown("""
<div class="research-card" style="text-align: center;">
  <div style="font-size: 22px; margin-bottom: 8px;">⚙</div>
  <div style="font-weight: 600; font-size: 14px; color: #1A1A2E; margin-bottom: 4px;">Source Code</div>
  <div style="font-size: 12px; color: #6B7280; margin-bottom: 12px;">
    Full implementation, experiments, and benchmark
  </div>
  <a href="https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance"
     target="_blank"
     style="background: #1A1A2E; color: #F9FAFB; padding: 5px 16px; border-radius: 6px;
            font-size: 12px; font-weight: 600; text-decoration: none;">
    View on GitHub
  </a>
</div>
""", unsafe_allow_html=True)

with lc2:
    st.markdown("""
<div class="research-card" style="text-align: center;">
  <div style="font-size: 22px; margin-bottom: 8px;">▶</div>
  <div style="font-weight: 600; font-size: 14px; color: #1A1A2E; margin-bottom: 4px;">Live Demo</div>
  <div style="font-size: 12px; color: #6B7280; margin-bottom: 12px;">
    Interactive Streamlit app — run scenarios, explore results
  </div>
  <a href="https://intent-aware-cloud-governance.streamlit.app/"
     target="_blank"
     style="background: #E11D48; color: #F9FAFB; padding: 5px 16px; border-radius: 6px;
            font-size: 12px; font-weight: 600; text-decoration: none;">
    Launch Demo
  </a>
</div>
""", unsafe_allow_html=True)

with lc3:
    st.markdown("""
<div class="research-card" style="text-align: center;">
  <div style="font-size: 22px; margin-bottom: 8px;">📋</div>
  <div style="font-weight: 600; font-size: 14px; color: #1A1A2E; margin-bottom: 4px;">Reproducibility</div>
  <div style="font-size: 12px; color: #6B7280; margin-bottom: 12px;">
    Run all experiments and verify reported values
  </div>
  <a href="https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance/blob/main/REPRODUCIBILITY.md"
     target="_blank"
     style="background: #0891B2; color: #F9FAFB; padding: 5px 16px; border-radius: 6px;
            font-size: 12px; font-weight: 600; text-decoration: none;">
    Reproduce Results
  </a>
</div>
""", unsafe_allow_html=True)
