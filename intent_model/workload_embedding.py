from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np

from .intent_catalog import INTENT_CATALOG, IntentProfile

_WORKLOAD_TYPES = ["etl", "adhoc", "ml_training", "llm_pipeline", "batch", "streaming"]
_CLOUDS         = ["aws", "azure", "gcp"]
_ENVS           = ["prod", "staging", "dev", "sandbox"]
_PRIORITIES     = ["low", "medium", "high", "critical"]
_LATENCIES      = ["batch_ok", "interactive", "real_time"]

_EMBED_DIM = 64
_COLD_START_DISTANCE_THRESHOLD = 1.5   # L2 distance above which we fall back to catalog


@dataclass
class WorkloadSpecificPrior:
    expected_utilization: float
    expected_duration_hours: float
    expected_cost_usd: float
    optimal_nodes: int
    confidence: float          # 0–1; low = cold-start fallback used
    source: str                # "knn" | "catalog"


def _onehot(value: str, categories: list[str]) -> list[float]:
    return [1.0 if value == c else 0.0 for c in categories]


def encode_intent(intent: dict[str, Any]) -> np.ndarray:
    """
    Encode a workload intent dict into a float[64] feature vector.

    Numeric features (normalised):
      expected_duration_hours / 24, node_count / 20, storage_gb / 2000

    Categorical one-hot:
      workload_type (6), cloud_provider (3), environment (4),
      priority (4), latency_sensitivity (3)

    Derived:
      recurrence (1), pii_signal (1), spot (1), over_provision_factor / 3
    """
    features: list[float] = []

    # Numeric (4)
    features.append(float(intent.get("expected_duration_hours", 4.0)) / 24.0)
    features.append(float(intent.get("node_count", 4)) / 20.0)
    features.append(float(intent.get("storage_gb", 100.0)) / 2000.0)
    features.append(float(intent.get("over_provision_factor", 1.0)) / 3.0)

    # Categorical one-hot (6 + 3 + 4 + 4 + 3 = 20)
    features += _onehot(intent.get("workload_type", "etl"), _WORKLOAD_TYPES)
    features += _onehot(intent.get("cloud_provider", "aws"), _CLOUDS)
    features += _onehot(intent.get("environment", "prod"), _ENVS)
    features += _onehot(intent.get("priority", "medium"), _PRIORITIES)
    features += _onehot(intent.get("latency_sensitivity", "batch_ok"), _LATENCIES)

    # Binary flags (3)
    features.append(1.0 if intent.get("recurrence_signal") == "recurring" else 0.0)
    features.append(1.0 if intent.get("pii_signal", False) else 0.0)
    features.append(1.0 if intent.get("use_spot", False) else 0.0)

    # Total so far: 4 + 20 + 3 = 27
    # Pad to _EMBED_DIM with zeros
    features += [0.0] * (_EMBED_DIM - len(features))
    return np.array(features[:_EMBED_DIM], dtype=np.float32)


def _catalog_prior(workload_type: str, config: dict[str, Any]) -> WorkloadSpecificPrior:
    profile: IntentProfile = INTENT_CATALOG.get(workload_type, INTENT_CATALOG["adhoc"])
    od_rate = 0.192   # m5.xlarge default if pricing lookup not available
    try:
        from cost_normalizer.normalizer import CrossCloudNormalizer
        norm = CrossCloudNormalizer()
        cloud = config.get("cloud_provider", "aws")
        instance = profile.default_instance[cloud]
        od_rate = norm._specs(cloud, instance)["od_hourly"]
    except Exception:
        pass

    mid_duration = sum(profile.duration_range) / 2.0
    mid_nodes = sum(profile.optimal_node_range) // 2
    return WorkloadSpecificPrior(
        expected_utilization=profile.expected_utilization,
        expected_duration_hours=mid_duration,
        expected_cost_usd=round(od_rate * mid_nodes * mid_duration, 2),
        optimal_nodes=mid_nodes,
        confidence=0.50,
        source="catalog",
    )


