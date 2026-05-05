from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from simulation_engine.cost_model import CloudCostModel

_STEP_MINUTES         = 5
_CPU_UNDERUTIL_THRESH = 0.30    # below this → scale down
_MEM_UNDERUTIL_THRESH = 0.30
_IDLE_MINUTES         = 10      # idle after auto_shutdown → terminate
_OVERRUN_FACTOR       = 1.5     # actual > 1.5× expected → alert


@dataclass
class CorrectionAction:
    run_id: str
    signal_type: str        # cpu_underutil | mem_underutil | idle | overrun | spot_interruption
    action: str             # SCALE_DOWN | TERMINATE | CHECKPOINT | ALERT | MIGRATE
    nodes_before: int
    nodes_after: int
    trigger_minute: int     # when in the run timeline this fired
    cost_prevented_usd: float
    detail: str


class ActionLogger:
    def __init__(self) -> None:
        self._log: list[CorrectionAction] = []

    def record(self, action: CorrectionAction) -> None:
        self._log.append(action)

    def all(self) -> list[CorrectionAction]:
        return list(self._log)

    def total_prevented(self) -> float:
        return round(sum(a.cost_prevented_usd for a in self._log), 4)


class AdaptiveOptimizer:
    """
    Event-driven runtime optimizer.
    Steps through a utilization time-series in 5-minute increments and fires
    correction actions when signals are detected.

    simulate_run() is the main entry point.
    """

    def __init__(self) -> None:
        self._cost_model = CloudCostModel()

    def simulate_run(self, run: dict[str, Any]) -> list[CorrectionAction]:
        """
        Simulate a single run and return all correction actions fired.

        run dict keys:
          run_id, cloud_provider, instance_type, node_count, use_spot,
          actual_duration_hours, auto_shutdown_hours, idle_time_hours,
          cpu_utilization_avg, memory_utilization_avg,
          expected_duration_hours, is_runaway (bool), spot_interruption (bool)
        """
        logger = ActionLogger()
        self._check_all_signals(run, logger)
        return logger.all()

    # ── Signal handlers ────────────────────────────────────────────────────────

    def _check_all_signals(self, run: dict[str, Any], logger: ActionLogger) -> None:
        run_id         = run.get("run_id", "unknown")
        cloud          = run.get("cloud_provider", "aws")
        instance       = run.get("instance_type", "m5.xlarge")
        nodes          = int(run.get("node_count", 4))
        use_spot       = bool(run.get("use_spot", False))
        actual_dur     = float(run.get("actual_duration_hours", 4.0))
        expected_dur   = float(run.get("expected_duration_hours", 4.0))
        auto_shutdown  = run.get("auto_shutdown_hours")
        idle_hours     = float(run.get("idle_time_hours", 0.0))
        cpu            = float(run.get("cpu_utilization_avg", 0.65))
        mem            = float(run.get("memory_utilization_avg", 0.55))
        is_runaway     = bool(run.get("is_runaway", False))
        spot_interrupt = bool(run.get("spot_interruption", False))

        rate = self._cost_model.hourly_rate(cloud, instance, use_spot)

        # Signal 1: CPU under-utilisation
        if cpu < _CPU_UNDERUTIL_THRESH and nodes > 1:
            import math
            optimal = max(1, math.ceil(nodes * cpu / 0.70))
            wasted_hours = actual_dur
            prevented = round((nodes - optimal) * rate * wasted_hours, 4)
            if prevented > 0:
                logger.record(CorrectionAction(
                    run_id=run_id,
                    signal_type="cpu_underutil",
                    action="SCALE_DOWN",
                    nodes_before=nodes,
                    nodes_after=optimal,
                    trigger_minute=_STEP_MINUTES,
                    cost_prevented_usd=prevented,
                    detail=f"CPU avg {cpu:.0%} < {_CPU_UNDERUTIL_THRESH:.0%} — scale {nodes}→{optimal}",
                ))

        # Signal 2: Memory under-utilisation (independent of CPU)
        elif mem < _MEM_UNDERUTIL_THRESH and nodes > 1 and cpu >= _CPU_UNDERUTIL_THRESH:
            import math
            optimal = max(1, math.ceil(nodes * mem / 0.70))
            prevented = round((nodes - optimal) * rate * actual_dur, 4)
            if prevented > 0:
                logger.record(CorrectionAction(
                    run_id=run_id,
                    signal_type="mem_underutil",
                    action="SCALE_DOWN",
                    nodes_before=nodes,
                    nodes_after=optimal,
                    trigger_minute=_STEP_MINUTES,
                    cost_prevented_usd=prevented,
                    detail=f"MEM avg {mem:.0%} < {_MEM_UNDERUTIL_THRESH:.0%}",
                ))

        # Signal 3: Idle cluster past auto_shutdown
        if idle_hours > 0 and auto_shutdown is not None:
            idle_minutes = idle_hours * 60
            if idle_minutes > _IDLE_MINUTES:
                prevented = round(nodes * rate * idle_hours, 4)
                logger.record(CorrectionAction(
                    run_id=run_id,
                    signal_type="idle",
                    action="TERMINATE",
                    nodes_before=nodes,
                    nodes_after=0,
                    trigger_minute=int(idle_minutes),
                    cost_prevented_usd=prevented,
                    detail=f"Idle {idle_hours:.1f} h past auto_shutdown={auto_shutdown} h",
                ))

        # Signal 4: Runaway job (actual > 1.5× expected)
        if is_runaway or (actual_dur > expected_dur * _OVERRUN_FACTOR):
            overrun_hours = actual_dur - expected_dur
            prevented = round(nodes * rate * max(0, overrun_hours), 4)
            logger.record(CorrectionAction(
                run_id=run_id,
                signal_type="overrun",
                action="CHECKPOINT",
                nodes_before=nodes,
                nodes_after=nodes,
                trigger_minute=int(expected_dur * 60),
                cost_prevented_usd=prevented,
                detail=f"Actual {actual_dur:.1f} h > {_OVERRUN_FACTOR}× expected {expected_dur:.1f} h",
            ))

        # Signal 5: Spot interruption
        if spot_interrupt:
            logger.record(CorrectionAction(
                run_id=run_id,
                signal_type="spot_interruption",
                action="MIGRATE",
                nodes_before=nodes,
                nodes_after=nodes,
                trigger_minute=int(actual_dur * 60 // 2),
                cost_prevented_usd=0.0,   # migration preserves work, no direct saving
                detail="Spot interruption — migrate to on-demand",
            ))