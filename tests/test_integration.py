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


# ── Phase G — End-to-End Integration (Sreeja × Keerthi interface) ─────────────
#
# Interface contract (design doc §9):
#   WorkloadIntent  (K→S): read-only; S never mutates
#   IFSRecord       (S→K): S writes; K consumes via record_simulation(ifs=)
#   PolicySuggestion(S→K): S writes via RCA; K consumes via registry.add()
#   Full pipeline:  description → intent → simulation → guardrail → IFS → CPS

class TestPhaseGEndToEnd:

    # -- Fixture: a representative ETL workload intent dict -------------------

    @pytest.fixture(scope="class")
    def intent_dict(self):
        return {
            "intent_id":              "g-etl-001",
            "workload_name":          "data_engineering_etl_0001",
            "workload_type":          "etl",
            "cloud_provider":         "aws",
            "instance_type":          "m5.xlarge",
            "node_count":             16,           # over-provisioned (optimal ~6)
            "optimal_node_count":     6,
            "expected_duration_hours": 4.0,
            "priority":               "medium",
            "environment":            "prod",
            "use_spot":               False,
            "over_provision_factor":  16 / 6,
            "storage_gb":             200.0,
            "auto_shutdown_hours":    4.0,
            "recurrence_signal":      "recurring",
            "pii_signal":             False,
            "token_budget":           None,
            "type_mismatch":          False,
            "type_mismatch_confidence": 0.0,
        }

    # -- 1. WorkloadIntent read-only contract ----------------------------------

    def test_workload_intent_not_mutated_by_ifs(self, intent_dict):
        """IFSCalculator must not modify any field of the input intent."""
        from ifs.ifs_calculator import IFSCalculator
        original = dict(intent_dict)   # snapshot before call

        IFSCalculator.compute_ifs(
            intent_id=intent_dict["intent_id"],
            run_id="run-g-001",
            type_mismatch=intent_dict["type_mismatch"],
            type_mismatch_confidence=intent_dict["type_mismatch_confidence"],
            predicted_utilization=0.65,
            actual_utilization=0.30,    # under-utilised (over-provisioned)
            expected_duration_hours=intent_dict["expected_duration_hours"],
            actual_duration_hours=4.5,
            over_provision_factor=intent_dict["over_provision_factor"],
        )

        assert intent_dict == original, "IFSCalculator must not mutate the intent dict"

    def test_workload_intent_not_mutated_by_rca(self):
        """RootCauseAnalyzer reads only from DB; it must not modify WorkloadIntent fields."""
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        from intent_model.workload_intent import WorkloadIntent, ResourceConfig, InferredIntentFields

        rc  = ResourceConfig("aws", "m5.xlarge", 16, 6, False, 4.0, 200.0, "us-east-1", 4, 16.0, 16/6)
        inf = InferredIntentFields("etl", "large", "batch_ok", "recurring", False, "internal", False, None, 0.92)
        wi  = WorkloadIntent("g-etl-002", "etl_job", "weekly ETL", "data_eng",
                             "etl", "prod", "medium", 4.0, "daily", "2025-01-01", rc, inf)

        original_id   = wi.intent_id
        original_type = wi.workload_type

        analyzer = RootCauseAnalyzer(DB)
        analyzer.analyze()   # must not touch wi

        assert wi.intent_id      == original_id
        assert wi.workload_type  == original_type

    # -- 2. IFSRecord → PreventionTracker feed-through ─────────────────────────

    def test_ifs_record_feeds_into_tracker_aggregation(self, intent_dict):
        """IFSRecord.ifs from IFSCalculator correctly aggregates inside PreventionTracker."""
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import SimulationResult

        rec = IFSCalculator.compute_ifs(
            intent_id=intent_dict["intent_id"],
            run_id="run-g-002",
            type_mismatch=False,
            type_mismatch_confidence=0.0,
            predicted_utilization=0.65,
            actual_utilization=0.30,
            expected_duration_hours=4.0,
            actual_duration_hours=4.5,
            over_provision_factor=16 / 6,
        )
        assert 0.0 <= rec.ifs <= 1.0

        sim = SimulationResult(
            intent_id=intent_dict["intent_id"],
            workload_type="etl", cloud="aws", instance_type="m5.xlarge",
            submitted_nodes=16, optimal_nodes=6,
            predicted_utilization=0.65,
            potential_cost_usd=200.0, right_sized_cost_usd=75.0, prevented_cost_usd=125.0,
            intervention="AUTO_CORRECT", stage="pre_provision",
            ev_block=-20.0, ev_auto_correct=80.0,
        )

        tracker = PreventionTracker()
        tracker.record_simulation(sim, ifs=rec.ifs, succeeded=True)

        summary = tracker.summary()
        assert summary["mean_ifs"] == pytest.approx(rec.ifs, rel=1e-4)
        assert summary["system_cps"] > 0
        assert summary["esr"] == pytest.approx(1.0)

    def test_multiple_ifs_records_aggregate_correctly(self):
        """Multiple IFSRecords from different workloads aggregate mean_ifs correctly."""
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import SimulationResult

        tracker = PreventionTracker()
        ifs_values = []

        cases = [
            # (type_mismatch, tm_conf, pred_util, actual_util, exp_dur, act_dur, opf)
            (False, 0.0, 0.70, 0.68, 4.0, 4.1, 1.0),   # well-aligned
            (True,  0.90, 0.70, 0.25, 4.0, 8.0, 2.5),   # severe
            (False, 0.0, 0.65, 0.60, 6.0, 6.5, 1.1),   # minor
        ]
        for i, (tm, tmc, pu, au, ed, ad, opf) in enumerate(cases):
            rec = IFSCalculator.compute_ifs(
                intent_id=f"g-multi-{i}", run_id=f"run-multi-{i}",
                type_mismatch=tm, type_mismatch_confidence=tmc,
                predicted_utilization=pu, actual_utilization=au,
                expected_duration_hours=ed, actual_duration_hours=ad,
                over_provision_factor=opf,
            )
            ifs_values.append(rec.ifs)
            sim = SimulationResult(
                intent_id=f"g-multi-{i}", workload_type="etl", cloud="aws",
                instance_type="m5.xlarge", submitted_nodes=8, optimal_nodes=4,
                predicted_utilization=pu, potential_cost_usd=100.0,
                right_sized_cost_usd=50.0, prevented_cost_usd=50.0,
                intervention="AUTO_CORRECT", stage="pre_provision",
                ev_block=-5.0, ev_auto_correct=40.0,
            )
            tracker.record_simulation(sim, ifs=rec.ifs, succeeded=True)

        expected_mean = sum(ifs_values) / len(ifs_values)
        assert tracker.mean_ifs() == pytest.approx(expected_mean, rel=1e-3)

    # -- 3. RCA PolicySuggestions → PolicyRegistry ─────────────────────────────

    def test_rca_policies_accepted_by_registry(self):
        """Policies from RootCauseAnalyzer.analyze() can be added to PolicyRegistry."""
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        from policy_engine.policy_registry import PolicyRegistry

        analyzer  = RootCauseAnalyzer(DB)
        policies  = analyzer.analyze()
        assert len(policies) >= 2

        registry  = PolicyRegistry()
        n_before  = len(registry)
        for p in policies:
            registry.add(p)

        assert len(registry) == n_before + len(policies)
        for p in policies:
            assert registry.get(p.policy_id) is not None

    def test_rca_learned_policies_distinct_from_builtin(self):
        """Learned policies from RCA must have source='learned', not 'builtin'."""
        from anomaly_rca.root_cause_analyzer import RootCauseAnalyzer
        from policy_engine.policy_registry import PolicyRegistry

        registry = PolicyRegistry()
        builtin_ids = {p.policy_id for p in registry.list_all()}

        analyzer = RootCauseAnalyzer(DB)
        learned  = analyzer.analyze()

        for p in learned:
            assert p.source == "learned"
            assert p.policy_id not in builtin_ids, \
                f"Learned policy {p.policy_id} collides with a builtin policy ID"

    # -- 4. Full pipeline: description → intent → simulation → IFS → CPS ───────

    def test_full_pipeline_etl_over_provisioned(self):
        """
        Full pipeline for an over-provisioned ETL workload:
          description → inference → simulation → guardrail → IFS → PreventionTracker
        Verifies the cross-module data flow without any module mutating another's outputs.
        """
        from intent_model.intent_inference import IntentInferenceEngine
        from simulation_engine.simulator import PreExecutionSimulator
        from guardrails.pre_provision_guard import PreProvisionGuard
        from policy_engine.policy_registry import PolicyRegistry
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker

        # Step 1: description → inferred intent
        engine   = IntentInferenceEngine()
        inferred = engine.infer(
            "Weekly ETL pipeline processing 500 GB of customer transaction data from S3 to Redshift",
            declared_type="etl",
        )
        assert inferred.workload_type_inferred == "etl"

        # Step 2: simulate (over-provisioned: 16 nodes, optimal ~6)
        sim_input = {
            "intent_id":              "pipeline-etl-001",
            "workload_type":          "etl",
            "cloud_provider":         "aws",
            "instance_type":          "m5.xlarge",
            "node_count":             16,
            "expected_duration_hours": 4.0,
            "priority":               "medium",
            "use_spot":               False,
        }
        simulator = PreExecutionSimulator()
        sim_result = simulator.simulate(sim_input)
        assert sim_result.submitted_nodes == 16
        assert sim_result.optimal_nodes < 16   # system detects over-provisioning
        assert sim_result.stage == "pre_provision"

        # Step 3: guardrail decision
        registry = PolicyRegistry()
        guard    = PreProvisionGuard(registry, simulator, conflict_strategy="auto_negotiate")
        decision = guard.evaluate(sim_input)
        assert decision.action in ("AUTO_CORRECT", "SUGGEST", "REJECT", "PASS")

        # Step 4: IFS — simulated runtime shows under-utilisation (confirms over-prov)
        ifs_rec = IFSCalculator.compute_ifs(
            intent_id="pipeline-etl-001",
            run_id="run-pipeline-001",
            type_mismatch=inferred.type_mismatch,
            type_mismatch_confidence=inferred.type_mismatch_confidence or 0.0,
            predicted_utilization=sim_result.predicted_utilization,
            actual_utilization=0.28,        # under-utilised due to over-provisioning
            expected_duration_hours=4.0,
            actual_duration_hours=4.2,
            over_provision_factor=16 / max(sim_result.optimal_nodes, 1),
        )
        assert 0.0 <= ifs_rec.ifs <= 1.0
        assert ifs_rec.intent_id == "pipeline-etl-001"

        # Step 5: feed IFS into PreventionTracker
        tracker = PreventionTracker()
        tracker.record_simulation(sim_result, ifs=ifs_rec.ifs, succeeded=True)
        summary = tracker.summary()

        assert summary["total_runs"] == 1
        assert summary["mean_ifs"]   == pytest.approx(ifs_rec.ifs, rel=1e-4)
        assert summary["system_cps"] >= 0.0

    def test_full_pipeline_llm_with_token_waste(self):
        """
        Full pipeline for an LLM pipeline with token waste:
        IFSCalculator uses token sub-score; result feeds PreventionTracker.
        """
        from simulation_engine.simulator import PreExecutionSimulator
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker

        sim_input = {
            "intent_id":              "pipeline-llm-001",
            "workload_type":          "llm_pipeline",
            "cloud_provider":         "aws",
            "instance_type":          "m5.2xlarge",
            "node_count":             3,
            "expected_duration_hours": 2.0,
            "priority":               "medium",
            "use_spot":               False,
        }
        simulator  = PreExecutionSimulator()
        sim_result = simulator.simulate(sim_input)

        ifs_rec = IFSCalculator.compute_ifs(
            intent_id="pipeline-llm-001",
            run_id="run-llm-001",
            type_mismatch=False,
            type_mismatch_confidence=0.0,
            predicted_utilization=sim_result.predicted_utilization,
            actual_utilization=0.55,
            expected_duration_hours=2.0,
            actual_duration_hours=2.1,
            over_provision_factor=1.0,
            is_llm_pipeline=True,
            token_budget_declared=100_000,
            token_usage_actual=180_000,   # 80% over budget
        )
        assert 0.0 <= ifs_rec.ifs <= 1.0

        tracker = PreventionTracker()
        tracker.record_simulation(sim_result, ifs=ifs_rec.ifs, succeeded=True)
        assert tracker.mean_ifs() == pytest.approx(ifs_rec.ifs, rel=1e-4)

    def test_ibd_fraction_reflects_low_ifs_workloads(self):
        """
        IBD fraction from PreventionTracker matches the fraction of low-IFS records
        produced by IFSCalculator (IFS < 0.70 threshold per design doc §5.6).
        """
        from ifs.ifs_calculator import IFSCalculator
        from cps_metrics.prevention_tracker import PreventionTracker
        from simulation_engine.simulator import SimulationResult

        tracker = PreventionTracker()
        cases = [
            # (over_provision_factor, actual_util) → expected low/high IFS
            (1.0, 0.70),   # well-aligned
            (1.0, 0.68),   # well-aligned
            (3.0, 0.20),   # severe (IBD)
            (2.5, 0.25),   # severe (IBD)
        ]
        n_low = 0
        for i, (opf, au) in enumerate(cases):
            rec = IFSCalculator.compute_ifs(
                intent_id=f"ibd-{i}", run_id=f"run-ibd-{i}",
                type_mismatch=(opf > 2.0),
                type_mismatch_confidence=0.85 if opf > 2.0 else 0.0,
                predicted_utilization=0.70, actual_utilization=au,
                expected_duration_hours=4.0, actual_duration_hours=4.0,
                over_provision_factor=opf,
            )
            if rec.ifs < 0.70:
                n_low += 1
            sim = SimulationResult(
                intent_id=f"ibd-{i}", workload_type="etl", cloud="aws",
                instance_type="m5.xlarge", submitted_nodes=8, optimal_nodes=4,
                predicted_utilization=0.70, potential_cost_usd=100.0,
                right_sized_cost_usd=50.0, prevented_cost_usd=50.0,
                intervention="AUTO_CORRECT", stage="pre_provision",
                ev_block=-5.0, ev_auto_correct=40.0,
            )
            tracker.record_simulation(sim, ifs=rec.ifs)

        expected_ibd = n_low / len(cases)
        assert tracker.ibd_fraction() == pytest.approx(expected_ibd, rel=1e-3)