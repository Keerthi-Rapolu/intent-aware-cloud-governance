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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: "Inter", "IBM Plex Sans", "Source Sans Pro", ui-sans-serif, system-ui, sans-serif;
}

/* ── Research card ─────────────────────────────────────── */
.research-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
    transition: border-color 0.2s ease;
}

/* ── Phase blocks ───────────────────────────────────────── */
.phase-block {
    background: #FFFFFF;
    border: 1px solid rgba(123,191,219,0.35);
    border-radius: 14px;
    padding: 24px;
    height: 100%;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.phase-title {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #E5E7EB;
}
.phase-step {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 12px;
    font-size: 13px;
    color: #374151;
    line-height: 1.55;
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
    color: #D1D5DB;
    font-size: 15px;
    margin: 2px 0;
}

/* ── Decision badge ─────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-sim    { background: rgba(123,191,219,0.15); color: #0891B2; border: 1px solid rgba(123,191,219,0.4); }
.badge-proto  { background: rgba(195,166,212,0.15); color: #7C3AED; border: 1px solid rgba(195,166,212,0.4); }
.badge-price  { background: rgba(129,201,149,0.15); color: #15803D; border: 1px solid rgba(129,201,149,0.4); }
.badge-warn   { background: rgba(255,183,77,0.15);  color: #B45309; border: 1px solid rgba(255,183,77,0.4); }

/* ── Intervention timeline card ─────────────────────────── */
.iv-card {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 14px;
    border-left: 3px solid;
    border-top: 1px solid #E5E7EB;
    border-right: 1px solid #E5E7EB;
    border-bottom: 1px solid #E5E7EB;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: box-shadow 0.15s ease;
}
.iv-card.ac  { border-left-color: #81C995; }
.iv-card.blk { border-left-color: #F28B82; }
.iv-card.sug { border-left-color: #FFB74D; }
.iv-card.pas { border-left-color: #A8D5A2; }
.iv-card h4  { margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #1A1A2E; }
.iv-card p   { margin: 2px 0; font-size: 12px; color: #6B7280; }
.iv-card .highlight { color: #1A1A2E; font-weight: 600; }

/* ── Case study card ────────────────────────────────────── */
.case-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-top: 2px solid #F28B82;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.case-card .case-title { font-size: 13px; font-weight: 600; color: #DC2626; margin-bottom: 10px; }
.case-card .case-row   { display: flex; justify-content: space-between; margin-bottom: 5px; }
.case-card .case-label { font-size: 12px; color: #9CA3AF; }
.case-card .case-val   { font-size: 12px; color: #374151; font-weight: 500; }
.case-card .case-ifs   { font-size: 20px; font-weight: 700; color: #DC2626; margin-top: 10px; }

/* ── Section label ──────────────────────────────────────── */
.section-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9CA3AF;
    margin-bottom: 14px;
}
</style>
""", unsafe_allow_html=True)

# -- Sidebar ------------------------------------------------------------------
st.sidebar.markdown("""
<div style="padding: 4px 0 12px 0;">
  <div style="font-size: 16px; font-weight: 600; color: #1A1A2E;">PBCP Research Demo</div>
  <div style="font-size: 11px; color: #6B7280; margin-top: 2px;">IACG v2.0 · Keerthi Rapolu &amp; Sreeja Katta</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.markdown("""
<div style="font-size: 12px; color: #6B7280; line-height: 1.8;">
<b style="color:#1A1A2E;">Pages</b><br>
Use the sidebar links above to navigate.
</div>
""", unsafe_allow_html=True)

# -- Home page ----------------------------------------------------------------
st.markdown("""
<div style="margin-bottom: 8px;">
  <span style="font-size: 11px; font-weight: 500; letter-spacing: 0.05em;
               color: #0891B2;">
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
| **Prevention Engine** | Opens on Live Demo by default; also includes Workload Catalogue and Anomaly Detection |
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

