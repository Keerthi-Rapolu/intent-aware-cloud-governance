"""Page 2 — Prevention Engine: Live Demo · Workload Catalogue · Anomaly Detection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.data_loader import (
    load_workloads,
    load_ibd_detector_metrics,
    load_ibd_threshold_sweep,
    load_ibd_mismatch_subgroup,
)
from components.charts import confusion_matrix_heatmap

st.set_page_config(page_title="Prevention Engine — PBCP", layout="wide")
st.title("Prevention Engine")
st.markdown(
    "This is where PBCP earns its keep — type in a workload description and watch it "
    "decide whether to block, fix, suggest, or wave it through **before** a single dollar "
    "is spent. Also includes the full workload catalogue and Sreeja's IBD anomaly detector "
    "that catches jobs whose actual behaviour doesn't match what was promised."
)

tab_demo, tab_catalogue, tab_anomaly = st.tabs(
    ["Live Demo", "Workload Catalogue", "Anomaly Detection"]
)

# ─────────────────────────────────────────────────────────────────────────────
# CHART THEME CONSTANTS (keep dark)
# ─────────────────────────────────────────────────────────────────────────────
_BG, _BG2, _GRID, _TEXT = "#FAFAF8", "#FFFFFF", "rgba(0,0,0,0.05)", "#6B7280"

INT_COLOR_MAP = {
    "BLOCK":        "#DC2626",
    "AUTO_CORRECT": "#15803D",
    "SUGGEST":      "#B45309",
    "PASS":         "#0891B2",
}
INT_CSS_CLASS = {"BLOCK": "blk", "AUTO_CORRECT": "ac", "SUGGEST": "sug", "PASS": "pas"}


# ============================================================
# TAB 1 — LIVE DEMO
# ============================================================
with tab_demo:
    st.caption(
        "Enter a workload description to see intent inference, pre-execution simulation, "
        "and Intent-Fit Score in real time."
    )
    st.markdown("""
<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;">
  <span class="badge badge-sim">Controlled Benchmark Priors</span>
  <span class="badge badge-price">Published Cloud Pricing</span>
  <span class="badge badge-proto">Research Prototype</span>
</div>
""", unsafe_allow_html=True)

    # ── Showcase scenario cards ───────────────────────────────────────────────
    st.markdown("#### Showcase Scenarios")
    st.caption(
        "Three preset scenarios illustrate the full intervention spectrum: "
        "aggressive correction, moderate optimization, and intelligent non-intervention."
    )

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown("""
<div class="iv-card ac">
  <h4>High-Impact Correction</h4>
  <p><span class="highlight">customer-churn-weekly</span></p>
  <p>32 nodes requested · 24% predicted utilization</p>
  <p>Spark ML · 3 TB dataset · PII</p>
  <p style="margin-top:8px; color:#15803D; font-weight:600;">
    AUTO_CORRECT → 9 nodes<br>$382 prevented · CPS 0.719
  </p>
</div>
""", unsafe_allow_html=True)

    with sc2:
        st.markdown("""
<div class="iv-card sug">
  <h4>Moderate Optimization</h4>
  <p><span class="highlight">billing-reconciliation-nightly</span></p>
  <p>16 nodes requested · 51% predicted utilization</p>
  <p>ETL · 500 GB Parquet · nightly window</p>
  <p style="margin-top:8px; color:#B45309; font-weight:600;">
    SUGGEST → 11 nodes<br>$40 estimated savings · CPS 0.312
  </p>
</div>
""", unsafe_allow_html=True)

    with sc3:
        st.markdown("""
