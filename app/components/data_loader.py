"""Cached DuckDB loaders for all app pages."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

_ROOT = Path(__file__).parent.parent.parent
DB_PATH = str(_ROOT / "data" / "full" / "iacg.duckdb")


def _query(sql: str, params: list | None = None) -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        df = con.execute(sql, params or []).df()
    finally:
        con.close()
    return df


@st.cache_data(ttl=300)
def load_kpis() -> dict:
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
    return _query("""
        SELECT ifs, ifs_category, stage
        FROM cps_ifs_records
        WHERE stage != 'baseline'
    """)


@st.cache_data(ttl=300)
def load_workloads() -> pd.DataFrame:
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
    return pd.DataFrame()