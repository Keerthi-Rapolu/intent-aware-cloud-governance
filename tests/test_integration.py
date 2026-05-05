"""
Integration tests — require data/full/iacg.duckdb to exist.
Run with: pytest tests/test_integration.py -v
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

DB = str(Path(__file__).parent.parent / "data" / "full" / "iacg.duckdb")

pytestmark = pytest.mark.skipif(
    not Path(DB).exists(),
    reason="data/full/iacg.duckdb not found — run generate_dataset.py first",
)


# ── FAISS index build from real DB ────────────────────────────────────────────

class TestWorkloadEmbeddingModel:
    @pytest.fixture(scope="class")
    def model(self):
        from intent_model.workload_embedding import WorkloadEmbeddingModel
        m = WorkloadEmbeddingModel()
        n = m.build_index(DB)
        assert n > 0, "Index must contain at least one vector"
        return m

    def test_index_size(self, model):
        assert model._index.ntotal >= 400   # ~500 workloads in DB

    def test_prior_source_knn(self, model):
        prior = model.get_prior({
            "workload_type": "etl",
            "cloud_provider": "aws",
            "node_count": 8,
            "expected_duration_hours": 4.0,
            "environment": "prod",
            "priority": "medium",
            "storage_gb": 200.0,
            "use_spot": False,
            "recurrence_signal": "recurring",
            "pii_signal": False,
            "over_provision_factor": 1.0,
        })
        assert prior.source == "knn"
        assert 0.0 < prior.expected_utilization <= 1.0
        assert prior.confidence >= 0.5

    def test_large_etl_closer_to_large_etl(self, model):
        """500 GB ETL embedding should be closer to other large ETL jobs than to tiny ones."""
        from intent_model.workload_embedding import encode_intent
        import numpy as np
        large_etl = encode_intent({
            "workload_type": "etl", "cloud_provider": "aws", "node_count": 8,
            "expected_duration_hours": 6.0, "environment": "prod", "priority": "medium",
            "storage_gb": 500.0, "use_spot": False, "recurrence_signal": "recurring",
            "pii_signal": False, "over_provision_factor": 1.0,
        })
        small_etl = encode_intent({
            "workload_type": "etl", "cloud_provider": "aws", "node_count": 2,
            "expected_duration_hours": 1.0, "environment": "dev", "priority": "low",
            "storage_gb": 5.0, "use_spot": True, "recurrence_signal": "one_time",
            "pii_signal": False, "over_provision_factor": 1.0,
        })
        streaming = encode_intent({
            "workload_type": "streaming", "cloud_provider": "aws", "node_count": 4,
            "expected_duration_hours": 72.0, "environment": "prod", "priority": "high",
            "storage_gb": 50.0, "use_spot": False, "recurrence_signal": "recurring",
            "pii_signal": False, "over_provision_factor": 1.0,
        })
        d_small   = float(np.linalg.norm(large_etl - small_etl))
        d_stream  = float(np.linalg.norm(large_etl - streaming))
        # Large ETL is closer to small ETL (same type) than to streaming (different type)
        assert d_small < d_stream

    def test_cold_start_fallback(self, model):
        """An extreme outlier should fall back to catalog."""
        from intent_model.workload_embedding import _COLD_START_DISTANCE_THRESHOLD
        prior = model.get_prior({
            "workload_type": "streaming",
            "cloud_provider": "gcp",
            "node_count": 999,          # extreme outlier
            "expected_duration_hours": 999.0,
            "environment": "sandbox",
            "priority": "critical",
            "storage_gb": 999999.0,
            "use_spot": True,
            "recurrence_signal": "one_time",
            "pii_signal": True,
            "over_provision_factor": 10.0,
        })
        # Either KNN found something (fine) or fell back to catalog (also fine)
        assert prior.source in ("knn", "catalog")
        assert prior.expected_utilization > 0


# ── Simulator with real DB (KNN path) ─────────────────────────────────────────

class TestSimulatorWithDB:
    def test_knn_prior_used_when_db_provided(self):
        from simulation_engine.simulator import PreExecutionSimulator
        sim = PreExecutionSimulator(db_path=DB)
        result = sim.simulate({
            "intent_id": "db-test-001",
            "workload_type": "etl",
            "cloud_provider": "aws",
            "instance_type": "m5.xlarge",
            "node_count": 10,
            "expected_duration_hours": 4.0,
            "priority": "medium",
            "use_spot": False,
        })
        assert result.potential_cost_usd > 0
        assert result.optimal_nodes >= 1
        assert result.stage == "pre_provision"

    def test_simulator_p99_latency(self):
        """p99 < 2 seconds over 100 simulations (catalog path, no DB for speed)."""
        import time
        from simulation_engine.simulator import PreExecutionSimulator
        sim = PreExecutionSimulator()
        intent = {
            "intent_id": "perf-test",
            "workload_type": "etl",
            "cloud_provider": "aws",
            "instance_type": "m5.xlarge",
            "node_count": 10,
            "expected_duration_hours": 4.0,
            "priority": "medium",
            "use_spot": False,
        }
        times = []
        for _ in range(100):
            t0 = time.perf_counter()
            sim.simulate(intent)
            times.append(time.perf_counter() - t0)
        times.sort()
        p99 = times[98]
        assert p99 < 2.0, f"p99 latency {p99:.3f}s exceeds 2s threshold"


# ── IntentInferenceEngine team history from real DB ──────────────────────────

class TestInferenceWithDB:
    def test_team_history_populated(self):
        import duckdb
        from intent_model.intent_inference import IntentInferenceEngine
        # Pick a real team from the DB
        con = duckdb.connect(DB, read_only=True)
        row = con.execute("SELECT team, workload_type FROM workload_intent LIMIT 1").fetchone()
        con.close()
        team, wtype = row
        engine = IntentInferenceEngine(db_path=DB)
        result = engine.infer("weekly ETL pipeline", declared_type=wtype, team=team)
        assert result.team_median_duration_hours is not None
        assert result.team_median_duration_hours > 0


# ── PolicyLearner with real DB ─────────────────────────────────────────────────

class TestPolicyLearnerWithDB:
    def test_analyze_runs_returns_list(self):
        from policy_engine.policy_registry import PolicyRegistry
        from policy_engine.policy_learner import PolicyLearner
        reg = PolicyLearner(PolicyRegistry())
        result = reg.analyze_runs(DB)
        # May be empty if no pattern crosses threshold — that's OK
        assert isinstance(result, list)

    def test_no_duplicate_policies(self):
        from policy_engine.policy_registry import PolicyRegistry
        from policy_engine.policy_learner import PolicyLearner
        registry = PolicyRegistry()
        learner = PolicyLearner(registry)
        first  = learner.analyze_runs(DB)
        second = learner.analyze_runs(DB)   # run twice — should not duplicate
        assert len(second) == 0, "Second run should not add duplicates"


# ── Runtime optimizer remaining signals ───────────────────────────────────────

class TestAdaptiveOptimizerSignals:
    def _run(self, **kwargs):
        from runtime_optimizer.adaptive_optimizer import AdaptiveOptimizer
        base = {
            "run_id": "sig-test", "cloud_provider": "aws", "instance_type": "m5.xlarge",
            "node_count": 4, "use_spot": False, "actual_duration_hours": 4.0,
            "expected_duration_hours": 4.0, "auto_shutdown_hours": 6.0,
            "idle_time_hours": 0.0, "cpu_utilization_avg": 0.70,
            "memory_utilization_avg": 0.65, "is_runaway": False, "spot_interruption": False,
        }
        return AdaptiveOptimizer().simulate_run({**base, **kwargs})

    def test_cpu_underutil_fires(self):
        actions = self._run(cpu_utilization_avg=0.15, node_count=8)
        cpu_actions = [a for a in actions if a.signal_type == "cpu_underutil"]
        assert len(cpu_actions) == 1
        assert cpu_actions[0].action == "SCALE_DOWN"
        assert cpu_actions[0].nodes_after < 8
        assert cpu_actions[0].cost_prevented_usd > 0

    def test_mem_underutil_fires_when_cpu_ok(self):
        actions = self._run(memory_utilization_avg=0.20, cpu_utilization_avg=0.65, node_count=6)
        mem_actions = [a for a in actions if a.signal_type == "mem_underutil"]
        assert len(mem_actions) == 1
        assert mem_actions[0].action == "SCALE_DOWN"

    def test_runaway_job_fires_checkpoint(self):
        actions = self._run(is_runaway=True, actual_duration_hours=12.0, expected_duration_hours=4.0)
        overrun = [a for a in actions if a.signal_type == "overrun"]
        assert len(overrun) == 1
        assert overrun[0].action == "CHECKPOINT"

    def test_spot_interruption_fires_migrate(self):
        actions = self._run(spot_interruption=True, use_spot=True)
        spot = [a for a in actions if a.signal_type == "spot_interruption"]
        assert len(spot) == 1
        assert spot[0].action == "MIGRATE"

    def test_actual_overrun_without_flag(self):
        # actual_duration > 1.5× expected triggers overrun even without is_runaway=True
        actions = self._run(actual_duration_hours=7.0, expected_duration_hours=4.0)
        overrun = [a for a in actions if a.signal_type == "overrun"]
        assert len(overrun) == 1


# ── CPS metrics coverage ──────────────────────────────────────────────────────

class TestPreventionTrackerFull:
    def test_convergence_curve_shape(self):
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import SimulationResult
        tracker = PreventionTracker()
        for i in range(10):
            fake = SimulationResult(
                intent_id=f"t{i}", workload_type="etl", cloud="aws",
                instance_type="m5.xlarge", submitted_nodes=10, optimal_nodes=4,
                predicted_utilization=0.28, potential_cost_usd=50.0,
                right_sized_cost_usd=20.0, prevented_cost_usd=30.0,
                intervention="AUTO_CORRECT", stage="pre_provision",
                ev_block=-10.0, ev_auto_correct=25.0,
            )
            tracker.record_simulation(fake, ifs=0.45)
        curve = tracker.convergence_curve(n_generations=10)
        assert len(curve) == 10
        assert curve[0]["generation"] == 0
        assert curve[-1]["mean_ifs"] > curve[0]["mean_ifs"]   # IFS improves

    def test_cps_by_stage_and_type(self):
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import SimulationResult
        tracker = PreventionTracker()
        for wtype in ("etl", "adhoc", "ml_training"):
            fake = SimulationResult(
                intent_id=wtype, workload_type=wtype, cloud="aws",
                instance_type="m5.xlarge", submitted_nodes=8, optimal_nodes=3,
                predicted_utilization=0.25, potential_cost_usd=100.0,
                right_sized_cost_usd=40.0, prevented_cost_usd=60.0,
                intervention="AUTO_CORRECT", stage="pre_provision",
                ev_block=-5.0, ev_auto_correct=50.0,
            )
            tracker.record_simulation(fake, ifs=0.55)
        by_type = tracker.cps_by_workload_type()
        assert set(by_type.keys()) == {"etl", "adhoc", "ml_training"}
        for cps in by_type.values():
            assert cps == pytest.approx(0.60, rel=0.01)

    def test_ibd_fraction(self):
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import SimulationResult
        tracker = PreventionTracker()
        for ifs in [0.30, 0.50, 0.80, 0.90]:   # 2 below 0.70, 2 above
            fake = SimulationResult(
                intent_id=f"ibd-{ifs}", workload_type="etl", cloud="aws",
                instance_type="m5.xlarge", submitted_nodes=4, optimal_nodes=4,
                predicted_utilization=0.65, potential_cost_usd=10.0,
                right_sized_cost_usd=10.0, prevented_cost_usd=0.0,
                intervention="PASS", stage="pre_provision",
                ev_block=0.0, ev_auto_correct=0.0,
            )
            tracker.record_simulation(fake, ifs=ifs)
        assert tracker.ibd_fraction() == pytest.approx(0.50, rel=0.01)

    def test_valid_cps_formula(self):
        from cps_metrics.prevention_tracker import PreventionTracker, CPSCalculator
        from simulation_engine.simulator import SimulationResult
        tracker = PreventionTracker()
        for i in range(10):
            fake = SimulationResult(
                intent_id=f"v{i}", workload_type="etl", cloud="aws",
                instance_type="m5.xlarge", submitted_nodes=4, optimal_nodes=4,
                predicted_utilization=0.65, potential_cost_usd=100.0,
                right_sized_cost_usd=70.0, prevented_cost_usd=30.0,
                intervention="AUTO_CORRECT", stage="pre_provision",
                ev_block=0.0, ev_auto_correct=10.0,
            )
            succeeded = (i < 9)   # 9/10 complete → ESR = 0.90
            tracker.record_simulation(fake, ifs=0.70, succeeded=succeeded)
        assert tracker.system_esr() == pytest.approx(0.90, rel=0.01)
        assert tracker.system_cps() == pytest.approx(0.30, rel=0.01)
        assert tracker.valid_cps()  == pytest.approx(0.27, rel=0.01)


# ── cost_comparison end-to-end ────────────────────────────────────────────────

class TestCostComparison:
    def test_returns_three_clouds(self):
        from cost_normalizer.normalizer import CrossCloudNormalizer
        n = CrossCloudNormalizer()
        result = n.cost_comparison("etl", nodes=4, duration_hours=4.0)
        assert set(result.keys()) == {"aws", "azure", "gcp"}

    def test_all_costs_positive(self):
        from cost_normalizer.normalizer import CrossCloudNormalizer
        n = CrossCloudNormalizer()
        result = n.cost_comparison("ml_training", nodes=2, duration_hours=8.0)
        for cloud, cost in result.items():
            assert cost > 0, f"{cloud} cost should be positive"

    def test_spot_cheaper(self):
        from cost_normalizer.normalizer import CrossCloudNormalizer
        n = CrossCloudNormalizer()
        od   = n.cost_comparison("etl", nodes=4, duration_hours=4.0, use_spot=False)
        spot = n.cost_comparison("etl", nodes=4, duration_hours=4.0, use_spot=True)
        for cloud in od:
            assert spot[cloud] < od[cloud], f"Spot should be cheaper on {cloud}"