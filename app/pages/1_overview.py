"""Page 1 — System Overview: KPIs, architecture, comparison, research positioning."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.data_loader import load_kpis

st.set_page_config(page_title="Overview — PBCP", layout="wide")

st.title("PBCP — Pre-Billing Cost Prevention Framework")
st.caption(
    "IACG v2.0 Research System · Keerthi Rapolu · "
    "Controlled evaluation benchmark: seed 42, 500 workloads, 28,423 runs"
)

st.info(
    "**Research prototype.**  "
    "All experiments run over a controlled evaluation workload benchmark "
    "(500 workloads, 28,423 simulated runs, seed 42). "
    "Utilization priors are KNN over this benchmark; cost figures use published "
    "AWS/Azure/GCP on-demand pricing. Production deployment would require "
    "calibration against an organization's own historical run data.",
    icon="ℹ️",
)

# -- KPIs -------------------------------------------------------------------
kpis = load_kpis()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Workloads",        "500",
          help="Controlled evaluation benchmark · seed 42")
c2.metric("Total Prevented",  f"${kpis['total_prevented']:,.0f}",
          help="Sum of prevented_cost_usd across all non-baseline intervention records")
c3.metric("System CPS",       f"{kpis['system_cps']:.3f}",
          help="prevented_cost / potential_cost (Cost Prevention Score)")
c4.metric("Mean IFS",         f"{kpis['mean_ifs']:.3f}",
          help="Intent-Fit Score: 0–1, higher = declared intent matched runtime behavior")
c5.metric("IBD Rate",         f"{kpis['ibd_fraction']*100:.1f}%",
          help="Fraction of workloads with IFS < 0.70 (Intent-Behavior Discrepancy)")

st.divider()

# -- Architecture + Problem -------------------------------------------------
col_arch, col_desc = st.columns([1, 1])

with col_arch:
    st.subheader("System Architecture")
    st.code("""
  Workload Description (NL)
          |
          v
  [Intent Inference]        FAISS KNN + catalog priors
          |                 Hybrid: keyword + DistilBERT
          v
  [Pre-Execution Simulator] EV decision model
          |                 BLOCK / AUTO_CORRECT / SUGGEST / PASS
          v
  [Pre-Provision Guard]     Policy enforcement
          |
          v
  [Runtime Optimizer]       cpu_underutil | idle | overrun
          |
          v
  [CPS + IFS Tracker]       Cost Prevention × Intent-Fit
    """, language="text")

with col_desc:
    st.subheader("Problem Statement")
    st.markdown("""
Cloud compute waste from over-provisioning is largely invisible until the billing cycle closes.
Workloads are submitted requesting 20 nodes when 6 would suffice — the excess runs idle,
billed at full rate, with no retroactive remedy.

**PBCP intercepts this before billing:**
- Infers the true workload type from natural-language job descriptions
- Predicts utilization using KNN over historical runs (FAISS, 64-dim embeddings)
- Right-sizes node counts via an EV decision model that weighs correction risk
- Applies policy guardrails and runtime corrections
- Tracks CPS (Cost Prevention Score) and IFS (Intent-Fit Score) as governance metrics
    """)

    st.subheader("Key Experimental Results")
    st.markdown("""
| Experiment | Metric | Result |
|-----------|--------|--------|
| Calibration (Exp 0) | Util MAE / Cost rel-RMSE | 0.054 / 0.306† |
| Pre-Provision (Exp 1) | Showcase CPS | 0.500 (20 → 10 nodes) |
| Runtime (Exp 2) | Scenario C cost prevented | $97.92 |
| IBD Detection (Exp 3) | IFS detector F1 vs CPU-threshold | 0.761 vs 0.605 |
| System Roll-up (Exp 5) | Valid CPS · ESR | 0.559 · 0.981 |
| Convergence (Exp 6) | Peak CPS vs no-phase-3 | 0.733 vs 0.013 |

† Cost rel-RMSE reflects duration uncertainty: the simulator predicts cost at submission time using
expected duration; actual cost depends on runtime duration (±25% variation by design).
Pre-execution cost prediction inherently carries this uncertainty; 0.306 is within the expected
range for submission-time models.
    """)

st.divider()

# -- Comparison table -------------------------------------------------------
st.subheader("PBCP vs. Existing Approaches")
st.markdown("""
| Capability | PBCP | Sedai¹ | AWS Compute Optimizer² |
|------------|------|--------|------------------------|
| Intercepts before any resource is provisioned | **Yes** | No — corrects live utilization | No — retrospective recommendations |
| Governance grounded in natural-language intent | **Yes** | No | No |
| KNN workload-similarity priors (FAISS) | **Yes** | No | No |
| Decision-theoretic intervention (EV model) | **Yes** | No | No |
| Intent-Fit Score (IFS) alignment metric | **Yes** | No | No |
| Runtime corrections | **Yes** | Yes | Advisory only |
| Multi-cloud (AWS / Azure / GCP) | **Yes** | Yes | AWS only |
| Gaming-resistant metric (CPS × ESR) | **Yes** | No | No |

¹ Sedai autonomously right-sizes live resources (post-execution). Pre-billing interception is out of scope by design.
² AWS Compute Optimizer analyzes up to 14 days of historical utilization and produces advisory recommendations; no enforcement mechanism.
""")

st.divider()

# -- Metric definitions -----------------------------------------------------
with st.expander("Metric definitions"):
    st.markdown("""
**CPS (Cost Prevention Score)** = `prevented_cost / potential_cost_without_system` (0–1, higher is better).
Fraction of wasteful spend intercepted before billing.

**Valid CPS** = `CPS × ESR` where ESR (Execution Success Rate) = fraction of workloads that completed
successfully. ESR makes CPS gaming-resistant: a system that blocks aggressively earns low ESR and
therefore low Valid CPS regardless of savings claimed.

**IFS (Intent-Fit Score)** = `0.35 × type_alignment + 0.25 × util_alignment + 0.20 × duration_alignment
+ 0.20 × resource_alignment` (0–1, higher is better). Measures how well a workload's declared intent
matched its observed runtime behavior.

Categories: well_aligned ≥ 0.85 · minor ≥ 0.70 · significant ≥ 0.50 · severe < 0.50.

**IBD (Intent-Behavior Discrepancy)**: IFS < 0.70 — declared intent and actual behavior diverged enough
to warrant a governance alert.
    """)