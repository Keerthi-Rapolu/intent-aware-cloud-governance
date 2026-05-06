"""Page 6 — Anomaly Detection (Exp 3 / Sreeja Katta)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.data_loader import (
    load_ibd_detector_metrics,
    load_ibd_threshold_sweep,
    load_ibd_mismatch_subgroup,
)
from components.charts import (
    ibd_detector_bar,
    ibd_threshold_sweep,
    ibd_mismatch_bar,
    ibd_roc_scatter,
)

st.set_page_config(page_title="Anomaly Detection — PBCP", layout="wide")
st.title("Anomaly Detection")
st.caption(
    "Catching misbehaving jobs early — our smart detector vs a simple CPU check · "
    "Owner: Sreeja Katta"
)

m       = load_ibd_detector_metrics()
sweep   = load_ibd_threshold_sweep()
mismatch = load_ibd_mismatch_subgroup()

# -- KPI row ----------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Runs",       f"{m['n_total']:,}")
c2.metric("True Anomalies",   f"{m['n_anomaly']:,}",
          help="Runs with is_anomaly OR is_runaway OR is_idle_injected")
c3.metric("IFS Detector F1",  f"{m['ifs']['f1']:.3f}",
          delta=f"+{m['ifs']['f1'] - m['threshold']['f1']:.3f} vs threshold",
          delta_color="normal")
c4.metric("IFS Precision",    f"{m['ifs']['precision']:.3f}")
c5.metric("IFS Recall",       f"{m['ifs']['recall']:.3f}")

# -- Gate badge -------------------------------------------------------------
gate_f1 = m["ifs"]["f1"] >= m["threshold"]["f1"]
gate_mm = (
    mismatch.set_index("group").loc["type_mismatch", "anomaly_rate"] >=
    mismatch.set_index("group").loc["non-mismatch",  "anomaly_rate"]
)
col_g1, col_g2 = st.columns(2)
col_g1.success("✓ Gate: IFS F1 ≥ Threshold F1") if gate_f1 else col_g1.error("✗ Gate: IFS F1 ≥ Threshold F1")
col_g2.success("✓ Gate: type_mismatch anomaly rate higher") if gate_mm else col_g2.error("✗ Gate: type_mismatch anomaly rate higher")

st.divider()

# -- Row 1: detector comparison + ROC scatter -------------------------------
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Detector Comparison")
    st.caption("Precision, Recall, F1 — CPU Threshold (cpu < 0.30) vs IFS Detector (IFS < 0.65)")
    st.plotly_chart(ibd_detector_bar(m), use_container_width=True)

with col_r:
    st.subheader("ROC-style View")
    st.caption("False Positive Rate vs True Positive Rate (Recall)")
    st.plotly_chart(ibd_roc_scatter(m), use_container_width=True)

st.divider()

# -- Row 2: threshold sweep + mismatch subgroup -----------------------------
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Precision–Recall–F1 vs θ_ifs")
    st.caption(
        "Sweep IBD threshold from 0.45 → 0.95. "
        "Default θ = 0.65 (dashed line) chosen to maximise F1."
    )
    theta = st.slider("IBD threshold (θ)", 0.45, 0.95, 0.65, 0.05,
                      key="theta_slider",
                      help="Move to see how detection quality changes with threshold")
    st.plotly_chart(ibd_threshold_sweep(sweep, current_theta=theta),
                    use_container_width=True)

with col_r:
    st.subheader("type_mismatch Subgroup")
    st.caption(
        "Workloads where NLP-inferred type ≠ declared type have "
        "significantly higher anomaly rate and lower mean IFS."
    )
    st.plotly_chart(ibd_mismatch_bar(mismatch), use_container_width=True)

    # Mean IFS comparison
    mm_idx = mismatch.set_index("group")
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Mean IFS — type_mismatch",
                  f"{mm_idx.loc['type_mismatch', 'mean_ifs']:.3f}")
    col_m2.metric("Mean IFS — non-mismatch",
                  f"{mm_idx.loc['non-mismatch', 'mean_ifs']:.3f}")

st.divider()

# -- Detector detail table --------------------------------------------------
st.subheader("Detector Metrics Detail")
import pandas as pd
rows = []
for name, label in [("threshold", "CPU Threshold (cpu < 0.30)"),
                     ("ifs",       "IFS Detector (IFS < 0.65)")]:
    d = m[name]
    rows.append({
        "Detector":  label,
        "Precision": f"{d['precision']:.4f}",
        "Recall":    f"{d['recall']:.4f}",
        "F1":        f"{d['f1']:.4f}",
        "FPR":       f"{d['fpr']:.4f}",
        "TP": d["tp"], "FP": d["fp"], "TN": d["tn"], "FN": d["fn"],
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
