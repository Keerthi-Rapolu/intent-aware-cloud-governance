from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .workload_intent import WorkloadType


@dataclass
class IntentProfile:
    expected_utilization: float          # mean CPU utilization for healthy runs
    duration_range: tuple[float, float]  # (min_hours, max_hours)
    optimal_node_range: tuple[int, int]  # (min_nodes, max_nodes)
    spot_eligible: bool
    auto_shutdown_hours: Optional[float] # None = streaming
    latency: str
    default_instance: dict[str, str]     # {cloud: instance_type}


# Values mirror PROFILES in data/generate_dataset.py so simulation priors match
# generated data exactly.
INTENT_CATALOG: dict[str, IntentProfile] = {
    "etl": IntentProfile(
        expected_utilization=0.65,
        duration_range=(2.0, 8.0),
        optimal_node_range=(4, 8),
        spot_eligible=True,
        auto_shutdown_hours=4.0,
        latency="batch_ok",
        default_instance={"aws": "m5.xlarge", "azure": "Standard_D4s_v3", "gcp": "n2-standard-4"},
    ),
    "adhoc": IntentProfile(
        expected_utilization=0.50,
        duration_range=(0.5, 3.0),
        optimal_node_range=(1, 5),
        spot_eligible=True,
        auto_shutdown_hours=2.0,
        latency="interactive",
        default_instance={"aws": "m5.xlarge", "azure": "Standard_D4s_v3", "gcp": "n2-standard-4"},
    ),
    "ml_training": IntentProfile(
        expected_utilization=0.75,
        duration_range=(4.0, 24.0),
        optimal_node_range=(1, 4),
        spot_eligible=False,
        auto_shutdown_hours=24.0,
        latency="batch_ok",
        default_instance={"aws": "p3.2xlarge", "azure": "Standard_NC6", "gcp": "a2-highgpu-1g"},
    ),
    "llm_pipeline": IntentProfile(
        expected_utilization=0.57,
        duration_range=(1.0, 6.0),
        optimal_node_range=(2, 4),
        spot_eligible=False,
        auto_shutdown_hours=6.0,
        latency="interactive",
        default_instance={"aws": "m5.2xlarge", "azure": "Standard_D8s_v3", "gcp": "n2-standard-8"},
    ),
    "batch": IntentProfile(
        expected_utilization=0.71,
        duration_range=(4.0, 12.0),
        optimal_node_range=(4, 12),
        spot_eligible=True,
        auto_shutdown_hours=12.0,
        latency="batch_ok",
        default_instance={"aws": "m5.4xlarge", "azure": "Standard_D8s_v3", "gcp": "n2-standard-8"},
    ),
    "streaming": IntentProfile(
        expected_utilization=0.67,
        duration_range=(24.0, 168.0),
        optimal_node_range=(2, 6),
        spot_eligible=False,
        auto_shutdown_hours=None,
        latency="real_time",
        default_instance={"aws": "c5.xlarge", "azure": "Standard_D4s_v3", "gcp": "n2-standard-4"},
    ),
}


def get_profile(workload_type: str) -> IntentProfile:
    try:
        return INTENT_CATALOG[workload_type]
    except KeyError:
        raise ValueError(f"Unknown workload type: {workload_type!r}")