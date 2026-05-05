#!/usr/bin/env python3
"""
PBCP / IACG v2.0 — Synthetic Dataset Generator

Generates all 8 research database tables into a DuckDB file.
DuckDB is already installed (shared with multicloud-finops-framework).
Schema is inferred automatically from pandas DataFrames — no DDL needed.

Tables produced:
  1. workload_intent       500 rows  — submissions with NLP-inferred fields
  2. provisioned_config    500 rows  — resource configs (35% ETL over-provisioned)
  3. runtime_metrics       ~30K rows — 30-90 runs per workload with utilization telemetry
  4. cost_records          ~30K rows — per-run cost (baseline: no PBCP intervention)
  5. historical_incidents  ~100 rows — injected anomaly events
  6. ai_workload_metrics   ~50 rows  — LLM/ML-specific metrics
  7. cps_ifs_records       ~30K rows — pre-computed PBCP outputs (CPS + IFS per run)
  8. policy_registry       10 rows   — built-in governance policies

Usage:
    python data/generate_dataset.py                              # 500 workloads, seed 42
    python data/generate_dataset.py --seed 43
    python data/generate_dataset.py --sample                     # also write 100-row sample
    python data/generate_dataset.py --output data/full/iacg.duckdb

Reading the output:
    import duckdb
    con = duckdb.connect("data/full/iacg.duckdb", read_only=True)
    df  = con.execute("SELECT * FROM workload_intent").df()
"""

import argparse
import random
import duckdb
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ── Configuration ──────────────────────────────────────────────────────────────

WORKLOAD_COUNTS = {
    "etl":          200,
    "adhoc":        100,
    "ml_training":  100,
    "llm_pipeline":  50,
    "batch":         30,
    "streaming":     20,
}
TOTAL_WORKLOADS = sum(WORKLOAD_COUNTS.values())   # 500

INJECTION_RATES = {
    "over_provision_etl":   0.35,   # 35% of ETL: 2-3x optimal nodes
    "idle_cluster_adhoc":   0.25,   # 25% of adhoc: idle time > auto_shutdown
    "token_waste_llm":      0.30,   # 30% of llm_pipeline: missing/exceeded budget
    "type_mismatch_global": 0.15,   # 15% of all workloads: description ≠ declared type
    "anomaly_run_rate":     0.20,   # 20% of runs: injected inefficiency
    "runaway_ml_rate":      0.10,   # 10% of ml_training runs: 3x expected duration
}

# All run timestamps are capped at this date so data is clearly historical
RUN_CUTOFF = datetime(2026, 4, 30)

TEAMS = ["data_engineering", "data_science", "ml_platform", "analytics", "infra", "product"]
ENVIRONMENTS = ["prod", "staging", "dev", "sandbox"]
ENV_WEIGHTS  = [0.40,    0.20,      0.30,  0.10]
PRIORITIES   = ["low", "medium", "high", "critical"]
PRIO_WEIGHTS = [0.20,  0.50,    0.25,  0.05]
CLOUDS       = ["aws", "azure", "gcp"]

# Realistic on-demand hourly rates (USD) — matches REQUIREMENTS.md Section 3
PRICING = {
    "aws": {
        "m5.xlarge":  {"vcpu": 4,  "memory_gb": 16, "od_hourly": 0.192},
        "m5.2xlarge": {"vcpu": 8,  "memory_gb": 32, "od_hourly": 0.384},
        "m5.4xlarge": {"vcpu": 16, "memory_gb": 64, "od_hourly": 0.768},
        "r5.xlarge":  {"vcpu": 4,  "memory_gb": 32, "od_hourly": 0.252},
        "c5.xlarge":  {"vcpu": 4,  "memory_gb": 8,  "od_hourly": 0.170},
        "p3.2xlarge": {"vcpu": 8,  "memory_gb": 61, "od_hourly": 3.060},
    },
    "azure": {
        "Standard_D4s_v3": {"vcpu": 4,  "memory_gb": 16, "od_hourly": 0.192},
        "Standard_D8s_v3": {"vcpu": 8,  "memory_gb": 32, "od_hourly": 0.384},
        "Standard_E4s_v3": {"vcpu": 4,  "memory_gb": 32, "od_hourly": 0.252},
        "Standard_NC6":    {"vcpu": 6,  "memory_gb": 56, "od_hourly": 0.900},
    },
    "gcp": {
        "n2-standard-4": {"vcpu": 4,  "memory_gb": 16, "od_hourly": 0.190},
        "n2-standard-8": {"vcpu": 8,  "memory_gb": 32, "od_hourly": 0.380},
        "n2-highmem-4":  {"vcpu": 4,  "memory_gb": 32, "od_hourly": 0.248},
        "a2-highgpu-1g": {"vcpu": 12, "memory_gb": 85, "od_hourly": 3.670},
    },
}

SPOT_DISCOUNTS = {"aws": 0.70, "azure": 0.60, "gcp": 0.80}

