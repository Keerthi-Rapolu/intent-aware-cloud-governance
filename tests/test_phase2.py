"""Phase 2 unit tests — run with: pytest tests/test_phase2.py -v"""
import math
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── 2.1 cost_normalizer ────────────────────────────────────────────────────────

def test_cost_normalizer_unit():
    from cost_normalizer.normalizer import CrossCloudNormalizer
    n = CrossCloudNormalizer()
    cost = n.compute_cost("aws", "m5.xlarge", nodes=4, duration_hours=2.0)
    assert abs(cost - 1.536) < 0.001, f"Expected 1.536, got {cost}"

def test_cost_normalizer_spot_discount():
    from cost_normalizer.normalizer import CrossCloudNormalizer
    n = CrossCloudNormalizer()
    od   = n.compute_cost("aws", "m5.xlarge", 4, 2.0, use_spot=False)
    spot = n.compute_cost("aws", "m5.xlarge", 4, 2.0, use_spot=True)
    assert spot < od
    assert abs(spot - od * 0.30) < 0.01   # 70% discount

def test_normalize_record():
    from cost_normalizer.normalizer import CrossCloudNormalizer
    n = CrossCloudNormalizer()
    rec = n.normalize({
        "cloud_provider": "aws", "instance_type": "m5.xlarge",
        "node_count": 4, "actual_duration_hours": 2.0, "use_spot": False,
    })
    assert rec.total_cost == pytest.approx(1.536, rel=1e-3)
    assert rec.vcpu_total == 16
    assert rec.memory_gb_total == 64.0

# ── 2.2 / 2.3 intent model ────────────────────────────────────────────────────

def test_intent_catalog_all_types():
    from intent_model.intent_catalog import INTENT_CATALOG
    for t in ("etl", "adhoc", "ml_training", "llm_pipeline", "batch", "streaming"):
        assert t in INTENT_CATALOG
        p = INTENT_CATALOG[t]
        assert 0 < p.expected_utilization <= 1.0
        assert len(p.default_instance) == 3

def test_workload_intent_effective_type():
    from intent_model.workload_intent import (
        WorkloadIntent, ResourceConfig, InferredIntentFields
    )
    rc = ResourceConfig("aws","m5.xlarge",4,4,False,4.0,100.0,"us-east-1",4,16.0,1.0)
    inf = InferredIntentFields("ml_training","large","batch_ok","recurring",
                               False,"internal",True,0.92,0.91)
    wi = WorkloadIntent("id1","job","desc","team","etl","prod","medium",4.0,"daily","2025-01-01",rc,inf)
    assert wi.effective_workload_type == "ml_training"

# ── 2.4 intent_inference ──────────────────────────────────────────────────────

def test_inference_recurring_pii():
    from intent_model.intent_inference import IntentInferenceEngine
    engine = IntentInferenceEngine()
    result = engine.infer(
        "weekly customer churn model retraining on 3TB dataset",
        declared_type="ml_training",
    )
    assert result.recurrence_signal == "recurring"
    assert result.pii_signal is True
    assert result.type_mismatch is False

def test_inference_type_mismatch_detected():
    from intent_model.intent_inference import IntentInferenceEngine
    engine = IntentInferenceEngine()
    result = engine.infer(
        "Continuous real-time processing of event stream",
        declared_type="etl",
    )
    assert result.workload_type_inferred == "streaming"
    assert result.type_mismatch is True

def test_inference_data_volume():
    from intent_model.intent_inference import IntentInferenceEngine
    engine = IntentInferenceEngine()
    r = engine.infer("process 500 GB of data", declared_type="etl")
    assert r.data_volume_estimate in ("large", "xl")

# ── 2.6 cost_model ────────────────────────────────────────────────────────────

def test_cost_model_matches_normalizer():
    from simulation_engine.cost_model import CloudCostModel
    m = CloudCostModel()
    assert m.compute_cost("aws", "m5.xlarge", 4, 2.0) == pytest.approx(1.536, rel=1e-3)

# ── 2.7 correction_cost_model ─────────────────────────────────────────────────

def test_ev_block_negative_for_critical():
    from simulation_engine.correction_cost_model import CostOfCorrectionModel
    m = CostOfCorrectionModel()
    # critical job: failure cost = 2000, delay cost = 25 × 4 = 100
    # waste_cost = 0.60 × 100 = 60 → EV = 60 - 100 - 0.06*2000 = 60 - 100 - 120 = -160
    ev = m.ev_block("etl", "critical", expected_duration_hours=4.0, waste_cost=60.0)
    assert ev < 0, f"EV(BLOCK) for critical should be negative, got {ev}"

