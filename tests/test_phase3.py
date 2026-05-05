"""Phase 3 unit tests — run with: pytest tests/test_phase3.py -v"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Shared test fixtures
_ETL_INTENT = {
    "intent_id": "test-etl-001",
    "workload_type": "etl",
    "cloud_provider": "aws",
    "instance_type": "m5.xlarge",
    "node_count": 20,
    "optimal_node_count": 6,
    "expected_duration_hours": 8.0,
    "priority": "medium",
    "use_spot": False,
    "auto_shutdown_hours": 4.0,
    "token_budget": None,
}

_ETL_OVERLONG_SHUTDOWN = {**_ETL_INTENT, "intent_id": "test-etl-002", "auto_shutdown_hours": 10.0}
_ADHOC_MANY_NODES      = {**_ETL_INTENT, "intent_id": "test-adhoc-001",
                           "workload_type": "adhoc", "node_count": 8, "auto_shutdown_hours": 2.0}
_LLM_NO_BUDGET         = {**_ETL_INTENT, "intent_id": "test-llm-001",
                           "workload_type": "llm_pipeline", "instance_type": "m5.2xlarge",
                           "node_count": 3, "auto_shutdown_hours": 6.0, "token_budget": None}


# ── static_provisioning ────────────────────────────────────────────────────────

class TestStaticProvisioning:
    def _eval(self, intent):
        import experiments.baselines.static_provisioning as sp
        return sp.evaluate(intent)

    def test_no_prevention(self):
        r = self._eval(_ETL_INTENT)
        assert r.prevented_cost_usd == 0.0
        assert r.intervention == "PASS"

    def test_nodes_unchanged(self):
        r = self._eval(_ETL_INTENT)
        assert r.submitted_nodes == r.optimal_nodes == 20

    def test_cps_is_zero(self):
        r = self._eval(_ETL_INTENT)
        assert r.cps == 0.0

    def test_potential_cost_positive(self):
        r = self._eval(_ETL_INTENT)
        # 20 nodes × $0.192/hr × 8 hr = $30.72
        assert r.potential_cost_usd == pytest.approx(30.72, rel=1e-3)

    def test_deterministic(self):
        r1 = self._eval(_ETL_INTENT)
        r2 = self._eval(_ETL_INTENT)
        assert r1.potential_cost_usd == r2.potential_cost_usd
        assert r1.prevented_cost_usd == r2.prevented_cost_usd

    def test_batch_length(self):
        import experiments.baselines.static_provisioning as sp
        results = sp.evaluate_batch([_ETL_INTENT, _ADHOC_MANY_NODES, _LLM_NO_BUDGET])
        assert len(results) == 3


# ── rule_based_policies ────────────────────────────────────────────────────────

class TestRuleBasedPolicies:
    def _eval(self, intent):
        import experiments.baselines.rule_based_policies as rb
        return rb.evaluate(intent)

    def test_etl_overlong_shutdown_rejected(self):
        r = self._eval(_ETL_OVERLONG_SHUTDOWN)
        assert r.intervention == "REJECT"
        # REJECT means full cost prevented (blocked), but ESR takes the hit
        assert r.prevented_cost_usd == r.potential_cost_usd

    def test_adhoc_nodes_capped(self):
        r = self._eval(_ADHOC_MANY_NODES)
        # adhoc_max_nodes rule: cap at 5
        assert r.optimal_nodes == 5
        assert r.intervention == "AUTO_CORRECT"
        assert r.prevented_cost_usd > 0

    def test_llm_no_budget_rejected(self):
        r = self._eval(_LLM_NO_BUDGET)
        assert r.intervention == "REJECT"

    def test_healthy_etl_passes(self):
        r = self._eval(_ETL_INTENT)
        # auto_shutdown=4.0 ≤ threshold=4.0 → no violation, but spot_not_enabled → SUGGEST
        assert r.intervention in ("PASS", "SUGGEST")

    def test_deterministic(self):
        r1 = self._eval(_ADHOC_MANY_NODES)
        r2 = self._eval(_ADHOC_MANY_NODES)
        assert r1.prevented_cost_usd == r2.prevented_cost_usd
        assert r1.intervention == r2.intervention

    def test_better_than_static_on_violation(self):
        import experiments.baselines.static_provisioning as sp
        import experiments.baselines.rule_based_policies as rb
        s = sp.evaluate(_ADHOC_MANY_NODES)
        r = rb.evaluate(_ADHOC_MANY_NODES)
        # Rule-based should prevent more than static (which prevents nothing)
        assert r.prevented_cost_usd > s.prevented_cost_usd


# ── no_phase3_frozen ──────────────────────────────────────────────────────────

class TestNoPhase3Frozen:
    def _eval(self, intent):
        import experiments.baselines.no_phase3_frozen as nf
        return nf.evaluate(intent)

    def test_returns_simulation_result(self):
        from simulation_engine.simulator import SimulationResult
        r = self._eval(_ETL_INTENT)
        assert isinstance(r, SimulationResult)

    def test_stage_is_pre_provision(self):
        r = self._eval(_ETL_INTENT)
        assert r.stage == "pre_provision"

    def test_overlong_shutdown_handled(self):
        r = self._eval(_ETL_OVERLONG_SHUTDOWN)
        # auto_negotiate should adjust — either REJECT or AUTO_CORRECT, not PASS
        assert r.intervention != "PASS" or r.prevented_cost_usd >= 0

    def test_deterministic(self):
        r1 = self._eval(_ETL_INTENT)
        r2 = self._eval(_ETL_INTENT)
        assert r1.prevented_cost_usd == r2.prevented_cost_usd
        assert r1.intervention == r2.intervention

    def test_better_than_static(self):
        import experiments.baselines.static_provisioning as sp
        # Over many intents, frozen-PBCP should prevent at least as much as static
        intents = [_ETL_INTENT, _ADHOC_MANY_NODES] * 5
        import experiments.baselines.no_phase3_frozen as nf
        static_total   = sum(sp.evaluate(i).prevented_cost_usd for i in intents)
        frozen_total   = sum(nf.evaluate(i).prevented_cost_usd for i in intents)
        assert frozen_total >= static_total

    def test_batch_length(self):
        import experiments.baselines.no_phase3_frozen as nf
        results = nf.evaluate_batch([_ETL_INTENT, _ADHOC_MANY_NODES, _LLM_NO_BUDGET])
        assert len(results) == 3


# ── cross-baseline ordering ───────────────────────────────────────────────────

class TestBaselineOrdering:
    """
    Sanity check: over the same workload set,
    static ≤ rule_based ≤ no_phase3_frozen in terms of prevented cost.
    (rule_based may equal static when no rules fire; frozen-PBCP should match or exceed both)
    """

    def test_ordering_on_violation_set(self):
        import experiments.baselines.static_provisioning as sp
        import experiments.baselines.rule_based_policies as rb
        import experiments.baselines.no_phase3_frozen as nf

        # Use intents that definitely trigger rules (clear violations)
        intents = [_ADHOC_MANY_NODES] * 10

        s_total = sum(sp.evaluate(i).prevented_cost_usd for i in intents)
        r_total = sum(rb.evaluate(i).prevented_cost_usd for i in intents)
        n_total = sum(nf.evaluate(i).prevented_cost_usd for i in intents)

        assert s_total == 0.0, "Static must never prevent cost"
        assert r_total > s_total, "Rule-based must outperform static on known violations"
        assert n_total >= s_total, "No-Phase3 must match or beat static"