# Per-workload-type resource and behavioral profile
PROFILES = {
    "etl": {
        "instance":   {"aws": "m5.xlarge",  "azure": "Standard_D4s_v3", "gcp": "n2-standard-4"},
        "node_range": (4, 8),
        "duration":   (2.0, 8.0),
        "util_alpha": 5.0, "util_beta": 2.5,   # Beta params for CPU util ~0.65
        "spot_eligible": True,
        "auto_shutdown_hours": 4.0,
        "latency":    "batch_ok",
        "storage_gb": (50, 500),
        "frequency":  ["daily", "weekly", "on_demand"],
    },
    "adhoc": {
        "instance":   {"aws": "m5.xlarge",  "azure": "Standard_D4s_v3", "gcp": "n2-standard-4"},
        "node_range": (1, 5),
        "duration":   (0.5, 3.0),
        "util_alpha": 3.0, "util_beta": 3.0,   # ~0.50
        "spot_eligible": True,
        "auto_shutdown_hours": 2.0,
        "latency":    "interactive",
        "storage_gb": (10, 100),
        "frequency":  ["on_demand"],
    },
    "ml_training": {
        "instance":   {"aws": "p3.2xlarge", "azure": "Standard_NC6",    "gcp": "a2-highgpu-1g"},
        "node_range": (1, 4),
        "duration":   (4.0, 24.0),
        "util_alpha": 6.0, "util_beta": 2.0,   # ~0.75 GPU util
        "spot_eligible": False,
        "auto_shutdown_hours": 24.0,
        "latency":    "batch_ok",
        "storage_gb": (100, 2000),
        "frequency":  ["on_demand", "weekly"],
    },
    "llm_pipeline": {
        "instance":   {"aws": "m5.2xlarge", "azure": "Standard_D8s_v3", "gcp": "n2-standard-8"},
        "node_range": (2, 4),
        "duration":   (1.0, 6.0),
        "util_alpha": 4.0, "util_beta": 3.0,   # ~0.57
        "spot_eligible": False,
        "auto_shutdown_hours": 6.0,
        "latency":    "interactive",
        "storage_gb": (10, 200),
        "frequency":  ["daily", "on_demand"],
    },
    "batch": {
        "instance":   {"aws": "m5.4xlarge", "azure": "Standard_D8s_v3", "gcp": "n2-standard-8"},
        "node_range": (4, 12),
        "duration":   (4.0, 12.0),
        "util_alpha": 5.0, "util_beta": 2.0,   # ~0.71
        "spot_eligible": True,
        "auto_shutdown_hours": 12.0,
        "latency":    "batch_ok",
        "storage_gb": (100, 1000),
        "frequency":  ["nightly", "weekly"],
    },
    "streaming": {
        "instance":   {"aws": "c5.xlarge",  "azure": "Standard_D4s_v3", "gcp": "n2-standard-4"},
        "node_range": (2, 6),
        "duration":   (24.0, 168.0),
        "util_alpha": 5.0, "util_beta": 2.5,   # ~0.67 sustained
        "spot_eligible": False,
        "auto_shutdown_hours": None,
        "latency":    "real_time",
        "storage_gb": (10, 100),
        "frequency":  ["continuous"],
    },
}

# ── Description templates ──────────────────────────────────────────────────────

_DATASETS   = ["customer", "transaction", "product catalog", "clickstream", "sales",
                "inventory", "user behavior", "payment", "order history", "event log"]
_SOURCES    = ["S3", "RDS", "DynamoDB", "PostgreSQL", "Kafka", "BigQuery", "Snowflake"]
_TARGETS    = ["data warehouse", "Redshift", "Snowflake", "BigQuery", "analytics layer"]
_SCALES     = ["50 GB", "100 GB", "500 GB", "1 TB", "2 TB", "200 GB"]
_MODELS     = ["churn prediction", "recommendation", "fraud detection",
               "demand forecasting", "sentiment analysis", "anomaly detection",
               "click-through rate", "image classification"]
_PERIODS    = ["weekly", "daily", "nightly", "monthly", "quarterly"]
_ANALYSES   = ["Q1 revenue", "campaign performance", "user retention", "cohort",
               "product usage", "funnel", "A/B test results", "NPS score"]