def test_ev_auto_correct_positive_for_large_waste():
    from simulation_engine.correction_cost_model import CostOfCorrectionModel
    m = CostOfCorrectionModel()
    ev = m.ev_auto_correct("etl", "low", 4.0, waste_cost=100.0, right_sized_cost=20.0)
    assert ev > 0

def test_decide_pass_for_minimal_waste():
    from simulation_engine.correction_cost_model import CostOfCorrectionModel
    m = CostOfCorrectionModel()
    action, prevented = m.decide("etl", "medium", 4.0, waste_cost=0.5, right_sized_cost=0.4)
    assert action in ("PASS", "SUGGEST")

# ── 2.8 simulator ─────────────────────────────────────────────────────────────

def test_simulator_right_sizing():
    from simulation_engine.simulator import PreExecutionSimulator
    sim = PreExecutionSimulator()   # no DB — catalog fallback
    result = sim.simulate({
        "intent_id": "test-001",
        "workload_type": "etl",
        "cloud_provider": "aws",
        "instance_type": "m5.xlarge",
        "node_count": 20,
        "expected_duration_hours": 8.0,
        "priority": "medium",
        "use_spot": False,
    })
    # catalog prior for ETL = 0.65 util → optimal = ceil(20 * 0.65 / 0.70) = 19 → ~same
    # but with an over-provisioned scenario the catalog will still right-size
    assert result.optimal_nodes <= result.submitted_nodes
    assert result.potential_cost_usd > 0
    assert result.stage == "pre_provision"

def test_simulator_high_waste_triggers_intervention():
    from simulation_engine.simulator import PreExecutionSimulator
    from intent_model.intent_catalog import INTENT_CATALOG
    # Temporarily patch catalog util to simulate over-provisioning
    original = INTENT_CATALOG["adhoc"].expected_utilization
    INTENT_CATALOG["adhoc"] = INTENT_CATALOG["adhoc"].__class__(
        expected_utilization=0.15,
        **{k: getattr(INTENT_CATALOG["adhoc"], k)
           for k in ("duration_range","optimal_node_range","spot_eligible",
                     "auto_shutdown_hours","latency","default_instance")}
    )
    try:
        sim = PreExecutionSimulator()
        result = sim.simulate({
            "intent_id": "test-002",
            "workload_type": "adhoc",
            "cloud_provider": "aws",
            "instance_type": "m5.xlarge",
            "node_count": 10,
            "expected_duration_hours": 4.0,
            "priority": "low",
            "use_spot": False,
        })
        assert result.intervention in ("AUTO_CORRECT", "BLOCK", "SUGGEST")
        assert result.optimal_nodes < 10
    finally:
        INTENT_CATALOG["adhoc"] = INTENT_CATALOG["adhoc"].__class__(
            expected_utilization=original,
            **{k: getattr(INTENT_CATALOG["adhoc"], k)
               for k in ("duration_range","optimal_node_range","spot_eligible",
                         "auto_shutdown_hours","latency","default_instance")}
        )

# ── 2.9 policy_engine ─────────────────────────────────────────────────────────

def test_policy_registry_loads_builtins():
    from policy_engine.policy_registry import PolicyRegistry
    reg = PolicyRegistry()
    assert len(reg) >= 7
    assert reg.get("etl_auto_shutdown") is not None

def test_policy_enforcer_fires_on_violation():
    from policy_engine.policy_registry import PolicyRegistry
    from policy_engine.policy_enforcer import PolicyEnforcer
    reg = PolicyRegistry()
    enf = PolicyEnforcer(reg)
    violations = enf.check({
        "workload_type": "etl",
        "priority": "high",
        "auto_shutdown_hours": 10.0,   # exceeds threshold of 4
        "node_count": 4,
        "use_spot": False,
    })
    ids = [v.policy_id for v in violations]
    assert "etl_auto_shutdown" in ids

def test_policy_enforcer_no_violation():
    from policy_engine.policy_registry import PolicyRegistry
    from policy_engine.policy_enforcer import PolicyEnforcer
    reg = PolicyRegistry()
    enf = PolicyEnforcer(reg)
    violations = enf.check({
        "workload_type": "etl",
        "priority": "medium",
        "auto_shutdown_hours": 3.0,    # within threshold
        "node_count": 4,
        "use_spot": True,
    })
    shutdown_violations = [v for v in violations if v.policy_id == "etl_auto_shutdown"]
    assert len(shutdown_violations) == 0

