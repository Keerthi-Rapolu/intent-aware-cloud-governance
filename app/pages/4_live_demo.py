"""Page 4 — Live Demo: type a workload description and see live simulation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="Live Demo — PBCP", layout="wide")
st.title("Live Demo")
st.caption("Type a workload description — see intent inference, simulation, and IFS in real time.")

# Check whether the ML pipeline modules are available (not on Streamlit Cloud free tier)
try:
    from intent_model.intent_inference import IntentInferenceEngine  # noqa: F401
    _PIPELINE_AVAILABLE = True
except Exception:
    _PIPELINE_AVAILABLE = False

if not _PIPELINE_AVAILABLE:
    st.warning(
        "**Live pipeline requires local installation.**  "
        "The ML models (DistilBERT, FAISS index) are not deployed to Streamlit Cloud "
        "due to size constraints.  \n\n"
        "To run locally:  \n"
        "```bash\n"
        "git clone https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance\n"
        "pip install -r requirements.txt\n"
        "python data/generate_dataset.py\n"
        "streamlit run app/app.py\n"
        "```"
    )
    st.divider()
    st.subheader("Example Output (Exp 2 — Scenario C)")
    st.success("AUTO_CORRECT — nodes reduced 20 → 9 | prevented $97.92 | CPS 0.667")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Intervention",   "AUTO_CORRECT")
    c2.metric("Optimal nodes",  "9 / 20 submitted")
    c3.metric("Cost prevented", "$97.92")
    c4.metric("CPS",            "0.667")
    st.stop()

# -- Inputs -----------------------------------------------------------------
col_in, col_cfg = st.columns([2, 1])

with col_in:
    description = st.text_area(
        "Workload description",
        height=120,
        placeholder=(
            "e.g., weekly customer churn model retraining on 3 TB dataset with PII"
        ),
    )

with col_cfg:
    declared_type = st.selectbox(
        "Declared workload type",
        ["etl", "adhoc", "ml_training", "llm_pipeline", "batch", "streaming"],
        index=2,
    )
    cloud    = st.selectbox("Cloud provider", ["aws", "azure", "gcp"])
    instance = st.selectbox(
        "Instance type",
        ["m5.xlarge", "m5.2xlarge", "m5.4xlarge", "p3.2xlarge",
         "r5.xlarge", "c5.xlarge"],
    )
    nodes    = st.slider("Node count",    min_value=1,   max_value=50,  value=20)
    duration = st.slider("Expected hours", min_value=0.5, max_value=24.0, value=8.0, step=0.5)
    priority = st.selectbox("Priority", ["low", "medium", "high", "critical"], index=1)
    use_spot = st.checkbox("Use spot instances", value=False)

run_btn = st.button("Simulate", type="primary", use_container_width=False)

if not run_btn:
    st.info("Fill in the fields above and click **Simulate**.")
    st.stop()

if not description.strip():
    st.warning("Enter a workload description to run the simulation.")
    st.stop()

# -- Run pipeline -----------------------------------------------------------
with st.spinner("Running PBCP pipeline..."):
    try:
        from simulation_engine.simulator import PreExecutionSimulator
        from ifs.ifs_calculator import IFSCalculator
        from simulation_engine.cost_model import CloudCostModel

        # 1. Intent inference
        engine   = IntentInferenceEngine()
        inferred = engine.infer(description, declared_type=declared_type)

        # 2. Simulation
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
        simulator = PreExecutionSimulator()
        sim = simulator.simulate(intent_dict)

        # 3. Static (no-op) cost for comparison
        cost_model   = CloudCostModel()
        static_cost  = cost_model.compute_cost(cloud, instance, nodes, duration, use_spot)

        # 4. IFS estimate using predicted vs. typical actual utilization
        typical_actual = sim.predicted_utilization * 0.90   # slight underuse
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

if not ok:
    st.stop()

# -- Results ----------------------------------------------------------------
st.divider()

# Intervention colour
INT_COLOR = {
    "BLOCK":        "red",
    "AUTO_CORRECT": "green",
    "SUGGEST":      "orange",
    "PASS":         "blue",
}
color = INT_COLOR.get(sim.intervention, "grey")

# Row 1: intervention banner
if sim.intervention == "AUTO_CORRECT":
    st.success(f"AUTO_CORRECT — nodes reduced {nodes} -> {sim.optimal_nodes} "
               f"| prevented ${sim.prevented_cost_usd:.2f} | CPS {sim.cps:.3f}")
elif sim.intervention == "BLOCK":
    st.error(f"BLOCK — submission rejected | waste would be ${sim.prevented_cost_usd:.2f}")
elif sim.intervention == "SUGGEST":
    st.warning(f"SUGGEST — consider reducing to {sim.optimal_nodes} nodes")
else:
    st.info(f"PASS — no intervention needed (utilization looks healthy)")

# Row 2: 4 metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Intervention",      sim.intervention)
c2.metric("Optimal nodes",     f"{sim.optimal_nodes} / {nodes} submitted")
c3.metric("Cost prevented",    f"${sim.prevented_cost_usd:.2f}")
c4.metric("CPS",               f"{sim.cps:.3f}")

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

st.divider()
st.subheader("🎯 Intent-Fit Score (IFS)")
st.caption("How well does this job's predicted behaviour match what it said it would do? — Sreeja Katta")

import plotly.graph_objects as go

# ── IFS score card ─────────────────────────────────────────────────────────
ifs_meta = {
    "well_aligned": ("green",  "✅ Well Aligned",  "This job looks healthy — behaviour matches intent."),
    "minor":        ("#f0a500","⚠️ Minor Divergence","Small gap between intent and predicted behaviour."),
    "significant":  ("orange", "🔶 Significant",    "Noticeable gap — worth investigating."),
    "severe":       ("red",    "🚨 Severe Divergence","Large gap — this job is likely misbehaving."),
}
color, badge, verdict_msg = ifs_meta.get(ifs_rec.ifs_category, ("grey", "Unknown", ""))

# Gauge chart
gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=ifs_rec.ifs,
    number={"font": {"size": 48}, "valueformat": ".3f"},
    gauge={
        "axis": {"range": [0, 1], "tickwidth": 1, "tickcolor": "#555"},
        "bar":  {"color": color, "thickness": 0.25},
        "steps": [
            {"range": [0.00, 0.50], "color": "#fde8e8"},
            {"range": [0.50, 0.70], "color": "#fef3e2"},
            {"range": [0.70, 0.85], "color": "#e8f5e9"},
            {"range": [0.85, 1.00], "color": "#c8e6c9"},
        ],
        "threshold": {
            "line": {"color": "red", "width": 3},
            "thickness": 0.8,
            "value": 0.65,
        },
    },
    title={"text": f"<b>{badge}</b>", "font": {"size": 18}},
))
gauge.update_layout(height=260, margin=dict(t=40, b=0, l=30, r=30))

col_gauge, col_verdict = st.columns([1, 1])
with col_gauge:
    st.plotly_chart(gauge, use_container_width=True)

with col_verdict:
    st.markdown(f"### {badge}")
    st.markdown(verdict_msg)
    st.markdown(f"**Score:** `{ifs_rec.ifs:.3f}` &nbsp;|&nbsp; **Category:** `{ifs_rec.ifs_category}`")

    # Anomaly detector verdict
    IBD_THRESHOLD = 0.65
    if ifs_rec.ifs < IBD_THRESHOLD:
        # infer root cause from lowest sub-score
        sub = {
            "Job type mismatch":      ifs_rec.type_alignment,
            "Utilisation mismatch":   ifs_rec.util_alignment,
            "Duration mismatch":      ifs_rec.duration_alignment,
            "Resource over-provision": ifs_rec.resource_alignment,
        }
        root_cause_label = min(sub, key=lambda k: sub[k])
        st.error(
            f"🚨 **Anomaly Detector would flag this job.**  \n"
            f"IFS {ifs_rec.ifs:.3f} is below the alert threshold of {IBD_THRESHOLD}.  \n"
            f"Most likely cause: **{root_cause_label}** "
            f"(sub-score: {sub[root_cause_label]:.3f})"
        )
        st.info(
            "💡 **Feedback loop:** If this pattern repeats 3+ more times, "
            "the system will auto-generate a prevention rule so future similar "
            "jobs are caught *before* resources are created."
        )
    else:
        st.success(
            f"✅ **Anomaly Detector: No flag.**  \n"
            f"IFS {ifs_rec.ifs:.3f} is above the alert threshold of {IBD_THRESHOLD}."
        )

# ── Sub-score breakdown ─────────────────────────────────────────────────────
st.markdown("#### Sub-score Breakdown")
st.caption("Each bar shows how well one dimension of the job aligns with its declared intent. Red = problem area.")

sub_scores = {
    "Job Type\nAlignment":       ifs_rec.type_alignment,
    "Utilisation\nAlignment":    ifs_rec.util_alignment,
    "Duration\nAlignment":       ifs_rec.duration_alignment,
    "Resource\nAlignment":       ifs_rec.resource_alignment,
}
bar_colors = ["#d62728" if v < 0.50 else "#ff7f0e" if v < 0.70 else "#2ca02c"
              for v in sub_scores.values()]

bar_fig = go.Figure(go.Bar(
    x=list(sub_scores.keys()),
    y=list(sub_scores.values()),
    marker_color=bar_colors,
    text=[f"{v:.3f}" for v in sub_scores.values()],
    textposition="outside",
))
bar_fig.add_hline(y=0.65, line_dash="dash", line_color="red", line_width=1.5,
                  annotation_text="Alert threshold (0.65)",
                  annotation_position="top right",
                  annotation_font_color="red")
bar_fig.add_hline(y=1.0, line_color="rgba(0,0,0,0)")
bar_fig.update_layout(
    yaxis=dict(range=[0, 1.15], title="Alignment Score", gridcolor="#f0f0f0"),
    plot_bgcolor="white", margin=dict(t=30, b=10), showlegend=False,
)
st.plotly_chart(bar_fig, use_container_width=True)