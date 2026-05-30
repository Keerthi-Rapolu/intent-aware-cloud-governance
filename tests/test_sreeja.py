"""Sreeja's unit and integration tests — run with: pytest tests/test_sreeja.py -v"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = str(Path(__file__).parent.parent / "data" / "full" / "iacg.duckdb")

_db_available = Path(DB_PATH).exists()
skip_no_db = pytest.mark.skipif(not _db_available, reason="data/full/iacg.duckdb not found")

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


# ── TestPreventionFeedback ─────────────────────────────────────────────────────

class TestPreventionFeedback:
    """Tests for anomaly_rca/prevention_feedback.py — IBD feedback loop."""

    def _make_ifs_record(self, intent_id: str, run_id: str, ifs: float,
                          category: str = "significant",
                          type_align: float = 0.40,
                          util_align: float = 0.40,
                          dur_align: float = 0.40,
                          res_align: float = 0.40):
        """Minimal fake IFSRecord duck-typed for AnomalyPreventionFeedback."""
        class FakeIFSRecord:
            pass
        r = FakeIFSRecord()
        r.intent_id         = intent_id
        r.run_id            = run_id
        r.ifs               = ifs
        r.ifs_category      = category
        r.type_alignment    = type_align
        r.util_alignment    = util_align
        r.duration_alignment = dur_align
        r.resource_alignment = res_align
        return r

    @pytest.fixture
    def registry(self):
        from policy_engine.policy_registry import PolicyRegistry
        return PolicyRegistry()

    @pytest.fixture
    def feedback(self, registry):
        from anomaly_rca.prevention_feedback import AnomalyPreventionFeedback
        return AnomalyPreventionFeedback(registry)

    def test_well_aligned_records_skipped(self, feedback):
        rec = self._make_ifs_record("i1", "r1", ifs=0.80)
        anomalies = feedback.process([rec], {"i1": "etl"})
        assert anomalies == []

    def test_ibd_record_creates_anomaly(self, feedback):
        rec = self._make_ifs_record("i2", "r2", ifs=0.55)
        anomalies = feedback.process([rec], {"i2": "etl"})
        assert len(anomalies) == 1
        assert anomalies[0].is_ibd_flagged is True

    def test_anomaly_record_fields(self, feedback):
        from anomaly_rca.prevention_feedback import AnomalyRecord
        rec = self._make_ifs_record("i3", "r3", ifs=0.45, category="severe")
        anomalies = feedback.process([rec], {"i3": "batch"})
        a = anomalies[0]
        assert isinstance(a, AnomalyRecord)
        assert a.intent_id  == "i3"
        assert a.run_id     == "r3"
        assert a.ifs        == pytest.approx(0.45)
        assert a.ifs_category == "severe"
        assert a.workload_type == "batch"

    def test_cost_impact_severe_is_high(self, feedback):
        rec = self._make_ifs_record("i4", "r4", ifs=0.40)
        anomalies = feedback.process([rec], {"i4": "etl"}, {"i4": 200.0})
        assert anomalies[0].estimated_cost_impact >= 50.0   # >= 50% of 200

    def test_cost_impact_significant_is_moderate(self, feedback):
        rec = self._make_ifs_record("i5", "r5", ifs=0.60)
        anomalies = feedback.process([rec], {"i5": "etl"}, {"i5": 200.0})
        assert 10.0 <= anomalies[0].estimated_cost_impact < 100.0

    def test_policy_generated_after_threshold_count(self, registry):
        from anomaly_rca.prevention_feedback import AnomalyPreventionFeedback
        feedback = AnomalyPreventionFeedback(registry)
        # 6 over_provisioned records → confidence = 0.60 → policy added
        records = [
            self._make_ifs_record(f"i{k}", f"r{k}", ifs=0.55,
                                   type_align=0.90, util_align=0.90,
                                   dur_align=0.90, res_align=0.20)
            for k in range(6)
        ]
        wtype_map = {f"i{k}": "etl" for k in range(6)}
        feedback.process(records, wtype_map)
        pol = registry.get("feedback_etl_over_provisioned")
        assert pol is not None

    def test_no_policy_below_min_count(self, registry):
        from anomaly_rca.prevention_feedback import AnomalyPreventionFeedback
        feedback = AnomalyPreventionFeedback(registry)
        # 2 records → confidence=0.20 → below MIN_CONFIDENCE=0.60
        records = [
            self._make_ifs_record(f"j{k}", f"s{k}", ifs=0.55,
                                   type_align=0.90, util_align=0.90,
                                   dur_align=0.90, res_align=0.20)
            for k in range(2)
        ]
        feedback.process(records, {f"j{k}": "batch" for k in range(2)})
        assert registry.get("feedback_batch_over_provisioned") is None

    def test_duplicate_policy_not_added_twice(self, registry):
        from anomaly_rca.prevention_feedback import AnomalyPreventionFeedback
        feedback = AnomalyPreventionFeedback(registry)
        records = [
            self._make_ifs_record(f"m{k}", f"t{k}", ifs=0.50,
                                   type_align=0.90, util_align=0.20,
                                   dur_align=0.90, res_align=0.90)
            for k in range(7)
        ]
        wtype_map = {f"m{k}": "streaming" for k in range(7)}
        n_before = len(registry)
        feedback.process(records, wtype_map)
        n_after_first = len(registry)
        feedback.process(records, wtype_map)
        n_after_second = len(registry)
        assert n_after_first == n_after_second, "Policy was added twice"

    def test_summary_aggregates_correctly(self, feedback):
        from anomaly_rca.prevention_feedback import AnomalyPreventionFeedback
        recs = [self._make_ifs_record(f"s{k}", f"u{k}", ifs=0.50) for k in range(3)]
        anomalies = feedback.process(recs, {f"s{k}": "etl" for k in range(3)})
        s = feedback.summary(anomalies)
        assert s["n_ibd"] == 3
        assert "mean_ifs" in s
        assert "total_cost_impact" in s
        assert s["mean_ifs"] == pytest.approx(0.50, rel=1e-4)

    def test_summary_empty_returns_zeros(self, feedback):
        s = feedback.summary([])
        assert s["n_ibd"] == 0
        assert s["mean_ifs"] == 0.0
        assert s["total_cost_impact"] == 0.0

    def test_unknown_intent_id_defaults_to_wildcard(self, feedback):
        rec = self._make_ifs_record("unknown_id", "r99", ifs=0.55)
        # no entry in workload_type_map → defaults to "*"
        anomalies = feedback.process([rec], {})
        assert anomalies[0].workload_type == "*"

    def test_root_cause_inferred_from_lowest_subscore(self, feedback):
        from anomaly_rca.prevention_feedback import _infer_root_cause
        rec = self._make_ifs_record(
            "rc_test", "rc_run", ifs=0.50,
            type_align=0.90, util_align=0.20, dur_align=0.80, res_align=0.80
        )
        assert _infer_root_cause(rec) == "idle_cluster"

    def test_root_cause_unknown_when_all_scores_high(self, feedback):
        from anomaly_rca.prevention_feedback import _infer_root_cause
        rec = self._make_ifs_record(
            "rc2", "rc2r", ifs=0.60,
            type_align=0.80, util_align=0.70, dur_align=0.75, res_align=0.72
        )
        # All sub-scores >= 0.50, so root cause should be "unknown"
        assert _infer_root_cause(rec) == "unknown"


# ── TestExp3IBDDetection ───────────────────────────────────────────────────────

class TestExp3IBDDetection:
    """Unit tests for exp3_ibd_detection.py detector logic (no DB required)."""

    def _make_run(self, **kwargs):
        defaults = dict(
            run_id="run-e3-1",
            intent_id="int-e3-1",
            cpu_util=0.50,
            mem_util=0.60,
            idle_time_hours=0.0,
            actual_duration_hours=4.0,
            expected_duration_hours=4.0,
            is_anomaly=False,
            is_runaway=False,
            is_idle_injected=False,
            workload_type="etl",
            type_mismatch=False,
            type_mismatch_confidence=0.0,
            wi_expected_dur=4.0,
            over_provision_factor=1.0,
            ifs=0.80,
            ifs_category="well_aligned",
        )
        defaults.update(kwargs)
        return defaults

    def test_ground_truth_anomaly_flag(self):
        from experiments.exp3_ibd_detection import _is_anomaly_gt
        assert _is_anomaly_gt(self._make_run(is_anomaly=True))  is True
        assert _is_anomaly_gt(self._make_run(is_runaway=True))  is True
        assert _is_anomaly_gt(self._make_run(is_idle_injected=True)) is True
        assert _is_anomaly_gt(self._make_run()) is False

    def test_threshold_detector_cpu_below(self):
        from experiments.exp3_ibd_detection import _threshold_detector
        assert _threshold_detector(self._make_run(cpu_util=0.20)) is True
        assert _threshold_detector(self._make_run(cpu_util=0.50)) is False

    def test_threshold_detector_idle_time(self):
        from experiments.exp3_ibd_detection import _threshold_detector
        assert _threshold_detector(self._make_run(idle_time_hours=1.0)) is True
        assert _threshold_detector(self._make_run(idle_time_hours=0.0)) is False

    def test_ifs_detector_below_threshold(self):
        from experiments.exp3_ibd_detection import _ifs_detector
        assert _ifs_detector(self._make_run(ifs=0.60)) is True
        assert _ifs_detector(self._make_run(ifs=0.80)) is False

    def test_compute_metrics_perfect_detector(self):
        from experiments.exp3_ibd_detection import _compute_metrics, _is_anomaly_gt
        # All anomalies detected, no false positives
        data = [
            self._make_run(run_id=f"r{i}", is_anomaly=True,  ifs=0.50) for i in range(5)
        ] + [
            self._make_run(run_id=f"r{i+5}", is_anomaly=False, ifs=0.80) for i in range(5)
        ]
        metrics = _compute_metrics(data, lambda r: r["ifs"] < 0.65)
        assert metrics["precision"] == pytest.approx(1.0)
        assert metrics["recall"]    == pytest.approx(1.0)
        assert metrics["f1"]        == pytest.approx(1.0)
        assert metrics["fpr"]       == pytest.approx(0.0)

    def test_compute_metrics_random_detector(self):
        from experiments.exp3_ibd_detection import _compute_metrics
        data = [self._make_run(run_id=f"r{i}", is_anomaly=(i % 2 == 0)) for i in range(10)]
        # Always-false detector
        metrics = _compute_metrics(data, lambda r: False)
        assert metrics["tp"] == 0
        assert metrics["fp"] == 0
        assert metrics["recall"] == 0.0

    def test_type_mismatch_analysis_separates_groups(self):
        from experiments.exp3_ibd_detection import _type_mismatch_analysis
        data = (
            [self._make_run(run_id=f"m{i}", type_mismatch=True,
                             is_anomaly=True, ifs=0.50) for i in range(5)] +
            [self._make_run(run_id=f"n{i}", type_mismatch=False,
                             is_anomaly=False, ifs=0.85) for i in range(5)]
        )
        tm = _type_mismatch_analysis(data)
        assert tm["mismatch_n"] == 5
        assert tm["non_mismatch_n"] == 5
        assert tm["mismatch_anomaly_rate"] > tm["non_mismatch_anomaly_rate"]
        assert tm["mismatch_mean_ifs"]     < tm["non_mismatch_mean_ifs"]


# ── TestIFSWithDB ──────────────────────────────────────────────────────────────

@skip_no_db
class TestIFSWithDB:
    """Integration tests: IFS calculator against real cps_ifs_records in DB."""

    @pytest.fixture(scope="class")
    def ifs_rows(self):
        """Baseline rows represent the 500-workload population distribution."""
        import duckdb
        con = duckdb.connect(DB_PATH, read_only=True)
        rows = con.execute(
            "SELECT ifs, ifs_category FROM cps_ifs_records WHERE stage = 'baseline' LIMIT 1000"
        ).fetchall()
        con.close()
        return rows

    def test_db_has_ifs_records(self, ifs_rows):
        assert len(ifs_rows) > 0, "cps_ifs_records has no baseline rows"

    def test_mean_ifs_in_expected_range(self, ifs_rows):
        mean = sum(r[0] for r in ifs_rows) / len(ifs_rows)
        assert 0.60 <= mean <= 0.80, f"Mean IFS {mean:.3f} outside expected 0.60–0.80"

    def test_all_ifs_values_bounded(self, ifs_rows):
        for ifs, _ in ifs_rows:
            assert 0.0 <= ifs <= 1.0, f"IFS value {ifs} out of [0,1]"

    def test_all_four_categories_present(self):
        """All four categories must exist across the full cps_ifs_records table."""
        import duckdb
        con = duckdb.connect(DB_PATH, read_only=True)
        cats = {r[0] for r in con.execute(
            "SELECT DISTINCT ifs_category FROM cps_ifs_records"
        ).fetchall()}
        con.close()
        assert {"well_aligned", "minor", "significant", "severe"} <= cats

    def test_well_aligned_fraction_reasonable(self, ifs_rows):
        n_well = sum(1 for _, cat in ifs_rows if cat == "well_aligned")
        frac = n_well / len(ifs_rows)
        assert 0.10 <= frac <= 0.60, f"well_aligned fraction {frac:.2%} out of expected range"

    def test_severe_fraction_reasonable(self, ifs_rows):
        n_severe = sum(1 for _, cat in ifs_rows if cat == "severe")
        frac = n_severe / len(ifs_rows)
        assert 0.05 <= frac <= 0.50, f"severe fraction {frac:.2%} out of expected range"

    def test_well_aligned_ifs_above_threshold(self, ifs_rows):
        for ifs, cat in ifs_rows:
            if cat == "well_aligned":
                assert ifs >= 0.85, f"well_aligned but IFS={ifs}"


# ── TestRCAWithDB ──────────────────────────────────────────────────────────────

@skip_no_db
class TestRCAWithDB:
    """Integration tests: RootCauseAnalyzer against real historical_incidents."""

    @pytest.fixture(scope="class")
    def analyzer(self):
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        return RootCauseAnalyzer(DB_PATH)

    @pytest.fixture(scope="class")
    def policies(self, analyzer):
        return analyzer.analyze()

    def test_incident_table_has_rows(self):
        import duckdb
        con = duckdb.connect(DB_PATH, read_only=True)
        n = con.execute("SELECT COUNT(*) FROM historical_incidents").fetchone()[0]
        con.close()
        assert n >= 10, "historical_incidents has too few rows"

    def test_analyze_returns_policies(self, policies):
        assert len(policies) >= 2

    def test_policies_all_learned(self, policies):
        assert all(p.source == "learned" for p in policies)

    def test_policies_confidence_range(self, policies):
        for p in policies:
            assert 0.60 <= p.confidence <= 0.95

    def test_policies_have_valid_actions(self, policies):
        valid = {"AUTO_CORRECT", "SUGGEST", "REJECT"}
        for p in policies:
            assert p.action in valid

    def test_top_incidents_count(self, analyzer):
        rows = analyzer.top_incidents(n=10)
        assert len(rows) == 10

    def test_top_incidents_descending_cost(self, analyzer):
        rows = analyzer.top_incidents(n=20)
        costs = [r["cost_impact_usd"] for r in rows]
        assert costs == sorted(costs, reverse=True)

    def test_known_incident_types_covered(self, analyzer):
        rows = analyzer.top_incidents(n=50)
        incident_types = {r["incident_type"] for r in rows}
        assert "over_provisioned" in incident_types
        assert "idle_cluster" in incident_types

    def test_policy_ids_are_unique(self, policies):
        ids = [p.policy_id for p in policies]
        assert len(ids) == len(set(ids))

    def test_policies_accepted_by_registry(self, policies):
        from policy_engine.policy_registry import PolicyRegistry
        registry = PolicyRegistry()
        n_before = len(registry)
        for p in policies:
            registry.add(p)
        assert len(registry) == n_before + len(policies)

    def test_learned_policy_ids_not_in_builtin(self, policies):
        from policy_engine.policy_registry import PolicyRegistry
        builtin_ids = {p.policy_id for p in PolicyRegistry().list_all()}
        for p in policies:
            assert p.policy_id not in builtin_ids


# ── TestPreventionFeedbackWithDB ───────────────────────────────────────────────

@skip_no_db
class TestPreventionFeedbackWithDB:
    """Integration: AnomalyPreventionFeedback processing DB-derived IFS records."""

    @pytest.fixture(scope="class")
    def db_ifs_data(self):
        """Load a sample of IBD-flagged rows from the DB."""
        import duckdb
        con = duckdb.connect(DB_PATH, read_only=True)
        rows = con.execute("""
            SELECT c.intent_id, c.run_id, c.ifs, c.ifs_category,
                   w.workload_type, c.potential_cost_usd
            FROM cps_ifs_records c
            JOIN workload_intent w USING (intent_id)
            WHERE c.ifs < 0.65 AND c.stage != 'baseline'
            LIMIT 50
        """).fetchall()
        con.close()
        return rows

    def test_db_has_ibd_records(self, db_ifs_data):
        assert len(db_ifs_data) > 0, "No IBD records found in DB"

    def test_feedback_processes_db_records(self, db_ifs_data):
        from anomaly_rca.prevention_feedback import AnomalyPreventionFeedback
        from policy_engine.policy_registry import PolicyRegistry

        class _FakeRec:
            def __init__(self, row):
                self.intent_id = row[0]
                self.run_id = row[1]
                self.ifs = row[2]
                self.ifs_category = row[3]
                self.type_alignment = 0.40
                self.util_alignment = 0.40
                self.duration_alignment = 0.40
                self.resource_alignment = 0.40

        records = [_FakeRec(r) for r in db_ifs_data]
        wtype_map = {r[0]: r[4] for r in db_ifs_data}
        cost_map  = {r[0]: r[5] for r in db_ifs_data}

        registry = PolicyRegistry()
        feedback = AnomalyPreventionFeedback(registry)
        anomalies = feedback.process(records, wtype_map, cost_map)

        assert len(anomalies) == len(records)
        assert all(a.is_ibd_flagged for a in anomalies)

    def test_all_anomalies_have_workload_type(self, db_ifs_data):
        from anomaly_rca.prevention_feedback import AnomalyPreventionFeedback
        from policy_engine.policy_registry import PolicyRegistry

        class _FakeRec:
            def __init__(self, row):
                self.intent_id = row[0]; self.run_id = row[1]; self.ifs = row[2]
                self.ifs_category = row[3]; self.type_alignment = 0.4
                self.util_alignment = 0.4; self.duration_alignment = 0.4
                self.resource_alignment = 0.4

        records  = [_FakeRec(r) for r in db_ifs_data]
        wtype_map = {r[0]: r[4] for r in db_ifs_data}
        feedback  = AnomalyPreventionFeedback(PolicyRegistry())
        anomalies = feedback.process(records, wtype_map)

        for a in anomalies:
            assert a.workload_type, "workload_type must not be empty"

    def test_summary_ibd_count_matches(self, db_ifs_data):
        from anomaly_rca.prevention_feedback import AnomalyPreventionFeedback
        from policy_engine.policy_registry import PolicyRegistry

        class _FakeRec:
            def __init__(self, row):
                self.intent_id = row[0]; self.run_id = row[1]; self.ifs = row[2]
                self.ifs_category = row[3]; self.type_alignment = 0.4
                self.util_alignment = 0.4; self.duration_alignment = 0.4
                self.resource_alignment = 0.4

        records  = [_FakeRec(r) for r in db_ifs_data]
        feedback = AnomalyPreventionFeedback(PolicyRegistry())
        anomalies = feedback.process(records, {r[0]: r[4] for r in db_ifs_data})
        s = feedback.summary(anomalies)

        assert s["n_ibd"] == len(records)
        assert 0.0 <= s["mean_ifs"] < 0.65


# ── TestExp3WithDB ─────────────────────────────────────────────────────────────

@skip_no_db
class TestExp3WithDB:
    """Integration: Exp 3 IBD detector evaluation against real DB data."""

    @pytest.fixture(scope="class")
    def db_runs(self):
        import duckdb
        con = duckdb.connect(DB_PATH, read_only=True)
        rows = con.execute("""
            SELECT r.run_id, r.intent_id, r.cpu_utilization_avg,
                   r.idle_time_hours, r.actual_duration_hours, r.expected_duration_hours,
                   r.is_anomaly, r.is_runaway, r.is_idle_injected,
                   c.ifs, c.ifs_category, w.type_mismatch, w.type_mismatch_confidence
            FROM runtime_metrics r
            JOIN cps_ifs_records c ON r.run_id = c.run_id
            JOIN workload_intent w ON r.intent_id = w.intent_id
            WHERE c.stage != 'baseline'
            LIMIT 300
        """).fetchall()
        con.close()
        cols = ["run_id","intent_id","cpu_util","idle_time_hours","actual_duration_hours",
                "expected_duration_hours","is_anomaly","is_runaway","is_idle_injected",
                "ifs","ifs_category","type_mismatch","type_mismatch_confidence"]
        return [dict(zip(cols, r)) for r in rows]

    def test_db_returns_runs(self, db_runs):
        assert len(db_runs) > 0

    def test_ifs_detector_f1_exceeds_threshold_f1(self, db_runs):
        from experiments.exp3_ibd_detection import _compute_metrics, _threshold_detector, _ifs_detector
        thresh_m = _compute_metrics(db_runs, _threshold_detector)
        ifs_m    = _compute_metrics(db_runs, _ifs_detector)
        assert ifs_m["f1"] >= thresh_m["f1"], (
            f"IFS F1 {ifs_m['f1']:.3f} should exceed threshold F1 {thresh_m['f1']:.3f}"
        )

    def test_ifs_detector_recall_exceeds_threshold(self, db_runs):
        from experiments.exp3_ibd_detection import _compute_metrics, _threshold_detector, _ifs_detector
        thresh_m = _compute_metrics(db_runs, _threshold_detector)
        ifs_m    = _compute_metrics(db_runs, _ifs_detector)
        assert ifs_m["recall"] >= thresh_m["recall"], (
            f"IFS recall {ifs_m['recall']:.3f} should be >= threshold recall {thresh_m['recall']:.3f}"
        )

    def test_metrics_keys_complete(self, db_runs):
        from experiments.exp3_ibd_detection import _compute_metrics, _ifs_detector
        m = _compute_metrics(db_runs, _ifs_detector)
        for key in ("precision", "recall", "f1", "fpr", "tp", "fp", "tn", "fn"):
            assert key in m

    def test_no_anomaly_in_db_means_no_tp(self, db_runs):
        from experiments.exp3_ibd_detection import _compute_metrics
        # always-false detector → TP must be 0
        m = _compute_metrics(db_runs, lambda r: False)
        assert m["tp"] == 0
        assert m["fp"] == 0

    def test_type_mismatch_subgroup_has_higher_anomaly_rate(self, db_runs):
        from experiments.exp3_ibd_detection import _type_mismatch_analysis
        mismatch_rows = [r for r in db_runs if r.get("type_mismatch")]
        if len(mismatch_rows) < 2:
            pytest.skip("not enough type_mismatch rows in DB sample")
        tm = _type_mismatch_analysis(db_runs)
        assert tm["mismatch_anomaly_rate"] >= tm["non_mismatch_anomaly_rate"]
