from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .policy_registry import Policy, PolicyRegistry

_MIN_CONFIDENCE = 0.80
_ROLLING_DAYS   = 90
_MIN_SAMPLES    = 20


@dataclass
class LearningCandidate:
    workload_type: str
    condition: str
    threshold: float
    confidence: float
    sample_count: int
    description: str


class PolicyLearner:
    """
    Analyses historical runtime_metrics to discover learned policies.
    Emits a new Policy when:
      - a condition occurs in ≥ 80% of runs for a workload type over 90 days
      - the sample count is ≥ MIN_SAMPLES
    """

    def __init__(self, registry: PolicyRegistry) -> None:
        self._registry = registry

    def analyze_runs(self, db_path: str) -> list[Policy]:
        """
        Query the DB for patterns that exceed the confidence threshold.
        Returns newly-created learned policies (also adds them to the registry).
        """
        try:
            import duckdb
            con = duckdb.connect(db_path, read_only=True)
            learned = self._find_candidates(con)
            con.close()
        except Exception:
            return []

        new_policies: list[Policy] = []
        for cand in learned:
            policy_id = f"learned_{cand.workload_type}_{cand.condition}"
            if self._registry.get(policy_id) is not None:
                continue   # already registered
            p = Policy(
                policy_id=policy_id,
                workload_type=cand.workload_type,
                condition=cand.condition,
                threshold=round(cand.threshold, 2),
                action="SUGGEST",
                description=cand.description,
                source="learned",
                confidence=round(cand.confidence, 3),
            )
            self._registry.add(p)
            new_policies.append(p)
        return new_policies

    def _find_candidates(self, con) -> list[LearningCandidate]:
        candidates: list[LearningCandidate] = []

        # Pattern 1: workload types with consistently low CPU (< 0.40)
        # → candidate for a max-node or auto_shutdown policy
        rows = con.execute("""
            SELECT
                wi.workload_type,
                COUNT(*) AS n,
                AVG(rm.cpu_utilization_avg) AS avg_cpu,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY rm.cpu_utilization_avg) AS p90_cpu
            FROM runtime_metrics rm
            JOIN workload_intent wi ON rm.intent_id = wi.intent_id
            WHERE rm.run_start >= (CURRENT_TIMESTAMP - INTERVAL 90 DAY)
              AND rm.cpu_utilization_avg IS NOT NULL
            GROUP BY wi.workload_type
            HAVING COUNT(*) >= ?
        """, [_MIN_SAMPLES]).fetchall()

        for wtype, n, avg_cpu, p90_cpu in rows:
            if avg_cpu is not None and avg_cpu < 0.40:
                confidence = min(1.0, (0.40 - avg_cpu) / 0.40 + 0.60)
                if confidence >= _MIN_CONFIDENCE:
                    candidates.append(LearningCandidate(
                        workload_type=wtype,
                        condition="node_count_exceeds",
                        threshold=4.0,
                        confidence=confidence,
                        sample_count=int(n),
                        description=f"Learned: {wtype} jobs avg {avg_cpu:.0%} CPU — "
                                    f"cap at 4 nodes (confidence={confidence:.2f})",
                    ))

        return candidates