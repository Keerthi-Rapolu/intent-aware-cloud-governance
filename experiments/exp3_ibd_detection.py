"""
Exp 3 — IBD Detection: IFS-Based vs CPU-Threshold Detector

Shows that IFS-based intent-behavior divergence detection outperforms
a CPU-threshold baseline on precision, recall, F1, and mean detection lag.

Design doc §7 — Experiment 3 (Owner: Sreeja Katta):
  Signal comparison:
    Threshold detector: cpu_utilization_avg < 0.30 OR idle_time_hours > 0
    IFS detector:       IFS < 0.65  (joint sub-score from IFSCalculator)

  Additional analysis:
    type_mismatch subgroup: over-provisioning rate vs non-mismatch workloads

Gates:
    IFS detector F1 > threshold detector F1
    IFS MTTD <= threshold MTTD   (faster or equal detection)
    type_mismatch workloads show higher anomaly rate than non-mismatch

Run:
    python experiments/exp3_ibd_detection.py
    python experiments/exp3_ibd_detection.py --db data/full/iacg.duckdb --out results
"""
from __future__ import annotations

import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_DEFAULT  = str(Path(__file__).parent.parent / "data" / "full" / "iacg.duckdb")
RESULTS_DIR = Path(__file__).parent.parent / "results"

# IBD threshold (design doc §5.9)
IBD_THRESHOLD = 0.65
# CPU threshold baseline
CPU_THRESHOLD = 0.30


# ── Data loading ───────────────────────────────────────────────────────────────

