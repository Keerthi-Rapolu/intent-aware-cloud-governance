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