"""
All metric functions used across PBCP experiments.

Primary reportable metric: valid_cps = CPS × ESR (anti-gaming constraint).
"""
from __future__ import annotations

import math
from typing import Sequence


# ── Core PBCP metrics ─────────────────────────────────────────────────────────

def cps(prevented: float, potential: float) -> float:
    """Cost Prevention Score = prevented / potential."""
    return prevented / potential if potential > 0 else 0.0


def esr(completed: int, submitted: int) -> float:
    """Execution Success Rate = completed / submitted."""
    return completed / submitted if submitted > 0 else 0.0


def valid_cps(cps_val: float, esr_val: float) -> float:
    """Valid CPS = CPS × ESR (penalises interventions that cause failures)."""
    return cps_val * esr_val


def ibd_fraction(ifs_values: Sequence[float], threshold: float = 0.70) -> float:
    """Intent–Behavior Divergence fraction: share of IFS values below threshold."""
    if not ifs_values:
        return 0.0
    return sum(1 for v in ifs_values if v < threshold) / len(ifs_values)


# ── Calibration / regression metrics ─────────────────────────────────────────

def mae(predicted: Sequence[float], actual: Sequence[float]) -> float:
    """Mean Absolute Error."""
    if not predicted:
        return float("nan")
    return sum(abs(p - a) for p, a in zip(predicted, actual)) / len(predicted)


def rmse(predicted: Sequence[float], actual: Sequence[float]) -> float:
    """Root Mean Squared Error."""
    if not predicted:
        return float("nan")
    mse = sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(predicted)
    return math.sqrt(mse)


def bias(predicted: Sequence[float], actual: Sequence[float]) -> float:
    """Mean bias = mean(predicted − actual).  Positive → over-prediction."""
    if not predicted:
        return float("nan")
    return sum(p - a for p, a in zip(predicted, actual)) / len(predicted)


def relative_rmse(predicted: Sequence[float], actual: Sequence[float]) -> float:
    """RMSE / mean(actual) — dimensionless cost error."""
    denom = sum(actual) / len(actual) if actual else 0.0
    return rmse(predicted, actual) / denom if denom > 0 else float("nan")


# ── Classification metrics (policy evaluation) ───────────────────────────────

def precision_recall(
    tp: int, fp: int, fn: int
) -> tuple[float, float]:
    """
    Returns (precision, recall).
    tp = correctly flagged violations
    fp = false alarms (flagged but no violation)
    fn = missed violations
    """
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return precision, recall


def f1(precision: float, recall: float) -> float:
    denom = precision + recall
    return 2 * precision * recall / denom if denom > 0 else 0.0


# ── Time-to-detect ────────────────────────────────────────────────────────────

def mttd(action_minutes: Sequence[float]) -> float:
    """Mean Time-To-Detect: average minute at which runtime actions fired."""
    if not action_minutes:
        return float("nan")
    return sum(action_minutes) / len(action_minutes)


# ── Aggregation helpers ───────────────────────────────────────────────────────

def cps_by_group(records: list[dict], group_key: str = "workload_type") -> dict[str, float]:
    """
    Aggregate CPS per group.
    Each record must have: group_key, prevented_cost_usd, potential_cost_usd.
    """
    buckets: dict[str, list[float]] = {}
    totals: dict[str, list[float]] = {}
    for rec in records:
        g = rec.get(group_key, "unknown")
        buckets.setdefault(g, []).append(rec.get("prevented_cost_usd", 0.0))
        totals.setdefault(g, []).append(rec.get("potential_cost_usd", 0.0))
    return {
        g: cps(sum(buckets[g]), sum(totals[g]))
        for g in buckets
    }


def ci_95(values: Sequence[float]) -> tuple[float, float]:
    """
    95% confidence interval via normal approximation.
    Returns (lower, upper) around the mean.
    """
    n = len(values)
    if n < 2:
        m = values[0] if n == 1 else float("nan")
        return m, m
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    se = math.sqrt(variance / n)
    # z = 1.96 for 95%
    return round(mean - 1.96 * se, 6), round(mean + 1.96 * se, 6)


def summary_stats(values: Sequence[float]) -> dict:
    """Returns dict with mean, std, min, max, ci_lower, ci_upper."""
    if not values:
        return {"mean": float("nan"), "std": 0.0, "min": float("nan"), "max": float("nan")}
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1) if n > 1 else 0.0
    std = math.sqrt(variance)
    lo, hi = ci_95(values)
    return {
        "mean": round(mean, 6),
        "std": round(std, 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "ci_lower": lo,
        "ci_upper": hi,
    }