<div class="iv-card pas">
  <h4>Well-Aligned Workload</h4>
  <p><span class="highlight">fraud-stream-monitor</span></p>
  <p>6 nodes requested · 82% predicted utilization</p>
  <p>Streaming · Kafka · autoscaling enabled</p>
  <p style="margin-top:8px; color:#0891B2; font-weight:600;">
    PASS · No intervention required<br>IFS 0.921 · well-aligned
  </p>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── Pipeline availability check ──────────────────────────────────────────
    try:
        from intent_model.intent_inference import IntentInferenceEngine
        _PIPELINE_AVAILABLE = True
    except Exception:
        _PIPELINE_AVAILABLE = False

    if not _PIPELINE_AVAILABLE:
        st.warning(
            "**Live pipeline requires local installation.**  "
            "DistilBERT and FAISS models are not deployed to Streamlit Cloud "
            "due to size constraints.  \n\n"
            "To run the full pipeline locally:\n"
            "```bash\n"
            "git clone https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance\n"
            "pip install -r requirements.txt\n"
            "python data/generate_dataset.py\n"
            "streamlit run app/app.py\n"
            "```"
        )
        st.divider()

        st.subheader("Example Output — Exp 2 Scenario C (Runaway ML Job)")
        st.success(
            "AUTO_CORRECT — nodes reduced 20 → 9 | cost prevented $97.92 | CPS 0.667"
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Intervention",   "AUTO_CORRECT")
        c2.metric("Optimal nodes",  "9 / 20 submitted")
        c3.metric("Cost prevented", "$97.92")
        c4.metric("CPS",            "0.667")

        st.divider()
        st.subheader("Intent-Fit Score — Example")
        st.caption(
            "IFS measures alignment between the workload's declared intent and its "
            "predicted runtime behavior. Displayed sub-scores are interpretable "
            "components contributing to the embedding-based IFS calculation."
        )
        ec1, ec2, ec3 = st.columns(3)
        ec1.metric("IFS",          "0.712",
                   help="Weighted: 0.35×type + 0.25×util + 0.20×duration + 0.20×resource")
        ec2.metric("Category",     "minor")
        ec3.metric("Anomaly flag", "No (above 0.65 threshold)")

        example_sub = {
            "Job Type\nAlignment":    0.85,
            "Utilisation\nAlignment": 0.62,
            "Duration\nAlignment":    0.70,
            "Resource\nAlignment":    0.68,
        }
        _bar_c = ["#F28B82" if v < 0.50 else "#FFB74D" if v < 0.70 else "#81C995"
                  for v in example_sub.values()]
        eg_fig = go.Figure(go.Bar(
            x=list(example_sub.keys()), y=list(example_sub.values()),
            marker_color=_bar_c,
            text=[f"{v:.3f}" for v in example_sub.values()],
            textposition="outside",
        ))
        eg_fig.add_hline(y=0.65, line_dash="dash", line_color="#DC2626", line_width=1.5,
                         annotation_text="Alert threshold (0.65)",
                         annotation_position="top right",
                         annotation_font_color="#DC2626")
        eg_fig.update_layout(
            yaxis=dict(range=[0, 1.18], title="Alignment Score", gridcolor=_GRID,
                       title_font=dict(size=12, color=_TEXT)),
            paper_bgcolor=_BG, plot_bgcolor=_BG2,
            font=dict(color=_TEXT, size=12),
            margin=dict(t=32, b=10, l=10, r=24), showlegend=False,
        )
        st.plotly_chart(eg_fig, use_container_width=True)

    if _PIPELINE_AVAILABLE:
        # ── Preset buttons ────────────────────────────────────────────────────
        PRESETS = {
            "High Impact — ML Training": (
                "Weekly customer churn model retraining on 3 TB Spark ML dataset "
                "with PII records — hyperparameter search, XGBoost, distributed training",
                "ml_training", 32,
            ),
            "Moderate — Nightly ETL": (
                "Nightly billing reconciliation ETL on 500 GB Parquet files from S3 "
                "into Redshift — includes PII customer payment records, scheduled 02:00 UTC",
                "etl", 16,
            ),
            "Well-Aligned — Streaming": (
                "Real-time fraud monitoring Kafka stream with tumbling 60-second windows "
                "— continuous processing of live payment events, autoscaling enabled",
                "streaming", 6,
            ),
            "LLM Pipeline": (
                "Batch RAG pipeline for customer support summarization — embedding "
                "500K documents into FAISS vector store via OpenAI API completions",
                "llm_pipeline", 12,
            ),
            "Adhoc Analytics": (
                "One-off exploratory analysis of Q2 marketing campaign performance "
                "across customer segments — ad-hoc query on 200 GB transaction data",
                "adhoc", 10,
            ),
        }

        if "demo_desc" not in st.session_state:
            st.session_state.demo_desc = (
                "Weekly customer churn model retraining on 3 TB Spark ML dataset "
                "with PII records — hyperparameter search, XGBoost, distributed training"
            )
        if "demo_type" not in st.session_state:
            st.session_state.demo_type = "ml_training"
        if "demo_nodes" not in st.session_state:
            st.session_state.demo_nodes = 32

        st.markdown("**Quick-start presets:**")
        pcols = st.columns(len(PRESETS))
        for col, (label, (desc, wtype, node_default)) in zip(pcols, PRESETS.items()):
            if col.button(label, key=f"preset_{label}", use_container_width=True):
                st.session_state.demo_desc  = desc
                st.session_state.demo_type  = wtype
                st.session_state.demo_nodes = node_default

        # ── Input form ────────────────────────────────────────────────────────
        col_in, col_cfg = st.columns([2, 1])

        with col_in:
            description = st.text_area(
                "Workload description",
                value=st.session_state.demo_desc,
                height=120,
                placeholder=(
                    "e.g., weekly customer churn model retraining on 3 TB dataset "
                    "with PII — Spark ML, XGBoost"
                ),
            )

        type_options = ["etl", "adhoc", "ml_training", "llm_pipeline", "batch", "streaming"]
        default_idx  = (type_options.index(st.session_state.demo_type)
                        if st.session_state.demo_type in type_options else 2)

        with col_cfg:
            declared_type = st.selectbox("Declared workload type", type_options, index=default_idx)
            cloud    = st.selectbox("Cloud provider", ["aws", "azure", "gcp"])
            instance = st.selectbox(
                "Instance type",
                ["m5.xlarge", "m5.2xlarge", "m5.4xlarge", "p3.2xlarge",
                 "r5.xlarge", "c5.xlarge"],
            )
            nodes    = st.slider("Node count",     min_value=1,   max_value=50,
                                 value=st.session_state.demo_nodes)
            duration = st.slider("Expected hours", min_value=0.5, max_value=24.0,
                                 value=8.0, step=0.5)
            priority = st.selectbox("Priority", ["low", "medium", "high", "critical"], index=1)
            use_spot = st.checkbox("Use spot instances", value=False)

        run_btn = st.button("Simulate", type="primary")

        if not run_btn:
            st.info("Fill in the fields above and click **Simulate**.")
        elif not description.strip():
            st.warning("Enter a workload description to run the simulation.")
        else:
            # ── Run pipeline ──────────────────────────────────────────────────
            with st.spinner("Running PBCP pipeline..."):
                try:
                    from simulation_engine.simulator import PreExecutionSimulator
                    from ifs.ifs_calculator import IFSCalculator
                    from simulation_engine.cost_model import CloudCostModel

                    engine   = IntentInferenceEngine()
                    inferred = engine.infer(description, declared_type=declared_type)

                    intent_dict = {
                        "intent_id":               "live-demo",
                        "workload_type":           declared_type,
                        "cloud_provider":          cloud,
                        "instance_type":           instance,
                        "node_count":              nodes,
                        "use_spot":                use_spot,
                        "priority":                priority,
                        "expected_duration_hours": duration,
                    }
                    simulator   = PreExecutionSimulator()
                    sim         = simulator.simulate(intent_dict)
                    cost_model  = CloudCostModel()
                    static_cost = cost_model.compute_cost(cloud, instance, nodes, duration, use_spot)

                    typical_actual = sim.predicted_utilization * 0.90
                    ifs_rec = IFSCalculator.compute_ifs(
                        intent_id="live-demo", run_id="demo",
                        type_mismatch=inferred.type_mismatch,
                        type_mismatch_confidence=inferred.type_mismatch_confidence or 0.0,
                        predicted_utilization=sim.predicted_utilization,
                        actual_utilization=typical_actual,
                        expected_duration_hours=duration,
                        actual_duration_hours=duration,
                        over_provision_factor=nodes / max(sim.optimal_nodes, 1),
                    )
                    ok = True
                except Exception as exc:
                    st.error(f"Pipeline error: {exc}")
                    import traceback; traceback.print_exc()
                    ok = False

            if ok:
                # ── Results ───────────────────────────────────────────────────
                st.divider()
                color = INT_COLOR_MAP.get(sim.intervention, "#94A3B8")

                if sim.intervention == "AUTO_CORRECT":
                    st.success(
                        f"AUTO_CORRECT — nodes reduced {nodes} → {sim.optimal_nodes} "
                        f"| cost prevented ${sim.prevented_cost_usd:.2f} | CPS {sim.cps:.3f}"
                    )
                elif sim.intervention == "BLOCK":
                    st.error(
                        f"BLOCK — submission rejected | potential waste ${sim.prevented_cost_usd:.2f}"
                    )
                elif sim.intervention == "SUGGEST":
                    st.warning(
                        f"SUGGEST — predicted utilization ({sim.predicted_utilization:.0%}) indicates "
                        f"{sim.optimal_nodes} nodes would suffice vs {nodes} submitted. "
                        f"EV model favors suggestion over forced correction "
                        f"(EV_AUTO_CORRECT = {sim.ev_auto_correct:.1f})."
                    )
                else:
                    if inferred.type_mismatch:
                        st.info(
                            f"PASS — workload type divergence detected "
                            f"(declared: {declared_type}, inferred: {inferred.workload_type_inferred}), "
                            f"but EV model determines correction cost exceeds expected waste "
                            f"(EV_AUTO_CORRECT = {sim.ev_auto_correct:.1f})."
                        )
                    else:
                        st.info("PASS — no intervention required (utilization healthy, no type mismatch)")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Intervention",   sim.intervention)
                c2.metric("Optimal nodes",  f"{sim.optimal_nodes} / {nodes} submitted")
                c3.metric("Cost prevented", f"${sim.prevented_cost_usd:.2f}")
                c4.metric("CPS",            f"{sim.cps:.3f}")

                # Before / After cards
                st.divider()
                col_before, col_after = st.columns(2)
                with col_before:
                    st.markdown("""
<div style="font-size:11px; font-weight:700; letter-spacing:0.08em;
            text-transform:uppercase; color:#475569; margin-bottom:8px;">
As Submitted
</div>""", unsafe_allow_html=True)
                    st.metric("Node count",        nodes)
                    st.metric("Projected cost",    f"${static_cost:.2f}",
                              help="Cost at submitted configuration, unmodified")

                with col_after:
                    st.markdown(f"""
<div style="font-size:11px; font-weight:700; letter-spacing:0.08em;
            text-transform:uppercase; color:{color}; margin-bottom:8px;">
After PBCP Intervention
</div>""", unsafe_allow_html=True)
                    st.metric("Optimal nodes",    sim.optimal_nodes,
                              delta=f"{sim.optimal_nodes - nodes:+d} node adjustment")
                    st.metric("Right-sized cost", f"${sim.right_sized_cost_usd:.2f}",
                              delta=f"-${sim.prevented_cost_usd:.2f}", delta_color="inverse")

                st.divider()
                col_l, col_r = st.columns(2)

                with col_l:
                    st.subheader("Intent Inference")
                    st.json({
                        "declared_type":        declared_type,
                        "inferred_type":        inferred.workload_type_inferred,
                        "type_mismatch":        inferred.type_mismatch,
                        "mismatch_confidence":  inferred.type_mismatch_confidence,
                        "pii_signal":           inferred.pii_signal,
                        "recurrence":           inferred.recurrence_signal,
                        "data_volume":          inferred.data_volume_estimate,
                        "latency_sensitivity":  inferred.latency_sensitivity,
                        "inference_confidence": inferred.inference_confidence,
                    })

                with col_r:
                    st.subheader("Simulation Result")
                    st.json({
                        "predicted_utilization": sim.predicted_utilization,
                        "submitted_nodes":       sim.submitted_nodes,
                        "optimal_nodes":         sim.optimal_nodes,
                        "potential_cost_usd":    round(sim.potential_cost_usd, 4),
                        "right_sized_cost_usd":  round(sim.right_sized_cost_usd, 4),
                        "prevented_cost_usd":    round(sim.prevented_cost_usd, 4),
                        "intervention":          sim.intervention,
                        "ev_auto_correct":       sim.ev_auto_correct,
                        "ev_block":              sim.ev_block,
                    })

                # ── IFS gauge + sub-scores ────────────────────────────────────
                st.divider()
                st.subheader("Intent-Fit Score (IFS)")
                st.caption(
                    "Measures alignment between the workload's declared intent and its predicted "
                    "runtime behavior. Displayed sub-scores are interpretable components "
                    "contributing to the embedding-based IFS calculation. IFS < 0.65 triggers "
                    "the anomaly detector."
                )

                ifs_meta = {
                    "well_aligned": ("#15803D", "Well Aligned",
                                     "Predicted behavior aligns with declared intent."),
                    "minor":        ("#0891B2", "Minor Divergence",
                                     "Small gap between intent and predicted behavior."),
                    "significant":  ("#B45309", "Significant Divergence",
                                     "Noticeable divergence — warrants investigation."),
                    "severe":       ("#DC2626", "Severe Divergence",
                                     "Large divergence — workload is likely misconfigured."),
                }
                ifs_color, ifs_badge, verdict_msg = ifs_meta.get(
                    ifs_rec.ifs_category, ("#94A3B8", "Unknown", "")
                )

                gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=ifs_rec.ifs,
                    number={"font": {"size": 48, "color": ifs_color}, "valueformat": ".3f"},
                    gauge={
                        "axis": {"range": [0, 1], "tickwidth": 1, "tickcolor": "#334155",
                                 "tickfont": {"color": "#94A3B8"}},
                        "bar":  {"color": ifs_color, "thickness": 0.25},
                        "bgcolor": "#FAFAF8",
                        "borderwidth": 0,
                        "steps": [
                            {"range": [0.00, 0.50], "color": "rgba(242,139,130,0.18)"},
                            {"range": [0.50, 0.65], "color": "rgba(255,183,77,0.15)"},
                            {"range": [0.65, 0.85], "color": "rgba(123,191,219,0.12)"},
                            {"range": [0.85, 1.00], "color": "rgba(129,201,149,0.18)"},
                        ],
                        "threshold": {
                            "line": {"color": "#DC2626", "width": 2},
                            "thickness": 0.8, "value": 0.65,
                        },
                    },
                    title={"text": f"<b>{ifs_badge}</b>",
                           "font": {"size": 16, "color": ifs_color}},
                ))
                gauge.update_layout(height=260, paper_bgcolor="#FAFAF8", plot_bgcolor="#FAFAF8",
                                    font=dict(color=_TEXT, size=12),
                                    margin=dict(t=40, b=0, l=32, r=32))

                col_gauge, col_verdict = st.columns([1, 1])
                with col_gauge:
                    st.plotly_chart(gauge, use_container_width=True)

                with col_verdict:
                    st.markdown(f"### {ifs_badge}")
                    st.markdown(verdict_msg)
                    st.markdown(
                        f"**Score:** `{ifs_rec.ifs:.3f}` &nbsp;·&nbsp; "
                        f"**Category:** `{ifs_rec.ifs_category}`"
                    )
                    IBD_THRESHOLD = 0.65
                    if ifs_rec.ifs < IBD_THRESHOLD:
                        sub = {
                            "Job type mismatch":       ifs_rec.type_alignment,
                            "Utilisation mismatch":    ifs_rec.util_alignment,
                            "Duration mismatch":       ifs_rec.duration_alignment,
                            "Resource over-provision": ifs_rec.resource_alignment,
                        }
                        root_cause_label = min(sub, key=lambda k: sub[k])
                        st.error(
                            f"Anomaly detector would flag this workload.  \n"
                            f"IFS {ifs_rec.ifs:.3f} is below the alert threshold {IBD_THRESHOLD}.  \n"
                            f"Primary driver: **{root_cause_label}** "
                            f"(sub-score: {sub[root_cause_label]:.3f})"
                        )
                    else:
                        st.success(
                            f"Anomaly detector: no flag.  \n"
                            f"IFS {ifs_rec.ifs:.3f} is above the alert threshold {IBD_THRESHOLD}."
                        )

                st.markdown("#### Sub-score Breakdown")
                st.caption(
                    "Interpretable components contributing to the embedding-based IFS. "
                    "Red = primary divergence driver."
                )
                sub_scores = {
                    "Job Type\nAlignment":    ifs_rec.type_alignment,
                    "Utilisation\nAlignment": ifs_rec.util_alignment,
                    "Duration\nAlignment":    ifs_rec.duration_alignment,
                    "Resource\nAlignment":    ifs_rec.resource_alignment,
                }
                bar_colors = ["#F28B82" if v < 0.50 else "#FFB74D" if v < 0.70 else "#81C995"
                              for v in sub_scores.values()]
                bar_fig = go.Figure(go.Bar(
                    x=list(sub_scores.keys()), y=list(sub_scores.values()),
                    marker_color=bar_colors, opacity=0.85,
                    text=[f"{v:.3f}" for v in sub_scores.values()],
                    textposition="outside",
                ))
                bar_fig.add_hline(y=0.65, line_dash="dash", line_color="#DC2626", line_width=1.5,
                                  annotation_text="Alert threshold (0.65)",
                                  annotation_position="top right",
                                  annotation_font_color="#DC2626")
                bar_fig.add_hline(y=1.0, line_color="rgba(0,0,0,0)")
                bar_fig.update_layout(
                    yaxis=dict(range=[0, 1.18], title="Alignment Score", gridcolor=_GRID,
                               title_font=dict(size=12, color=_TEXT)),
                    paper_bgcolor=_BG, plot_bgcolor=_BG2,
                    font=dict(color=_TEXT, size=12),
                    margin=dict(t=32, b=10, l=10, r=24), showlegend=False,
                )
                st.plotly_chart(bar_fig, use_container_width=True)


