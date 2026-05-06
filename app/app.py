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
| **Home** | System overview, KPIs, architecture |
| **Explore Workloads** | Browse and filter 500 synthetic workloads |
| **Cost Savings Dashboard** | Prevention metrics by stage and workload type |
| **Live Demo** | Type a workload description — see live simulation + IFS score |
| **System Improvement Over Time** | Learning curve across 10 generations, 4 scenarios |
| **Anomaly Detection** | Smart detector vs CPU-threshold comparison (Exp 3) |
| **How the System Learns** | The 4-step feedback loop that turns mistakes into rules |
""")