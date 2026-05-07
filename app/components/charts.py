"""Shared Plotly chart helpers — enterprise dark-theme palette."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Enterprise color palette (muted, professional)
_BG      = "#0D1117"
_BG2     = "#161B27"
_GRID    = "rgba(255,255,255,0.06)"
_TEXT    = "#94A3B8"

STAGE_COLORS  = {"pre_provision": "#38BDF8", "runtime": "#10B981", "ai_workload": "#6366F1"}
TYPE_COLORS   = {
    "etl":         "#38BDF8",
    "adhoc":       "#F59E0B",
    "ml_training": "#10B981",
    "llm_pipeline":"#818CF8",
    "batch":       "#94A3B8",
    "streaming":   "#34D399",
}
IFS_COLORS = {
    "well_aligned": "#10B981",
    "minor":        "#38BDF8",
    "significant":  "#F59E0B",
    "severe":       "#EF4444",
}
CURVE_STYLES  = {
    "full_pbcp":      ("#38BDF8", "solid"),
    "no_phase3":      ("#F59E0B", "dash"),
    "policy_only":    ("#10B981", "dot"),
    "embedding_only": ("#8B5CF6", "dashdot"),
}


def _base_layout(**kwargs) -> dict:
    """Common dark-theme layout overrides."""
    base = dict(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG2,
        font=dict(color=_TEXT, size=12),
        xaxis=dict(gridcolor=_GRID, linecolor=_GRID, zerolinecolor=_GRID,
                   title_font=dict(size=12, color=_TEXT)),
        yaxis=dict(gridcolor=_GRID, linecolor=_GRID, zerolinecolor=_GRID,
                   title_font=dict(size=12, color=_TEXT)),
        margin=dict(t=40, b=10, l=10, r=24),
    )
    base.update(kwargs)
    return base


def cps_by_stage_bar(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="stage", y="cps", color="stage",
        color_discrete_map=STAGE_COLORS,
        text=df["cps"].apply(lambda v: f"{v:.3f}"),
        labels={"cps": "Cost Prevention Score (CPS)", "stage": "Evaluation Stage"},
    )
    fig.update_traces(textposition="outside", marker_opacity=0.80)
    fig.update_layout(
        showlegend=False,
        yaxis_range=[0, df["cps"].max() * 1.38],
        **_base_layout(),
    )
    return fig


def cps_by_type_bar(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("cps")
    fig = go.Figure(go.Bar(
        x=df["cps"], y=df["workload_type"], orientation="h",
        marker_color="#38BDF8", marker_opacity=0.78,
        text=df["cps"].apply(lambda v: f"{v:.3f}"),
        textposition="outside",
        textfont=dict(color=_TEXT, size=12),
    ))
    fig.update_layout(
        showlegend=False,
        xaxis_range=[0, df["cps"].max() * 1.38],
        xaxis_title="Cost Prevention Score (CPS)",
        **_base_layout(),
    )
    return fig


def ifs_histogram(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_vrect(x0=0.85, x1=1.01, fillcolor="#10B981", opacity=0.07,
                  annotation_text="well-aligned", annotation_position="top left",
                  annotation_font_color="#10B981")
    fig.add_vrect(x0=0.70, x1=0.85, fillcolor="#38BDF8", opacity=0.07,
                  annotation_text="minor", annotation_position="top left",
                  annotation_font_color="#38BDF8")
    fig.add_vrect(x0=0.50, x1=0.70, fillcolor="#F59E0B", opacity=0.07,
                  annotation_text="significant", annotation_position="top left",
                  annotation_font_color="#F59E0B")
    fig.add_vrect(x0=0.00, x1=0.50, fillcolor="#EF4444", opacity=0.05,
                  annotation_text="severe", annotation_position="top left",
                  annotation_font_color="#EF4444")
    fig.add_trace(go.Histogram(
        x=df["ifs"], nbinsx=30, marker_color="#38BDF8",
        opacity=0.72, name="IFS",
        marker_line=dict(width=0.5, color=_BG),
    ))
    fig.update_layout(
        xaxis_title="Intent-Fit Score (IFS)",
        yaxis_title="Run Count",
        showlegend=False,
        **_base_layout(),
    )
    return fig


def ifs_category_donut(df: pd.DataFrame) -> go.Figure:
    counts = df["ifs_category"].value_counts().reset_index()
    counts.columns = ["category", "n"]
    fig = px.pie(
        counts, names="category", values="n",
        color="category", color_discrete_map=IFS_COLORS,
        hole=0.48,
    )
    fig.update_traces(textinfo="percent+label", textfont_color="#E2E8F0",
                      marker=dict(line=dict(color=_BG, width=2)))
    fig.update_layout(showlegend=False, **_base_layout())
    return fig


ROOT_CAUSE_COLORS = {
    "over_provisioned": "#38BDF8",
    "idle_cluster":     "#F59E0B",
    "runaway_job":      "#EF4444",
    "type_mismatch":    "#8B5CF6",
    "unknown":          "#475569",
}


def ibd_detector_bar(m: dict) -> go.Figure:
    """Grouped bar: Precision/Recall/F1 for both detectors."""
    metrics = ["Precision", "Recall", "F1"]
    thresh  = [m["threshold"]["precision"], m["threshold"]["recall"], m["threshold"]["f1"]]
    ifs_v   = [m["ifs"]["precision"],       m["ifs"]["recall"],       m["ifs"]["f1"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="CPU Threshold", x=metrics, y=thresh,
                         marker_color="#F59E0B", opacity=0.8,
                         text=[f"{v:.3f}" for v in thresh], textposition="outside"))
    fig.add_trace(go.Bar(name="IFS Detector",  x=metrics, y=ifs_v,
                         marker_color="#38BDF8", opacity=0.8,
                         text=[f"{v:.3f}" for v in ifs_v], textposition="outside"))
    fig.update_layout(barmode="group", yaxis_range=[0, 1.15],
                      legend=dict(orientation="h", y=1.12),
                      **_base_layout())
    return fig


def ibd_threshold_sweep(df: pd.DataFrame, current_theta: float = 0.65) -> go.Figure:
    """Precision / Recall / F1 vs θ_ifs sweep."""
    fig = go.Figure()
    for col, color, name in [
        ("precision", "#10B981", "Precision"),
        ("recall",    "#EF4444", "Recall"),
        ("f1",        "#38BDF8", "F1"),
    ]:
        fig.add_trace(go.Scatter(x=df["threshold"], y=df[col],
                                 mode="lines+markers", name=name,
                                 line=dict(color=color, width=2.5)))
    fig.add_vline(x=current_theta, line_dash="dash", line_color="#475569",
                  annotation_text=f"θ={current_theta}", annotation_position="top right",
                  annotation_font_color="#94A3B8")
    fig.update_layout(xaxis_title="IBD Threshold (θ_ifs)",
                      yaxis_title="Score", yaxis_range=[0, 1.05],
                      legend=dict(orientation="h", y=1.12),
                      **_base_layout())
    return fig


def ibd_mismatch_bar(df: pd.DataFrame) -> go.Figure:
    """Grouped bar: anomaly rate and mean IFS for mismatch vs non-mismatch."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Anomaly Rate", x=df["group"],
                         y=df["anomaly_rate"],
                         marker_color=["#F59E0B", "#10B981"],
                         opacity=0.85,
                         text=[f"{v:.2%}" for v in df["anomaly_rate"]],
                         textposition="outside"))
    fig.update_layout(yaxis_title="Anomaly Rate", yaxis_range=[0, 1.0],
                      showlegend=False, **_base_layout())
    return fig