# ── 2.10 guardrails ───────────────────────────────────────────────────────────

def test_guardrail_auto_negotiate_critical_etl():
    from policy_engine.policy_registry import PolicyRegistry
    from simulation_engine.simulator import PreExecutionSimulator
    from guardrails.pre_provision_guard import PreProvisionGuard
    reg = PolicyRegistry()
    sim = PreExecutionSimulator()
    guard = PreProvisionGuard(reg, sim, conflict_strategy="auto_negotiate")
    decision = guard.evaluate({
        "intent_id": "grd-001",
        "workload_type": "etl",
        "cloud_provider": "aws",
        "instance_type": "m5.xlarge",
        "node_count": 8,
        "expected_duration_hours": 6.0,
        "priority": "critical",
        "auto_shutdown_hours": 10.0,   # violates etl_auto_shutdown (threshold=4)
        "use_spot": False,
    })
    assert len(decision.violations) > 0
    assert decision.resolved_config["auto_shutdown_hours"] == 4.0

# ── 2.11 runtime_optimizer ────────────────────────────────────────────────────

def test_idle_cluster_terminates():
    from runtime_optimizer.adaptive_optimizer import AdaptiveOptimizer
    opt = AdaptiveOptimizer()
    actions = opt.simulate_run({
        "run_id": "run-idle-001",
        "cloud_provider": "aws",
        "instance_type": "m5.xlarge",
        "node_count": 4,
        "use_spot": False,
        "actual_duration_hours": 2.0,
        "expected_duration_hours": 2.0,
        "auto_shutdown_hours": 2.0,
        "idle_time_hours": 1.5,        # > 10-min threshold
        "cpu_utilization_avg": 0.60,
        "memory_utilization_avg": 0.55,
        "is_runaway": False,
        "spot_interruption": False,
    })
    idle_actions = [a for a in actions if a.signal_type == "idle"]
    assert len(idle_actions) == 1
    assert idle_actions[0].action == "TERMINATE"
    assert idle_actions[0].cost_prevented_usd > 0

def test_no_actions_for_healthy_run():
    from runtime_optimizer.adaptive_optimizer import AdaptiveOptimizer
    opt = AdaptiveOptimizer()
    actions = opt.simulate_run({
        "run_id": "run-healthy",
        "cloud_provider": "aws",
        "instance_type": "m5.xlarge",
        "node_count": 4,
        "use_spot": False,
        "actual_duration_hours": 4.0,
        "expected_duration_hours": 4.0,
        "auto_shutdown_hours": 6.0,
        "idle_time_hours": 0.0,
        "cpu_utilization_avg": 0.70,
        "memory_utilization_avg": 0.65,
        "is_runaway": False,
        "spot_interruption": False,
    })
    assert len(actions) == 0

# ── 2.12 cps_metrics ──────────────────────────────────────────────────────────

def test_cps_calculator():
    from cps_metrics.prevention_tracker import CPSCalculator
    assert CPSCalculator.cps(30, 100) == pytest.approx(0.30)
    assert CPSCalculator.esr(95, 100) == pytest.approx(0.95)
    assert CPSCalculator.valid_cps(0.30, 0.95) == pytest.approx(0.285)
    assert CPSCalculator.cps(0, 0) == 0.0   # edge case: no runs

def test_prevention_tracker_summary():
    from cps_metrics.prevention_tracker import PreventionTracker
    from simulation_engine.simulator import SimulationResult
    tracker = PreventionTracker()
    fake_sim = SimulationResult(
        intent_id="t1", workload_type="etl", cloud="aws",
        instance_type="m5.xlarge", submitted_nodes=20, optimal_nodes=6,
        predicted_utilization=0.15, potential_cost_usd=200.0,
        right_sized_cost_usd=60.0, prevented_cost_usd=140.0,
        intervention="AUTO_CORRECT", stage="pre_provision",
        ev_block=-50.0, ev_auto_correct=120.0,
    )
    tracker.record_simulation(fake_sim, ifs=0.72, succeeded=True)
    s = tracker.summary()
    assert s["system_cps"] == pytest.approx(0.70, rel=0.01)
    assert s["esr"] == pytest.approx(1.0)
    assert s["valid_cps"] == pytest.approx(0.70, rel=0.01)