from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Optional

from policy_engine.policy_registry import PolicyRegistry
from policy_engine.policy_enforcer import PolicyEnforcer, PolicyViolation
from simulation_engine.simulator import PreExecutionSimulator, SimulationResult


@dataclass
class GuardrailDecision:
    intent_id: str
    action: str                              # REJECT | AUTO_CORRECT | SUGGEST | PASS
    violations: list[PolicyViolation]
    simulation: SimulationResult
    resolved_config: dict[str, Any]          # potentially right-sized config
    conflict_strategy: Optional[str] = None  # resolution strategy used


class PolicyConflictResolver:
    """
    When multiple policies fire on the same intent, resolve using one of
    four strategies.
    """

    @staticmethod
    def resolve(
        violations: list[PolicyViolation],
        intent: dict[str, Any],
        strategy: str = "most_restrictive",
    ) -> tuple[str, dict[str, Any]]:
        """
        Returns (resolved_action, adjusted_intent_config).
        """
        if not violations:
            return "PASS", intent

        if strategy == "highest_priority_wins":
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            top = max(violations, key=lambda v: severity_order.get(v.severity, 1))
            return top.policy_action, intent

        if strategy == "most_restrictive":
            action_order = {"REJECT": 3, "AUTO_CORRECT": 2, "SUGGEST": 1}
            top = max(violations, key=lambda v: action_order.get(v.policy_action, 0))
            return top.policy_action, intent

        if strategy == "auto_negotiate":
            return PolicyConflictResolver._auto_negotiate(violations, intent)

        if strategy == "human_escalate":
            return "SUGGEST", intent   # escalate = surface to user, don't block

        return "SUGGEST", intent

    @staticmethod
    def _auto_negotiate(
        violations: list[PolicyViolation],
        intent: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """
        Try to adjust the config to satisfy all constraints without REJECT.
        Falls back to SUGGEST if constraints are irreconcilable.
        """
        adjusted = copy.deepcopy(intent)
        has_reject = any(v.policy_action == "REJECT" for v in violations)

        for v in violations:
            cond = v.condition
            if cond == "auto_shutdown_hours_exceeds":
                adjusted["auto_shutdown_hours"] = v.threshold
            elif cond == "node_count_exceeds":
                adjusted["node_count"] = int(v.threshold)
            elif cond == "spot_not_enabled":
                adjusted["use_spot"] = True
            elif cond == "token_budget_missing":
                adjusted["token_budget"] = 50_000   # default safe budget

        # If we handled all REJECT conditions by adjusting config → AUTO_CORRECT
        if has_reject:
            still_violated = [v for v in violations
                              if v.condition == "auto_shutdown_hours_exceeds"
                              and float(adjusted.get("auto_shutdown_hours") or 0) > v.threshold]
            if still_violated:
                return "SUGGEST", adjusted
            return "AUTO_CORRECT", adjusted

        return "AUTO_CORRECT", adjusted


class PreProvisionGuard:
    """
    Single entry point for pre-provision evaluation.
    Combines policy enforcement + simulation into one GuardrailDecision.
    """

    def __init__(
        self,
        registry: PolicyRegistry,
        simulator: PreExecutionSimulator,
        conflict_strategy: str = "auto_negotiate",
    ) -> None:
        self._enforcer  = PolicyEnforcer(registry)
        self._simulator = simulator
        self._strategy  = conflict_strategy

    def evaluate(self, intent: dict[str, Any]) -> GuardrailDecision:
        violations = self._enforcer.check(intent)
        resolved_action, resolved_config = PolicyConflictResolver.resolve(
            violations, intent, self._strategy
        )

        # Always run simulation, even on REJECT — for paper metrics
        sim = self._simulator.simulate(intent)

        # If simulation strongly recommends intervention and policy says PASS → upgrade
        if resolved_action == "PASS" and sim.intervention in ("AUTO_CORRECT", "BLOCK"):
            resolved_action = sim.intervention
            resolved_config = _apply_sim_correction(intent, sim)

        return GuardrailDecision(
            intent_id=intent.get("intent_id", "unknown"),
            action=resolved_action,
            violations=violations,
            simulation=sim,
            resolved_config=resolved_config,
            conflict_strategy=self._strategy,
        )


def _apply_sim_correction(intent: dict[str, Any], sim: SimulationResult) -> dict[str, Any]:
    adjusted = copy.deepcopy(intent)
    adjusted["node_count"] = sim.optimal_nodes
    return adjusted