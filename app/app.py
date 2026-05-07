"""
PBCP Research Demo — main entry point.

Run:  streamlit run app/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="PBCP — Pre-Billing Cost Prevention",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Global enterprise CSS injection ------------------------------------------
st.markdown("""
<style>
/* ── Typography ─────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: "Inter", "IBM Plex Sans", "Source Sans Pro", ui-sans-serif, system-ui, sans-serif;
}

/* ── Research card ─────────────────────────────────────── */
.research-card {
    background: #161B27;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 14px;
}

/* ── Phase blocks ───────────────────────────────────────── */
.phase-block {
    background: #1A2235;
    border: 1px solid rgba(56,189,248,0.18);
    border-radius: 14px;
    padding: 22px;
    height: 100%;
}
.phase-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}
.phase-step {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
    font-size: 13px;
    color: #CBD5E1;
    line-height: 1.5;
}
.phase-step-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
}
.phase-arrow {
    text-align: center;
    color: rgba(255,255,255,0.25);
    font-size: 16px;
    margin: 4px 0;
}

/* ── Decision badge ─────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
}
.badge-sim    { background: rgba(56,189,248,0.12); color: #38BDF8;  border: 1px solid rgba(56,189,248,0.3); }
.badge-proto  { background: rgba(139,92,246,0.12); color: #A78BFA;  border: 1px solid rgba(139,92,246,0.3); }
.badge-price  { background: rgba(16,185,129,0.12); color: #34D399;  border: 1px solid rgba(16,185,129,0.3); }
.badge-warn   { background: rgba(245,158,11,0.12); color: #FBBF24;  border: 1px solid rgba(245,158,11,0.3); }

/* ── Intervention timeline card ─────────────────────────── */
.iv-card {
    background: #161B27;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
    border-left: 3px solid;
}
.iv-card.ac  { border-color: #10B981; }
.iv-card.blk { border-color: #EF4444; }
.iv-card.sug { border-color: #F59E0B; }
.iv-card.pas { border-color: #38BDF8; }
.iv-card h4  { margin: 0 0 6px 0; font-size: 14px; font-weight: 700; color: #E2E8F0; }
.iv-card p   { margin: 2px 0; font-size: 12px; color: #94A3B8; }
.iv-card .highlight { color: #E2E8F0; font-weight: 600; }

/* ── Case study card ────────────────────────────────────── */
.case-card {
    background: #161B27;
    border: 1px solid rgba(239,68,68,0.18);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.case-card .case-title { font-size: 13px; font-weight: 700; color: #F87171; margin-bottom: 8px; }
.case-card .case-row   { display: flex; justify-content: space-between; margin-bottom: 4px; }
.case-card .case-label { font-size: 12px; color: #64748B; }
.case-card .case-val   { font-size: 12px; color: #CBD5E1; font-weight: 600; }
.case-card .case-ifs   { font-size: 20px; font-weight: 800; color: #EF4444; margin-top: 8px; }

/* ── Section divider ────────────────────────────────────── */
.section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #475569;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# -- Sidebar ------------------------------------------------------------------
st.sidebar.markdown("""
<div style="padding: 4px 0 12px 0;">
  <div style="font-size: 16px; font-weight: 700; color: #E2E8F0;">PBCP Research Demo</div>
  <div style="font-size: 11px; color: #64748B; margin-top: 2px;">IACG v2.0 · Keerthi Rapolu</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.markdown("""
<div style="font-size: 12px; color: #94A3B8; line-height: 1.8;">
<b style="color:#E2E8F0;">Pages</b><br>
Use the sidebar links above to navigate.
</div>
""", unsafe_allow_html=True)

# -- Home page ----------------------------------------------------------------
st.markdown("""
<div style="margin-bottom: 8px;">
  <span style="font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
               text-transform: uppercase; color: #38BDF8;">
    Cloud Systems Research · IACG v2.0
  </span>
</div>
""", unsafe_allow_html=True)

st.title("PBCP — Pre-Billing Cost Prevention")
st.markdown(
    "An intent-aware cloud governance framework that intercepts compute waste "
    "**before** billing — using hybrid NLP, FAISS KNN, and decision-theoretic "
    "intervention."
)

st.markdown("""
<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;">
  <span class="badge badge-sim">Simulated Benchmark</span>
  <span class="badge badge-proto">Research Prototype</span>
  <span class="badge badge-price">Published Cloud Pricing</span>
  <span class="badge badge-warn">Controlled Anomaly Injection</span>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Navigate the Demo")
    st.markdown("""
| Page | Content |
|------|---------|
| **Overview** | Architecture, KPIs, system comparison, metric definitions |
| **Prevention Engine** | Live Demo with 3 showcase scenarios · Workload Catalogue · Anomaly Detection |
| **Runtime & Savings** | CPS / IFS dashboard · Intervention timeline · Stage breakdown |
| **Learning System** | Convergence study (Exp 6) · Policy synthesis · Feedback loop |
""")

with col2:
    st.markdown("#### Published Experimental Results")
    st.markdown("""
| Experiment | Key Result |
|-----------|-----------|
| Calibration (Exp 0) | Util MAE 0.054 |
| Pre-Provision (Exp 1) | Showcase CPS 0.500 |
| Runtime (Exp 2) | $97.92 prevented (Scenario C) |
| IBD Detection (Exp 3) | IFS F1 0.761 vs CPU-threshold 0.605 |
| System Roll-up (Exp 5) | Valid CPS 0.559 · ESR 0.981 |
| Convergence (Exp 6) | Peak CPS 0.733 · 58× vs no-Phase-3 |
""")