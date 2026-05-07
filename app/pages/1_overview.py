"""Page 1 — System Overview: architecture, KPIs, comparison, research positioning."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.data_loader import load_kpis

st.set_page_config(page_title="Overview — PBCP", layout="wide")

# Research identity bar
st.markdown("""
<div style="font-size: 11px; font-weight: 500; letter-spacing: 0.05em;
            color: #0891B2; margin-bottom: 6px;">
  Cloud Systems Research &nbsp;·&nbsp; IACG v2.0
</div>
""", unsafe_allow_html=True)

st.title("PBCP — Pre-Billing Cost Prevention Framework")
st.markdown(
    "An intent-aware cloud governance system that intercepts compute waste "
    "**before** billing using hybrid NLP, FAISS KNN similarity retrieval, "
    "and an expected-value intervention model."
)

st.markdown("""
<div style="display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 20px 0;">
  <span class="badge badge-sim">Simulated Benchmark</span>
  <span class="badge badge-proto">Research Prototype</span>
  <span class="badge badge-price">Published Cloud Pricing</span>
  <span class="badge badge-warn">Controlled Anomaly Injection</span>
</div>
""", unsafe_allow_html=True)

# -- KPIs -------------------------------------------------------------------
kpis = load_kpis()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Benchmark Workloads", "500",
          help="Controlled evaluation benchmark · seed 42")
c2.metric("Total Cost Prevented", f"${kpis['total_prevented']:,.0f}",
          help="Sum of prevented_cost_usd across all non-baseline intervention records")
c3.metric("System CPS", f"{kpis['system_cps']:.3f}",
          help="Cost Prevention Score = prevented / potential")
c4.metric("Mean IFS", f"{kpis['mean_ifs']:.3f}",
          help="Intent-Fit Score: 0–1, higher = intent aligned with behavior")
c5.metric("IBD Rate", f"{kpis['ibd_fraction']*100:.0f}%",
          help="Fraction of workloads with IFS < 0.65 (controlled injection)")

st.caption(
    "Benchmark includes controlled anomaly injection to evaluate governance "
    "effectiveness under realistic cloud waste scenarios."
)

st.divider()

# ── Architecture ────────────────────────────────────────────────────────────
st.subheader("System Architecture")
st.caption("Three-phase intent-aware governance pipeline.")

arch_col1, arch_col2, arch_col3 = st.columns(3)

with arch_col1:
    st.markdown("""
<div class="phase-block">
  <div class="phase-title" style="color: #0891B2;">
    Phase 1 &nbsp;·&nbsp; PREVENT
  </div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#7BBFDB;"></div>
    <div><b style="color:#1A1A2E;">Natural Language Workload</b><br>
    Job description submitted via CLI, API, or scheduler integration</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#7BBFDB;"></div>
    <div><b style="color:#1A1A2E;">Intent Inference</b><br>
    Hybrid NLP: deterministic keyword extraction → DistilBERT (optional)</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#7BBFDB;"></div>
    <div><b style="color:#1A1A2E;">FAISS KNN Retrieval</b><br>
    64-dim workload embeddings, cosine similarity over historical runs</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#7BBFDB;"></div>
    <div><b style="color:#1A1A2E;">Pre-Execution Simulation</b><br>
    Predicts utilization · right-sizes node count · computes cost delta</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#7BBFDB;"></div>
    <div><b style="color:#1A1A2E;">EV Decision Engine</b><br>
    Maximises E[savings − correction_cost] per intervention option</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
    <span style="background:rgba(242,139,130,0.18); color:#DC2626; padding:3px 9px;
                 border-radius:6px; font-size:12px; font-weight:600;">BLOCK</span>
    <span style="background:rgba(129,201,149,0.18); color:#15803D; padding:3px 9px;
                 border-radius:6px; font-size:12px; font-weight:600;">AUTO_CORRECT</span>
    <span style="background:rgba(255,183,77,0.18); color:#B45309; padding:3px 9px;
                 border-radius:6px; font-size:12px; font-weight:600;">SUGGEST</span>
    <span style="background:rgba(123,191,219,0.18); color:#0891B2; padding:3px 9px;
                 border-radius:6px; font-size:12px; font-weight:600;">PASS</span>
  </div>
