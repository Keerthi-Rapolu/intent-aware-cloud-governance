from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .policy_registry import Policy, PolicyRegistry


@dataclass
class PolicyViolation:
    policy_id: str
    policy_action: str          # REJECT | AUTO_CORRECT | SUGGEST
    condition: str
    threshold: float
    actual_value: float
    description: str
    severity: str               # critical | high | medium | low (from workload priority)


def _extract_value(intent: dict[str, Any], condition: str) -> float:
    """Map a policy condition name to the numeric value from an intent dict."""
    mapping = {
        "auto_shutdown_hours_exceeds": lambda d: float(d.get("auto_shutdown_hours") or 0),
        "node_count_exceeds":          lambda d: float(d.get("node_count", 0)),
        "token_budget_missing":        lambda d: 0.0 if d.get("token_budget") else 1.0,
        "spot_not_enabled":            lambda d: 0.0 if d.get("use_spot", False) else 1.0,
    }
    extractor = mapping.get(condition)
    if extractor is None:
        return 0.0
    return extractor(intent)


def _is_violated(condition: str, actual: float, threshold: float) -> bool:
    # "missing" conditions: threshold=0 means flag when actual > 0 (flag absence)
    if condition in ("token_budget_missing", "spot_not_enabled"):
        return actual > threshold   # actual=1 → not set
    return actual > threshold


class PolicyEnforcer:
    """
    Checks a WorkloadIntent dict against all registered policies.
    Returns a list of PolicyViolation for every policy that fires.
    """

    def __init__(self, registry: PolicyRegistry) -> None:
        self._registry = registry

    def check(self, intent: dict[str, Any]) -> list[PolicyViolation]:
        workload_type = intent.get("workload_type", "adhoc")
        priority      = intent.get("priority", "medium")
        violations: list[PolicyViolation] = []

        for policy in self._registry.list_for_type(workload_type):
            actual = _extract_value(intent, policy.condition)
            if _is_violated(policy.condition, actual, policy.threshold):
                violations.append(PolicyViolation(
                    policy_id=policy.policy_id,
                    policy_action=policy.action,
                    condition=policy.condition,
                    threshold=policy.threshold,
                    actual_value=actual,
                    description=policy.description,
                    severity=priority,
                ))
        return violations

    def has_blocking_violations(self, violations: list[PolicyViolation]) -> bool:
        return any(v.policy_action == "REJECT" for v in violations)