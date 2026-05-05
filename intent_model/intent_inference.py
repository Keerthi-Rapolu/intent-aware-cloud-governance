from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Any

from .workload_intent import (
    InferredIntentFields, WorkloadType,
    DataVolumeEstimate, LatencySensitivity, RecurrenceSignal,
)
from .intent_catalog import INTENT_CATALOG

# ── Keyword maps ───────────────────────────────────────────────────────────────

_TYPE_KEYWORDS: dict[str, list[str]] = {
    "etl":          ["etl", "pipeline", "ingest", "transform", "load", "extract",
                     "batch transformation", "data pipeline"],
    "adhoc":        ["ad-hoc", "adhoc", "exploratory", "quick", "one-off", "investigate",
                     "spot check", "interactive"],
    "ml_training":  ["train", "retrain", "fine-tune", "hyperparameter", "model refit",
                     "fit", "model training", "retraining"],
    "llm_pipeline": ["llm", "embedding", "rag", "vector", "prompt", "inference",
                     "batch llm", "completion", "token"],
    "batch":        ["batch scoring", "batch inference", "batch export", "overnight",
                     "aggregation job", "scoring", "reconciliation", "enrichment pipeline"],
    "streaming":    ["streaming", "real-time", "real time", "continuous", "live",
                     "event stream", "kafka", "cdc", "tumbling window"],
}

_PII_KEYWORDS = ["customer", "user", "payment", "pii", "personal", "ssn",
                 "credit card", "email", "phone", "address"]

_RECURRENCE_PATTERNS = [
    r"\b(weekly|daily|nightly|monthly|quarterly|hourly)\b",
    r"\brecurr(ing|ent)\b",
    r"\bschedul(ed|e)\b",
    r"\b(every|each)\s+(day|week|night|hour)\b",
]

_DATA_VOLUME_PATTERNS = {
    "xl":     [r"\b([5-9]\d{2}|[1-9]\d{3,})\s*[gt]b\b", r"\b[12]\s*tb\b"],
    "large":  [r"\b([1-9]\d{2})\s*[gt]b\b", r"\b5\d{2}\s*mb\b"],
    "medium": [r"\b[1-9]\d\s*gb\b", r"\b[1-9]\d{2}\s*mb\b"],
}

_LATENCY_KEYWORDS: dict[str, list[str]] = {
    "real_time":   ["real-time", "real time", "live", "streaming", "continuous", "always-on"],
    "interactive": ["interactive", "ad-hoc", "adhoc", "quick", "exploratory"],
}


# ── Regex helpers ──────────────────────────────────────────────────────────────

def _detect_recurrence(text: str) -> RecurrenceSignal:
    lower = text.lower()
    for pattern in _RECURRENCE_PATTERNS:
        if re.search(pattern, lower):
            return "recurring"
    return "one_time"


def _detect_pii(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _PII_KEYWORDS)


def _detect_data_volume(text: str) -> DataVolumeEstimate:
    lower = text.lower()
    for level in ("xl", "large", "medium"):
        for pattern in _DATA_VOLUME_PATTERNS[level]:
            if re.search(pattern, lower):
                return level  # type: ignore[return-value]
    return "small"


def _detect_latency(text: str) -> LatencySensitivity:
    lower = text.lower()
    for latency, keywords in _LATENCY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return latency  # type: ignore[return-value]
    return "batch_ok"


def _classify_type(text: str) -> tuple[WorkloadType, float]:
    """
    Keyword-based workload type classifier.
    Returns (predicted_type, confidence).
    Replace with fine-tuned DistilBERT checkpoint for paper results (Option A).
    """
    lower = text.lower()
    scores: dict[str, int] = {t: 0 for t in _TYPE_KEYWORDS}
    for wtype, keywords in _TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[wtype] += 1

    best_type = max(scores, key=lambda t: scores[t])
    best_score = scores[best_type]

    if best_score == 0:
        return "adhoc", 0.55   # safe default

    total = sum(scores.values())
    confidence = round(min(0.50 + (best_score / total) * 0.45, 0.98), 3)
    return best_type, confidence  # type: ignore[return-value]


def load_bert_classifier():
    """
    Load fine-tuned DistilBERT checkpoint if available.
    Falls back to keyword classifier when checkpoint is missing.
    Checkpoint path: intent_model/checkpoints/workload_type_classifier/
    """
    checkpoint = Path(__file__).parent / "checkpoints" / "workload_type_classifier"
    if not checkpoint.exists():
        return None
    try:
        from transformers import pipeline as hf_pipeline
        return hf_pipeline("text-classification", model=str(checkpoint))
    except Exception:
        return None


# ── Main engine ───────────────────────────────────────────────────────────────

class IntentInferenceEngine:
    """
    Extracts InferredIntentFields from a natural-language workload description.

    Usage:
        engine = IntentInferenceEngine()
        fields = engine.infer("weekly customer churn model retraining", declared_type="ml_training")
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path
        self._bert = load_bert_classifier()   # None when no checkpoint

    def infer(
        self,
        description: str,
        declared_type: str,
        team: Optional[str] = None,
    ) -> InferredIntentFields:
        inferred_type, confidence = self._classify(description, declared_type)
        type_mismatch = inferred_type != declared_type
        mismatch_conf = round(confidence, 3) if type_mismatch else None
        pii = _detect_pii(description)

        team_median, team_p90 = self._team_history(team, declared_type)

        return InferredIntentFields(
            workload_type_inferred=inferred_type,
            data_volume_estimate=_detect_data_volume(description),
            latency_sensitivity=_detect_latency(description),
            recurrence_signal=_detect_recurrence(description),
            pii_signal=pii,
            data_sensitivity="customer_pii" if pii else "internal",
            type_mismatch=type_mismatch,
            type_mismatch_confidence=mismatch_conf,
            inference_confidence=confidence,
            team_median_duration_hours=team_median,
            team_p90_cost_usd=team_p90,
        )

    def _classify(self, description: str, declared_type: str) -> tuple[WorkloadType, float]:
        if self._bert is not None:
            try:
                result = self._bert(description[:512])[0]
                label: WorkloadType = result["label"]
                if label in INTENT_CATALOG:
                    return label, float(result["score"])
            except Exception:
                pass
        return _classify_type(description)

    def _team_history(
        self, team: Optional[str], workload_type: str
    ) -> tuple[Optional[float], Optional[float]]:
        if team is None or self._db_path is None:
            return None, None
        try:
            import duckdb
            con = duckdb.connect(self._db_path, read_only=True)
            row = con.execute("""
                SELECT
                    MEDIAN(rm.actual_duration_hours) AS median_dur,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY cr.actual_cost_usd) AS p90_cost
                FROM runtime_metrics rm
                JOIN workload_intent wi ON rm.intent_id = wi.intent_id
                JOIN cost_records cr ON rm.run_id = cr.run_id
                WHERE wi.team = ? AND wi.workload_type = ?
                LIMIT 30
            """, [team, workload_type]).fetchone()
            con.close()
            if row and row[0] is not None:
                return round(float(row[0]), 2), round(float(row[1]), 2) if row[1] else None
        except Exception:
            pass
        return None, None