# ============================================================
# TAB 2 — WORKLOAD CATALOGUE
# ============================================================
with tab_catalogue:
    st.caption(
        "Controlled evaluation benchmark — 500 workloads, seed 42. "
        "Includes controlled anomaly injection for governance evaluation."
    )

    df = load_workloads()

    col_f1, col_f2, col_f3 = st.columns(3)
    types = col_f1.multiselect(
        "Workload type", sorted(df["workload_type"].unique()),
        default=sorted(df["workload_type"].unique()),
    )
    teams = col_f2.multiselect(
        "Team", sorted(df["team"].unique()),
        default=sorted(df["team"].unique()),
    )
    envs = col_f3.multiselect(
        "Environment", sorted(df["environment"].unique()),
        default=sorted(df["environment"].unique()),
    )
    col_f4, col_f5 = st.columns(2)
    over_prov = col_f4.checkbox("Over-provisioned only (OPF ≥ 1.5)")
    mismatch  = col_f5.checkbox("Type-mismatch only")

    filt = df[
        df["workload_type"].isin(types) &
        df["team"].isin(teams) &
        df["environment"].isin(envs)
    ]
    if over_prov:
        filt = filt[filt["is_over_provisioned"]]
    if mismatch:
        filt = filt[filt["type_mismatch"]]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Workloads", len(filt))
    c2.metric(
        "Over-provisioned",
        f"{filt['is_over_provisioned'].sum()} ({filt['is_over_provisioned'].mean()*100:.0f}%)"
        if len(filt) else "—",
    )
    c3.metric(
        "Type divergence",
        f"{filt['type_mismatch'].sum()} ({filt['type_mismatch'].mean()*100:.0f}%)"
        if len(filt) else "—",
    )
    c4.metric(
        "Avg expected duration",
        f"{filt['expected_h'].mean():.1f} h" if len(filt) else "—",
    )

    display_cols = [
        "workload_name", "workload_type", "team", "environment", "priority",
        "expected_h", "node_count", "opf", "is_over_provisioned",
        "type_mismatch", "use_spot", "instance_type",
    ]
    st.dataframe(
        filt[display_cols].rename(columns={
            "workload_name": "Name", "workload_type": "Type", "team": "Team",
            "environment": "Env", "priority": "Priority", "expected_h": "Exp. h",
            "node_count": "Nodes", "opf": "OPF",
            "is_over_provisioned": "Over-prov",
            "type_mismatch": "Type divergence",
            "use_spot": "Spot", "instance_type": "Instance",
        }),
        use_container_width=True, height=420,
    )

    if len(filt):
        st.divider()
        st.subheader("Workload Detail")
        selected_name = st.selectbox(
            "Select a workload", options=filt["workload_name"].tolist(), index=0
        )
        if selected_name:
            row = filt[filt["workload_name"] == selected_name].iloc[0]
            cl, cr = st.columns(2)
            with cl:
                st.markdown(f"**Description:** {row['description']}")
                st.markdown(
                    f"**Type:** {row['workload_type']} · **Team:** {row['team']} · "
                    f"**Priority:** {row['priority']}"
                )
                st.markdown(
                    f"**Environment:** {row['environment']} · **Spot:** {row['use_spot']}"
                )
            with cr:
                st.markdown(
                    f"**Nodes:** {row['node_count']} · **Instance:** {row['instance_type']}"
                )
                st.markdown(
                    f"**OPF:** {row['opf']:.2f} · "
                    f"**Over-provisioned:** {row['is_over_provisioned']}"
                )
                st.markdown(
                    f"**Type divergence:** {row['type_mismatch']} · "
                    f"**PII:** {row['pii_signal']}"
                )


