"""
Baseline 1 — Static Provisioning (no intervention).

Represents the pre-PBCP status quo: workloads run exactly as submitted.
No right-sizing, no policy checks, no simulation.
CPS is always 0 — the full potential cost is incurred.

Used as the lower bound in all experiment comparisons.
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


def evaluate(intent: dict[str, Any]) -> SimulationResult:
    """
    Passthrough: accept the workload exactly as submitted.
    No changes to node count, no cost prevention.
    """
    wtype    = intent.get("workload_type", "adhoc")
    cloud    = intent.get("cloud_provider", "aws")
    instance = intent.get("instance_type",
                           INTENT_CATALOG[wtype].default_instance.get(cloud, "m5.xlarge"))
    nodes    = int(intent.get("node_count", 4))
    duration = float(intent.get("expected_duration_hours", 4.0))
    use_spot = bool(intent.get("use_spot", False))

    cost = _cost_model.compute_cost(cloud, instance, nodes, duration, use_spot)

    return SimulationResult(
        intent_id=intent.get("intent_id", "unknown"),
        workload_type=wtype,
        cloud=cloud,
        instance_type=instance,
        submitted_nodes=nodes,
        optimal_nodes=nodes,        # no change
        predicted_utilization=0.0,  # not estimated
        potential_cost_usd=cost,
        right_sized_cost_usd=cost,  # no right-sizing
        prevented_cost_usd=0.0,     # nothing prevented
        intervention="PASS",
        stage="pre_provision",
        ev_block=0.0,
        ev_auto_correct=0.0,
    )


def evaluate_batch(intents: list[dict[str, Any]]) -> list[SimulationResult]:
    return [evaluate(i) for i in intents]