DESCRIPTIONS = {
    "etl": [
        "{period} ETL pipeline processing {scale} of {dataset} data from {source} to {target}",
        "Batch transformation of {dataset} records — extract from {source}, load to {target}",
        "{period} data pipeline: {scale} {dataset} ingestion and normalization",
        "Transform and load {dataset} updates into {target} for downstream analytics",
        "Batch ETL job: {scale} {dataset} processing from {source} with schema validation",
        "Nightly {dataset} pipeline — join across {source} tables, write to {target}",
    ],
    "adhoc": [
        "Quick exploratory analysis of {analysis} data",
        "Ad-hoc query on {analysis} for executive presentation",
        "Investigate data quality issues in {dataset} table",
        "One-off {analysis} report requested by {team}",
        "Interactive exploration of {analysis} metrics — estimated 1-2 hours",
        "Spot check on {dataset} after last night's pipeline run",
    ],
    "ml_training": [
        "Train {model} model on {scale} {dataset} dataset",
        "Retrain {model} with last 90 days of {dataset} data",
        "Fine-tune {model} classifier on {dataset} records",
        "{period} retraining of {model} pipeline on updated {dataset}",
        "Full model refit for {model} — {scale} training data from {source}",
        "Hyperparameter search for {model} on {dataset} benchmark",
    ],
    "llm_pipeline": [
        "Batch LLM inference on {dataset} records for {model} task",
        "RAG pipeline processing {scale} of {dataset} documents",
        "Embedding generation for {dataset} corpus — {scale} vectors",
        "LLM-based {model} classification over {dataset} at scale",
        "Batch prompt completion for {dataset} summarization pipeline",
        "Vector index rebuild for {dataset} retrieval system",
    ],
    "batch": [
        "{period} batch scoring of {model} model on {scale} {dataset}",
        "Overnight {dataset} aggregation job for {target} reporting layer",
        "Large-scale {dataset} enrichment pipeline — {scale} records",
        "{period} batch inference run: {model} predictions on {dataset}",
        "Full-dataset {dataset} reconciliation job — {scale} rows",
        "Batch export of {dataset} to {target} for partner delivery",
    ],
    "streaming": [
        "Continuous real-time processing of {dataset} event stream",
        "Live {dataset} ingestion and enrichment pipeline",
        "Streaming {dataset} aggregation with 5-minute tumbling windows",
        "Real-time fraud detection on {dataset} event stream",
        "Always-on {dataset} CDC pipeline from {source} to {target}",
        "Persistent Kafka consumer for {dataset} with stateful aggregation",
    ],
}

# Mismatch descriptions: declare type X but description sounds like type Y
MISMATCH_DESCRIPTIONS = {
    "etl":          ("ml_training",   "Train {model} model on {scale} {dataset} dataset"),
    "adhoc":        ("streaming",     "Continuous real-time processing of {dataset} event stream"),
    "ml_training":  ("adhoc",         "Quick exploratory analysis of {analysis} data"),
    "llm_pipeline": ("etl",           "{period} ETL pipeline processing {scale} of {dataset} data from {source} to {target}"),
    "batch":        ("adhoc",         "Ad-hoc query on {analysis} for executive presentation"),
    "streaming":    ("batch",         "{period} batch scoring of {model} model on {scale} {dataset}"),
}

def _desc(wtype: str) -> str:
    tmpl = random.choice(DESCRIPTIONS[wtype])
    return tmpl.format(
        period=random.choice(_PERIODS),
        scale=random.choice(_SCALES),
        dataset=random.choice(_DATASETS),
        source=random.choice(_SOURCES),
        target=random.choice(_TARGETS),
        model=random.choice(_MODELS),
        analysis=random.choice(_ANALYSES),
        team=random.choice(TEAMS),
    )

def _mismatch_desc(declared_type: str) -> tuple[str, str]:
    """Returns (inferred_type, description) for a type_mismatch workload."""
    inferred, tmpl = MISMATCH_DESCRIPTIONS[declared_type]
    desc = tmpl.format(
        period=random.choice(_PERIODS),
        scale=random.choice(_SCALES),
        dataset=random.choice(_DATASETS),
        source=random.choice(_SOURCES),
        target=random.choice(_TARGETS),
        model=random.choice(_MODELS),
        analysis=random.choice(_ANALYSES),
        team=random.choice(TEAMS),
    )
    return inferred, desc

# ── Table generators ───────────────────────────────────────────────────────────

_FREQ_TO_DAY_STEP = {
    "daily":      1,
    "nightly":    1,
    "weekly":     7,
    "on_demand":  3,
    "continuous": 1,   # streaming jobs: treat as daily observations
}


