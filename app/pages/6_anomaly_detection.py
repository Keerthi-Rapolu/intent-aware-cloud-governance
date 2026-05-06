"""Page 6 — Anomaly Detection (Exp 3 / Sreeja Katta)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from components.data_loader import (
    load_ibd_detector_metrics,
    load_ibd_threshold_sweep,
    load_ibd_mismatch_subgroup,
)

st.set_page_config(page_title="Anomaly Detection — PBCP", layout="wide")

# ── Hero ───────────────────────────────────────────────────────────────────────
st.title("🔍 Anomaly Detection")
st.markdown(
    """
    Can we tell when a cloud job is misbehaving — *before* the bill arrives?
    This page compares two approaches: a **simple CPU check** (flag anything with low CPU)
    versus our **smart detector** that scores every job's overall behaviour
    against its declared intent.
    """
)
st.divider()

m        = load_ibd_detector_metrics()
sweep    = load_ibd_threshold_sweep()
mismatch = load_ibd_mismatch_subgroup()

# ── KPI row ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
f1_delta = m["ifs"]["f1"] - m["threshold"]["f1"]
c1.metric("Total Jobs Analysed",    f"{m['n_total']:,}")
c2.metric("Confirmed Bad Jobs",     f"{m['n_anomaly']:,}",
          help="Jobs confirmed as anomalous (idle, runaway, or flagged by dataset)")
c3.metric("Smart Detector — F1",    f"{m['ifs']['f1']:.3f}",
          delta=f"+{f1_delta:.3f} vs basic check",
          help="F1 balances catching bad jobs (recall) vs not crying wolf (precision)")
c4.metric("Smart Detector — Precision", f"{m['ifs']['precision']:.3f}",
          help="Of jobs we flagged, how many were actually bad?")
c5.metric("Smart Detector — Recall",    f"{m['ifs']['recall']:.3f}",
          help="Of all bad jobs, how many did we catch?")

# ── Gate badges ────────────────────────────────────────────────────────────────
gate_f1 = m["ifs"]["f1"] >= m["threshold"]["f1"]
mm_idx  = mismatch.set_index("group")
gate_mm = (mm_idx.loc["type_mismatch", "anomaly_rate"] >=
           mm_idx.loc["non-mismatch",  "anomaly_rate"])

col_g1, col_g2, col_g3 = st.columns([1, 1, 2])
if gate_f1:
    col_g1.success("✅ Smart detector beats basic check")
else:
    col_g1.error("❌ Smart detector does not beat basic check")
if gate_mm:
    col_g2.success("✅ Mislabelled jobs fail more often")
else:
    col_g2.error("❌ Mislabelled jobs not more anomalous")

st.divider()

# ── Row 1: detector comparison + ROC ──────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("How do the two detectors compare?")
    st.caption("Higher is better for Precision, Recall, and F1. Lower is better for False Alarm Rate.")

    metrics   = ["Precision", "Recall", "F1 Score", "False Alarm Rate"]
    basic_v   = [m["threshold"]["precision"], m["threshold"]["recall"],
                 m["threshold"]["f1"],        m["threshold"]["fpr"]]
    smart_v   = [m["ifs"]["precision"],       m["ifs"]["recall"],
                 m["ifs"]["f1"],              m["ifs"]["fpr"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Basic CPU Check", x=metrics, y=basic_v,
        marker_color="#E07B54", opacity=0.85,
        text=[f"{v:.3f}" for v in basic_v], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Smart Detector", x=metrics, y=smart_v,
        marker_color="#4C72B0", opacity=0.85,
        text=[f"{v:.3f}" for v in smart_v], textposition="outside",
    ))
    fig.update_layout(
        barmode="group", yaxis_range=[0, 1.15],
        legend=dict(orientation="h", y=1.14, x=0),
        margin=dict(t=50, b=10), plot_bgcolor="white",
        yaxis=dict(gridcolor="#f0f0f0"),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("Catch rate vs false alarm rate")
    st.caption(
        "Top-left corner = perfect. Smart Detector catches more bad jobs "
        "while keeping false alarms low."
    )
    fig2 = go.Figure()
    fig2.add_shape(type="line", x0=0, y0=0, x1=1, y1=1,
                   line=dict(dash="dot", color="#cccccc", width=1.5))
    fig2.add_annotation(x=0.55, y=0.5, text="Random guess", showarrow=False,
                        font=dict(size=10, color="#aaaaaa"), textangle=-35)

    for name, label, color, sym in [
        ("threshold", "Basic CPU Check", "#E07B54", "square"),
        ("ifs",       "Smart Detector",  "#4C72B0", "circle"),
    ]:
        dm = m[name]
        fig2.add_trace(go.Scatter(
            x=[dm["fpr"]], y=[dm["recall"]],
            mode="markers", name=label,
            marker=dict(size=18, color=color, symbol=sym,
                        line=dict(width=2, color="white")),
        ))
        fig2.add_annotation(
            x=dm["fpr"] + 0.03, y=dm["recall"] - 0.03,
            text=f"<b>{label}</b><br>F1 = {dm['f1']:.3f}",
            showarrow=False, font=dict(size=11, color=color),
            align="left",
        )

    fig2.update_layout(
        xaxis_title="False Alarm Rate (lower = better)",
        yaxis_title="Catch Rate / Recall (higher = better)",
        xaxis_range=[-0.05, 1.05], yaxis_range=[-0.05, 1.05],
        legend=dict(orientation="h", y=1.14, x=0),
        margin=dict(t=50, b=10), plot_bgcolor="white",
        xaxis=dict(gridcolor="#f0f0f0"),
        yaxis=dict(gridcolor="#f0f0f0"),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Row 2: threshold sweep + mismatch ─────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Finding the right sensitivity level")
    st.caption(
        "Move the slider to make the detector more or less strict. "
        "Too strict = misses bad jobs. Too lenient = too many false alarms. "
        "The dashed line shows our chosen setting."
    )
    theta = st.slider(
        "Sensitivity (lower = stricter)", 0.45, 0.95, 0.65, 0.05,
        key="theta_slider",
        help="This is the IFS score cutoff. Jobs scoring below this are flagged as anomalous.",
        format="%.2f",
    )
    fig3 = go.Figure()
    colors = {"precision": "#2ca02c", "recall": "#d62728", "f1": "#1f77b4"}
    labels = {"precision": "Precision", "recall": "Recall (Catch Rate)", "f1": "F1 Score"}
    for col, color in colors.items():
        fig3.add_trace(go.Scatter(
            x=sweep["threshold"], y=sweep[col],
            mode="lines+markers", name=labels[col],
            line=dict(color=color, width=2.5),
            marker=dict(size=7),
        ))
    fig3.add_vline(x=theta, line_dash="dash", line_color="#555555", line_width=2,
                   annotation_text=f"  Current: {theta:.2f}",
                   annotation_font_size=12)
    fig3.update_layout(
        xaxis_title="Sensitivity Level (IFS threshold)",
        yaxis_title="Score", yaxis_range=[0, 1.05],
        legend=dict(orientation="h", y=1.14, x=0),
        margin=dict(t=50, b=10), plot_bgcolor="white",
        xaxis=dict(gridcolor="#f0f0f0"),
        yaxis=dict(gridcolor="#f0f0f0"),
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_r:
    st.subheader("Does a mislabelled job type predict trouble?")
    st.caption(
        "Some jobs declare one type (e.g. 'ETL') but NLP analysis infers a different type. "
        "Do those jobs fail more often?"
    )
    labels_mm = ["Mislabelled\nJob Type", "Correctly\nLabelled"]
    anomaly_rates = [
        mm_idx.loc["type_mismatch", "anomaly_rate"],
        mm_idx.loc["non-mismatch",  "anomaly_rate"],
    ]
    mean_ifs_vals = [
        mm_idx.loc["type_mismatch", "mean_ifs"],
        mm_idx.loc["non-mismatch",  "mean_ifs"],
    ]

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        name="Failure Rate", x=["Mislabelled", "Correctly Labelled"],
        y=anomaly_rates,
        marker_color=["#DD8452", "#55A868"], opacity=0.9,
        text=[f"{v:.1%}" for v in anomaly_rates], textposition="outside",
        yaxis="y1",
    ))
    fig4.update_layout(
        yaxis=dict(title="Failure Rate", range=[0, max(anomaly_rates) * 1.6],
                   tickformat=".0%", gridcolor="#f0f0f0"),
        margin=dict(t=30, b=10), plot_bgcolor="white",
        showlegend=False,
    )
    st.plotly_chart(fig4, use_container_width=True)

    # Mini metrics beneath
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Mislabelled — Failure Rate",
                  f"{mm_idx.loc['type_mismatch','anomaly_rate']:.1%}",
                  delta=f"+{mm_idx.loc['type_mismatch','anomaly_rate'] - mm_idx.loc['non-mismatch','anomaly_rate']:.1%} vs correctly labelled",
                  delta_color="inverse")
    col_m2.metric("Mislabelled — Avg Score",
                  f"{mm_idx.loc['type_mismatch','mean_ifs']:.3f}",
                  help="Lower score = worse alignment with declared intent")

st.divider()

# ── Detail table (collapsed) ──────────────────────────────────────────────────
with st.expander("📋 Full detector metrics table"):
    rows = []
    for name, label in [("threshold", "Basic CPU Check (cpu < 30%)"),
                         ("ifs",       "Smart Detector (score < 0.65)")]:
        d = m[name]
        rows.append({
            "Detector":        label,
            "Precision":       f"{d['precision']:.4f}",
            "Recall":          f"{d['recall']:.4f}",
            "F1 Score":        f"{d['f1']:.4f}",
            "False Alarm Rate": f"{d['fpr']:.4f}",
            "Correctly Caught (TP)": d["tp"],
            "False Alarms (FP)":     d["fp"],
            "Correctly Cleared (TN)": d["tn"],
            "Missed (FN)":           d["fn"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
