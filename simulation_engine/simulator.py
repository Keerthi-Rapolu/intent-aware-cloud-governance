from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from .cost_model import CloudCostModel
from .correction_cost_model import CostOfCorrectionModel
from intent_model.intent_catalog import INTENT_CATALOG


@dataclass
class SimulationResult:
    intent_id: str
    workload_type: str
    cloud: str
    instance_type: str

    # Node counts
    submitted_nodes: int
    optimal_nodes: int

    # Utilization
    predicted_utilization: float   # fraction 0–1

    # Costs
    potential_cost_usd: float      # cost if we do nothing
    right_sized_cost_usd: float    # cost at optimal_nodes
    prevented_cost_usd: float      # potential - right_sized (0 if PASS/SUGGEST)

    # Decision
    intervention: str              # BLOCK | AUTO_CORRECT | SUGGEST | PASS
    stage: str                     # pre_provision | runtime | ai_workload

    # EV scores (for logging / paper tables)
    ev_block: float
    ev_auto_correct: float

    @property
    def cps(self) -> float:
        if self.potential_cost_usd <= 0:
            return 0.0
        return round(self.prevented_cost_usd / self.potential_cost_usd, 4)

    @property
    def waste_fraction(self) -> float:
        return round(1.0 - self.predicted_utilization, 4)


class PreExecutionSimulator:
    """
    Pre-provision simulation: given a WorkloadIntent (or equivalent dict),
    predict utilization, compute costs, and recommend an intervention.

    simulate() runs in < 10 ms; p99 < 2 s over 100 parallel calls.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._cost_model  = CloudCostModel()
        self._ev_model    = CostOfCorrectionModel()
        self._db_path     = db_path
        self._embed_model = None   # lazy-loaded on first KNN request

    # ── Public API ─────────────────────────────────────────────────────────────

    def simulate(self, intent: dict[str, Any]) -> SimulationResult:
        """
        Full pre-provision pipeline:
          1. Get workload-specific prior (KNN or catalog fallback)
          2. Right-size: optimal_nodes = ceil(submitted × predicted_util / 0.70)
          3. Compute costs
          4. Run EV decision model
        """
        wtype       = intent.get("workload_type", "adhoc")
        cloud       = intent.get("cloud_provider", "aws")
        instance    = intent.get("instance_type",
                                  INTENT_CATALOG[wtype].default_instance.get(cloud, "m5.xlarge"))
        nodes       = int(intent.get("node_count", 4))
        duration    = float(intent.get("expected_duration_hours", 4.0))
        priority    = intent.get("priority", "medium")
        use_spot    = bool(intent.get("use_spot", False))
        intent_id   = intent.get("intent_id", "unknown")

        prior = self._get_prior(intent)
        predicted_util = prior.expected_utilization

        optimal_nodes = max(1, math.ceil(nodes * predicted_util / 0.70))
        optimal_nodes = min(optimal_nodes, nodes)   # never increase

        potential_cost    = self._cost_model.compute_cost(cloud, instance, nodes,    duration, use_spot)
        right_sized_cost  = self._cost_model.compute_cost(cloud, instance, optimal_nodes, duration, use_spot)
        waste_cost        = potential_cost - right_sized_cost

        ev_b  = self._ev_model.ev_block(wtype, priority, duration, waste_cost)
        ev_ac = self._ev_model.ev_auto_correct(wtype, priority, duration, waste_cost, right_sized_cost)

        action, prevented = self._ev_model.decide(wtype, priority, duration, waste_cost, right_sized_cost)

        return SimulationResult(
            intent_id=intent_id,
            workload_type=wtype,
            cloud=cloud,
            instance_type=instance,
            submitted_nodes=nodes,
            optimal_nodes=optimal_nodes,
            predicted_utilization=round(predicted_util, 4),
            potential_cost_usd=round(potential_cost, 4),
            right_sized_cost_usd=round(right_sized_cost, 4),
            prevented_cost_usd=round(prevented, 4),
            intervention=action,
            stage="pre_provision",
            ev_block=ev_b,
            ev_auto_correct=ev_ac,
        )

    # ── KNN prior (lazy) ───────────────────────────────────────────────────────

    def _get_prior(self, intent: dict[str, Any]):
        from intent_model.workload_embedding import WorkloadSpecificPrior, _catalog_prior
        if self._db_path is None:
            return _catalog_prior(intent.get("workload_type", "adhoc"), intent)
        if self._embed_model is None:
            from intent_model.workload_embedding import WorkloadEmbeddingModel
            self._embed_model = WorkloadEmbeddingModel()
            self._embed_model.build_index(self._db_path)
        return self._embed_model.get_prior(intent)