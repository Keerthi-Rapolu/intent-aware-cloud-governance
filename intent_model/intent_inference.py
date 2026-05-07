from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .workload_intent import (
    InferredIntentFields, WorkloadType,
    DataVolumeEstimate, LatencySensitivity, RecurrenceSignal,
)
from .intent_catalog import INTENT_CATALOG

# ── Keyword maps ───────────────────────────────────────────────────────────────

_TYPE_KEYWORDS: dict[str, list[str]] = {
    "etl":          ["etl", "ingest", "transform", "extract", "batch transformation",
                     "data pipeline", "reconciliation", "parquet", "warehouse load",
                     "nightly load", "daily load", "data lake", "snowflake", "redshift",
                     "sales etl", "billing etl"],
    "adhoc":        ["ad-hoc", "adhoc", "exploratory", "one-off", "investigate",
                     "spot check", "temporary", "analysis", "campaign analysis",
                     "marketing analysis", "quick query", "exploration", "exploratory sql"],
    "ml_training":  ["train", "retrain", "fine-tune", "fine-tuning", "hyperparameter",
                     "model refit", "model training", "retraining", "feature engineering",
                     "spark ml", "xgboost", "sklearn", "pytorch training", "model fitting",
                     "churn model", "forecast model", "propensity"],
    "llm_pipeline": ["llm", "embedding", "rag", "vector", "prompt", "gpt", "openai",
                     "batch llm", "completion", "token", "vector search",
                     "semantic search", "summarization", "inference pipeline",
                     "rag pipeline", "customer support summary"],
    "batch":        ["batch scoring", "batch inference", "batch export", "overnight",
                     "aggregation job", "scoring", "enrichment pipeline",
                     "bulk processing", "nightly scoring", "periodic batch"],
    "streaming":    ["streaming", "real-time", "real time", "continuous", "live",
                     "event stream", "kafka", "cdc", "tumbling window",
                     "clickstream", "fraud monitoring", "realtime", "stream processing",
                     "aggregation pipeline"],
}

_PII_KEYWORDS = ["customer", "user", "payment", "pii", "personal", "ssn",
                 "credit card", "email", "phone", "address", "gdpr", "hipaa"]

_RECURRENCE_PATTERNS = [
    r"\b(weekly|daily|nightly|monthly|quarterly|hourly)\b",
    r"\brecurr(ing|ent)\b",
    r"\bschedul(ed|e)\b",
    r"\b(every|each)\s+(day|week|night|hour)\b",
]

# Deterministic numeric extraction: detect value + unit and convert to GB
_DATA_VOL_RE = re.compile(r'\b(\d+(?:\.\d+)?)\s*(pb|tb|gb|mb)\b', re.IGNORECASE)

_LATENCY_KEYWORDS: dict[str, list[str]] = {
    "real_time":   ["real-time", "real time", "live", "streaming", "continuous", "always-on"],
    "interactive": ["interactive", "ad-hoc", "adhoc", "exploratory"],
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
    """
    Deterministic numeric extraction: parse value + unit, convert to GB.
    Mapping: <100 GB → small, 100 GB–1 TB → medium, 1–10 TB → large, >10 TB → xl.
    3 TB correctly maps to 'large'; this fixes the prior regex that missed sub-4-digit TB values.
    """
    m = _DATA_VOL_RE.search(text)
    if not m:
        return "small"
    value, unit = float(m.group(1)), m.group(2).lower()
    gb = value * {"pb": 1_048_576, "tb": 1_024, "gb": 1, "mb": 1 / 1_024}[unit]
    if gb >= 10_240:
        return "xl"      # > 10 TB
    if gb >= 1_024:
        return "large"   # 1 TB – 10 TB
    if gb >= 100:
        return "medium"  # 100 GB – 1 TB
    return "small"       # < 100 GB


def _detect_latency(text: str) -> LatencySensitivity:
    lower = text.lower()
    for latency, keywords in _LATENCY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return latency  # type: ignore[return-value]
    return "batch_ok"


def _classify_type(text: str) -> tuple[WorkloadType, float]:
    """
    Deterministic keyword classifier — stage 1 of hybrid inference.
    Returns (predicted_type, confidence).
    High confidence (≥ 0.75) when two or more distinct signals match.
    Falls back to BERT when confidence is low (see _classify).
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
        return "adhoc", 0.52   # conservative default

    total = sum(scores.values())
    # High deterministic confidence when >= 2 keyword signals agree
    if best_score >= 2:
        confidence = round(min(0.75 + (best_score / total) * 0.20, 0.97), 3)
    else:
        confidence = round(min(0.52 + (best_score / total) * 0.40, 0.80), 3)

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
    Hybrid inference: deterministic keyword extraction → BERT (if checkpoint present).
    Deterministic result is preferred when confidence ≥ 0.75 (≥ 2 keyword signals).

    Usage:
        engine = IntentInferenceEngine()
        fields = engine.infer(
            "weekly customer churn model retraining on 3TB Spark ML dataset",
            declared_type="ml_training",
        )
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
        """
        Hybrid inference:
        1. Deterministic keyword extraction.
        2. If deterministic confidence is high (>= 0.75), return immediately.
        3. Otherwise attempt BERT; take BERT only if it is more confident by >= 0.10.
        """
        det_type, det_conf = _classify_type(description)

        if det_conf >= 0.75:
            return det_type, det_conf

        if self._bert is not None:
            try:
                result = self._bert(description[:512])[0]
                label: WorkloadType = result["label"]
                if label in INTENT_CATALOG:
                    bert_conf = float(result["score"])
                    if bert_conf >= det_conf + 0.10:
                        return label, round(bert_conf, 3)
            except Exception:
                pass

        return det_type, det_conf

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