</div>
""", unsafe_allow_html=True)

with arch_col2:
    st.markdown("""
<div class="phase-block">
  <div class="phase-title" style="color: #15803D;">
    Phase 2 &nbsp;·&nbsp; CORRECT
  </div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#81C995;"></div>
    <div><b style="color:#1A1A2E;">Runtime Monitoring</b><br>
    Continuous telemetry ingestion: CPU, memory, network, idle time</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#81C995;"></div>
    <div><b style="color:#1A1A2E;">Anomaly Signals</b><br>
    Idle cluster detection · utilization underrun · runtime overrun</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#81C995;"></div>
    <div><b style="color:#1A1A2E;">Runtime Optimizer</b><br>
    Mid-execution right-sizing decisions with EV model re-evaluation</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#81C995;"></div>
    <div><b style="color:#1A1A2E;">Intervention Actions</b><br>
    Node downscale · spot migration · graceful job termination</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#81C995;"></div>
    <div><b style="color:#1A1A2E;">CPS Computation</b><br>
    CPS = prevented / potential · ESR multiplier for gaming resistance</div>
  </div>

  <div style="margin-top: 16px; padding: 10px 12px; background: rgba(129,201,149,0.12);
              border-radius: 8px; border: 1px solid rgba(129,201,149,0.35);">
    <div style="font-size: 12px; color: #15803D; font-weight: 600;">Exp 2 Scenario C Result</div>
    <div style="font-size: 11px; color: #6B7280; margin-top: 4px;">
      Runaway ML job · 20 → 9 nodes<br>$97.92 prevented · CPS 0.667
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

