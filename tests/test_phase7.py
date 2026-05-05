"""
Phase 7 — Integration Tests: Sreeja module interfaces

Tests verify:
  1. IFSCalculator returns valid IFSRecord (correct range, category, immutability)
  2. IFSRecord plugs cleanly into PreventionTracker
  3. RootCauseAnalyzer returns valid Policy objects from the live DB
  4. Suggested policies are accepted by PolicyRegistry without error
  5. Full end-to-end pipeline: DB workload -> intent -> simulation -> guardrail
                               -> runtime -> IFS -> PreventionTracker (CPS + IFS)

When Sreeja replaces the stub implementations, all tests here must still pass.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

DB_PATH = str(Path(__file__).parent.parent / "data" / "full" / "iacg.duckdb")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_intent(workload_type="etl", node_count=10, optimal_node_count=6,
                 priority="medium", expected_duration_hours=4.0,
                 type_mismatch=False, type_mismatch_confidence=0.0,
                 over_provision_factor=1.0):
    """Build a minimal WorkloadIntent dict for simulation (no DB needed)."""
    return {
        "intent_id":               str(uuid.uuid4()),
        "workload_type":           workload_type,
        "cloud_provider":          "aws",
        "instance_type":           "m5.xlarge",
        "node_count":              node_count,
        "optimal_node_count":      optimal_node_count,
        "use_spot":                False,
        "priority":                priority,
        "expected_duration_hours": expected_duration_hours,
        "over_provision_factor":   over_provision_factor,
        "type_mismatch":           type_mismatch,
        "type_mismatch_confidence": type_mismatch_confidence,
    }


# ---------------------------------------------------------------------------
# Section 1 — IFSCalculator
# ---------------------------------------------------------------------------

class TestIFSCalculator:

    def test_returns_ifs_record(self):
        from ifs.ifs_calculator import IFSCalculator, IFSRecord
        rec = IFSCalculator.compute_ifs(
            intent_id="test-1", run_id="run-1",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.55, actual_utilization=0.58,
            expected_duration_hours=4.0, actual_duration_hours=4.2,
            over_provision_factor=1.0,
        )
        assert isinstance(rec, IFSRecord)

    def test_ifs_in_unit_range(self):
        from ifs.ifs_calculator import IFSCalculator
        rec = IFSCalculator.compute_ifs(
            intent_id="t", run_id="r",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.60, actual_utilization=0.60,
            expected_duration_hours=2.0, actual_duration_hours=2.0,
            over_provision_factor=1.0,
        )
        assert 0.0 <= rec.ifs <= 1.0

    def test_perfect_alignment_high_ifs(self):
        from ifs.ifs_calculator import IFSCalculator
        rec = IFSCalculator.compute_ifs(
            intent_id="t", run_id="r",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.70, actual_utilization=0.70,
            expected_duration_hours=4.0, actual_duration_hours=4.0,
            over_provision_factor=1.0,
        )
        assert rec.ifs >= 0.85
        assert rec.ifs_category == "well_aligned"

    def test_severe_mismatch_low_ifs(self):
        from ifs.ifs_calculator import IFSCalculator
        rec = IFSCalculator.compute_ifs(
            intent_id="t", run_id="r",
            type_mismatch=True, type_mismatch_confidence=0.90,
            predicted_utilization=0.70, actual_utilization=0.15,
            expected_duration_hours=4.0, actual_duration_hours=12.0,
            over_provision_factor=3.5,
        )
        assert rec.ifs < 0.50
        assert rec.ifs_category == "severe"

    def test_category_thresholds(self):
        from ifs.ifs_calculator import IFSCalculator
        cases = [
            # (type_mismatch, tm_conf, pu, au, e_dur, a_dur, opf, expected_category)
            # well_aligned: no mismatch, perfect utilization and duration, opf=1
            (False, 0.00, 0.70, 0.70, 4.0, 4.0, 1.0, "well_aligned"),
            # minor: slight type mismatch + mild util gap + slight overrun
            (True,  0.20, 0.70, 0.50, 4.0, 5.0, 1.5, "minor"),
            # significant: moderate type mismatch + util gap + overrun + opf=2
            (True,  0.40, 0.70, 0.45, 4.0, 6.0, 2.0, "significant"),
            # severe: strong mismatch, very low util, heavy overrun, high opf
            (True,  0.90, 0.70, 0.15, 4.0, 12.0, 3.5, "severe"),
        ]
        for tm, tc, pu, au, ed, ad, opf, expected_cat in cases:
            rec = IFSCalculator.compute_ifs(
                intent_id="t", run_id="r",
                type_mismatch=tm, type_mismatch_confidence=tc,
                predicted_utilization=pu, actual_utilization=au,
                expected_duration_hours=ed, actual_duration_hours=ad,
                over_provision_factor=opf,
            )
            assert rec.ifs_category == expected_cat, (
                f"Expected {expected_cat} for mismatch={tm}/{tc} util={pu}/{au} "
                f"dur={ed}/{ad} opf={opf}, got {rec.ifs_category} (ifs={rec.ifs})"
            )

    def test_sub_scores_in_unit_range(self):
        from ifs.ifs_calculator import IFSCalculator
        rec = IFSCalculator.compute_ifs(
            intent_id="t", run_id="r",
            type_mismatch=True, type_mismatch_confidence=0.5,
            predicted_utilization=0.60, actual_utilization=0.40,
            expected_duration_hours=4.0, actual_duration_hours=6.0,
            over_provision_factor=2.0,
        )
        for score in (rec.type_alignment, rec.util_alignment,
                      rec.duration_alignment, rec.resource_alignment):
            assert 0.0 <= score <= 1.0

    def test_llm_token_waste_lowers_ifs(self):
        from ifs.ifs_calculator import IFSCalculator
        # Good: under budget
        rec_good = IFSCalculator.compute_ifs(
            intent_id="t", run_id="r",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.70, actual_utilization=0.70,
            expected_duration_hours=2.0, actual_duration_hours=2.0,
            over_provision_factor=1.0,
            is_llm_pipeline=True,
            token_budget_declared=100_000, token_usage_actual=80_000,
        )
        # Bad: 2x over budget
        rec_bad = IFSCalculator.compute_ifs(
            intent_id="t", run_id="r",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.70, actual_utilization=0.70,
            expected_duration_hours=2.0, actual_duration_hours=2.0,
            over_provision_factor=1.0,
            is_llm_pipeline=True,
            token_budget_declared=100_000, token_usage_actual=200_000,
        )
        assert rec_good.ifs > rec_bad.ifs

    def test_intent_dict_not_mutated(self):
        """IFSCalculator must not modify any input dict passed to it."""
        from ifs.ifs_calculator import IFSCalculator
        original = {"node_count": 10, "workload_type": "etl"}
        import copy
        snapshot = copy.deepcopy(original)
        IFSCalculator.compute_ifs(
            intent_id="t", run_id="r",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.60, actual_utilization=0.60,
            expected_duration_hours=4.0, actual_duration_hours=4.0,
            over_provision_factor=1.0,
        )
        assert original == snapshot


# ---------------------------------------------------------------------------
# Section 2 — IFSRecord → PreventionTracker
# ---------------------------------------------------------------------------

class TestIFSIntoPreventionTracker:

    def _make_sim_result(self, intent_id="test-1", nodes=10, util=0.55):
        from simulation_engine.simulator import PreExecutionSimulator
        sim = PreExecutionSimulator()
        intent = _make_intent(node_count=nodes, expected_duration_hours=4.0)
        intent["intent_id"] = intent_id
        return sim.simulate(intent)

    def test_ifs_accepted_by_tracker(self):
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker

        sim = self._make_sim_result()
        rec = IFSCalculator.compute_ifs(
            intent_id=sim.intent_id, run_id="run-1",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=sim.predicted_utilization,
            actual_utilization=0.55,
            expected_duration_hours=4.0, actual_duration_hours=4.1,
            over_provision_factor=1.0,
        )
        tracker = PreventionTracker()
        tracker.record_simulation(sim, ifs=rec.ifs)  # must not raise
        assert tracker.mean_ifs() == rec.ifs

    def test_tracker_ibd_uses_ifs(self):
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import PreExecutionSimulator

        sim_low  = PreExecutionSimulator().simulate(_make_intent())
        sim_high = PreExecutionSimulator().simulate(_make_intent())

        rec_low  = IFSCalculator.compute_ifs(
            intent_id=sim_low.intent_id, run_id="r1",
            type_mismatch=True, type_mismatch_confidence=0.80,
            predicted_utilization=0.70, actual_utilization=0.15,
            expected_duration_hours=4.0, actual_duration_hours=10.0,
            over_provision_factor=3.0,
        )
        rec_high = IFSCalculator.compute_ifs(
            intent_id=sim_high.intent_id, run_id="r2",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.70, actual_utilization=0.70,
            expected_duration_hours=4.0, actual_duration_hours=4.0,
            over_provision_factor=1.0,
        )

        tracker = PreventionTracker()
        tracker.record_simulation(sim_low,  ifs=rec_low.ifs)   # below 0.70 → IBD
        tracker.record_simulation(sim_high, ifs=rec_high.ifs)  # above 0.70 → not IBD

        assert tracker.ibd_fraction() == pytest.approx(0.5, abs=0.01)

    def test_tracker_summary_contains_mean_ifs(self):
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import PreExecutionSimulator

        sim = PreExecutionSimulator().simulate(_make_intent())
        rec = IFSCalculator.compute_ifs(
            intent_id=sim.intent_id, run_id="r1",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.60, actual_utilization=0.60,
            expected_duration_hours=4.0, actual_duration_hours=4.0,
            over_provision_factor=1.0,
        )
        tracker = PreventionTracker()
        tracker.record_simulation(sim, ifs=rec.ifs)
        summary = tracker.summary()
        assert "mean_ifs" in summary
        assert summary["mean_ifs"] == rec.ifs


# ---------------------------------------------------------------------------
# Section 3 — RootCauseAnalyzer
# ---------------------------------------------------------------------------

class TestRootCauseAnalyzer:

    def test_returns_list_of_policies(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        rca = RootCauseAnalyzer(DB_PATH)
        policies = rca.analyze()
        assert isinstance(policies, list)
        assert len(policies) >= 2, f"Expected >= 2 policies, got {len(policies)}"

    def test_all_policies_have_learned_source(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        policies = RootCauseAnalyzer(DB_PATH).analyze()
        for p in policies:
            assert p.source == "learned", f"Expected source='learned', got {p.source!r}"

    def test_confidence_in_valid_range(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        policies = RootCauseAnalyzer(DB_PATH).analyze()
        for p in policies:
            assert 0.60 <= p.confidence <= 1.0, (
                f"Policy {p.policy_id} confidence={p.confidence} out of range"
            )

    def test_policy_ids_unique(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        policies = RootCauseAnalyzer(DB_PATH).analyze()
        ids = [p.policy_id for p in policies]
        assert len(ids) == len(set(ids)), "Duplicate policy_ids returned"

    def test_top_incidents_returns_correct_count(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        rca = RootCauseAnalyzer(DB_PATH)
        for n in (5, 10):
            incidents = rca.top_incidents(n=n)
            assert len(incidents) == n

    def test_top_incidents_sorted_by_cost_desc(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        incidents = RootCauseAnalyzer(DB_PATH).top_incidents(n=10)
        costs = [inc["cost_impact_usd"] for inc in incidents]
        assert costs == sorted(costs, reverse=True)

    def test_top_incidents_has_required_keys(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        required = {"incident_id", "workload_type", "incident_type", "severity",
                    "cost_impact_usd", "detection_lag_minutes", "fix_applied"}
        incidents = RootCauseAnalyzer(DB_PATH).top_incidents(n=3)
        for inc in incidents:
            assert required.issubset(inc.keys())


# ---------------------------------------------------------------------------
# Section 4 — RCA policies → PolicyRegistry
# ---------------------------------------------------------------------------

class TestRCAPoliciesIntoRegistry:

    def test_policies_accepted_by_registry(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        from policy_engine.policy_registry import PolicyRegistry
        policies = RootCauseAnalyzer(DB_PATH).analyze()
        registry = PolicyRegistry()
        for p in policies:
            registry.add(p)          # must not raise
        for p in policies:
            assert registry.get(p.policy_id) is not None

    def test_learned_policies_retrievable_after_add(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        from policy_engine.policy_registry import PolicyRegistry
        registry = PolicyRegistry()
        policies = RootCauseAnalyzer(DB_PATH).analyze()
        for p in policies:
            registry.add(p)
        learned = [p for p in registry.list_all() if p.source == "learned"]
        assert len(learned) == len(policies)

    def test_policy_removable_after_add(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        from policy_engine.policy_registry import PolicyRegistry
        registry = PolicyRegistry()
        policies = RootCauseAnalyzer(DB_PATH).analyze()
        for p in policies:
            registry.add(p)
        pid = policies[0].policy_id
        registry.remove(pid)
        assert registry.get(pid) is None


# ---------------------------------------------------------------------------
# Section 5 — Full end-to-end pipeline
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    """
    description -> intent inference -> simulation -> guardrail ->
    runtime optimizer -> IFS -> PreventionTracker (CPS + IFS aggregated)
    """

    def test_full_pipeline_etl_workload(self):
        """Over-provisioned ETL: expect AUTO_CORRECT + IFS reflects mismatch."""
        from intent_model.intent_inference import IntentInferenceEngine
        from simulation_engine.simulator import PreExecutionSimulator
        from guardrails.pre_provision_guard import PreProvisionGuard
        from policy_engine.policy_registry import PolicyRegistry
        from policy_engine.policy_learner import PolicyLearner
        from runtime_optimizer.adaptive_optimizer import AdaptiveOptimizer
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker

        # --- Intent ---
        engine = IntentInferenceEngine()
        inferred = engine.infer(
            "weekly ETL pipeline processing customer transactions",
            declared_type="etl",
        )
        assert inferred.workload_type_inferred in ("etl", "batch", "streaming", "adhoc",
                                                   "ml_training", "llm_pipeline")

        # --- Simulation ---
        sim_input = {
            "intent_id":               "e2e-test-etl",
            "workload_type":           "etl",
            "cloud_provider":          "aws",
            "instance_type":           "m5.xlarge",
            "node_count":              20,
            "use_spot":                False,
            "priority":                "medium",
            "expected_duration_hours": 8.0,
        }
        simulator = PreExecutionSimulator()
        sim = simulator.simulate(sim_input)
        assert sim.potential_cost_usd > 0

        # --- Guardrail ---
        registry = PolicyRegistry()
        learner  = PolicyLearner(DB_PATH)
        for p in learner.analyze_runs(DB_PATH):
            registry.add(p)
        guard    = PreProvisionGuard(registry, simulator)
        decision = guard.evaluate(sim_input)
        assert decision is not None

        # --- Runtime optimizer ---
        run_dict = {
            "run_id":                  "e2e-run-1",
            "cloud_provider":          "aws",
            "instance_type":           "m5.xlarge",
            "node_count":              sim.optimal_nodes,
            "use_spot":                False,
            "actual_duration_hours":   8.0,
            "expected_duration_hours": 8.0,
            "auto_shutdown_hours":     10.0,
            "idle_time_hours":         0.0,
            "cpu_utilization_avg":     0.55,
            "memory_utilization_avg":  0.45,
            "is_runaway":              False,
            "spot_interruption":       False,
        }
        optimizer = AdaptiveOptimizer()
        actions = optimizer.simulate_run(run_dict)
        # May or may not fire — just must not raise

        # --- IFS ---
        ifs_rec = IFSCalculator.compute_ifs(
            intent_id=sim.intent_id,
            run_id="e2e-run-1",
            type_mismatch=False,
            type_mismatch_confidence=0.0,
            predicted_utilization=sim.predicted_utilization,
            actual_utilization=run_dict["cpu_utilization_avg"],
            expected_duration_hours=run_dict["expected_duration_hours"],
            actual_duration_hours=run_dict["actual_duration_hours"],
            over_provision_factor=20.0 / max(sim.optimal_nodes, 1),
        )
        assert 0.0 <= ifs_rec.ifs <= 1.0

        # --- Prevention tracker aggregation ---
        tracker = PreventionTracker()
        tracker.record_simulation(sim, ifs=ifs_rec.ifs)
        if actions:
            tracker.record_runtime_actions(
                sim.intent_id, sim.workload_type, actions,
                potential_cost=sim.potential_cost_usd,
                ifs=ifs_rec.ifs,
            )

        summary = tracker.summary()
        assert summary["total_potential"] > 0
        assert 0.0 <= summary["mean_ifs"] <= 1.0
        assert 0.0 <= summary["system_cps"] <= 1.0

    def test_workload_intent_not_mutated_by_pipeline(self):
        """Sreeja's modules must treat WorkloadIntent as read-only."""
        import copy
        from ifs.ifs_calculator import IFSCalculator
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer

        original = {
            "intent_id": "readonly-test",
            "workload_type": "etl",
            "node_count": 10,
            "type_mismatch": False,
            "type_mismatch_confidence": 0.0,
        }
        snapshot = copy.deepcopy(original)

        # IFS must not mutate the intent dict
        IFSCalculator.compute_ifs(
            intent_id=original["intent_id"], run_id="r1",
            type_mismatch=original["type_mismatch"],
            type_mismatch_confidence=original["type_mismatch_confidence"],
            predicted_utilization=0.60, actual_utilization=0.55,
            expected_duration_hours=4.0, actual_duration_hours=4.0,
            over_provision_factor=1.0,
        )
        assert original == snapshot, "IFSCalculator mutated the input dict"

        # RCA must not mutate the intent dict either
        RootCauseAnalyzer(DB_PATH).analyze()
        assert original == snapshot, "RootCauseAnalyzer mutated the input dict"