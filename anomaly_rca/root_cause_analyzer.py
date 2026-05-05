"""
Root Cause Analyzer — mines historical_incidents to suggest learned policies.

NOTE: This is a reference implementation. Sreeja's production version replaces
this file — the RootCauseAnalyzer interface must be preserved exactly.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import duckdb

from policy_engine.policy_registry import Policy

_LOOKBACK_SQL = """
    SELECT workload_type, incident_type, COUNT(*) AS n,
           AVG(cost_impact_usd) AS avg_cost
    FROM historical_incidents
    WHERE date_diff('day', CAST(occurred_at AS DATE), CURRENT_DATE) <= ?
    GROUP BY workload_type, incident_type
    HAVING COUNT(*) >= 3
    ORDER BY n DESC
"""

_TOP_INCIDENTS_SQL = """
    SELECT incident_id, workload_type, incident_type, severity,
           cost_impact_usd, detection_lag_minutes, fix_applied
    FROM historical_incidents
    ORDER BY cost_impact_usd DESC
    LIMIT ?
"""

# Maps incident_type -> Policy field defaults
_INCIDENT_TO_POLICY: dict[str, dict] = {
    "over_provisioned": {
        "condition": "over_provision_factor",
        "threshold": 1.5,
        "action":    "AUTO_CORRECT",
    },
    "idle_cluster": {
        "condition": "idle_time_hours",
        "threshold": 1.0,
        "action":    "AUTO_CORRECT",
    },
    "runaway_job": {
        "condition": "actual_vs_expected_duration_ratio",
        "threshold": 2.0,
        "action":    "SUGGEST",
    },
    "token_waste": {
        "condition": "token_budget",
        "threshold": 0.0,
        "action":    "SUGGEST",
    },
}


class RootCauseAnalyzer:
    """
    Mines historical_incidents to produce Policy suggestions for PolicyRegistry.

    Only returns policies with confidence >= 0.60 (count-based: min(count/10, 0.95)).
    Does NOT write to DB or modify PolicyRegistry — the caller does that.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def analyze(self, lookback_days: int = 90) -> list[Policy]:
        """Return newly suggested policies based on incident frequency patterns."""
        con = duckdb.connect(self._db_path, read_only=True)
        try:
            rows = con.execute(_LOOKBACK_SQL, [lookback_days]).fetchall()
        finally:
            con.close()

        policies: list[Policy] = []
        seen: set[str] = set()

        for workload_type, incident_type, count, avg_cost in rows:
            if incident_type not in _INCIDENT_TO_POLICY:
                continue

            confidence = min(count / 10.0, 0.95)
            if confidence < 0.60:
                continue

            spec    = _INCIDENT_TO_POLICY[incident_type]
            pol_id  = f"rca_{workload_type}_{incident_type}"
            if pol_id in seen:
                continue
            seen.add(pol_id)

            policies.append(Policy(
                policy_id=pol_id,
                workload_type=workload_type,
                condition=spec["condition"],
                threshold=spec["threshold"],
                action=spec["action"],
                description=(
                    f"RCA: {count} {incident_type} incidents for {workload_type} "
                    f"in past {lookback_days}d (avg impact ${avg_cost:.0f})"
                ),
                source="learned",
                confidence=round(confidence, 4),
            ))

        return policies

    def top_incidents(self, n: int = 10) -> list[dict[str, Any]]:
        """Return the n highest-cost incidents, sorted by cost_impact_usd descending."""
        con = duckdb.connect(self._db_path, read_only=True)
        try:
            rows = con.execute(_TOP_INCIDENTS_SQL, [n]).fetchall()
        finally:
            con.close()

        cols = [
            "incident_id", "workload_type", "incident_type", "severity",
            "cost_impact_usd", "detection_lag_minutes", "fix_applied",
        ]
        return [dict(zip(cols, row)) for row in rows]