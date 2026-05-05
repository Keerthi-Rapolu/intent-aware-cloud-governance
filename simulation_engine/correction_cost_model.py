from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "simulation_config.yml"


def _load_cfg() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


class CostOfCorrectionModel:
    """
    Decision-theoretic EV model for intervention choices.

    EV(BLOCK)       = waste_prevented - delay_cost - P(fail) × failure_cost
    EV(AUTO_CORRECT)= savings_vs_right_sized - correction_overhead - P(fail) × failure_cost
    EV(SUGGEST)     = small positive nudge (user-driven, low risk)

    All parameters from simulation_config.yml.
    """

    def __init__(self) -> None:
        cfg = _load_cfg()
        self._failure_cost: dict[str, float] = {k: float(v) for k, v in cfg["failure_cost"].items()}
        self._correction_failure_rates: dict[str, float] = {
            k: float(v) for k, v in cfg["correction_failure_rates"].items()
        }
        self._delay_block_per_hour: float = float(cfg["delay_cost_block_per_hour"])
        self._delay_auto_correct: float   = float(cfg["delay_cost_auto_correct"])

    def _p_failure(self, workload_type: str) -> float:
        return self._correction_failure_rates.get(workload_type, 0.05)

    def _fail_cost(self, priority: str) -> float:
        return self._failure_cost.get(priority, self._failure_cost["medium"])

    def ev_block(
        self,
        workload_type: str,
        priority: str,
        expected_duration_hours: float,
        waste_cost: float,
    ) -> float:
        """
        Expected value of blocking the submission entirely.
        Negative EV → do not block (too costly for high-priority jobs).
        """
        delay_cost    = self._delay_block_per_hour * expected_duration_hours
        p_fail        = self._p_failure(workload_type)
        fail_cost_val = self._fail_cost(priority)
        ev = waste_cost - delay_cost - p_fail * fail_cost_val
        return round(ev, 4)

    def ev_auto_correct(
        self,
        workload_type: str,
        priority: str,
        expected_duration_hours: float,
        waste_cost: float,
        right_sized_cost: float,
    ) -> float:
        """
        Expected value of automatically right-sizing the config before launch.
        waste_cost = potential_cost - right_sized_cost (the savings from right-sizing).
        right_sized_cost retained in signature for symmetry with decide().
        """
        savings       = waste_cost          # already = potential - right_sized
        overhead      = self._delay_auto_correct * expected_duration_hours
        p_fail        = self._p_failure(workload_type)
        fail_cost_val = self._fail_cost(priority)
        ev = savings - overhead - p_fail * fail_cost_val
        return round(ev, 4)

    def ev_suggest(self, waste_cost: float) -> float:
        """Suggest is always mildly positive — small fraction of potential savings."""
        return round(waste_cost * 0.10, 4)

    def decide(
        self,
        workload_type: str,
        priority: str,
        expected_duration_hours: float,
        waste_cost: float,
        right_sized_cost: float,
    ) -> tuple[str, float]:
        """
        Return (action, prevented_cost_estimate).
        Action is one of: BLOCK, AUTO_CORRECT, SUGGEST, PASS.
        """
        ev_b  = self.ev_block(workload_type, priority, expected_duration_hours, waste_cost)
        ev_ac = self.ev_auto_correct(workload_type, priority, expected_duration_hours,
                                     waste_cost, right_sized_cost)
        ev_s  = self.ev_suggest(waste_cost)

        if ev_b > ev_ac and ev_b > ev_s and ev_b > 0:
            return "BLOCK", round(waste_cost, 4)
        if ev_ac > ev_s and ev_ac > 0:
            return "AUTO_CORRECT", round(waste_cost, 4)   # waste_cost = potential - right_sized
        if ev_s > 0:
            return "SUGGEST", round(waste_cost * 0.10, 4)
        return "PASS", 0.0