with arch_col3:
    st.markdown("""
<div class="phase-block">
  <div class="phase-title" style="color: #7C3AED;">
    Phase 3 &nbsp;·&nbsp; LEARN
  </div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#C3A6D4;"></div>
    <div><b style="color:#1A1A2E;">IFS Computation</b><br>
    Alignment score from workload embedding similarity to behavior embedding</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#C3A6D4;"></div>
    <div><b style="color:#1A1A2E;">Intent-Behavior Divergence Detection</b><br>
    IFS &lt; 0.65 triggers anomaly classification and root-cause attribution</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#C3A6D4;"></div>
    <div><b style="color:#1A1A2E;">Policy Synthesis</b><br>
    Recurring failure patterns (≥ 3 occurrences) trigger automated rule generation</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#C3A6D4;"></div>
    <div><b style="color:#1A1A2E;">Embedding Updates</b><br>
    Prior distributions updated with new behavioral evidence</div>
  </div>
  <div class="phase-arrow">↓</div>

  <div class="phase-step">
    <div class="phase-step-dot" style="background:#C3A6D4;"></div>
    <div><b style="color:#1A1A2E;">Convergence Improvement</b><br>
    CPS improves across generations · Exp 6: peak 0.733, 58× vs no-Phase-3</div>
  </div>

  <div style="margin-top: 16px; padding: 10px 12px; background: rgba(195,166,212,0.15);
              border-radius: 8px; border: 1px solid rgba(195,166,212,0.4);">
    <div style="font-size: 12px; color: #7C3AED; font-weight: 600;">IBD Detection Result (Exp 3)</div>
    <div style="font-size: 11px; color: #6B7280; margin-top: 4px;">
      IFS detector F1 = 0.761<br>CPU-threshold baseline F1 = 0.605
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# -- Problem + IFS note --------------------------------------------------------
col_prob, col_ifs = st.columns(2)

with col_prob:
    st.subheader("Problem Statement")
    st.markdown("""
Cloud compute waste from over-provisioning remains largely invisible until the billing cycle
closes. Workloads are submitted requesting 20 nodes when 6 would suffice — the excess
runs idle, billed at the full on-demand rate, with no retroactive remedy available.

**Three compounding failure modes:**
- **Over-provisioning**: node count exceeds utilization requirements (primary waste driver)
- **Type mislabeling**: workloads declared as `adhoc` actually exhibit `ml_training` resource patterns, bypassing appropriate guardrails
- **Runaway execution**: jobs run 5–10× longer than declared, accumulating unbounded cost

**PBCP's approach:** intercept all three failure modes before billing through a combination of
intent inference, predictive simulation, and policy enforcement — rather than post-hoc analysis.
    """)

with col_ifs:
    st.subheader("IFS: Intent-Fit Score")
    st.markdown("""
**Canonical definition:** IFS is computed as the cosine similarity between a workload's
_intent embedding_ (derived from the natural-language job description) and its
_behavior embedding_ (derived from observed runtime telemetry).

**Interpretability decomposition:** For dashboard transparency, the system surfaces four
alignment sub-scores that contribute to the overall embedding alignment:

| Sub-score | Weight | Captures |
|-----------|--------|----------|
| Type alignment | 0.35 | Declared vs. inferred workload class |
| Utilization alignment | 0.25 | Predicted vs. actual CPU utilization |
| Duration alignment | 0.20 | Expected vs. actual job duration |
| Resource alignment | 0.20 | Over-provision factor |

> Displayed sub-scores are interpretable components contributing to the
> embedding-based IFS calculation. They are not the canonical research definition.

**Thresholds:** well-aligned ≥ 0.85 · minor ≥ 0.70 · significant ≥ 0.50 · severe < 0.50 · IBD alert < 0.65
    """)

st.divider()

# -- Comparison table ----------------------------------------------------------
st.subheader("PBCP vs. Existing Approaches")
st.markdown("""
| Capability | PBCP | Sedai | AWS Compute Optimizer |
|------------|------|-------|----------------------|
| Intercepts waste **before** any resource is provisioned | **Yes** | No — corrects live resources | No — retrospective advisory |
| Governance grounded in natural-language intent | **Yes** | No | No |
| KNN workload-similarity priors (FAISS) | **Yes** | No | No |
| Decision-theoretic EV intervention model | **Yes** | No | No |
| Intent-Fit Score (IFS) alignment metric | **Yes** | No | No |
| Runtime corrections | **Yes** | Yes | Advisory only |
| Multi-cloud (AWS / Azure / GCP) | **Yes** | Yes | AWS only |
| Gaming-resistant Valid CPS (CPS × ESR) | **Yes** | No | No |
| Self-improving policy synthesis (Phase 3) | **Yes** | No | No |

Sedai autonomously right-sizes live resources (post-execution); pre-billing interception is out of
scope by design. AWS Compute Optimizer analyzes up to 14 days of historical utilization and produces
advisory recommendations with no enforcement mechanism.
""")

st.divider()

# -- Metric definitions --------------------------------------------------------
with st.expander("Metric definitions"):
    st.markdown("""
**CPS (Cost Prevention Score)** = `prevented_cost / potential_cost_without_system` (0–1).
Fraction of wasteful spend intercepted before billing.

**Valid CPS** = `CPS × ESR`. ESR (Execution Success Rate) = fraction of workloads that completed
successfully. Penalizes over-aggressive blocking to prevent gaming.

**IFS (Intent-Fit Score)** — see sub-score decomposition above. Canonical: cosine similarity
between intent and behavior embeddings.

**IBD (Intent-Behavior Discrepancy)**: IFS < 0.65 — divergence sufficient to trigger the
anomaly detector and initiate root-cause attribution.

**Note on benchmark IFS distribution:** The controlled evaluation benchmark injects anomalies
at a rate calibrated to stress-test detection sensitivity. Production IBD rates would reflect
actual organizational behavior, not injected faults.
    """)