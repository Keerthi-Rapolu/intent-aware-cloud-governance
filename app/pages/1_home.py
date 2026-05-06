"""Page 1 — Home / System Overview."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.data_loader import load_kpis

st.set_page_config(page_title="Home — PBCP", layout="wide")
st.title("PBCP — Pre-Billing Cost Prevention Framework")
st.caption("IACG v2.0 Research System · Keerthi Rapolu · Dataset: seed 42, 500 workloads, generated 2026-05-05")

# -- KPIs -------------------------------------------------------------------
kpis = load_kpis()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Workloads",         f"{500:,}")
c2.metric("Total Prevented",   f"${kpis['total_prevented']:,.0f}")
c3.metric("System CPS",        f"{kpis['system_cps']:.3f}")
c4.metric("Mean IFS",          f"{kpis['mean_ifs']:.3f}")

st.divider()

# -- Architecture -----------------------------------------------------------
col_arch, col_desc = st.columns([1, 1])

with col_arch:
    st.subheader("System Architecture")
    st.code("""
  Workload Description (NL)
          |
          v
  [Intent Inference]  <-- FAISS KNN + catalog priors
          |
          v
  [Pre-Execution Simulator]  EV decision model
          |                  (BLOCK / AUTO_CORRECT / SUGGEST / PASS)
          v
  [Pre-Provision Guard]  Policy enforcement
          |
          v
  [Runtime Optimizer]  cpu_underutil | idle | overrun | ...
          |
          v
  [CPS + IFS Tracker]  Cost Prevention Score x Intent-Fit Score
    """, language="text")

with col_desc:
    st.subheader("The Problem")
    st.markdown("""
Cloud compute waste from over-provisioning is largely invisible until the bill arrives.
Teams submit jobs requesting 20 nodes when 6 would suffice — the excess runs idle,
billed at full rate, with no retroactive remedy.

**PBCP intercepts this before billing:**
- Infers the true workload type from natural-language descriptions
- Predicts utilization using KNN over historical runs (FAISS, 64-dim embeddings)
- Right-sizes node counts via an EV decision model that weighs correction risk
- Applies policy guardrails and runtime corrections
- Tracks CPS (Cost Prevention Score) and IFS (Intent-Fit Score)
    """)

    st.subheader("Key Results (Exp 0–6)")
    st.markdown("""
| Experiment | Result |
|-----------|--------|
| Calibration (Exp 0) | Util MAE = 0.054 · Cost rel-RMSE = 0.306† |
| Pre-Provision (Exp 1) | Showcase CPS = 0.500 (20 → 10 nodes) |
| Runtime (Exp 2) | Scenario C: $97.92 prevented (runaway ML) |
| System Roll-up (Exp 5) | Valid CPS = 0.559 · ESR = 0.981 |
| IBD Detection (Exp 3) | IFS detector F1 = 0.761 vs. CPU-threshold F1 = 0.605 |
| Convergence (Exp 6) | Peak CPS = 0.733 vs. 0.013 baseline (58×) |

† Cost rel-RMSE reflects duration uncertainty: simulator predicts cost using
expected duration at submission time; actual cost depends on runtime duration
(±25% variation by design). Pre-execution cost prediction inherently carries
this uncertainty; 0.306 is within the expected range for submission-time models.
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