# ============================================================
# TAB 3 — ANOMALY DETECTION
# ============================================================
with tab_anomaly:
    st.caption(
        "Exp 3 — IBD detection evaluation. "
        "Compares the IFS-based detector against a CPU-utilization threshold baseline. "
        "Benchmark includes controlled anomaly injection for evaluation."
    )

    m              = load_ibd_detector_metrics()
    sweep          = load_ibd_threshold_sweep()
    mismatch_df    = load_ibd_mismatch_subgroup()

    c1, c2, c3, c4, c5 = st.columns(5)
    f1_delta = m["ifs"]["f1"] - m["threshold"]["f1"]
    c1.metric("Total Runs Analysed",      f"{m['n_total']:,}")
    c2.metric("Confirmed Anomalous Runs", f"{m['n_anomaly']:,}",
              help="Runs confirmed anomalous: idle, runaway, or injected fault")
    c3.metric("IFS Detector — F1",        f"{m['ifs']['f1']:.3f}",
              delta=f"+{f1_delta:.3f} vs CPU threshold")
    c4.metric("IFS Detector — Precision", f"{m['ifs']['precision']:.3f}")
    c5.metric("IFS Detector — Recall",    f"{m['ifs']['recall']:.3f}")

    mm_idx  = mismatch_df.set_index("group")
    gate_f1 = m["ifs"]["f1"] >= m["threshold"]["f1"]
    gate_mm = (mm_idx.loc["type_mismatch", "anomaly_rate"] >=
               mm_idx.loc["non-mismatch",  "anomaly_rate"])

    col_g1, col_g2, _ = st.columns([1, 1, 2])
    (col_g1.success if gate_f1 else col_g1.error)(
        "IFS detector outperforms CPU baseline"
        if gate_f1 else "IFS detector does not outperform CPU baseline"
    )
    (col_g2.success if gate_mm else col_g2.error)(
        "Type-divergent workloads exhibit higher anomaly rates"
        if gate_mm else "Type-divergence signal not significant"
    )

    st.divider()

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Detector Comparison")
        st.caption(
            "IFS-based detector vs CPU-utilization threshold. "
            "Higher P/R/F1 and lower False Alarm Rate are preferred."
        )
        metrics = ["Precision", "Recall", "F1 Score", "False Alarm Rate"]
        basic_v = [m["threshold"]["precision"], m["threshold"]["recall"],
                   m["threshold"]["f1"],        m["threshold"]["fpr"]]
        smart_v = [m["ifs"]["precision"],       m["ifs"]["recall"],
                   m["ifs"]["f1"],              m["ifs"]["fpr"]]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="CPU Threshold", x=metrics, y=basic_v, marker_color="#FFB74D", opacity=0.82,
            text=[f"{v:.3f}" for v in basic_v], textposition="outside",
        ))
        fig.add_trace(go.Bar(
            name="IFS Detector", x=metrics, y=smart_v, marker_color="#7BBFDB", opacity=0.82,
            text=[f"{v:.3f}" for v in smart_v], textposition="outside",
        ))
        fig.update_layout(
            barmode="group", yaxis_range=[0, 1.18],
            legend=dict(orientation="h", y=1.14, x=0, font=dict(color=_TEXT, size=12),
                        bgcolor="rgba(0,0,0,0)", borderwidth=0),
            paper_bgcolor=_BG, plot_bgcolor=_BG2, font=dict(color=_TEXT, size=12),
            yaxis=dict(gridcolor=_GRID, title="Score"),
            xaxis=dict(gridcolor=_GRID),
            margin=dict(t=54, b=10, l=10, r=24),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Confusion Matrix")
        det_choice = st.radio(
            "Detector", ["IFS Detector", "CPU Threshold"], horizontal=True
        )
        det_key = "ifs" if det_choice == "IFS Detector" else "threshold"
        st.plotly_chart(confusion_matrix_heatmap(m, det_key), use_container_width=True)
        dm = m[det_key]
        st.caption(
            f"TP {dm['tp']:,} · FP {dm['fp']:,} · TN {dm['tn']:,} · FN {dm['fn']:,} "
            f"| F1 = {dm['f1']:.3f} · FPR = {dm['fpr']:.3f}"
        )

    st.divider()

    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.subheader("Sensitivity Sweep")
        st.caption(
            "Trade-off between precision and recall as the IFS alert threshold θ varies."
        )
        theta = st.slider(
            "Alert threshold (θ_ifs)", 0.45, 0.95, 0.65, 0.05,
            format="%.2f",
            help="Runs scoring below θ are flagged as anomalous.",
        )
        fig3 = go.Figure()
        for col_k, color, name in [
            ("precision", "#81C995", "Precision"),
            ("recall",    "#F28B82", "Recall"),
            ("f1",        "#7BBFDB", "F1 Score"),
        ]:
            fig3.add_trace(go.Scatter(
                x=sweep["threshold"], y=sweep[col_k],
                mode="lines+markers", name=name,
                line=dict(color=color, width=2.5), marker=dict(size=7),
            ))
        fig3.add_vline(x=theta, line_dash="dash", line_color="#9CA3AF", line_width=2,
                       annotation_text=f"  θ = {theta:.2f}",
                       annotation_font=dict(color=_TEXT, size=12))
        fig3.update_layout(
            xaxis_title="Alert Threshold (θ_ifs)",
            yaxis_title="Score",
            yaxis_range=[0, 1.08],
            legend=dict(orientation="h", y=1.14, x=0, font=dict(color=_TEXT, size=12),
                        bgcolor="rgba(0,0,0,0)", borderwidth=0),
            paper_bgcolor=_BG, plot_bgcolor=_BG2, font=dict(color=_TEXT, size=12),
            xaxis=dict(gridcolor=_GRID, title_font=dict(size=12, color=_TEXT)),
            yaxis=dict(gridcolor=_GRID, title_font=dict(size=12, color=_TEXT)),
            margin=dict(t=54, b=10, l=10, r=24),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col_r2:
        st.subheader("Type-Divergence Subgroup")
        st.caption(
            "Workloads whose declared type differs from the NLP-inferred type — "
            "do they exhibit higher anomaly rates?"
        )
        anomaly_rates = [
            mm_idx.loc["type_mismatch", "anomaly_rate"],
            mm_idx.loc["non-mismatch",  "anomaly_rate"],
        ]
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=["Type Divergence", "No Divergence"],
            y=anomaly_rates,
            marker_color=["#FFB74D", "#81C995"], opacity=0.85,
            text=[f"{v:.1%}" for v in anomaly_rates], textposition="outside",
        ))
        fig4.update_layout(
            yaxis=dict(title="Anomaly Rate", range=[0, max(anomaly_rates) * 1.65],
                       tickformat=".0%", gridcolor=_GRID,
                       title_font=dict(size=12, color=_TEXT)),
            paper_bgcolor=_BG, plot_bgcolor=_BG2, font=dict(color=_TEXT, size=12),
            margin=dict(t=32, b=10, l=10, r=24), showlegend=False,
        )
        st.plotly_chart(fig4, use_container_width=True)

        col_m1, col_m2 = st.columns(2)
        col_m1.metric(
            "Type Divergence — Anomaly Rate",
            f"{mm_idx.loc['type_mismatch','anomaly_rate']:.1%}",
            delta=(f"+{mm_idx.loc['type_mismatch','anomaly_rate'] - mm_idx.loc['non-mismatch','anomaly_rate']:.1%}"
                   " vs correct"),
            delta_color="inverse",
        )
        col_m2.metric(
            "Type Divergence — Mean IFS",
            f"{mm_idx.loc['type_mismatch','mean_ifs']:.3f}",
            help="Lower score indicates weaker alignment with declared intent",
        )

    # ── Case studies ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Representative Governance Failure Patterns")
    st.caption(
        "Stylized examples from the controlled evaluation benchmark. "
        "Each illustrates a distinct failure mode detected by the IBD system."
    )

    cc1, cc2, cc3 = st.columns(3)

    with cc1:
        st.markdown("""
<div class="case-card">
  <div class="case-title">Case 1 — Idle Cluster</div>
  <div class="case-row">
    <span class="case-label">Declared type</span>
    <span class="case-val">ETL</span>
  </div>
  <div class="case-row">
    <span class="case-label">Observed idle time</span>
    <span class="case-val">91% of runtime</span>
  </div>
  <div class="case-row">
    <span class="case-label">Root cause</span>
    <span class="case-val">Abandoned cluster</span>
  </div>
  <div class="case-row">
    <span class="case-label">Wasted spend</span>
    <span class="case-val">$312 / run</span>
  </div>
  <div class="case-ifs">IFS 0.31</div>
  <div style="font-size:11px; color:#64748B; margin-top:4px;">
    Severe divergence · Anomaly flagged
  </div>
</div>
""", unsafe_allow_html=True)

    with cc2:
        st.markdown("""
<div class="case-card">
  <div class="case-title">Case 2 — Misclassified Workload</div>
  <div class="case-row">
    <span class="case-label">Declared type</span>
    <span class="case-val">adhoc</span>
  </div>
  <div class="case-row">
    <span class="case-label">Inferred type</span>
    <span class="case-val">ml_training</span>
  </div>
  <div class="case-row">
    <span class="case-label">Observed</span>
    <span class="case-val">GPU-heavy execution</span>
  </div>
  <div class="case-row">
    <span class="case-label">Root cause</span>
    <span class="case-val">Workload-type divergence</span>
  </div>
  <div class="case-ifs">IFS 0.42</div>
  <div style="font-size:11px; color:#64748B; margin-top:4px;">
    Significant divergence · Policy guardrail bypassed
  </div>
</div>
""", unsafe_allow_html=True)

    with cc3:
        st.markdown("""
<div class="case-card">
  <div class="case-title">Case 3 — Runtime Overrun</div>
  <div class="case-row">
    <span class="case-label">Declared duration</span>
    <span class="case-val">2 h</span>
  </div>
  <div class="case-row">
    <span class="case-label">Actual duration</span>
    <span class="case-val">17 h</span>
  </div>
  <div class="case-row">
    <span class="case-label">Duration ratio</span>
    <span class="case-val">8.5×</span>
  </div>
  <div class="case-row">
    <span class="case-label">Root cause</span>
    <span class="case-val">Runaway batch job</span>
  </div>
  <div class="case-ifs">IFS 0.28</div>
  <div style="font-size:11px; color:#64748B; margin-top:4px;">
    Severe divergence · Runtime termination triggered
  </div>
</div>
""", unsafe_allow_html=True)

    with st.expander("Full detector metrics table"):
        rows = []
        for name, label in [
            ("threshold", "CPU Threshold (cpu_util < 30%)"),
            ("ifs",       "IFS Detector (score < 0.65)"),
        ]:
            d = m[name]
            rows.append({
                "Detector":         label,
                "Precision":        f"{d['precision']:.4f}",
                "Recall":           f"{d['recall']:.4f}",
                "F1 Score":         f"{d['f1']:.4f}",
                "False Alarm Rate": f"{d['fpr']:.4f}",
                "TP": d["tp"], "FP": d["fp"], "TN": d["tn"], "FN": d["fn"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)