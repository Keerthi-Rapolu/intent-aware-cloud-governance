"""Page 4 — Live Demo: type a workload description and see live simulation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Live Demo — PBCP", layout="wide")
st.title("Live Demo")
st.caption("Type a workload description — see intent inference, simulation, and IFS in real time.")

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
        from intent_model.intent_inference import IntentInferenceEngine
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
st.subheader("Intent-Fit Score (IFS) Estimate")

ifs_color = {
    "well_aligned": "green", "minor": "blue",
    "significant": "orange", "severe": "red",
}.get(ifs_rec.ifs_category, "grey")

c1, c2, c3 = st.columns(3)
c1.metric("IFS",              f"{ifs_rec.ifs:.3f}")
c2.metric("Category",         ifs_rec.ifs_category)
c3.metric("Type alignment",   f"{ifs_rec.type_alignment:.3f}")

with st.expander("IFS sub-scores"):
    st.json({
        "type_alignment":     ifs_rec.type_alignment,
        "util_alignment":     ifs_rec.util_alignment,
        "duration_alignment": ifs_rec.duration_alignment,
        "resource_alignment": ifs_rec.resource_alignment,
        "detail":             ifs_rec.detail,
    })