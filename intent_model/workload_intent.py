from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

WorkloadType = Literal["etl", "adhoc", "ml_training", "llm_pipeline", "batch", "streaming"]
CloudProvider = Literal["aws", "azure", "gcp"]
Environment = Literal["prod", "staging", "dev", "sandbox"]
Priority = Literal["low", "medium", "high", "critical"]
DataSensitivity = Literal["none", "internal", "customer_pii", "regulated"]
LatencySensitivity = Literal["real_time", "interactive", "batch_ok"]
RecurrenceSignal = Literal["recurring", "one_time"]
DataVolumeEstimate = Literal["small", "medium", "large", "xl"]


@dataclass
class ResourceConfig:
    cloud_provider: CloudProvider
    instance_type: str
    node_count: int
    optimal_node_count: int
    use_spot: bool
    auto_shutdown_hours: Optional[float]   # None = streaming (no shutdown)
    storage_gb: float
    region: str
    vcpu_per_node: int = 0
    memory_gb_per_node: float = 0.0
    over_provision_factor: float = 1.0


@dataclass
class InferredIntentFields:
    workload_type_inferred: WorkloadType
    data_volume_estimate: DataVolumeEstimate
    latency_sensitivity: LatencySensitivity
    recurrence_signal: RecurrenceSignal
    pii_signal: bool
    data_sensitivity: DataSensitivity
    type_mismatch: bool
    type_mismatch_confidence: Optional[float]   # None when no mismatch
    inference_confidence: float
    # Team history (filled by IntentInferenceEngine when DB is available)
    team_median_duration_hours: Optional[float] = None
    team_p90_cost_usd: Optional[float] = None


@dataclass
class WorkloadIntent:
    intent_id: str
    workload_name: str
    description: str
    team: str
    workload_type: WorkloadType          # declared type
    environment: Environment
    priority: Priority
    expected_duration_hours: float
    frequency: str
    submitted_at: str
    resource_config: ResourceConfig
    inferred: InferredIntentFields
    token_budget: Optional[int] = None  # LLM pipelines only

    @property
    def is_spot_eligible(self) -> bool:
        return self.resource_config.use_spot

    @property
    def effective_workload_type(self) -> WorkloadType:
        """Use inferred type when mismatch is detected."""
        if self.inferred.type_mismatch:
            return self.inferred.workload_type_inferred
        return self.workload_type