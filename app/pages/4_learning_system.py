"""Page 4 — Learning System: Convergence Study · Policy Adaptation · Feedback Loop."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.data_loader import (
    load_convergence,
    load_prevention_summary,
    load_root_cause_breakdown,
    load_policy_registry,
    load_ifs_distribution,
)
from components.charts import convergence_line

_BG, _BG2, _GRID, _TEXT = "#FAFAF8", "#FFFFFF", "rgba(0,0,0,0.05)", "#6B7280"

st.set_page_config(page_title="Learning System — PBCP", layout="wide")
st.title("Learning System")
st.markdown(
    "PBCP doesn't just react — it gets smarter over time. "
    "The Convergence Study shows CPS climbing across generations as the system learns from past runs. "
    "The Feedback Loop (Sreeja's module) watches for recurring anomalies and automatically "
    "writes new prevention rules so the same mistake doesn't cost money twice."
)
st.caption(
    "Phase 3 of PBCP — policy adaptation, divergence accumulation, "
    "and prospective guardrail synthesis from observed failure patterns."
)

tab_conv, tab_feedback = st.tabs(["Convergence Study", "Feedback Loop"])

# ============================================================
# TAB 1 — CONVERGENCE STUDY (Exp 6)
# ============================================================
with tab_conv:
    st.caption(
        "Exp 6 — System improvement across 10 generations, 5 seeds (42–46). "
        "Compares Full PBCP against three ablated configurations."
    )

    df = load_convergence()

    if df.empty:
        st.warning(
            "results/exp6_convergence.csv not found. "
            "Run: `python experiments/exp6_phase3_convergence.py`"
        )
        st.stop()

    full_col  = "full_pbcp_cps_mean"
    no3_col   = "no_phase3_cps_mean"
    peak_full = df[full_col].max()
    peak_no3  = df[no3_col].max()
    peak_gen  = int(df.loc[df[full_col].idxmax(), "generation"])
    improvement = round(peak_full / peak_no3, 1) if peak_no3 > 0 else float("inf")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Peak Full PBCP CPS",         f"{peak_full:.3f}", f"gen {peak_gen}")
    c2.metric("Peak No Phase 3 CPS",        f"{peak_no3:.3f}")
    c3.metric("Improvement vs. no-Phase-3", f"{improvement:.1f}×")
    c4.metric("Seeds",                      "5  (42–46)")

    st.divider()
    st.subheader("CPS Convergence Across Generations")
    st.plotly_chart(convergence_line(df), use_container_width=True)
    st.caption(
        "Vertical dashed lines separate pre-provision (gens 0–3), runtime (gens 4–7), "
        "and wrap-up (gens 8–9) record types. Shaded bands show ±95% CI across 5 seeds."
    )

    st.divider()
    st.subheader("Per-Generation Detail")
    gen = st.slider("Select generation", min_value=0, max_value=9, value=5)
    row = df[df["generation"] == gen].iloc[0]

    cols = st.columns(4)
    scenarios = [
        ("Full PBCP",      "full_pbcp"),
        ("No Phase 3",     "no_phase3"),
        ("Policy-only",    "policy_only"),
        ("Embedding-only", "embedding_only"),
    ]
    for col, (label, key) in zip(cols, scenarios):
        mean = row.get(f"{key}_cps_mean", 0.0)
        std  = row.get(f"{key}_cps_std",  0.0)
        col.metric(label, f"{mean:.3f}", f"±{std:.3f} std")

    st.divider()
    with st.expander("Raw convergence data"):
        st.caption(
            "**Generation 9 shows 0.000 for all configurations** — this is expected. "
            "Gen 9 is the final wrap-up pass: no new active-stage workloads are evaluated "
            "and no intervention records are produced, so CPS is undefined (displayed as 0). "
            "Peak performance is at gen 7–8; gen 9 is structural, not a regression."
        )
        display = df.copy()
        float_cols = [c for c in display.columns if c != "generation"]
        display[float_cols] = display[float_cols].round(4)
        st.dataframe(display, use_container_width=True, hide_index=True)


# ============================================================
# TAB 2 — FEEDBACK LOOP
# ============================================================
with tab_feedback:
    st.caption(
        "Phase 3 — intent-behavior discrepancy detection and policy synthesis. "
        "Misaligned workloads are diagnosed by root cause; recurring patterns "
        "generate new prevention rules that are applied prospectively."
    )

    st.subheader("The Four-Phase Learning Loop")

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown("**1. Measure**")
        st.info(
            "Every completed workload is scored (IFS, 0–1).  \n\n"
            "A score below **0.65** indicates that the workload's runtime behavior "
            "diverged significantly from its declared intent."
        )
    with s2:
        st.markdown("**2. Diagnose**")
        st.warning(
            "The system evaluates four alignment dimensions: job type, resource "
            "utilization, run duration, and provisioning ratio.  \n\n"
            "The lowest-scoring dimension is attributed as the primary failure mode."
        )
    with s3:
        st.markdown("**3. Learn**")
        st.warning(
            "If the same failure pattern recurs **three or more times** for a "
            "given workload type, the system synthesises a new prevention rule.  \n\n"
            "Rule confidence scales with the number of supporting observations."
        )
    with s4:
        st.markdown("**4. Prevent**")
        st.success(
            "The synthesised rule is registered in the policy store.  \n\n"
            "Subsequent submissions matching the failure pattern are intercepted "
            "**before resources are provisioned**, converting retrospective "
            "diagnoses into prospective guardrails."
        )

    st.divider()

    summary  = load_prevention_summary()
    rc_df    = load_root_cause_breakdown()
    pol_df   = load_policy_registry()
    ifs_df   = load_ifs_distribution()

    RC_LABELS = {
        "over_provisioned": "Over-Provisioned",
        "idle_cluster":     "Idle Cluster",
        "runaway_job":      "Runaway Job",
        "type_mismatch":    "Type Mismatch",
        "unknown":          "Unknown",
    }

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Misaligned Workloads Flagged", f"{summary['n_ibd']:,}",
              help="Workloads whose IFS fell below 0.65")
    c2.metric("Flagged Runs → Rules",         f"{summary['n_feedback_generated']:,}",
              help=(
                  "IBD-flagged run records whose (job type, failure mode) pattern "
                  "recurred ≥ 3 times, providing sufficient evidence to synthesise a "
                  "prevention rule. Many runs can share one rule — see 'Active Prevention "
                  "Rules' for the distinct rule count."
              ))
    c3.metric("Avg Score — Flagged Workloads", f"{summary['mean_ifs']:.3f}",
              help="Mean IFS of misaligned workloads (lower = more severe divergence)")
    c4.metric("Estimated Prevented Waste",     f"${summary['total_cost_impact']:,.0f}",
              help="Estimated cloud spend attributable to detected misalignments")
    learned_n = int((pol_df["source"] == "learned").sum()) if not pol_df.empty else 0
    c5.metric("Rules Synthesised",             str(learned_n),
              help="Prevention rules generated automatically from observed failure patterns")

    st.divider()

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Primary Failure Mode Distribution")
        st.caption(
            "Root cause attributed to each misaligned workload, "
            "diagnosed from the lowest-scoring IFS sub-dimension."
        )
        if not rc_df.empty:
            rc_plot = rc_df.copy()
            rc_plot["label"] = rc_plot["root_cause"].map(lambda x: RC_LABELS.get(x, x))
            RC_COLORS = {
                "Over-Provisioned": "#7BBFDB",
                "Idle Cluster":     "#FFB74D",
                "Runaway Job":      "#F28B82",
                "Type Mismatch":    "#C3A6D4",
                "Unknown":          "#9CA3AF",
            }
            colors = [RC_COLORS.get(l, "#9CA3AF") for l in rc_plot["label"]]
            fig = go.Figure(go.Pie(
                labels=rc_plot["label"], values=rc_plot["n"],
                hole=0.48, marker_colors=colors, textinfo="percent+label",
                textfont_color="#374151",
                marker=dict(line=dict(color=_BG, width=2)),
            ))
            fig.update_layout(showlegend=False, paper_bgcolor=_BG, plot_bgcolor=_BG2,
                              font=dict(color=_TEXT, size=12), margin=dict(t=24, b=10, l=10, r=24))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available.")

    with col_r:
        st.subheader("Estimated Waste by Failure Mode")
        st.caption(
            "Mean estimated wasted spend per workload run, by root cause. "
            "Idle clusters and over-provisioned workloads account for the largest share."
        )
        if not rc_df.empty:
            rc_plot = rc_df.copy()
            rc_plot["label"] = rc_plot["root_cause"].map(lambda x: RC_LABELS.get(x, x))
            rc_plot = rc_plot.sort_values("mean_cost_impact")
            bar_colors2 = [RC_COLORS.get(l, "#9CA3AF") for l in rc_plot["label"]]
            fig2 = go.Figure(go.Bar(
                x=rc_plot["mean_cost_impact"], y=rc_plot["label"],
                orientation="h", marker_color=bar_colors2, opacity=0.85,
                text=[f"${v:.0f}" for v in rc_plot["mean_cost_impact"]],
                textposition="outside",
            ))
            fig2.update_layout(
                xaxis_title="Estimated Wasted Cost per Run ($)",
                xaxis_range=[0, rc_plot["mean_cost_impact"].max() * 1.42],
                paper_bgcolor=_BG, plot_bgcolor=_BG2,
                font=dict(color=_TEXT, size=12),
                xaxis=dict(gridcolor=_GRID, title_font=dict(size=12, color=_TEXT)),
                margin=dict(t=24, b=10, l=10, r=24),
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.subheader("Built-in vs Synthesised Rules")
        st.caption(
            "**Built-in rules** were defined a priori (e.g., 'ETL jobs must shut down within 4 hours').  \n"
            "**Synthesised rules** were generated automatically after the system observed "
            "recurring failure patterns with sufficient evidence (≥ 3 occurrences)."
        )
        if not pol_df.empty:
            counts = pol_df["source"].value_counts().reset_index()
            counts.columns = ["source", "n"]
            counts["label"] = counts["source"].map(
                {"builtin": "Built-in Rules", "learned": "Synthesised Rules"}
            ).fillna(counts["source"])
            fig3 = go.Figure(go.Bar(
                x=counts["label"], y=counts["n"],
                marker_color=["#7BBFDB", "#81C995"][:len(counts)],
                opacity=0.85,
                text=counts["n"], textposition="outside",
            ))
            fig3.update_layout(
                yaxis=dict(range=[0, counts["n"].max() * 1.55], gridcolor=_GRID,
                           title="Rule Count"),
                paper_bgcolor=_BG, plot_bgcolor=_BG2,
                font=dict(color=_TEXT, size=12),
                showlegend=False, margin=dict(t=24, b=10, l=10, r=24),
            )
            st.plotly_chart(fig3, use_container_width=True)

    with col_r2:
        st.subheader("IFS Score Distribution — Flagged Workloads")
        st.caption(
            "Scores of workloads that triggered the feedback loop (IFS < 0.65). "
            "Most cluster around 0.50–0.65 — sufficient to flag, but not catastrophic."
        )
        ibd_ifs = ifs_df[ifs_df["ifs"] < 0.65] if not ifs_df.empty else ifs_df
        if not ibd_ifs.empty:
            fig4 = go.Figure()
            fig4.add_trace(go.Histogram(
                x=ibd_ifs["ifs"], nbinsx=25,
                marker_color="#F28B82", opacity=0.72,
                marker_line=dict(width=0.5, color="#FFFFFF"),
            ))
            fig4.add_vline(x=0.65, line_dash="dash", line_color="#9CA3AF",
                           annotation_text="Alert threshold (0.65)",
                           annotation_position="top right",
                           annotation_font_color=_TEXT)
            fig4.update_layout(
                xaxis_title="Intent-Fit Score (IFS)",
                yaxis_title="Workload Count",
                paper_bgcolor=_BG, plot_bgcolor=_BG2,
                font=dict(color=_TEXT, size=12),
                xaxis=dict(gridcolor=_GRID, title_font=dict(size=12, color=_TEXT)),
                yaxis=dict(gridcolor=_GRID, title_font=dict(size=12, color=_TEXT)),
                margin=dict(t=24, b=10, l=10, r=24), showlegend=False,
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No flagged workloads found.")

    st.divider()

    with st.expander("Failure breakdown by root cause"):
        if not rc_df.empty:
            display = rc_df.copy()
            display["root_cause"] = display["root_cause"].map(lambda x: RC_LABELS.get(x, x))
            st.dataframe(
                display.rename(columns={
                    "root_cause": "Failure Mode", "n": "Workloads Flagged",
                    "mean_ifs": "Avg IFS", "mean_cost_impact": "Avg Waste ($)",
                }),
                use_container_width=True, hide_index=True,
            )

    with st.expander("Active prevention rules"):
        st.caption("All rules currently registered. Synthesised rules were generated automatically.")
        if not pol_df.empty:
            display_cols = ["policy_id", "workload_type", "source", "action", "confidence"]
            if "description" in pol_df.columns:
                display_cols.append("description")
            pol_display = pol_df[display_cols].copy()
            pol_display["source"] = pol_display["source"].map(
                {"builtin": "Built-in", "learned": "Synthesised"}
            ).fillna(pol_display["source"])
            st.dataframe(
                pol_display.rename(columns={
                    "policy_id": "Rule ID", "workload_type": "Job Type",
                    "source": "Origin", "action": "Action",
                    "confidence": "Confidence", "description": "Description",
                }),
                use_container_width=True, hide_index=True,
            )