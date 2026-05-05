from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "cost_config.yml"


def _load_pricing() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


@dataclass
class UnifiedCostRecord:
    cloud: str
    instance_type: str
    nodes: int
    vcpu_total: int
    memory_gb_total: float
    od_hourly_rate: float      # per node
    spot_hourly_rate: float    # per node
    duration_hours: float
    use_spot: bool
    total_cost: float

    @property
    def effective_hourly_rate(self) -> float:
        return self.spot_hourly_rate if self.use_spot else self.od_hourly_rate

    @property
    def cost_per_hour(self) -> float:
        return self.nodes * self.effective_hourly_rate


class CrossCloudNormalizer:
    def __init__(self) -> None:
        self._pricing = _load_pricing()

    def _specs(self, cloud: str, instance_type: str) -> dict:
        try:
            return self._pricing[cloud][instance_type]
        except KeyError:
            raise ValueError(f"Unknown instance {cloud}/{instance_type}")

    def normalize(self, config: dict[str, Any]) -> UnifiedCostRecord:
        """Turn a provisioned_config row dict into a UnifiedCostRecord."""
        cloud = config["cloud_provider"]
        instance = config["instance_type"]
        specs = self._specs(cloud, instance)
        nodes = int(config["node_count"])
        duration = float(config.get("actual_duration_hours", config.get("expected_duration_hours", 1.0)))
        use_spot = bool(config.get("use_spot", False))
        od_rate = float(specs["od_hourly"])
        spot_rate = round(od_rate * (1.0 - float(specs.get("spot_discount", 0.0))), 6)
        effective_rate = spot_rate if use_spot else od_rate
        total_cost = round(nodes * effective_rate * duration, 4)
        return UnifiedCostRecord(
            cloud=cloud,
            instance_type=instance,
            nodes=nodes,
            vcpu_total=specs["vcpu"] * nodes,
            memory_gb_total=float(specs["memory_gb"]) * nodes,
            od_hourly_rate=od_rate,
            spot_hourly_rate=spot_rate,
            duration_hours=duration,
            use_spot=use_spot,
            total_cost=total_cost,
        )

    def compute_cost(self, cloud: str, instance_type: str, nodes: int,
                     duration_hours: float, use_spot: bool = False) -> float:
        """Direct cost calculation — used by CloudCostModel."""
        specs = self._specs(cloud, instance_type)
        od = float(specs["od_hourly"])
        if use_spot:
            rate = round(od * (1.0 - float(specs.get("spot_discount", 0.0))), 6)
        else:
            rate = od
        return round(nodes * rate * duration_hours, 4)

    def cost_comparison(self, workload_type: str, nodes: int,
                        duration_hours: float, use_spot: bool = False) -> dict[str, float]:
        """Return cost for each cloud for the default instance of a workload type."""
        from intent_model.intent_catalog import INTENT_CATALOG
        profile = INTENT_CATALOG[workload_type]
        result: dict[str, float] = {}
        for cloud in ("aws", "azure", "gcp"):
            instance = profile.default_instance[cloud]
            result[cloud] = self.compute_cost(cloud, instance, nodes, duration_hours, use_spot)
        return result