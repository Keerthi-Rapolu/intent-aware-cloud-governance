"""
Baseline 2 — Rule-Based Policies (fixed rules, no simulation, no learning).

Represents a naive governance system: a hardcoded lookup table of
"if workload_type X and node_count > N → reject/suggest".
No EV calculation, no utilization prediction, no KNN embedding.

This isolates how much of PBCP's gain comes from simulation + learning
vs. simple static policies alone.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from simulation_engine.cost_model import CloudCostModel
from simulation_engine.simulator import SimulationResult
from intent_model.intent_catalog import INTENT_CATALOG

_cost_model = CloudCostModel()

# Hardcoded rules: (workload_type, condition, threshold, action, cap_nodes)
# These mirror the 7 built-in policies but without EV reasoning.
_RULES: list[dict] = [
    {"workload_type": "etl",         "condition": "auto_shutdown_exceeds", "threshold": 4.0,  "action": "REJECT",       "cap_nodes": None},
    {"workload_type": "adhoc",        "condition": "node_count_exceeds",    "threshold": 5.0,  "action": "AUTO_CORRECT", "cap_nodes": 5},
    {"workload_type": "llm_pipeline", "condition": "token_budget_missing",  "threshold": 0.0,  "action": "REJECT",       "cap_nodes": None},
    {"workload_type": "adhoc",        "condition": "spot_not_enabled",      "threshold": 0.0,  "action": "SUGGEST",      "cap_nodes": None},
    {"workload_type": "etl",          "condition": "spot_not_enabled",      "threshold": 0.0,  "action": "SUGGEST",      "cap_nodes": None},
    {"workload_type": "batch",        "condition": "auto_shutdown_exceeds", "threshold": 12.0, "action": "REJECT",       "cap_nodes": None},
    {"workload_type": "ml_training",  "condition": "auto_shutdown_exceeds", "threshold": 24.0, "action": "REJECT",       "cap_nodes": None},
]


def _apply_rules(intent: dict[str, Any]) -> tuple[str, int]:
    """
    Returns (action, effective_node_count).
    Applies rules in order; first REJECT wins. AUTO_CORRECT caps nodes.
    """
    wtype         = intent.get("workload_type", "adhoc")
    nodes         = int(intent.get("node_count", 4))
    auto_shutdown = float(intent.get("auto_shutdown_hours") or 0)
    token_budget  = intent.get("token_budget")
    use_spot      = bool(intent.get("use_spot", False))

    action = "PASS"
    effective_nodes = nodes

    for rule in _RULES:
        if rule["workload_type"] != wtype:
            continue
        cond = rule["condition"]
        fired = False
        if cond == "auto_shutdown_exceeds" and auto_shutdown > rule["threshold"]:
            fired = True
        elif cond == "node_count_exceeds" and nodes > rule["threshold"]:
            fired = True
        elif cond == "token_budget_missing" and not token_budget:
            fired = True
        elif cond == "spot_not_enabled" and not use_spot:
            fired = True

        if fired:
            if rule["action"] == "REJECT":
                return "REJECT", nodes   # immediate exit — no cost prevention on blocked job
            if rule["action"] == "AUTO_CORRECT" and rule["cap_nodes"]:
                effective_nodes = min(nodes, int(rule["cap_nodes"]))
                action = "AUTO_CORRECT"
            elif action == "PASS":
                action = rule["action"]

    return action, effective_nodes


def evaluate(intent: dict[str, Any]) -> SimulationResult:
    """
    Apply hardcoded rules to the intent.
    No utilization prediction — savings come only from capped node counts.
    """
    wtype    = intent.get("workload_type", "adhoc")
    cloud    = intent.get("cloud_provider", "aws")
    instance = intent.get("instance_type",
                           INTENT_CATALOG[wtype].default_instance.get(cloud, "m5.xlarge"))
    nodes    = int(intent.get("node_count", 4))
    duration = float(intent.get("expected_duration_hours", 4.0))
    use_spot = bool(intent.get("use_spot", False))

    action, effective_nodes = _apply_rules(intent)

    potential_cost   = _cost_model.compute_cost(cloud, instance, nodes,           duration, use_spot)
    right_sized_cost = _cost_model.compute_cost(cloud, instance, effective_nodes,  duration, use_spot)

    if action == "REJECT":
        # REJECT blocks the job — full cost is prevented but ESR takes the hit
        prevented = potential_cost
        right_sized_cost = 0.0
    elif action == "AUTO_CORRECT":
        prevented = potential_cost - right_sized_cost
    else:
        prevented = 0.0

    return SimulationResult(
        intent_id=intent.get("intent_id", "unknown"),
        workload_type=wtype,
        cloud=cloud,
        instance_type=instance,
        submitted_nodes=nodes,
        optimal_nodes=effective_nodes,
        predicted_utilization=0.0,   # no prediction in this baseline
        potential_cost_usd=potential_cost,
        right_sized_cost_usd=right_sized_cost,
        prevented_cost_usd=prevented,
        intervention=action,
        stage="pre_provision",
        ev_block=0.0,
        ev_auto_correct=0.0,
    )


def evaluate_batch(intents: list[dict[str, Any]]) -> list[SimulationResult]:
    return [evaluate(i) for i in intents]