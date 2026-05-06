"""Shared Plotly chart helpers used across app pages."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

STAGE_COLORS  = {"pre_provision": "#1f77b4", "runtime": "#ff7f0e", "ai_workload": "#2ca02c"}
TYPE_COLORS   = {
    "etl": "#1f77b4", "adhoc": "#ff7f0e", "ml_training": "#2ca02c",
    "llm_pipeline": "#9467bd", "batch": "#8c564b", "streaming": "#e377c2",
}
IFS_COLORS    = {
    "well_aligned": "#2ca02c", "minor": "#98df8a",
    "significant":  "#ffbb78", "severe": "#d62728",
}
CURVE_STYLES  = {
    "full_pbcp":      ("#1f77b4", "solid"),
    "no_phase3":      ("#ff7f0e", "dash"),
    "policy_only":    ("#2ca02c", "dot"),
    "embedding_only": ("#9467bd", "dashdot"),
}


def cps_by_stage_bar(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="stage", y="cps", color="stage",
        color_discrete_map=STAGE_COLORS,
        text=df["cps"].apply(lambda v: f"{v:.3f}"),
        labels={"cps": "CPS", "stage": "Stage"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, yaxis_range=[0, df["cps"].max() * 1.3],
                      margin=dict(t=30, b=10))
    return fig


def cps_by_type_bar(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("cps")
    fig = px.bar(
        df, x="cps", y="workload_type", orientation="h",
        color="workload_type", color_discrete_map=TYPE_COLORS,
        text=df["cps"].apply(lambda v: f"{v:.3f}"),
        labels={"cps": "CPS", "workload_type": "Workload type"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, xaxis_range=[0, df["cps"].max() * 1.3],
                      margin=dict(t=30, b=10))
    return fig


def ifs_histogram(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_vrect(x0=0.85, x1=1.01, fillcolor="#2ca02c", opacity=0.08,
                  annotation_text="well-aligned", annotation_position="top left")
    fig.add_vrect(x0=0.70, x1=0.85, fillcolor="#98df8a", opacity=0.12,
                  annotation_text="minor", annotation_position="top left")
    fig.add_vrect(x0=0.50, x1=0.70, fillcolor="#ffbb78", opacity=0.12,
                  annotation_text="significant", annotation_position="top left")
    fig.add_vrect(x0=0.00, x1=0.50, fillcolor="#d62728", opacity=0.06,
                  annotation_text="severe", annotation_position="top left")
    fig.add_trace(go.Histogram(
        x=df["ifs"], nbinsx=40, marker_color="#1f77b4",
        opacity=0.75, name="IFS",
    ))
    fig.update_layout(
        xaxis_title="IFS", yaxis_title="Count",
        margin=dict(t=30, b=10), showlegend=False,
    )
    return fig


def ifs_category_donut(df: pd.DataFrame) -> go.Figure:
    counts = df["ifs_category"].value_counts().reset_index()
    counts.columns = ["category", "n"]
    fig = px.pie(
        counts, names="category", values="n",
        color="category", color_discrete_map=IFS_COLORS,
        hole=0.45,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(showlegend=False, margin=dict(t=30, b=10))
    return fig


ROOT_CAUSE_COLORS = {
    "over_provisioned": "#1f77b4",
    "idle_cluster":     "#ff7f0e",
    "runaway_job":      "#d62728",
    "type_mismatch":    "#9467bd",
    "unknown":          "#7f7f7f",
}


def ibd_detector_bar(m: dict) -> go.Figure:
    """Grouped bar: Precision/Recall/F1 for both detectors."""
    metrics = ["Precision", "Recall", "F1"]
    thresh  = [m["threshold"]["precision"], m["threshold"]["recall"], m["threshold"]["f1"]]
    ifs_v   = [m["ifs"]["precision"],       m["ifs"]["recall"],       m["ifs"]["f1"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="CPU Threshold", x=metrics, y=thresh,
                         marker_color="#E07B54", text=[f"{v:.3f}" for v in thresh],
                         textposition="outside"))
    fig.add_trace(go.Bar(name="IFS Detector",  x=metrics, y=ifs_v,
                         marker_color="#4C72B0", text=[f"{v:.3f}" for v in ifs_v],
                         textposition="outside"))
    fig.update_layout(barmode="group", yaxis_range=[0, 1.15],
                      legend=dict(orientation="h", y=1.12),
                      margin=dict(t=40, b=10))
    return fig


def ibd_threshold_sweep(df: pd.DataFrame, current_theta: float = 0.65) -> go.Figure:
    """Precision / Recall / F1 vs θ_ifs sweep."""
    fig = go.Figure()
    for col, color, name in [
        ("precision", "#2ca02c", "Precision"),
        ("recall",    "#d62728", "Recall"),
        ("f1",        "#1f77b4", "F1"),
    ]:
        fig.add_trace(go.Scatter(x=df["threshold"], y=df[col],
                                 mode="lines+markers", name=name,
                                 line=dict(color=color, width=2)))
    fig.add_vline(x=current_theta, line_dash="dash", line_color="grey",
                  annotation_text=f"θ={current_theta}", annotation_position="top right")
    fig.update_layout(xaxis_title="IBD Threshold (θ_ifs)",
                      yaxis_title="Score", yaxis_range=[0, 1.05],
                      legend=dict(orientation="h", y=1.12),
                      margin=dict(t=40, b=10))
    return fig


def ibd_mismatch_bar(df: pd.DataFrame) -> go.Figure:
    """Grouped bar: anomaly rate and mean IFS for mismatch vs non-mismatch."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Anomaly Rate", x=df["group"],
                         y=df["anomaly_rate"],
                         marker_color=["#DD8452", "#55A868"],
                         text=[f"{v:.2%}" for v in df["anomaly_rate"]],
                         textposition="outside"))
    fig.update_layout(yaxis_title="Anomaly Rate", yaxis_range=[0, 1.0],
                      margin=dict(t=30, b=10), showlegend=False)
    return fig