def ibd_roc_scatter(m: dict) -> go.Figure:
    """ROC-style scatter: FPR vs TPR."""
    fig = go.Figure()
    fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1,
                  line=dict(dash="dash", color="#334155", width=1.5))
    for name, label, color, sym in [
        ("threshold", "CPU Threshold", "#F59E0B", "square"),
        ("ifs",       "IFS Detector",  "#38BDF8", "circle"),
    ]:
        dm = m[name]
        fig.add_trace(go.Scatter(
            x=[dm["fpr"]], y=[dm["recall"]],
            mode="markers", name=label,
            marker=dict(size=16, color=color, symbol=sym,
                        line=dict(width=2, color=_BG)),
        ))
        fig.add_annotation(
            x=dm["fpr"] + 0.03, y=dm["recall"] - 0.03,
            text=f"<b>{label}</b><br>F1 = {dm['f1']:.3f}",
            showarrow=False, font=dict(size=11, color=color), align="left",
        )
    fig.update_layout(xaxis_title="False Positive Rate",
                      yaxis_title="True Positive Rate (Recall)",
                      xaxis_range=[-0.05, 1.05], yaxis_range=[-0.05, 1.05],
                      legend=dict(orientation="h", y=1.12),
                      **_base_layout())
    return fig


def confusion_matrix_heatmap(m: dict, detector: str = "ifs") -> go.Figure:
    """2×2 annotated confusion matrix for a given detector ('ifs' or 'threshold')."""
    dm = m[detector]
    tp, fp, tn, fn = dm["tp"], dm["fp"], dm["tn"], dm["fn"]
    z = [[tn, fp], [fn, tp]]
    cell_labels = [["TN", "FP"], ["FN", "TP"]]

    annotations = []
    for r, row in enumerate(z):
        for c, val in enumerate(row):
            annotations.append(dict(
                x=c, y=r,
                text=f"<b>{cell_labels[r][c]}</b><br>{val:,}",
                showarrow=False, font=dict(size=14, color="#E2E8F0"),
                xref="x", yref="y",
            ))

    fig = go.Figure(go.Heatmap(
        z=z,
        colorscale=[[0.0, "#EF4444"], [0.5, "#F59E0B"], [1.0, "#10B981"]],
        showscale=False,
        xgap=4, ygap=4,
    ))
    fig.update_layout(
        paper_bgcolor=_BG, plot_bgcolor=_BG2,
        font=dict(color=_TEXT),
        xaxis=dict(tickvals=[0, 1], ticktext=["Predicted Normal", "Predicted Anomaly"],
                   side="top", gridcolor=_GRID),
        yaxis=dict(tickvals=[0, 1], ticktext=["Actual Normal", "Actual Anomaly"],
                   autorange="reversed", gridcolor=_GRID),
        annotations=annotations,
        margin=dict(t=60, b=20, l=120, r=20),
        height=270,
    )
    return fig


