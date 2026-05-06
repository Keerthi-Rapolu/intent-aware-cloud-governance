"""Sreeja's unit and integration tests — run with: pytest tests/test_sreeja.py -v"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = str(Path(__file__).parent.parent / "data" / "full" / "iacg.duckdb")

# ── TestIFSCalculator ──────────────────────────────────────────────────────────

class TestIFSCalculator:

    def _make_record(self, **kwargs):
        from ifs.ifs_calculator import IFSCalculator
        defaults = dict(
            intent_id="test-001",
            run_id="run-001",
            type_mismatch=False,
            type_mismatch_confidence=0.0,
            predicted_utilization=0.70,
            actual_utilization=0.65,
            expected_duration_hours=4.0,
            actual_duration_hours=4.2,
            over_provision_factor=1.0,
        )
        defaults.update(kwargs)
        return IFSCalculator.compute_ifs(**defaults)

    def test_returns_ifs_record_type(self):
        from ifs.ifs_calculator import IFSRecord
        rec = self._make_record()
        assert isinstance(rec, IFSRecord)

    def test_ifs_in_range(self):
        rec = self._make_record()
        assert 0.0 <= rec.ifs <= 1.0

    def test_no_mismatch_perfect_alignment(self):
        rec = self._make_record(
            type_mismatch=False,
            predicted_utilization=0.70,
            actual_utilization=0.70,
            expected_duration_hours=4.0,
            actual_duration_hours=4.0,
            over_provision_factor=1.0,
        )
        assert rec.ifs >= 0.85
        assert rec.ifs_category == "well_aligned"

    def test_severe_mismatch_low_ifs(self):
        rec = self._make_record(
            type_mismatch=True,
            type_mismatch_confidence=0.95,
            predicted_utilization=0.90,
            actual_utilization=0.10,
            expected_duration_hours=2.0,
            actual_duration_hours=8.0,
            over_provision_factor=3.0,
        )
        assert rec.ifs < 0.50
        assert rec.ifs_category == "severe"

    def test_category_well_aligned(self):
        rec = self._make_record(
            type_mismatch=False,
            predicted_utilization=0.80,
            actual_utilization=0.78,
            expected_duration_hours=4.0,
            actual_duration_hours=4.1,
            over_provision_factor=1.0,
        )
        assert rec.ifs >= 0.85
        assert rec.ifs_category == "well_aligned"

    def test_category_minor(self):
        rec = self._make_record(
            type_mismatch=False,
            type_mismatch_confidence=0.0,
            predicted_utilization=0.70,
            actual_utilization=0.55,
            expected_duration_hours=4.0,
            actual_duration_hours=4.8,
            over_provision_factor=1.2,
        )
        assert 0.50 <= rec.ifs <= 0.90

    def test_category_significant(self):
        rec = self._make_record(
            type_mismatch=True,
            type_mismatch_confidence=0.50,
            predicted_utilization=0.70,
            actual_utilization=0.40,
            expected_duration_hours=4.0,
            actual_duration_hours=6.0,
            over_provision_factor=1.5,
        )
        assert 0.0 <= rec.ifs <= 0.85

    def test_category_thresholds_exact(self):
        from ifs.ifs_calculator import _category
        assert _category(0.85) == "well_aligned"
        assert _category(0.70) == "minor"
        assert _category(0.50) == "significant"
        assert _category(0.49) == "severe"

    def test_sub_scores_in_range(self):
        rec = self._make_record()
        assert 0.0 <= rec.type_alignment <= 1.0
        assert 0.0 <= rec.util_alignment <= 1.0
        assert 0.0 <= rec.duration_alignment <= 1.0
        assert 0.0 <= rec.resource_alignment <= 1.0

    def test_over_provision_factor_penalises(self):
        good = self._make_record(over_provision_factor=1.0)
        bad  = self._make_record(over_provision_factor=3.0)
        assert good.resource_alignment > bad.resource_alignment
        assert good.ifs > bad.ifs

    def test_type_mismatch_penalises(self):
        no_mm = self._make_record(type_mismatch=False, type_mismatch_confidence=0.0)
        mm    = self._make_record(type_mismatch=True,  type_mismatch_confidence=0.90)
        assert no_mm.type_alignment > mm.type_alignment
        assert no_mm.ifs > mm.ifs

    def test_llm_pipeline_token_waste_sub_score(self):
        from ifs.ifs_calculator import IFSCalculator
        # Significant token waste should lower IFS
        no_waste = IFSCalculator.compute_ifs(
            intent_id="llm-001", run_id="r1",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.70, actual_utilization=0.70,
            expected_duration_hours=4.0, actual_duration_hours=4.0,
            over_provision_factor=1.0,
            is_llm_pipeline=True,
            token_budget_declared=100_000,
            token_usage_actual=80_000,   # under budget → token_score=1.0
        )
        waste = IFSCalculator.compute_ifs(
            intent_id="llm-002", run_id="r2",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.70, actual_utilization=0.70,
            expected_duration_hours=4.0, actual_duration_hours=4.0,
            over_provision_factor=1.0,
            is_llm_pipeline=True,
            token_budget_declared=100_000,
            token_usage_actual=190_000,   # 90% over budget
        )
        assert no_waste.ifs > waste.ifs

    def test_llm_under_budget_no_penalty(self):
        from ifs.ifs_calculator import IFSCalculator
        rec = IFSCalculator.compute_ifs(
            intent_id="llm-003", run_id="r3",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.80, actual_utilization=0.80,
            expected_duration_hours=2.0, actual_duration_hours=2.0,
            over_provision_factor=1.0,
            is_llm_pipeline=True,
            token_budget_declared=100_000,
            token_usage_actual=60_000,  # under budget
        )
        assert rec.ifs >= 0.85   # should be well-aligned

    def test_ifs_rounded_to_4dp(self):
        rec = self._make_record()
        assert rec.ifs == round(rec.ifs, 4)

    def test_detail_string_contains_sub_scores(self):
        rec = self._make_record()
        assert "type=" in rec.detail
        assert "util=" in rec.detail
        assert "dur=" in rec.detail
        assert "res=" in rec.detail


# ── TestRootCauseAnalyzer ──────────────────────────────────────────────────────

class TestRootCauseAnalyzer:

    @pytest.fixture(scope="class")
    def analyzer(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        return RootCauseAnalyzer(DB_PATH)

    @pytest.fixture(scope="class")
    def policies(self, analyzer):
        return analyzer.analyze()

    def test_returns_at_least_two_policies(self, policies):
        assert len(policies) >= 2, f"Expected >= 2 policies, got {len(policies)}"

    def test_all_policies_source_learned(self, policies):
        assert all(p.source == "learned" for p in policies)

    def test_all_policies_confidence_in_range(self, policies):
        for p in policies:
            assert 0.60 <= p.confidence <= 1.0, (
                f"Policy {p.policy_id} confidence {p.confidence} out of range"
            )

    def test_policy_has_required_fields(self, policies):
        from policy_engine.policy_registry import Policy
        for p in policies:
            assert isinstance(p, Policy)
            assert p.policy_id
            assert p.workload_type
            assert p.condition
            assert p.action in ("AUTO_CORRECT", "SUGGEST", "REJECT")

    def test_top_incidents_returns_n_rows(self, analyzer):
        rows = analyzer.top_incidents(n=5)
        assert len(rows) == 5

    def test_top_incidents_sorted_by_cost_desc(self, analyzer):
        rows = analyzer.top_incidents(n=10)
        costs = [r["cost_impact_usd"] for r in rows]
        assert costs == sorted(costs, reverse=True)

    def test_top_incidents_has_required_keys(self, analyzer):
        rows = analyzer.top_incidents(n=3)
        required = {
            "incident_id", "workload_type", "incident_type", "severity",
            "cost_impact_usd", "detection_lag_minutes", "fix_applied",
        }
        for row in rows:
            assert required <= set(row.keys()), f"Missing keys: {required - set(row.keys())}"

    def test_analyze_with_short_lookback_returns_less(self, analyzer):
        # Very short lookback should return fewer policies (possibly 0)
        policies_long  = analyzer.analyze(lookback_days=365)
        policies_short = analyzer.analyze(lookback_days=1)
        assert len(policies_long) >= len(policies_short)

    def test_confidence_capped_at_095(self, policies):
        assert all(p.confidence <= 0.95 for p in policies)


# ── TestIntegration ────────────────────────────────────────────────────────────

class TestIntegration:

    def test_ifs_record_plugs_into_prevention_tracker(self):
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import SimulationResult

        rec = IFSCalculator.compute_ifs(
            intent_id="int-001", run_id="run-int-001",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.70, actual_utilization=0.65,
            expected_duration_hours=4.0, actual_duration_hours=4.0,
            over_provision_factor=1.0,
        )

        fake_sim = SimulationResult(
            intent_id="int-001", workload_type="etl", cloud="aws",
            instance_type="m5.xlarge", submitted_nodes=8, optimal_nodes=6,
            predicted_utilization=0.70, potential_cost_usd=100.0,
            right_sized_cost_usd=75.0, prevented_cost_usd=25.0,
            intervention="AUTO_CORRECT", stage="pre_provision",
            ev_block=-10.0, ev_auto_correct=20.0,
        )

        tracker = PreventionTracker()
        tracker.record_simulation(fake_sim, ifs=rec.ifs, succeeded=True)
        s = tracker.summary()
        assert s["mean_ifs"] == pytest.approx(rec.ifs, rel=1e-4)
        assert s["system_cps"] > 0

    def test_rca_policies_can_be_added_to_registry(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        from policy_engine.policy_registry import PolicyRegistry

        analyzer  = RootCauseAnalyzer(DB_PATH)
        policies  = analyzer.analyze()
        registry  = PolicyRegistry()
        n_before  = len(registry)

        for p in policies:
            registry.add(p)   # must not raise KeyError

        assert len(registry) == n_before + len(policies)

    def test_rca_policy_ids_are_unique(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        analyzer = RootCauseAnalyzer(DB_PATH)
        policies = analyzer.analyze()
        ids = [p.policy_id for p in policies]
        assert len(ids) == len(set(ids)), "Duplicate policy IDs found"

    def test_ifs_workload_intent_not_mutated(self):
        from ifs.ifs_calculator import IFSCalculator
        original_id = "immutable-001"
        rec = IFSCalculator.compute_ifs(
            intent_id=original_id, run_id="run-x",
            type_mismatch=False, type_mismatch_confidence=0.0,
            predicted_utilization=0.65, actual_utilization=0.60,
            expected_duration_hours=3.0, actual_duration_hours=3.5,
            over_provision_factor=1.2,
        )
        # IFSRecord should preserve the intent_id unchanged
        assert rec.intent_id == original_id

    def test_prevention_tracker_ifs_affects_mean(self):
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import SimulationResult

        def make_sim(intent_id: str):
            return SimulationResult(
                intent_id=intent_id, workload_type="etl", cloud="aws",
                instance_type="m5.xlarge", submitted_nodes=10, optimal_nodes=6,
                predicted_utilization=0.65, potential_cost_usd=200.0,
                right_sized_cost_usd=120.0, prevented_cost_usd=80.0,
                intervention="AUTO_CORRECT", stage="pre_provision",
                ev_block=-5.0, ev_auto_correct=30.0,
            )

        tracker = PreventionTracker()
        tracker.record_simulation(make_sim("a"), ifs=0.90)
        tracker.record_simulation(make_sim("b"), ifs=0.50)
        assert tracker.mean_ifs() == pytest.approx(0.70, rel=1e-4)
