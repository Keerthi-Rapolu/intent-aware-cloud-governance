from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "cost_config.yml"


class CloudCostModel:
    """
    Computes cloud run costs from cost_config.yml.
    Identical to CrossCloudNormalizer.compute_cost — kept here so
    simulation_engine has no dependency on cost_normalizer.
    """

    def __init__(self) -> None:
        with open(_CONFIG_PATH) as f:
            self._pricing: dict = yaml.safe_load(f)

    def hourly_rate(self, cloud: str, instance_type: str, use_spot: bool = False) -> float:
        specs = self._pricing[cloud][instance_type]
        od = float(specs["od_hourly"])
        if use_spot:
            return round(od * (1.0 - float(specs.get("spot_discount", 0.0))), 6)
        return od

    def compute_cost(
        self,
        cloud: str,
        instance_type: str,
        nodes: int,
        duration_hours: float,
        use_spot: bool = False,
    ) -> float:
        rate = self.hourly_rate(cloud, instance_type, use_spot)
        return round(nodes * rate * duration_hours, 4)

    def compute_cost_from_config(self, config: dict[str, Any], duration_hours: float) -> float:
        return self.compute_cost(
            cloud=config["cloud_provider"],
            instance_type=config["instance_type"],
            nodes=int(config["node_count"]),
            duration_hours=duration_hours,
            use_spot=bool(config.get("use_spot", False)),
        )