def root_cause_donut(df: pd.DataFrame) -> go.Figure:
    """Donut: IBD root cause breakdown by count."""
    colors = [ROOT_CAUSE_COLORS.get(rc, "#475569") for rc in df["root_cause"]]
    fig = go.Figure(go.Pie(
        labels=df["root_cause"], values=df["n"],
        hole=0.48, marker_colors=colors,
        textinfo="percent+label", textfont_color="#E2E8F0",
        marker=dict(line=dict(color=_BG, width=2)),
    ))
    fig.update_layout(showlegend=False, **_base_layout())
    return fig


def root_cause_cost_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: mean cost impact per root cause."""
    df = df.sort_values("mean_cost_impact")
    colors = [ROOT_CAUSE_COLORS.get(rc, "#475569") for rc in df["root_cause"]]
    fig = go.Figure(go.Bar(
        x=df["mean_cost_impact"], y=df["root_cause"],
        orientation="h", marker_color=colors, opacity=0.85,
        text=[f"${v:.0f}" for v in df["mean_cost_impact"]],
        textposition="outside",
    ))
    fig.update_layout(xaxis_title="Mean Cost Impact ($)",
                      xaxis_range=[0, df["mean_cost_impact"].max() * 1.4],
                      **_base_layout())
    return fig


def policy_source_bar(df: pd.DataFrame) -> go.Figure:
    """Bar: policy count by source (builtin vs learned)."""
    counts = df["source"].value_counts().reset_index()
    counts.columns = ["source", "n"]
    fig = px.bar(counts, x="source", y="n",
                 color="source",
                 color_discrete_map={"builtin": "#38BDF8", "learned": "#10B981"},
                 text="n")
    fig.update_traces(textposition="outside", marker_opacity=0.85)
    fig.update_layout(showlegend=False, yaxis_range=[0, counts["n"].max() * 1.5],
                      **_base_layout())
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
            fill="toself", fillcolor=color, opacity=0.10,
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))

    fig.add_vline(x=3.5, line_dash="dash", line_color="#334155", opacity=0.8)
    fig.add_vline(x=7.5, line_dash="dash", line_color="#334155", opacity=0.8)
    fig.add_annotation(x=1.75, y=0.02, text="Pre-provision<br>gens 0–3",
                       showarrow=False, font=dict(size=10, color="#475569"), yref="paper")
    fig.add_annotation(x=5.75, y=0.02, text="Runtime<br>gens 4–7",
                       showarrow=False, font=dict(size=10, color="#475569"), yref="paper")
    fig.update_layout(
        xaxis_title="Generation",
        yaxis_title="Mean CPS (±95% CI, 5 seeds)",
        xaxis=dict(tickmode="linear", tick0=0, dtick=1, gridcolor=_GRID,
                   title_font=dict(size=12, color=_TEXT)),
        yaxis_range=[0, None],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color=_TEXT, size=12),
                    bgcolor="rgba(0,0,0,0)", borderwidth=0),
        paper_bgcolor=_BG, plot_bgcolor=_BG2,
        font=dict(color=_TEXT, size=12),
        margin=dict(t=56, b=10, l=10, r=24),
    )
    return fig