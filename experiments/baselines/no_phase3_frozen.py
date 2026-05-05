"""
Baseline 3 — PBCP with Phase 3 Disabled (frozen priors, no learning).

Runs the full PBCP pipeline (simulation + EV decisions + guardrails)
but with Phase 3 contributions removed:
  - No KNN embedding model; always uses INTENT_CATALOG priors (frozen)
  - No PolicyLearner; only built-in policies (no learned policies added)
  - PreExecutionSimulator is constructed without a DB path

This isolates the contribution of Phase 3 (adaptive learning) on CPS.
Used in Experiment 6 as the "PBCP No Phase 3" curve.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from simulation_engine.simulator import PreExecutionSimulator, SimulationResult
from policy_engine.policy_registry import PolicyRegistry
from policy_engine.policy_enforcer import PolicyEnforcer
from guardrails.pre_provision_guard import PreProvisionGuard

# Shared instances — no DB path means catalog-only priors (Phase 3 frozen)
_registry = PolicyRegistry()         # only built-in policies; no PolicyLearner called
_simulator = PreExecutionSimulator() # no db_path → catalog fallback always used
_guard     = PreProvisionGuard(_registry, _simulator, conflict_strategy="auto_negotiate")


def evaluate(intent: dict[str, Any]) -> SimulationResult:
    """
    Full PBCP guardrail pipeline but with catalog priors only (Phase 3 frozen).
    Learned policies are never added to the registry.
    """
    decision = _guard.evaluate(intent)
    sim = decision.simulation

    # Honour the guardrail action — if policy says REJECT, override simulation
    if decision.action == "REJECT":
        return SimulationResult(
            intent_id=sim.intent_id,
            workload_type=sim.workload_type,
            cloud=sim.cloud,
            instance_type=sim.instance_type,
            submitted_nodes=sim.submitted_nodes,
            optimal_nodes=sim.submitted_nodes,
            predicted_utilization=sim.predicted_utilization,
            potential_cost_usd=sim.potential_cost_usd,
            right_sized_cost_usd=0.0,
            prevented_cost_usd=sim.potential_cost_usd,
            intervention="REJECT",
            stage="pre_provision",
            ev_block=sim.ev_block,
            ev_auto_correct=sim.ev_auto_correct,
        )

    return SimulationResult(
        intent_id=sim.intent_id,
        workload_type=sim.workload_type,
        cloud=sim.cloud,
        instance_type=sim.instance_type,
        submitted_nodes=sim.submitted_nodes,
        optimal_nodes=decision.resolved_config.get("node_count", sim.optimal_nodes),
        predicted_utilization=sim.predicted_utilization,
        potential_cost_usd=sim.potential_cost_usd,
        right_sized_cost_usd=sim.right_sized_cost_usd,
        prevented_cost_usd=sim.prevented_cost_usd,
        intervention=decision.action,
        stage="pre_provision",
        ev_block=sim.ev_block,
        ev_auto_correct=sim.ev_auto_correct,
    )


def evaluate_batch(intents: list[dict[str, Any]]) -> list[SimulationResult]:
    return [evaluate(i) for i in intents]