def ibd_roc_scatter(m: dict) -> go.Figure:
    """ROC-style scatter: FPR vs TPR."""
    fig = go.Figure()
    fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1,
                  line=dict(dash="dash", color="lightgrey"))
    for name, label, color in [
        ("threshold", "CPU Threshold", "#E07B54"),
        ("ifs",       "IFS Detector",  "#4C72B0"),
    ]:
        dm = m[name]
        fig.add_trace(go.Scatter(
            x=[dm["fpr"]], y=[dm["recall"]],
            mode="markers+text", name=label,
            marker=dict(size=14, color=color),
            text=[f"  {label}<br>  F1={dm['f1']:.3f}"],
            textposition="middle right",
        ))
    fig.update_layout(xaxis_title="False Positive Rate",
                      yaxis_title="True Positive Rate (Recall)",
                      xaxis_range=[-0.05, 1.05], yaxis_range=[-0.05, 1.05],
                      legend=dict(orientation="h", y=1.12),
                      margin=dict(t=40, b=10))
    return fig


def root_cause_donut(df: pd.DataFrame) -> go.Figure:
    """Donut: IBD root cause breakdown by count."""
    colors = [ROOT_CAUSE_COLORS.get(rc, "#7f7f7f") for rc in df["root_cause"]]
    fig = go.Figure(go.Pie(
        labels=df["root_cause"], values=df["n"],
        hole=0.45, marker_colors=colors,
        textinfo="percent+label",
    ))
    fig.update_layout(showlegend=False, margin=dict(t=30, b=10))
    return fig


def root_cause_cost_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: mean cost impact per root cause."""
    df = df.sort_values("mean_cost_impact")
    colors = [ROOT_CAUSE_COLORS.get(rc, "#7f7f7f") for rc in df["root_cause"]]
    fig = go.Figure(go.Bar(
        x=df["mean_cost_impact"], y=df["root_cause"],
        orientation="h", marker_color=colors,
        text=[f"${v:.0f}" for v in df["mean_cost_impact"]],
        textposition="outside",
    ))
    fig.update_layout(xaxis_title="Mean Cost Impact ($)",
                      yaxis_title="Root Cause",
                      xaxis_range=[0, df["mean_cost_impact"].max() * 1.35],
                      margin=dict(t=30, b=10))
    return fig


def policy_source_bar(df: pd.DataFrame) -> go.Figure:
    """Bar: policy count by source (builtin vs learned)."""
    counts = df["source"].value_counts().reset_index()
    counts.columns = ["source", "n"]
    fig = px.bar(counts, x="source", y="n",
                 color="source",
                 color_discrete_map={"builtin": "#1f77b4", "learned": "#ff7f0e"},
                 text="n")
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, yaxis_range=[0, counts["n"].max() * 1.4],
                      margin=dict(t=30, b=10))
    return fig


def convergence_line(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    labels = {
        "full_pbcp":      "Full PBCP",
        "no_phase3":      "No Phase 3",
        "policy_only":    "Policy-only",
        "embedding_only": "Embedding-only",
    }
    import numpy as np
    N = 5
    for key, label in labels.items():
        mean_col = f"{key}_cps_mean"
        std_col  = f"{key}_cps_std"
        if mean_col not in df.columns:
            continue
        color, dash = CURVE_STYLES[key]
        mean = df[mean_col].values
        std  = df[std_col].values if std_col in df.columns else np.zeros_like(mean)
        ci   = 1.96 * std / np.sqrt(N)
        gens = df["generation"].values

        fig.add_trace(go.Scatter(
            x=gens, y=mean, name=label,
            line=dict(color=color, dash=dash, width=2.5),
            mode="lines",
        ))
        fig.add_trace(go.Scatter(
            x=list(gens) + list(gens[::-1]),
            y=list(mean + ci) + list((mean - ci)[::-1]),
            fill="toself", fillcolor=color, opacity=0.12,
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))

    fig.add_vline(x=3.5, line_dash="dash", line_color="grey", opacity=0.5)
    fig.add_vline(x=7.5, line_dash="dash", line_color="grey", opacity=0.5)
    fig.add_annotation(x=1.75, y=0.02, text="Pre-provision<br>gens 0–3",
                       showarrow=False, font=dict(size=10, color="grey"), yref="paper")
    fig.add_annotation(x=5.75, y=0.02, text="Runtime<br>gens 4–7",
                       showarrow=False, font=dict(size=10, color="grey"), yref="paper")
    fig.update_layout(
        xaxis_title="Generation", yaxis_title="Mean CPS (±95% CI, 5 seeds)",
        xaxis=dict(tickmode="linear", tick0=0, dtick=1),
        yaxis_range=[0, None],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=10),
    )
    return fig