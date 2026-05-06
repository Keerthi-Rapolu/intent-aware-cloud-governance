"""
Prevention Feedback Loop — anomaly_rca/prevention_feedback.py

Closes the measurement→prevention loop:
  low-IFS IFSRecords → AnomalyRecord → PolicySuggestion → PolicyRegistry

Design doc §5.9:
  "When a runtime anomaly is flagged, the system generates a PolicySuggestion
   and submits it to the policy registry."

Interface contract (design doc §9):
  PolicySuggestion  (S) → policy_engine/policy_registry.py (K)
  S writes; K consumes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import uuid

from policy_engine.policy_registry import Policy, PolicyRegistry

# IBD threshold: IFS below this → workload is flagged for intent-behavior divergence
IBD_THRESHOLD = 0.65

# Minimum confidence to add a feedback-derived policy
MIN_CONFIDENCE = 0.60

# Maps IFS category to (condition, threshold, action) for policy generation
_CATEGORY_TO_POLICY = {
    "over_provisioned": {
        "condition": "over_provision_factor",
        "threshold": 1.5,
        "action":    "AUTO_CORRECT",
    },
    "idle_cluster": {
        "condition": "idle_time_hours",
        "threshold": 1.0,
        "action":    "AUTO_CORRECT",
    },
    "runaway_job": {
        "condition": "actual_vs_expected_duration_ratio",
        "threshold": 2.0,
        "action":    "SUGGEST",
    },
    "type_mismatch": {
        "condition": "type_mismatch_confidence",
        "threshold": 0.80,
        "action":    "SUGGEST",
    },
    "token_waste": {
        "condition": "token_budget",
        "threshold": 0.0,
        "action":    "SUGGEST",
    },
}


@dataclass
class AnomalyRecord:
    """Produced for every IFSRecord where IFS < IBD_THRESHOLD."""
    anomaly_id: str
    intent_id: str
    run_id: str
    ifs: float
    ifs_category: str               # minor | significant | severe
    is_ibd_flagged: bool            # IFS < IBD_THRESHOLD
    workload_type: str
    root_cause_category: str        # over_provisioned | idle_cluster | runaway_job | type_mismatch | token_waste | unknown
    estimated_cost_impact: float    # derived from IFS severity
    prevention_feedback_generated: bool = False


def _infer_root_cause(ifs_rec) -> str:
    """
    Infer root cause category from IFSRecord sub-scores.
    Uses the lowest sub-score as the primary signal.
    """
    scores = {
        "type_mismatch":  ifs_rec.type_alignment,
        "over_provisioned": ifs_rec.resource_alignment,
        "runaway_job":    ifs_rec.duration_alignment,
        "idle_cluster":   ifs_rec.util_alignment,
    }
    # Return the category with the lowest sub-score (most deviant)
    worst = min(scores, key=lambda k: scores[k])
    # Only flag as that category if the sub-score is meaningfully low
    if scores[worst] < 0.50:
        return worst
    return "unknown"


def _estimate_cost_impact(ifs: float, potential_cost: float = 100.0) -> float:
    """
    Estimate cost impact from IFS severity.
    Severe misalignment (IFS < 0.50) → up to 50% waste; significant → up to 25%.
    """
    if ifs < 0.50:
        waste_fraction = 0.50
    elif ifs < 0.70:
        waste_fraction = 0.25
    else:
        waste_fraction = 0.10
    return round(potential_cost * waste_fraction, 2)


class AnomalyPreventionFeedback:
    """
    Processes batches of IFSRecords, flags IBD workloads, and generates
    PolicySuggestions for uncovered anomaly patterns.

    Closes the loop: runtime anomalies improve pre-execution prevention.

    Usage:
        feedback = AnomalyPreventionFeedback(registry)
        new_policies = feedback.process(ifs_records, workload_type_map)
        # new_policies are already added to registry
    """

    def __init__(self, registry: PolicyRegistry) -> None:
        self._registry = registry

    def process(
        self,
        ifs_records: list,                          # list[IFSRecord]
        workload_type_map: dict[str, str],          # intent_id → workload_type
        potential_cost_map: dict[str, float] | None = None,
    ) -> list[AnomalyRecord]:
        """
        Process IFSRecords, create AnomalyRecords for IBD workloads, and
        generate PolicySuggestions for uncovered scenarios.

        Returns all AnomalyRecords (including those without feedback generated).
        Newly suggested policies are added to the registry.
        """
        anomaly_records: list[AnomalyRecord] = []
        pattern_counts: dict[tuple[str, str], int] = {}

        for rec in ifs_records:
            if rec.ifs >= IBD_THRESHOLD:
                continue   # well-aligned; skip

            wtype       = workload_type_map.get(rec.intent_id, "*")
            root_cause  = _infer_root_cause(rec)
            pot_cost    = (potential_cost_map or {}).get(rec.intent_id, 100.0)
            cost_impact = _estimate_cost_impact(rec.ifs, pot_cost)

            anomaly = AnomalyRecord(
                anomaly_id=str(uuid.uuid4()),
                intent_id=rec.intent_id,
                run_id=rec.run_id,
                ifs=rec.ifs,
                ifs_category=rec.ifs_category,
                is_ibd_flagged=True,
                workload_type=wtype,
                root_cause_category=root_cause,
                estimated_cost_impact=cost_impact,
                prevention_feedback_generated=False,
            )
            anomaly_records.append(anomaly)

            if root_cause != "unknown":
                pattern_counts[(wtype, root_cause)] = \
                    pattern_counts.get((wtype, root_cause), 0) + 1

        # Generate policies for patterns seen >= 3 times with confidence >= MIN_CONFIDENCE
        for (wtype, root_cause), count in pattern_counts.items():
            confidence = min(count / 10.0, 0.95)
            if confidence < MIN_CONFIDENCE:
                continue

            spec    = _CATEGORY_TO_POLICY.get(root_cause)
            if spec is None:
                continue

            pol_id  = f"feedback_{wtype}_{root_cause}"
            # Skip if policy already exists
            if self._registry.get(pol_id) is not None:
                continue

            policy = Policy(
                policy_id=pol_id,
                workload_type=wtype,
                condition=spec["condition"],
                threshold=spec["threshold"],
                action=spec["action"],
                description=(
                    f"IBD feedback: {count} {root_cause} anomalies detected for "
                    f"{wtype} workloads (IFS < {IBD_THRESHOLD})"
                ),
                source="learned",
                confidence=round(confidence, 4),
            )
            self._registry.add(policy)

            # Mark anomaly records for this pattern as having generated feedback
            for anomaly in anomaly_records:
                if (anomaly.workload_type == wtype and
                        anomaly.root_cause_category == root_cause):
                    anomaly.prevention_feedback_generated = True

        return anomaly_records

    def summary(self, anomaly_records: list[AnomalyRecord]) -> dict:
        """Aggregate statistics over a batch of AnomalyRecords."""
        if not anomaly_records:
            return {"n_ibd": 0, "n_feedback_generated": 0,
                    "mean_ifs": 0.0, "total_cost_impact": 0.0}
        return {
            "n_ibd":                len(anomaly_records),
            "n_feedback_generated": sum(1 for a in anomaly_records
                                        if a.prevention_feedback_generated),
            "mean_ifs":             round(sum(a.ifs for a in anomaly_records)
                                          / len(anomaly_records), 4),
            "total_cost_impact":    round(sum(a.estimated_cost_impact
                                              for a in anomaly_records), 2),
            "by_root_cause":        {
                rc: sum(1 for a in anomaly_records if a.root_cause_category == rc)
                for rc in {a.root_cause_category for a in anomaly_records}
            },
        }
