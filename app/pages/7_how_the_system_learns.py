"""Page 7 — How the System Learns (anomaly_rca / Sreeja Katta)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.data_loader import (
    load_prevention_summary,
    load_root_cause_breakdown,
    load_policy_registry,
    load_ifs_distribution,
)

st.set_page_config(page_title="How the System Learns — PBCP", layout="wide")

# ── Hero ───────────────────────────────────────────────────────────────────────
st.title("🧠 How the System Learns")
st.markdown(
    """
    The system doesn't just catch bad jobs — it **remembers them** and uses that knowledge
    to stop the same problem happening again. Every misbehaving job teaches the system a
    new rule. Over time, fewer jobs waste money because the system has seen it all before.
    """
)

# ── 4-step visual loop ─────────────────────────────────────────────────────────
st.divider()
st.subheader("The Learning Loop — 4 Steps")

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown("### 1️⃣ Measure")
    st.info(
        "Every completed job gets a **behaviour score** (0–1).  \n\n"
        "A score below **0.65** means the job didn't do what it said it would — "
        "too much idle time, too many resources, ran too long."
    )
with s2:
    st.markdown("### 2️⃣ Diagnose")
    st.warning(
        "The system inspects **4 dimensions**: job type match, resource usage, "
        "run duration, and utilisation.  \n\n"
        "Whichever dimension scored lowest is flagged as the **root cause**."
    )
with s3:
    st.markdown("### 3️⃣ Learn")
    st.warning(
        "If the **same type of failure** shows up **3 or more times**, "
        "the system builds a new rule automatically.  \n\n"
        "Confidence grows with each repeat — more evidence = stronger rule."
    )
with s4:
    st.markdown("### 4️⃣ Prevent")
    st.success(
        "The new rule is added to the **policy registry**.  \n\n"
        "Next time a similar job is submitted, the system catches it "
        "**before resources are even created** — turning past mistakes into future savings."
    )

st.divider()

summary  = load_prevention_summary()
rc_df    = load_root_cause_breakdown()
pol_df   = load_policy_registry()
ifs_df   = load_ifs_distribution()

# Friendly root cause label map
RC_LABELS = {
    "over_provisioned": "Too Many Resources",
    "idle_cluster":     "Cluster Sitting Idle",
    "runaway_job":      "Job Ran Too Long",
    "type_mismatch":    "Wrong Job Type Declared",
    "unknown":          "Unknown",
}

# ── KPI row ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Misbehaving Jobs Caught",  f"{summary['n_ibd']:,}",
          help="Jobs whose behaviour score fell below 0.65")
c2.metric("New Rules Auto-Generated", f"{summary['n_feedback_generated']:,}",
          help="Prevention rules the system created by itself from repeated patterns")
c3.metric("Avg Score of Bad Jobs",    f"{summary['mean_ifs']:.3f}",
          help="Average behaviour score of the flagged jobs (lower = worse)")
c4.metric("Estimated Waste Caught",   f"${summary['total_cost_impact']:,.0f}",
          help="Estimated cloud spend that could have been prevented")
learned_n = int((pol_df["source"] == "learned").sum()) if not pol_df.empty else 0
c5.metric("Rules Learned So Far",     str(learned_n),
          help="Policies in the registry that the system wrote itself (not hand-coded)")

st.divider()

# ── Row 1: why jobs failed + cost per failure type ─────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Why did jobs fail?")
    st.caption(
        "Each slice shows the most common reason a job's behaviour didn't match "
        "its declared intent — diagnosed automatically from the lowest sub-score."
    )
    if not rc_df.empty:
        rc_plot = rc_df.copy()
        rc_plot["label"] = rc_plot["root_cause"].map(lambda x: RC_LABELS.get(x, x))
        RC_COLORS = {
            "Too Many Resources":      "#1f77b4",
            "Cluster Sitting Idle":    "#ff7f0e",
            "Job Ran Too Long":        "#d62728",
            "Wrong Job Type Declared": "#9467bd",
            "Unknown":                 "#7f7f7f",
        }
        colors = [RC_COLORS.get(l, "#aaaaaa") for l in rc_plot["label"]]
        fig = go.Figure(go.Pie(
            labels=rc_plot["label"], values=rc_plot["n"],
            hole=0.45, marker_colors=colors, textinfo="percent+label",
        ))
        fig.update_layout(showlegend=False, margin=dict(t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet.")

with col_r:
    st.subheader("How much does each failure type cost?")
    st.caption(
        "Average estimated waste per job run, by root cause. "
        "Idle clusters and over-provisioned jobs tend to be the most expensive."
    )
    if not rc_df.empty:
        rc_plot = rc_df.copy()
        rc_plot["label"] = rc_plot["root_cause"].map(lambda x: RC_LABELS.get(x, x))
        rc_plot = rc_plot.sort_values("mean_cost_impact")
        bar_colors = [RC_COLORS.get(l, "#aaaaaa") for l in rc_plot["label"]]
        fig2 = go.Figure(go.Bar(
            x=rc_plot["mean_cost_impact"], y=rc_plot["label"],
            orientation="h", marker_color=bar_colors,
            text=[f"${v:.0f}" for v in rc_plot["mean_cost_impact"]],
            textposition="outside",
        ))
        fig2.update_layout(
            xaxis_title="Average Wasted Cost per Job ($)",
            xaxis_range=[0, rc_plot["mean_cost_impact"].max() * 1.4],
            plot_bgcolor="white",
            xaxis=dict(gridcolor="#f0f0f0"),
            margin=dict(t=20, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Row 2: hand-coded vs learned rules + score distribution ────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Hand-coded rules vs rules the system wrote itself")
    st.caption(
        "**Built-in rules** were written by the team upfront (e.g. 'ETL jobs must shut down within 4 hours').  \n"
        "**Learned rules** were generated automatically by the system after spotting repeated failure patterns."
    )
    if not pol_df.empty:
        counts = pol_df["source"].value_counts().reset_index()
        counts.columns = ["source", "n"]
        counts["label"] = counts["source"].map(
            {"builtin": "Hand-coded rules", "learned": "Auto-generated rules"}
        ).fillna(counts["source"])
        fig3 = go.Figure(go.Bar(
            x=counts["label"], y=counts["n"],
            marker_color=["#1f77b4", "#ff7f0e"][:len(counts)],
            text=counts["n"], textposition="outside",
        ))
        fig3.update_layout(
            yaxis=dict(range=[0, counts["n"].max() * 1.5], gridcolor="#f0f0f0"),
            plot_bgcolor="white", showlegend=False,
            margin=dict(t=20, b=10),
        )
        st.plotly_chart(fig3, use_container_width=True)

with col_r:
    st.subheader("Score distribution of flagged jobs")
    st.caption(
        "This shows the behaviour scores of jobs that triggered the learning loop. "
        "Most cluster around 0.50–0.65 — bad enough to flag, but not catastrophic."
    )
    ibd_ifs = ifs_df[ifs_df["ifs"] < 0.65] if not ifs_df.empty else ifs_df
    if not ibd_ifs.empty:
        fig4 = go.Figure()
        fig4.add_trace(go.Histogram(
            x=ibd_ifs["ifs"], nbinsx=25,
            marker_color="#d62728", opacity=0.75,
        ))
        fig4.add_vline(x=0.65, line_dash="dash", line_color="#555",
                       annotation_text="Alert threshold (0.65)",
                       annotation_position="top right")
        fig4.update_layout(
            xaxis_title="Behaviour Score (IFS)",
            yaxis_title="Number of Jobs",
            plot_bgcolor="white",
            xaxis=dict(gridcolor="#f0f0f0"),
            yaxis=dict(gridcolor="#f0f0f0"),
            margin=dict(t=20, b=10), showlegend=False,
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No flagged jobs found.")

st.divider()

# ── Root cause detail table ─────────────────────────────────────────────────────
with st.expander("📋 Failure breakdown by root cause"):
    if not rc_df.empty:
        display = rc_df.copy()
        display["root_cause"] = display["root_cause"].map(lambda x: RC_LABELS.get(x, x))
        st.dataframe(
            display.rename(columns={
                "root_cause": "Failure Type", "n": "Jobs Flagged",
                "mean_ifs": "Avg Score", "mean_cost_impact": "Avg Waste ($)",
            }),
            use_container_width=True, hide_index=True,
        )

# ── Policy registry ─────────────────────────────────────────────────────────────
with st.expander("📋 Active prevention rules"):
    st.caption("Every rule currently in effect. Learned rules were written by the system itself.")
    if not pol_df.empty:
        display_cols = ["policy_id", "workload_type", "source", "action", "confidence"]
        if "description" in pol_df.columns:
            display_cols.append("description")
        pol_display = pol_df[display_cols].copy()
        pol_display["source"] = pol_display["source"].map(
            {"builtin": "Hand-coded", "learned": "Auto-generated"}
        ).fillna(pol_display["source"])
        st.dataframe(
            pol_display.rename(columns={
                "policy_id": "Rule ID", "workload_type": "Job Type",
                "source": "Origin", "action": "Action",
                "confidence": "Confidence", "description": "Description",
            }),
            use_container_width=True, hide_index=True,
        )
