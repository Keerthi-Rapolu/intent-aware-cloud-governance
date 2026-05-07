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
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("PBCP Research Demo")
st.sidebar.caption("IACG v2.0 — Pre-Billing Cost Prevention Framework")
st.sidebar.divider()
st.sidebar.markdown("""
**Navigation**

Use the pages in the sidebar to explore the system.

---
*Keerthi Rapolu · IACG v2.0*
""")

st.title("PBCP — Pre-Billing Cost Prevention Framework")
st.markdown("""
Welcome to the interactive research demo for **PBCP** (Pre-Billing Cost Prevention).

Use the sidebar to navigate between pages:

| Page | What it shows |
|------|---------------|
| **Overview** | System KPIs, architecture, comparison with existing approaches, metric definitions |
| **Prevention Engine** | Live Demo (5 presets, intent inference, IFS gauge) · Workload Catalogue · Anomaly Detection |
| **Runtime & Savings** | CPS/IFS metrics by stage, workload type, and alignment category |
| **Learning System** | Convergence study (Exp 6, 10 gens, 5 seeds) · Feedback loop and policy synthesis |
""")