def gen_workload_intent(n_total: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    # Submissions in 2025 so all run history is clearly historical
    base_time = datetime(2025, 1, 1)
    mismatch_budget = set(rng.choice(n_total, size=int(n_total * INJECTION_RATES["type_mismatch_global"]), replace=False))

    idx = 0
    for wtype, count in WORKLOAD_COUNTS.items():
        if count == 0:
            continue
        profile = PROFILES[wtype]
        for i in range(count):
            is_mismatch = idx in mismatch_budget
            if is_mismatch:
                inferred_type, description = _mismatch_desc(wtype)
                mismatch_conf = round(rng.uniform(0.85, 0.98), 3)
            else:
                description = _desc(wtype)
                inferred_type = wtype
                mismatch_conf = None

            # PII signal: customer/user/payment descriptions carry PII flag
            pii_signal = any(kw in description.lower() for kw in ["customer", "user", "payment", "pii"])
            data_sensitivity = "customer_pii" if pii_signal else random.choice(["none", "internal"])

            team = random.choice(TEAMS)
            env  = rng.choice(ENVIRONMENTS, p=ENV_WEIGHTS)
            prio = rng.choice(PRIORITIES,   p=PRIO_WEIGHTS)
            freq = random.choice(profile["frequency"])
            dur  = round(rng.uniform(*profile["duration"]), 2)
            token_budget = int(rng.integers(10_000, 200_000)) if wtype == "llm_pipeline" else None

            submitted_at = base_time + timedelta(
                days=int(rng.integers(0, 180)),   # Jan–Jun 2025 submission window
                hours=int(rng.integers(0, 24)),
            )

            rows.append({
                "intent_id":              str(uuid.uuid4()),
                "workload_name":          f"{team}_{wtype}_{idx:04d}",
                "description":            description,
                "team":                   team,
                "workload_type":          wtype,
                "environment":            str(env),
                "priority":               str(prio),
                "expected_duration_hours": dur,
                "frequency":              freq,
                "token_budget":           token_budget,
                "submitted_at":           submitted_at.isoformat(),
                # NLP-inferred fields
                "workload_type_inferred": inferred_type,
                "data_volume_estimate":   rng.choice(["small", "medium", "large", "xl"], p=[0.2, 0.4, 0.3, 0.1]),
                "latency_sensitivity":    profile["latency"],
                "recurrence_signal":      "recurring" if freq in ("daily", "weekly", "nightly", "continuous") else "one_time",
                "pii_signal":             pii_signal,
                "data_sensitivity":       data_sensitivity,
                "type_mismatch":          is_mismatch,
                "type_mismatch_confidence": mismatch_conf,
                "inference_confidence":   round(rng.uniform(0.80, 0.98), 3),
            })
            idx += 1

    return pd.DataFrame(rows)


def gen_provisioned_config(intents: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for _, w in intents.iterrows():
        wtype   = w["workload_type"]
        profile = PROFILES[wtype]
        cloud   = rng.choice(CLOUDS)
        instance = profile["instance"][cloud]
        specs    = PRICING[cloud][instance]

        opt_lo, opt_hi = profile["node_range"]
        optimal_nodes  = int(rng.integers(opt_lo, opt_hi + 1))

        # Injection: 35% of ETL gets 2-3x over-provisioned
        is_over = (wtype == "etl" and rng.random() < INJECTION_RATES["over_provision_etl"])
        if is_over:
            node_count = optimal_nodes * int(rng.choice([2, 3]))
            policy_type = "user_requested"
        else:
            node_count = optimal_nodes
            policy_type = "user_requested"

        use_spot = profile["spot_eligible"] and rng.random() < 0.50
        storage_gb = round(rng.uniform(*profile["storage_gb"]), 0)

        rows.append({
            "config_id":            str(uuid.uuid4()),
            "intent_id":            w["intent_id"],
            "cloud_provider":       cloud,
            "instance_type":        instance,
            "vcpu_per_node":        specs["vcpu"],
            "memory_gb_per_node":   specs["memory_gb"],
            "node_count":           node_count,
            "optimal_node_count":   optimal_nodes,
            "is_over_provisioned":  is_over,
            "over_provision_factor": round(node_count / optimal_nodes, 2) if is_over else 1.0,
            "storage_gb":           storage_gb,
            "use_spot":             use_spot,
            "auto_shutdown_hours":  profile["auto_shutdown_hours"],
            "region":               rng.choice(["us-east-1", "us-west-2", "eu-west-1"]),
            "policy_type":          policy_type,
        })
    return pd.DataFrame(rows)


def gen_runtime_metrics(intents: pd.DataFrame, configs: pd.DataFrame,
                        rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    merged = intents.merge(configs, on="intent_id")

    for _, w in merged.iterrows():
        wtype   = w["workload_type"]
        profile = PROFILES[wtype]
        n_runs  = int(rng.integers(30, 91))

        for run_i in range(n_runs):
            run_id = str(uuid.uuid4())
            is_anomaly = rng.random() < INJECTION_RATES["anomaly_run_rate"]

            # CPU utilization
            if w["is_over_provisioned"] or is_anomaly:
                # Underutilized — Beta(2, 5) → ~0.28
                cpu = float(np.clip(rng.beta(2.0, 5.0), 0.05, 0.45))
                mem = float(np.clip(rng.beta(2.0, 5.0), 0.05, 0.45))
            else:
                cpu = float(np.clip(rng.beta(profile["util_alpha"], profile["util_beta"]), 0.30, 0.95))
                mem = float(np.clip(rng.beta(profile["util_alpha"] * 0.8, profile["util_beta"]), 0.25, 0.92))

            # Duration
            expected = w["expected_duration_hours"]
            is_runaway = (wtype == "ml_training" and rng.random() < INJECTION_RATES["runaway_ml_rate"])
            if is_runaway:
                actual_duration = round(expected * rng.uniform(2.5, 3.5), 2)
            elif is_anomaly and wtype == "adhoc":
                actual_duration = round(expected * rng.uniform(0.1, 0.4), 2)   # finished early, idle left
            else:
                actual_duration = round(expected * rng.uniform(0.75, 1.25), 2)

            # Idle time for adhoc workloads with injection
            is_idle_inject = (wtype == "adhoc" and is_anomaly and
                              rng.random() < INJECTION_RATES["idle_cluster_adhoc"])
            if is_idle_inject:
                idle_hours = round(rng.uniform(1.5, 4.0), 2)
                total_billed_hours = actual_duration + idle_hours
            else:
                idle_hours = 0.0
                total_billed_hours = actual_duration

            failure = bool(rng.random() < 0.02)
            spot_interruption = bool(w["use_spot"] and rng.random() < 0.05)

            # Run timestamp — spaced by workload frequency so history stays realistic
            submitted = datetime.fromisoformat(str(w["submitted_at"]))
            day_step  = _FREQ_TO_DAY_STEP.get(str(w["frequency"]), 7)
            jitter    = int(rng.integers(0, max(1, day_step // 2)))
            run_start = submitted + timedelta(days=run_i * day_step + jitter,
                                             hours=int(rng.integers(0, 24)))
            if run_start > RUN_CUTOFF:
                break

            rows.append({
                "run_id":                 run_id,
                "intent_id":              w["intent_id"],
                "run_index":              run_i,
                "cpu_utilization_avg":    round(cpu, 4),
                "memory_utilization_avg": round(mem, 4),
                "expected_duration_hours": expected,
                "actual_duration_hours":  actual_duration,
                "idle_time_hours":        idle_hours,
                "total_billed_hours":     round(total_billed_hours, 2),
                "failure_flag":           failure,
                "spot_interruption":      spot_interruption,
                "is_anomaly":             is_anomaly,
                "is_runaway":             is_runaway,
                "is_idle_injected":       is_idle_inject,
                "run_start":              run_start.isoformat(),
            })

    return pd.DataFrame(rows)


def gen_cost_records(metrics: pd.DataFrame, intents: pd.DataFrame,
                     configs: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    cfg_map = configs.set_index("intent_id")
    rows = []

    for _, run in metrics.iterrows():
        iid = run["intent_id"]
        cfg = cfg_map.loc[iid]

        cloud    = cfg["cloud_provider"]
        instance = cfg["instance_type"]
        od_rate  = PRICING[cloud][instance]["od_hourly"]
        spot_rate = od_rate * (1.0 - SPOT_DISCOUNTS[cloud])
        rate     = spot_rate if cfg["use_spot"] else od_rate

        potential_cost = round(rate * cfg["node_count"] * run["total_billed_hours"], 4)

        # Baseline dataset: no PBCP intervention → actual = potential
        rows.append({
            "cost_id":           str(uuid.uuid4()),
            "run_id":            run["run_id"],
            "intent_id":         iid,
            "od_hourly_rate":    round(od_rate, 4),
            "effective_rate":    round(rate, 4),
            "node_count":        int(cfg["node_count"]),
            "billed_hours":      round(run["total_billed_hours"], 2),
            "potential_cost_usd": potential_cost,
            "actual_cost_usd":   potential_cost,  # no prevention in baseline
            "prevented_cost_usd": 0.0,
            "stage":             "baseline",
        })

    return pd.DataFrame(rows)


def gen_cps_ifs_records(metrics: pd.DataFrame, costs: pd.DataFrame,
                        configs: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """
    Pre-computed PBCP system outputs. Shows what the system would prevent.
    Stage assignment:
      - over-provisioned ETL → pre_provision AUTO_CORRECT
      - idle adhoc           → runtime terminate
      - runaway ml_training  → runtime enforce_limit
      - normal               → no prevention (CPS = 0)
    IFS values: normal ~Beta(8,2) → 0.75-0.95; anomalous ~Beta(2,5) → 0.20-0.45
    """
    cfg_map  = configs.set_index("intent_id")
    cost_map = costs.set_index("run_id")
    rows = []
    generation = 0  # incremented every 50 workloads for Phase 3

    seen_intents = {}
    for _, run in metrics.iterrows():
        iid = run["intent_id"]
        if iid not in seen_intents:
            seen_intents[iid] = len(seen_intents)
        generation = seen_intents[iid] // 50

        cfg  = cfg_map.loc[iid]
        cost = cost_map.loc[run["run_id"]]

        potential = float(cost["potential_cost_usd"])
        prevented = 0.0
        stage     = "baseline"
        source    = "none"

        # Pre-provision: over-provisioned ETL → AUTO_CORRECT
        if cfg["is_over_provisioned"] and not run["failure_flag"]:
            optimal = int(cfg["optimal_node_count"])
            cloud   = cfg["cloud_provider"]
            rate    = PRICING[cloud][cfg["instance_type"]]["od_hourly"]
            right_sized_cost = round(rate * optimal * run["total_billed_hours"], 4)
            prevented = max(0.0, potential - right_sized_cost)
            stage  = "pre_provision"
            source = "AUTO_CORRECT"

        # Runtime: idle adhoc cluster → terminate
        elif run["is_idle_injected"] and not run["failure_flag"]:
            idle_cost = float(cost["effective_rate"]) * float(cfg["node_count"]) * run["idle_time_hours"]
            prevented = round(idle_cost * 0.85, 4)   # terminate early, save ~85% of idle cost
            stage  = "runtime"
            source = "terminate"

        # Runtime: runaway ML job → enforce_limit
        elif run["is_runaway"] and not run["failure_flag"]:
            expected = run["expected_duration_hours"]
            actual   = run["actual_duration_hours"]
            rate     = float(cost["effective_rate"])
            n        = int(cfg["node_count"])
            runaway_extra = rate * n * (actual - expected)
            prevented = round(runaway_extra * 0.90, 4)
            stage  = "runtime"
            source = "enforce_limit"

        actual_cost = round(potential - prevented, 4)
        cps = round(prevented / potential, 4) if potential > 0 else 0.0

        # IFS: synthetic pre-computed alignment score
        is_misaligned = run["is_anomaly"] or cfg["is_over_provisioned"] or run["is_idle_injected"]
        if is_misaligned:
            ifs = float(np.clip(rng.beta(2.0, 5.0), 0.10, 0.60))
        else:
            ifs = float(np.clip(rng.beta(8.0, 2.0), 0.65, 1.00))

        if ifs >= 0.85:
            ifs_category = "well_aligned"
        elif ifs >= 0.65:
            ifs_category = "minor"
        elif ifs >= 0.40:
            ifs_category = "significant"
        else:
            ifs_category = "severe"

        # Synthetic 32-dim embedding vectors — placeholders until real IFS module runs.
        # Stored as JSON strings; load with json.loads() in downstream modules.
        intent_emb   = list(rng.normal(0, 1, 32).round(4))
        behavior_emb = list((rng.normal(0, 1, 32) * (1.0 - ifs) + np.array(intent_emb) * ifs).round(4))

        rows.append({
            "record_id":          str(uuid.uuid4()),
            "intent_id":          iid,
            "run_id":             run["run_id"],
            "stage":              stage,
            "potential_cost_usd": potential,
            "actual_cost_usd":    actual_cost,
            "prevented_cost_usd": prevented,
            "cps":                cps,
            "source_action":      source,
            "ifs":                round(ifs, 4),
            "ifs_category":       ifs_category,
            "intent_embedding":   str(intent_emb),
            "behavior_embedding": str(behavior_emb),
            "generation":         generation,
            "recorded_at":        run["run_start"],
        })

    return pd.DataFrame(rows)


def gen_historical_incidents(intents: pd.DataFrame, configs: pd.DataFrame,
                             rng: np.random.Generator) -> pd.DataFrame:
    incident_types = {
        "over_provisioned": 0.40,
        "idle_cluster":     0.30,
        "runaway_job":      0.20,
        "token_waste":      0.10,
    }
    n_incidents = 100
    rows = []

    pool = intents.copy()
    for _ in range(n_incidents):
        w    = pool.sample(1, random_state=int(rng.integers(0, 9999))).iloc[0]
        itype = rng.choice(list(incident_types.keys()), p=list(incident_types.values()))

        cost_map = {"over_provisioned": (50, 800), "idle_cluster": (20, 400),
                    "runaway_job": (100, 1500), "token_waste": (5, 120)}
        cost_impact = round(rng.uniform(*cost_map[itype]), 2)
        detection_lag = int(rng.integers(5, 120))

        descriptions = {
            "over_provisioned": f"Cluster provisioned at {rng.integers(2,3)}x optimal node count for {w['workload_type']} workload",
            "idle_cluster":     f"Cluster idle for {round(rng.uniform(1.5, 5.0), 1)} hours after job completion",
            "runaway_job":      f"Job runtime exceeded 2x expected duration — auto_shutdown not enforced",
            "token_waste":      f"LLM pipeline ran without token budget declaration — unbounded consumption",
        }
        fixes = {
            "over_provisioned": "Right-size to optimal node count; add simulation gate",
            "idle_cluster":     "Set auto_shutdown_hours; enforce terminate-on-idle policy",
            "runaway_job":      "Add hard runtime limit; alert team at 1.5x expected duration",
            "token_waste":      "Require token_budget on all llm_pipeline submissions",
        }

        rows.append({
            "incident_id":        str(uuid.uuid4()),
            "intent_id":          w["intent_id"],
            "workload_type":      w["workload_type"],
            "team":               w["team"],
            "incident_type":      itype,
            "description":        descriptions[itype],
            "fix_applied":        fixes[itype],
            "cost_impact_usd":    cost_impact,
            "detection_lag_minutes": detection_lag,
            "severity":           "high" if cost_impact > 300 else "medium" if cost_impact > 100 else "low",
            "occurred_at":        (datetime(2026, 1, 1) + timedelta(days=int(rng.integers(0, 120)))).isoformat(),
        })

    return pd.DataFrame(rows)


def gen_ai_workload_metrics(intents: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    llm_intents = intents[intents["workload_type"] == "llm_pipeline"].copy()
    rows = []

    for _, w in llm_intents.iterrows():
        declared_budget = w["token_budget"]
        has_token_waste = rng.random() < INJECTION_RATES["token_waste_llm"]

        if has_token_waste or declared_budget is None:
            token_budget = None
            actual_tokens = int(rng.integers(50_000, 300_000))
        else:
            token_budget = int(declared_budget)
            actual_tokens = int(rng.integers(token_budget // 2, token_budget))

        token_waste = max(0, actual_tokens - (token_budget or 0))
        estimated_cost = round(actual_tokens / 1000 * 0.002, 4)   # $0.002 per 1K tokens (approx)
        cache_hit = round(rng.uniform(0.0, 0.60), 3)

        rows.append({
            "metric_id":              str(uuid.uuid4()),
            "intent_id":              w["intent_id"],
            "model_type":             rng.choice(["gpt-3.5-turbo", "mistral-7b", "llama-3-8b", "claude-haiku"]),
            "embedding_dim":          int(rng.choice([384, 768, 1536])),
            "num_vectors":            int(rng.integers(1000, 500_000)),
            "token_budget_declared":  token_budget,
            "token_usage_actual":     actual_tokens,
            "token_waste":            token_waste,
            "rag_calls":              int(rng.integers(0, 5000)),
            "cache_hit_rate":         cache_hit,
            "estimated_cost_usd":     estimated_cost,
            "optimized_cost_usd":     round(estimated_cost * (1.0 - cache_hit * 0.4), 4),
            "cps_ai":                 round(max(0.0, 1.0 - (estimated_cost * (1.0 - cache_hit * 0.4)) / estimated_cost), 4),
        })

    return pd.DataFrame(rows)


def gen_policy_registry() -> pd.DataFrame:
    now = datetime.now(timezone.utc).isoformat()
    return pd.DataFrame([
        {"policy_id": "etl_auto_shutdown",         "workload_type": "etl",          "condition": "auto_shutdown_hours_exceeds", "threshold": 4.0,  "action": "REJECT",       "description": "ETL jobs must auto-shutdown within 4 hours",         "source": "builtin", "confidence": 1.0, "created_at": now},
        {"policy_id": "adhoc_max_nodes",            "workload_type": "adhoc",        "condition": "node_count_exceeds",          "threshold": 5.0,  "action": "AUTO_CORRECT", "description": "Adhoc jobs capped at 5 nodes",                       "source": "builtin", "confidence": 1.0, "created_at": now},
        {"policy_id": "llm_token_budget_required",  "workload_type": "llm_pipeline", "condition": "token_budget_missing",        "threshold": 0.0,  "action": "REJECT",       "description": "LLM pipelines must declare a token budget",          "source": "builtin", "confidence": 1.0, "created_at": now},
        {"policy_id": "adhoc_spot_required",        "workload_type": "adhoc",        "condition": "spot_not_enabled",            "threshold": 0.0,  "action": "SUGGEST",      "description": "Adhoc jobs should use spot/preemptible instances",   "source": "builtin", "confidence": 1.0, "created_at": now},
        {"policy_id": "etl_spot_required",          "workload_type": "etl",          "condition": "spot_not_enabled",            "threshold": 0.0,  "action": "SUGGEST",      "description": "ETL jobs should use spot/preemptible instances",     "source": "builtin", "confidence": 1.0, "created_at": now},
        {"policy_id": "batch_auto_shutdown",        "workload_type": "batch",        "condition": "auto_shutdown_hours_exceeds", "threshold": 12.0, "action": "REJECT",       "description": "Batch jobs must auto-shutdown within 12 hours",      "source": "builtin", "confidence": 1.0, "created_at": now},
        {"policy_id": "ml_training_auto_shutdown",  "workload_type": "ml_training",  "condition": "auto_shutdown_hours_exceeds", "threshold": 24.0, "action": "REJECT",       "description": "ML training jobs must auto-shutdown within 24 hours", "source": "builtin", "confidence": 1.0, "created_at": now},
        {"policy_id": "prod_no_sandbox_instance",   "workload_type": "*",            "condition": "prod_on_sandbox_instance",    "threshold": 0.0,  "action": "REJECT",       "description": "Production workloads cannot run on sandbox instances","source": "builtin", "confidence": 1.0, "created_at": now},
        {"policy_id": "learned_etl_node_cap",       "workload_type": "etl",          "condition": "node_count_exceeds",          "threshold": 10.0, "action": "AUTO_CORRECT", "description": "Learned: ETL p25 optimal node count is 10",          "source": "learned", "confidence": 0.87,"created_at": now},
        {"policy_id": "learned_ml_duration_cap",    "workload_type": "ml_training",  "condition": "auto_shutdown_hours_exceeds", "threshold": 18.0, "action": "SUGGEST",      "description": "Learned: ML training p25 duration is 18 hours",      "source": "learned", "confidence": 0.82,"created_at": now},
    ])

# ── Database writer ─────────────────────────────────────────────────────────────

def write_to_duckdb(db_path: Path, tables: dict[str, pd.DataFrame]) -> None:
    """Write all tables to a DuckDB file. Schema is inferred from DataFrames — no DDL needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    for name, df in tables.items():
        # CREATE OR REPLACE infers column names and types directly from the DataFrame
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM df")
    con.close()
    print(f"  Written {db_path}  ({db_path.stat().st_size / 1024:.0f} KB)")


# ── Summary printer ─────────────────────────────────────────────────────────────

def print_summary(tables: dict[str, pd.DataFrame]) -> None:
    wi  = tables["workload_intent"]
    cr  = tables["cost_records"]
    cps = tables["cps_ifs_records"]
    inc = tables["historical_incidents"]

    sep = "-" * 55
    print(f"\n{sep}")
    print("  Dataset Summary")
    print(sep)
    print(f"  Workloads:           {len(wi):,}")
    print(f"  Runs:                {len(tables['runtime_metrics']):,}")
    print(f"  Workload types:      {wi['workload_type'].value_counts().to_dict()}")
    print(f"  Type mismatches:     {wi['type_mismatch'].sum()} ({wi['type_mismatch'].mean():.1%})")
    print(f"  Over-provisioned:    {tables['provisioned_config']['is_over_provisioned'].sum()}")
    print(f"  Incidents:           {len(inc)}  ({inc['incident_type'].value_counts().to_dict()})")
    print(f"\n  Cost Summary")
    print(sep)
    print(f"  Total potential cost:  ${cr['potential_cost_usd'].sum():,.0f}")
    print(f"  Total prevented cost:  ${cps['prevented_cost_usd'].sum():,.0f}")
    sys_cps = cps["prevented_cost_usd"].sum() / max(cps["potential_cost_usd"].sum(), 1)
    print(f"  System CPS:            {sys_cps:.3f}")
    print(f"  Mean IFS:              {cps['ifs'].mean():.3f}")
    ibd = (cps["ifs"] < 0.65).mean()
    print(f"  IBD-flagged runs:      {ibd:.1%}")
    print(f"{sep}\n")


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PBCP synthetic dataset generator")
    parser.add_argument("--seed",          type=int,  default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--output",        type=str,  default="data/full/iacg.duckdb",
                        help="Output DuckDB path (default: data/full/iacg.duckdb)")
    parser.add_argument("--sample",        action="store_true",
                        help="Also write 100-workload sample to data/sample/iacg_sample.duckdb")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    random.seed(args.seed)
    print(f"\nGenerating PBCP synthetic dataset  seed={args.seed} …\n")

    print("  [1/8] workload_intent …")
    intents  = gen_workload_intent(TOTAL_WORKLOADS, rng)

    print("  [2/8] provisioned_config …")
    configs  = gen_provisioned_config(intents, rng)

    print("  [3/8] runtime_metrics …")
    metrics  = gen_runtime_metrics(intents, configs, rng)

    print("  [4/8] cost_records …")
    costs    = gen_cost_records(metrics, intents, configs, rng)

    print("  [5/8] historical_incidents …")
    incidents = gen_historical_incidents(intents, configs, rng)

    print("  [6/8] ai_workload_metrics …")
    ai_metrics = gen_ai_workload_metrics(intents, rng)

    print("  [7/8] cps_ifs_records …")
    cps_ifs  = gen_cps_ifs_records(metrics, costs, configs, rng)

    print("  [8/8] policy_registry …")
    policies = gen_policy_registry()

    tables = {
        "workload_intent":      intents,
        "provisioned_config":   configs,
        "runtime_metrics":      metrics,
        "cost_records":         costs,
        "historical_incidents": incidents,
        "ai_workload_metrics":  ai_metrics,
        "cps_ifs_records":      cps_ifs,
        "policy_registry":      policies,
    }

    write_to_duckdb(Path(args.output), tables)
    print_summary(tables)

    if args.sample:
        sample_intents = intents.sample(100, random_state=args.seed)
        sample_ids     = set(sample_intents["intent_id"])
        sample_tables  = {
            "workload_intent":      sample_intents,
            "provisioned_config":   configs[configs["intent_id"].isin(sample_ids)],
            "runtime_metrics":      metrics[metrics["intent_id"].isin(sample_ids)],
            "cost_records":         costs[costs["intent_id"].isin(sample_ids)],
            "historical_incidents": incidents[incidents["intent_id"].isin(sample_ids)],
            "ai_workload_metrics":  ai_metrics[ai_metrics["intent_id"].isin(sample_ids)],
            "cps_ifs_records":      cps_ifs[cps_ifs["intent_id"].isin(sample_ids)],
            "policy_registry":      policies,
        }
        write_to_duckdb(Path("data/sample/iacg_sample.duckdb"), sample_tables)
        print("  Sample written -> data/sample/iacg_sample.duckdb\n")


if __name__ == "__main__":
    main()
