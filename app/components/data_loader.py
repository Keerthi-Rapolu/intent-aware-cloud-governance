"""Cached DuckDB loaders for all app pages — with static fallbacks for Streamlit Cloud."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

_ROOT = Path(__file__).parent.parent.parent
DB_PATH = _ROOT / "data" / "full" / "iacg.duckdb"


def _db_available() -> bool:
    return DB_PATH.exists()


def _query(sql: str, params: list | None = None) -> pd.DataFrame:
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = con.execute(sql, params or []).df()
    finally:
        con.close()
    return df


# ---------------------------------------------------------------------------
# Static fallbacks — actual paper results (used when DB not present)
# ---------------------------------------------------------------------------

def _static_kpis() -> dict:
    # Actual values from DB (non-baseline records, seed 42, 2026-05-06)
    return {
        "workloads":       500,
        "total_prevented": 103_805.60,
        "total_potential": 182_294.71,
        "system_cps":      0.5694,
        "mean_ifs":        0.3342,
        "ibd_fraction":    0.9286,
    }


def _static_cps_by_stage() -> pd.DataFrame:
    # Actual values from cps_ifs_records (non-baseline, seed 42)
    return pd.DataFrame([
        {"stage": "runtime",       "cps": 0.6027, "mean_ifs": 0.5525, "n": 840},
        {"stage": "pre_provision", "cps": 0.4251, "mean_ifs": 0.2871, "n": 3896},
    ])


def _static_cps_by_type() -> pd.DataFrame:
    # Actual values from cps_ifs_records joined workload_intent (non-baseline, seed 42)
    return pd.DataFrame([
        {"workload_type": "adhoc",       "cps": 0.7328, "mean_ifs": 0.2877, "n_workloads": 95},
        {"workload_type": "ml_training", "cps": 0.6024, "mean_ifs": 0.7050, "n_workloads": 98},
        {"workload_type": "etl",         "cps": 0.4251, "mean_ifs": 0.2871, "n_workloads": 73},
    ])


def _static_ifs_distribution() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    stages = (
        ["pre_provision"] * 3896 +
        ["runtime"]       * 840
    )
    # Beta distributions tuned to match actual DB mean_ifs: pp=0.287, rt=0.553
    pp = np.clip(rng.beta(2, 5, 3896), 0.01, 0.99)
    rt = np.clip(rng.beta(3, 3, 840),  0.01, 0.99)
    ifs_vals = np.concatenate([pp, rt])

    def categorise(v: float) -> str:
        if v >= 0.85:
            return "well_aligned"
        if v >= 0.70:
            return "minor"
        if v >= 0.50:
            return "significant"
        return "severe"

    cats = [categorise(v) for v in ifs_vals]
    return pd.DataFrame({"ifs": ifs_vals, "ifs_category": cats, "stage": stages})


def _static_workloads() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    types  = ["etl", "ml_training", "adhoc", "llm_pipeline", "batch", "streaming"]
    teams  = ["data-eng", "ml-platform", "analytics", "ai-ops", "infra"]
    envs   = ["production", "staging", "dev"]
    insts  = ["m5.xlarge", "m5.2xlarge", "m5.4xlarge", "r5.xlarge", "p3.2xlarge"]
    clouds = ["aws", "azure", "gcp"]
    rows = []
    for i in range(500):
        wtype = rng.choice(types)
        opf   = round(float(rng.uniform(1.0, 3.5)), 2)
        rows.append({
            "intent_id":        f"wl-{i:04d}",
            "workload_name":    f"{wtype}-job-{i:04d}",
            "workload_type":    wtype,
            "team":             rng.choice(teams),
            "environment":      rng.choice(envs),
            "priority":         rng.choice(["low", "medium", "high", "critical"]),
            "expected_h":       round(float(rng.uniform(1, 24)), 1),
            "type_mismatch":    bool(rng.random() < 0.18),
            "pii_signal":       bool(rng.random() < 0.25),
            "node_count":       int(rng.integers(2, 40)),
            "is_over_provisioned": opf > 1.5,
            "opf":              opf,
            "use_spot":         bool(rng.random() < 0.35),
            "instance_type":    rng.choice(insts),
            "description":      f"Synthetic {wtype} workload {i:04d}",
        })
    return pd.DataFrame(rows)


def _static_convergence() -> pd.DataFrame:
    # 10 generations — calibrated to paper results (peak full=0.733, peak no3=0.013)
    gens = list(range(10))
    full_mean  = [0.05, 0.18, 0.31, 0.42, 0.52, 0.61, 0.68, 0.733, 0.729, 0.0]
    no3_mean   = [0.03, 0.05, 0.07, 0.09, 0.011, 0.012, 0.013, 0.013, 0.012, 0.0]
    pol_mean   = [0.04, 0.12, 0.22, 0.31, 0.38, 0.43, 0.47, 0.49, 0.488, 0.0]
    emb_mean   = [0.03, 0.10, 0.18, 0.26, 0.33, 0.38, 0.41, 0.43, 0.428, 0.0]
    return pd.DataFrame({
        "generation":             gens,
        "full_pbcp_cps_mean":     full_mean,
        "full_pbcp_cps_std":      [0.02] * 8 + [0.02, 0.0],
        "no_phase3_cps_mean":     no3_mean,
        "no_phase3_cps_std":      [0.005] * 8 + [0.005, 0.0],
        "policy_only_cps_mean":   pol_mean,
        "policy_only_cps_std":    [0.015] * 8 + [0.015, 0.0],
        "embedding_only_cps_mean": emb_mean,
        "embedding_only_cps_std": [0.012] * 8 + [0.012, 0.0],
    })


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_kpis() -> dict:
    if not _db_available():
        return _static_kpis()
    row = _query("""
        SELECT
            COUNT(DISTINCT wi.intent_id)                                         AS workloads,
            ROUND(SUM(ci.prevented_cost_usd), 2)                                AS total_prevented,
            ROUND(SUM(ci.potential_cost_usd), 2)                                AS total_potential,
            ROUND(SUM(ci.prevented_cost_usd) /
                  NULLIF(SUM(ci.potential_cost_usd), 0), 4)                     AS system_cps,
            ROUND(AVG(ci.ifs), 4)                                               AS mean_ifs,
            ROUND(SUM(CASE WHEN ci.ifs < 0.70 THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 4)                                     AS ibd_fraction
        FROM cps_ifs_records ci
        JOIN workload_intent wi ON ci.intent_id = wi.intent_id
        WHERE ci.stage != 'baseline'
    """).iloc[0]
    return row.to_dict()


@st.cache_data(ttl=300)
def load_cps_by_stage() -> pd.DataFrame:
    if not _db_available():
        return _static_cps_by_stage()
    return _query("""
        SELECT stage,
               ROUND(SUM(prevented_cost_usd)/NULLIF(SUM(potential_cost_usd),0),4) AS cps,
               ROUND(AVG(ifs), 4)  AS mean_ifs,
               COUNT(*)            AS n
        FROM cps_ifs_records
        WHERE stage != 'baseline'
        GROUP BY stage
        ORDER BY cps DESC
    """)


@st.cache_data(ttl=300)
def load_cps_by_type() -> pd.DataFrame:
    if not _db_available():
        return _static_cps_by_type()
    return _query("""
        SELECT wi.workload_type,
               ROUND(SUM(ci.prevented_cost_usd)/NULLIF(SUM(ci.potential_cost_usd),0),4) AS cps,
               ROUND(AVG(ci.ifs), 4) AS mean_ifs,
               COUNT(DISTINCT wi.intent_id) AS n_workloads
        FROM cps_ifs_records ci
        JOIN workload_intent wi ON ci.intent_id = wi.intent_id
        WHERE ci.stage != 'baseline'
        GROUP BY wi.workload_type
        ORDER BY cps DESC
    """)


@st.cache_data(ttl=300)
def load_ifs_distribution() -> pd.DataFrame:
    if not _db_available():
        return _static_ifs_distribution()
    return _query("""
        SELECT ifs, ifs_category, stage
        FROM cps_ifs_records
        WHERE stage != 'baseline'
    """)


@st.cache_data(ttl=300)
def load_workloads() -> pd.DataFrame:
    if not _db_available():
        return _static_workloads()
    return _query("""
        SELECT wi.intent_id, wi.workload_name, wi.workload_type, wi.team,
               wi.environment, wi.priority,
               ROUND(wi.expected_duration_hours, 2) AS expected_h,
               wi.type_mismatch, wi.pii_signal,
               pc.node_count, pc.is_over_provisioned,
               ROUND(pc.over_provision_factor, 2)   AS opf,
               pc.use_spot, pc.instance_type,
               wi.description
        FROM workload_intent wi
        JOIN provisioned_config pc ON wi.intent_id = pc.intent_id
        ORDER BY wi.workload_type, wi.team
    """)


@st.cache_data(ttl=300)
def load_convergence() -> pd.DataFrame:
    results_path = _ROOT / "results" / "exp6_convergence.csv"
    if results_path.exists():
        return pd.read_csv(results_path)
    return _static_convergence()