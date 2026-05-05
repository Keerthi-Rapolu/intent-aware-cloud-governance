from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "policy_config.yml"


@dataclass
class Policy:
    policy_id: str
    workload_type: str        # "*" means applies to all types
    condition: str
    threshold: float
    action: str               # REJECT | AUTO_CORRECT | SUGGEST
    description: str
    source: str               # builtin | learned | compliance
    confidence: float = 1.0


class PolicyRegistry:
    """
    In-memory policy store. Initialised from policy_config.yml.
    Supports add/remove/list for both built-in and learned policies.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        path = Path(config_path) if config_path else _CONFIG_PATH
        self._policies: dict[str, Policy] = {}
        self._load_builtins(path)

    def _load_builtins(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as f:
            data = yaml.safe_load(f)
        for p in data.get("policies", []):
            policy = Policy(
                policy_id=p["policy_id"],
                workload_type=p.get("workload_type", "*"),
                condition=p["condition"],
                threshold=float(p["threshold"]),
                action=p["action"],
                description=p.get("description", ""),
                source=p.get("source", "builtin"),
                confidence=float(p.get("confidence", 1.0)),
            )
            self._policies[policy.policy_id] = policy

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add(self, policy: Policy) -> None:
        self._policies[policy.policy_id] = policy

    def remove(self, policy_id: str) -> bool:
        return self._policies.pop(policy_id, None) is not None

    def get(self, policy_id: str) -> Optional[Policy]:
        return self._policies.get(policy_id)

    def list_all(self) -> list[Policy]:
        return list(self._policies.values())

    def list_for_type(self, workload_type: str) -> list[Policy]:
        return [p for p in self._policies.values()
                if p.workload_type in (workload_type, "*")]

    def __len__(self) -> int:
        return len(self._policies)