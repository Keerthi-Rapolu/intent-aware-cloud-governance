"""
Intent-Fit Score (IFS) calculator.

IFS measures how well a workload's declared intent matched what it actually did.
Scale: 0–1 (1 = perfect alignment, 0 = severe mismatch).

Categories:
  well_aligned  IFS >= 0.85
  minor         IFS >= 0.70
  significant   IFS >= 0.50
  severe        IFS <  0.50

NOTE: This is a reference implementation matching the formula specified in
SREEJA_TASKS.md. Sreeja's production implementation replaces this file —
the IFSRecord dataclass and IFSCalculator interface must be preserved exactly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IFSRecord:
    intent_id: str
    run_id: str
    ifs: float                  # 0–1; 1 = perfect alignment
    ifs_category: str           # well_aligned | minor | significant | severe
    type_alignment: float       # sub-score: declared vs. inferred workload type
    util_alignment: float       # sub-score: predicted vs. actual CPU utilisation
    duration_alignment: float   # sub-score: expected vs. actual duration
    resource_alignment: float   # sub-score: over-provision factor
    detail: str


def _category(ifs: float) -> str:
    if ifs >= 0.85:
        return "well_aligned"
    if ifs >= 0.70:
        return "minor"
    if ifs >= 0.50:
        return "significant"
    return "severe"


class IFSCalculator:
    """
    Stateless IFS calculator.  Call compute_ifs() with raw metric values.

    For LLM pipeline workloads, pass token_budget_declared and token_usage_actual
    to activate the token-waste sub-score.
    """

    @staticmethod
    def compute_ifs(
        intent_id: str,
        run_id: str,
        # Type alignment
        type_mismatch: bool,
        type_mismatch_confidence: float,        # 0–1; only used when type_mismatch=True
        # Utilisation alignment
        predicted_utilization: float,
        actual_utilization: float,
        # Duration alignment
        expected_duration_hours: float,
        actual_duration_hours: float,
        # Resource alignment
        over_provision_factor: float,
        # LLM-specific (optional)
        token_budget_declared: float = 0.0,
        token_usage_actual: float = 0.0,
        is_llm_pipeline: bool = False,
    ) -> IFSRecord:

        # 1. Type alignment
        type_score = (1.0 - type_mismatch_confidence) if type_mismatch else 1.0
        type_score = max(0.0, min(1.0, type_score))

        # 2. Utilisation alignment
        p, a = predicted_utilization, actual_utilization
        util_score = 1.0 - abs(p - a) / max(p, a, 0.01)
        util_score = max(0.0, min(1.0, util_score))

        # 3. Duration alignment
        e, d = expected_duration_hours, actual_duration_hours
        dur_score = 1.0 - abs(e - d) / max(e, d, 0.01)
        dur_score = max(0.0, min(1.0, dur_score))

        # 4. Resource alignment
        opf = max(over_provision_factor, 1.0)
        resource_score = 1.0 / opf

        # 5. Token waste sub-score (LLM pipelines only)
        if is_llm_pipeline and token_budget_declared > 0:
            token_waste = token_usage_actual - token_budget_declared
            token_score = 1.0 if token_waste <= 0 else max(
                0.0, 1.0 - token_waste / token_budget_declared
            )
            # Replace resource sub-score with split: 10% resource, 10% token
            ifs = (
                0.35 * type_score
                + 0.25 * util_score
                + 0.20 * dur_score
                + 0.10 * resource_score
                + 0.10 * token_score
            )
        else:
            ifs = (
                0.35 * type_score
                + 0.25 * util_score
                + 0.20 * dur_score
                + 0.20 * resource_score
            )

        ifs = round(max(0.0, min(1.0, ifs)), 4)

        detail = (
            f"type={type_score:.2f} util={util_score:.2f} "
            f"dur={dur_score:.2f} res={resource_score:.2f}"
        )

        return IFSRecord(
            intent_id=intent_id,
            run_id=run_id,
            ifs=ifs,
            ifs_category=_category(ifs),
            type_alignment=round(type_score, 4),
            util_alignment=round(util_score, 4),
            duration_alignment=round(dur_score, 4),
            resource_alignment=round(resource_score, 4),
            detail=detail,
        )