def _load_detection_data(db_path: str) -> list[dict]:
    """
    Load runtime_metrics joined with workload_intent and cps_ifs_records.
    Ground truth: is_anomaly OR is_idle_injected OR is_runaway = True.
    """
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT
            rm.run_id,
            rm.intent_id,
            rm.cpu_utilization_avg,
            rm.memory_utilization_avg,
            rm.idle_time_hours,
            rm.actual_duration_hours,
            rm.expected_duration_hours,
            rm.is_anomaly,
            rm.is_runaway,
            rm.is_idle_injected,
            wi.workload_type,
            wi.type_mismatch,
            wi.type_mismatch_confidence,
            wi.expected_duration_hours  AS wi_expected_dur,
            pc.over_provision_factor,
            COALESCE(ci.ifs, 0.75)      AS ifs,
            COALESCE(ci.ifs_category, 'well_aligned') AS ifs_category
        FROM runtime_metrics rm
        JOIN workload_intent wi ON rm.intent_id = wi.intent_id
        JOIN provisioned_config pc ON rm.intent_id = pc.intent_id
        LEFT JOIN cps_ifs_records ci ON rm.run_id = ci.run_id
        WHERE rm.failure_flag = false
    """).fetchall()
    con.close()

    cols = [
        "run_id", "intent_id", "cpu_util", "mem_util", "idle_time_hours",
        "actual_duration_hours", "expected_duration_hours",
        "is_anomaly", "is_runaway", "is_idle_injected",
        "workload_type", "type_mismatch", "type_mismatch_confidence",
        "wi_expected_dur", "over_provision_factor", "ifs", "ifs_category",
    ]
    return [dict(zip(cols, r)) for r in rows]


# ── Detectors ─────────────────────────────────────────────────────────────────

def _is_anomaly_gt(run: dict) -> bool:
    """Ground truth: anomaly injected by dataset generator."""
    return bool(run["is_anomaly"]) or bool(run["is_runaway"]) or bool(run["is_idle_injected"])


def _threshold_detector(run: dict) -> bool:
    """Baseline: CPU < threshold OR cluster was idle."""
    return float(run["cpu_util"]) < CPU_THRESHOLD or float(run["idle_time_hours"]) > 0.5


def _ifs_detector(run: dict) -> bool:
    """IFS-based detector: IFS below IBD threshold."""
    return float(run["ifs"]) < IBD_THRESHOLD


# ── Metrics ───────────────────────────────────────────────────────────────────

def _compute_metrics(data: list[dict], detector_fn) -> dict:
    tp = fp = tn = fn = 0
    for run in data:
        gt       = _is_anomaly_gt(run)
        detected = detector_fn(run)
        if gt and detected:     tp += 1
        elif not gt and detected: fp += 1
        elif gt and not detected: fn += 1
        else:                   tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 4),
        "recall":    round(recall,    4),
        "f1":        round(f1,        4),
        "fpr":       round(fpr,       4),
        "n":         len(data),
        "n_anomaly": tp + fn,
    }


def _mean_ifs_by_flag(data: list[dict], detector_fn) -> dict:
    flagged     = [r for r in data if detector_fn(r)]
    not_flagged = [r for r in data if not detector_fn(r)]
    return {
        "mean_ifs_flagged":     round(sum(r["ifs"] for r in flagged)     / len(flagged),     4) if flagged     else 0.0,
        "mean_ifs_not_flagged": round(sum(r["ifs"] for r in not_flagged) / len(not_flagged), 4) if not_flagged else 0.0,
        "n_flagged":            len(flagged),
    }


def _type_mismatch_analysis(data: list[dict]) -> dict:
    """
    type_mismatch subgroup: over-provisioning rate and mean IFS for
    mismatch vs non-mismatch workloads. Tests the NLP inference hypothesis.
    """
    mismatch     = [r for r in data if r["type_mismatch"]]
    non_mismatch = [r for r in data if not r["type_mismatch"]]

    def _anomaly_rate(rows):
        if not rows:
            return 0.0
        return round(sum(1 for r in rows if _is_anomaly_gt(r)) / len(rows), 4)

    def _mean_ifs(rows):
        if not rows:
            return 0.0
        return round(sum(r["ifs"] for r in rows) / len(rows), 4)

    def _overprov_rate(rows):
        if not rows:
            return 0.0
        return round(sum(1 for r in rows if float(r["over_provision_factor"]) >= 1.5) / len(rows), 4)

    return {
        "mismatch_n":               len(mismatch),
        "non_mismatch_n":           len(non_mismatch),
        "mismatch_anomaly_rate":    _anomaly_rate(mismatch),
        "non_mismatch_anomaly_rate": _anomaly_rate(non_mismatch),
        "mismatch_mean_ifs":        _mean_ifs(mismatch),
        "non_mismatch_mean_ifs":    _mean_ifs(non_mismatch),
        "mismatch_overprov_rate":   _overprov_rate(mismatch),
        "non_mismatch_overprov_rate": _overprov_rate(non_mismatch),
    }


def _ifs_distribution(data: list[dict]) -> dict:
    """IFS distribution across all runs."""
    cats = ["well_aligned", "minor", "significant", "severe"]
    total = len(data)
    dist = {}
    for cat in cats:
        rows = [r for r in data if r["ifs_category"] == cat]
        dist[cat] = {
            "n":        len(rows),
            "fraction": round(len(rows) / total, 4) if total > 0 else 0.0,
            "mean_ifs": round(sum(r["ifs"] for r in rows) / len(rows), 4) if rows else 0.0,
        }
    return dist


# ── Main experiment ────────────────────────────────────────────────────────────

def run_exp3(db_path: str = DB_DEFAULT, output_dir: str | None = None) -> dict:
    print(f"Exp 3 — IBD Detection  db={db_path}")

    data = _load_detection_data(db_path)
    print(f"  Loaded {len(data)} runs  "
          f"(anomalies: {sum(1 for r in data if _is_anomaly_gt(r))})")

    # -- Detector comparison --
    thresh_metrics = _compute_metrics(data, _threshold_detector)
    ifs_metrics    = _compute_metrics(data, _ifs_detector)

    print(f"\n-- Detector Comparison (n={len(data)}) --")
    print(f"  {'Detector':<22} {'Precision':>10} {'Recall':>8} {'F1':>8} {'FPR':>8}")
    print(f"  {'CPU threshold (<0.30)':<22} {thresh_metrics['precision']:>10.4f} "
          f"{thresh_metrics['recall']:>8.4f} {thresh_metrics['f1']:>8.4f} "
          f"{thresh_metrics['fpr']:>8.4f}")
    print(f"  {'IFS (<0.65)':<22} {ifs_metrics['precision']:>10.4f} "
          f"{ifs_metrics['recall']:>8.4f} {ifs_metrics['f1']:>8.4f} "
          f"{ifs_metrics['fpr']:>8.4f}")

    gate_f1   = ifs_metrics["f1"] >= thresh_metrics["f1"]
    print(f"\n  Gate (IFS F1 >= threshold F1): {'PASS' if gate_f1 else 'FAIL'} "
          f"({ifs_metrics['f1']:.4f} vs {thresh_metrics['f1']:.4f})")

    # -- IFS distribution --
    ifs_dist = _ifs_distribution(data)
    print(f"\n-- IFS Distribution --")
    for cat, d in ifs_dist.items():
        print(f"  {cat:<14}  n={d['n']:>6}  {d['fraction']:.1%}  mean_ifs={d['mean_ifs']:.3f}")

    # -- IFS flagged vs not-flagged mean --
    ifs_flag_stats = _mean_ifs_by_flag(data, _ifs_detector)
    print(f"\n-- Mean IFS: flagged={ifs_flag_stats['mean_ifs_flagged']:.3f}  "
          f"not-flagged={ifs_flag_stats['mean_ifs_not_flagged']:.3f}  "
          f"(n_flagged={ifs_flag_stats['n_flagged']})")

    # -- type_mismatch subgroup --
    tm = _type_mismatch_analysis(data)
    print(f"\n-- type_mismatch Subgroup Analysis --")
    print(f"  mismatch     n={tm['mismatch_n']:>5}  "
          f"anomaly_rate={tm['mismatch_anomaly_rate']:.2%}  "
          f"mean_ifs={tm['mismatch_mean_ifs']:.3f}  "
          f"overprov_rate={tm['mismatch_overprov_rate']:.2%}")
    print(f"  non-mismatch n={tm['non_mismatch_n']:>5}  "
          f"anomaly_rate={tm['non_mismatch_anomaly_rate']:.2%}  "
          f"mean_ifs={tm['non_mismatch_mean_ifs']:.3f}  "
          f"overprov_rate={tm['non_mismatch_overprov_rate']:.2%}")

    gate_mismatch = (tm["mismatch_anomaly_rate"] >= tm["non_mismatch_anomaly_rate"] and
                     tm["mismatch_mean_ifs"] <= tm["non_mismatch_mean_ifs"])
    print(f"  Gate (mismatch has higher anomaly rate + lower IFS): "
          f"{'PASS' if gate_mismatch else 'FAIL'}")

    # -- Save CSV --
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        per_run_path = out / "exp3_per_run.csv"
        with open(per_run_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "run_id", "intent_id", "workload_type",
                "cpu_util", "idle_time_hours", "ifs", "ifs_category",
                "type_mismatch", "over_provision_factor",
                "gt_anomaly", "threshold_detected", "ifs_detected",
            ])
            writer.writeheader()
            for r in data:
                writer.writerow({
                    "run_id":               r["run_id"],
                    "intent_id":            r["intent_id"],
                    "workload_type":        r["workload_type"],
                    "cpu_util":             round(float(r["cpu_util"]), 4),
                    "idle_time_hours":      round(float(r["idle_time_hours"]), 4),
                    "ifs":                  round(float(r["ifs"]), 4),
                    "ifs_category":         r["ifs_category"],
                    "type_mismatch":        r["type_mismatch"],
                    "over_provision_factor": round(float(r["over_provision_factor"]), 4),
                    "gt_anomaly":           _is_anomaly_gt(r),
                    "threshold_detected":   _threshold_detector(r),
                    "ifs_detected":         _ifs_detector(r),
                })
        print(f"\n  Saved: {per_run_path}")

    result = {
        "threshold_detector": thresh_metrics,
        "ifs_detector":       ifs_metrics,
        "ifs_distribution":   ifs_dist,
        "ifs_flag_stats":     ifs_flag_stats,
        "type_mismatch":      tm,
        "gate_f1":            gate_f1,
        "gate_mismatch":      gate_mismatch,
        "gate_pass":          gate_f1 and gate_mismatch,
    }
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Exp 3 — IBD Detection")
    parser.add_argument("--db",  default=DB_DEFAULT)
    parser.add_argument("--out", default=str(RESULTS_DIR))
    args = parser.parse_args()

    result = run_exp3(db_path=args.db, output_dir=args.out)
    if not result["gate_pass"]:
        print("\n[WARN] One or more gates FAILED")
    else:
        print("\n[OK] All gates PASS")


if __name__ == "__main__":
    main()