class WorkloadEmbeddingModel:
    """
    FAISS KNN model that retrieves workload-specific priors from historical runs.

    build_index() must be called once (or load_index() if a saved index exists)
    before get_prior() works.
    """

    def __init__(self) -> None:
        self._index = None
        self._metadata: list[dict] = []   # parallel to index rows

    # ── Index construction ─────────────────────────────────────────────────────

    def build_index(self, db_path: str) -> int:
        """
        Build FAISS index from workload_intent + runtime_metrics in the DB.
        Returns the number of vectors indexed.
        """
        import faiss
        import duckdb

        con = duckdb.connect(db_path, read_only=True)
        rows = con.execute("""
            SELECT
                wi.intent_id,
                wi.workload_type,
                wi.expected_duration_hours,
                wi.environment,
                wi.priority,
                wi.frequency,
                wi.pii_signal,
                pc.cloud_provider,
                pc.instance_type,
                pc.node_count,
                pc.optimal_node_count,
                pc.use_spot,
                pc.storage_gb,
                pc.over_provision_factor,
                AVG(rm.cpu_utilization_avg)       AS avg_cpu,
                AVG(rm.actual_duration_hours)     AS avg_duration,
                AVG(cr.actual_cost_usd)           AS avg_cost
            FROM workload_intent wi
            JOIN provisioned_config pc ON wi.intent_id = pc.intent_id
            JOIN runtime_metrics rm    ON wi.intent_id = rm.intent_id
            JOIN cost_records cr       ON rm.run_id    = cr.run_id
            GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14
        """).fetchall()
        con.close()

        cols = ["intent_id", "workload_type", "expected_duration_hours", "environment",
                "priority", "frequency", "pii_signal", "cloud_provider", "instance_type",
                "node_count", "optimal_node_count", "use_spot", "storage_gb",
                "over_provision_factor", "avg_cpu", "avg_duration", "avg_cost"]

        vectors: list[np.ndarray] = []
        self._metadata = []

        for row in rows:
            d = dict(zip(cols, row))
            d["recurrence_signal"] = "recurring" if d["frequency"] in ("daily","weekly","nightly","continuous") else "one_time"
            d["latency_sensitivity"] = INTENT_CATALOG.get(d["workload_type"], INTENT_CATALOG["adhoc"]).latency
            vec = encode_intent(d)
            vectors.append(vec)
            self._metadata.append(d)

        if not vectors:
            return 0

        matrix = np.stack(vectors).astype(np.float32)
        self._index = faiss.IndexFlatL2(_EMBED_DIM)
        self._index.add(matrix)
        return len(vectors)

    def save_index(self, path: str) -> None:
        import faiss, pickle
        faiss.write_index(self._index, path + ".faiss")
        with open(path + ".meta.pkl", "wb") as f:
            pickle.dump(self._metadata, f)

    def load_index(self, path: str) -> None:
        import faiss, pickle
        self._index = faiss.read_index(path + ".faiss")
        with open(path + ".meta.pkl", "rb") as f:
            self._metadata = pickle.load(f)

    # ── Inference ──────────────────────────────────────────────────────────────

    def get_prior(self, intent: dict[str, Any], k: int = 10) -> WorkloadSpecificPrior:
        """
        Retrieve K nearest neighbours and return aggregated prior.
        Falls back to INTENT_CATALOG when index is empty or distance is large.
        """
        workload_type = intent.get("workload_type", "adhoc")

        if self._index is None or self._index.ntotal == 0:
            return _catalog_prior(workload_type, intent)

        vec = encode_intent(intent).reshape(1, -1)
        k_actual = min(k, self._index.ntotal)
        distances, indices = self._index.search(vec, k_actual)

        min_dist = float(distances[0][0])
        if min_dist > _COLD_START_DISTANCE_THRESHOLD:
            return _catalog_prior(workload_type, intent)

        neighbours = [self._metadata[i] for i in indices[0] if i >= 0]
        if not neighbours:
            return _catalog_prior(workload_type, intent)

        avg_util     = float(np.mean([n["avg_cpu"]      for n in neighbours]))
        avg_duration = float(np.mean([n["avg_duration"] for n in neighbours]))
        avg_cost     = float(np.mean([n["avg_cost"]     for n in neighbours]))
        avg_nodes    = int(round(np.mean([n["optimal_node_count"] for n in neighbours])))

        # Confidence: inverse of mean distance, clipped to [0.5, 0.95]
        confidence = float(np.clip(1.0 / (1.0 + min_dist), 0.50, 0.95))

        return WorkloadSpecificPrior(
            expected_utilization=round(avg_util, 4),
            expected_duration_hours=round(avg_duration, 2),
            expected_cost_usd=round(avg_cost, 2),
            optimal_nodes=avg_nodes,
            confidence=round(confidence, 3),
            source="knn",
        )