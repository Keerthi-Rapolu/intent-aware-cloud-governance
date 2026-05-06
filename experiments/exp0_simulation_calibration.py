"""
Exp 0 â€” Simulation Calibration

Checks whether PreExecutionSimulator's predicted utilization matches
the actual cpu_utilization_avg measured in historical runs, and whether
pre-execution cost estimates are within a defensible range of actual cost.

Gate: utilization MAE < 0.10; cost relative-RMSE < 0.40; bias near zero.

Cost RMSE note: the simulator predicts cost using expected_duration at
submission time. Actual cost (from cost_records.potential_cost_usd) uses
actual_duration, which varies Â±25% from expected by construction. A
pre-execution cost rel-RMSE of 0.30-0.35 reflects this irreducible duration
uncertainty â€” it is expected and acceptable for a pre-execution model.

Run:
    python experiments/exp0_simulation_calibration.py
    python experiments/exp0_simulation_calibration.py --n 200 --db data/full/iacg.duckdb
"""
from __future__ import annotations

import sys
import argparse
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_DEFAULT = str(Path(__file__).parent.parent / "data" / "full" / "iacg.duckdb")
RESULTS_DIR = Path(__file__).parent.parent / "results"


def load_calibration_sample(db_path: str, n: int = 100) -> list[dict]:
    """
    Pull n workloads (one representative run each, averaged across all runs)
    with their actual utilisation and cost from the DB.
    Stratified: roughly equal across the 6 workload types.
    """
    import duckdb
    per_type = max(1, n // 6)
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute(f"""
        WITH ranked AS (
            SELECT
                wi.intent_id,
                wi.workload_type,
                wi.environment,
                wi.priority,
                wi.expected_duration_hours,
                pc.cloud_provider,
                pc.instance_type,
                pc.node_count,
                pc.optimal_node_count,
                pc.use_spot,
                pc.over_provision_factor,
                pc.storage_gb,
                wi.recurrence_signal,
                wi.pii_signal,
                AVG(rm.cpu_utilization_avg)   AS actual_util,
                AVG(rm.actual_duration_hours) AS actual_duration,
                AVG(cr.potential_cost_usd)    AS actual_potential_cost,
                AVG(cr.actual_cost_usd)       AS actual_cost,
                AVG(cr.od_hourly_rate)        AS od_hourly_rate,
                AVG(cr.effective_rate)        AS effective_rate,
                ROW_NUMBER() OVER (
                    PARTITION BY wi.workload_type
                    ORDER BY wi.intent_id
                ) AS rn
            FROM workload_intent wi
            JOIN provisioned_config pc ON wi.intent_id = pc.intent_id
            JOIN runtime_metrics   rm ON wi.intent_id = rm.intent_id
            JOIN cost_records      cr ON rm.run_id    = cr.run_id
            GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14
        )
        SELECT * EXCLUDE (rn) FROM ranked
        WHERE rn <= {per_type}
    """).fetchall()
    con.close()

    cols = [
        "intent_id", "workload_type", "environment", "priority",
        "expected_duration_hours", "cloud_provider", "instance_type",
        "node_count", "optimal_node_count", "use_spot", "over_provision_factor",
        "storage_gb", "recurrence_signal", "pii_signal",
        "actual_util", "actual_duration", "actual_potential_cost", "actual_cost",
        "od_hourly_rate", "effective_rate",
    ]
    return [dict(zip(cols, row)) for row in rows]


def build_intent(row: dict) -> dict:
    """Convert a DB row to the intent dict expected by PreExecutionSimulator."""
    return {
        "intent_id":              row["intent_id"],
        "workload_type":          row["workload_type"],
        "cloud_provider":         row["cloud_provider"],
        "instance_type":          row["instance_type"],
        "node_count":             int(row["node_count"]),
        "expected_duration_hours": float(row["expected_duration_hours"]),
        "priority":               row["priority"],
        "environment":            row["environment"],
        "use_spot":               bool(row["use_spot"]),
        "recurrence_signal":      row["recurrence_signal"],
        "pii_signal":             bool(row["pii_signal"]),
        "over_provision_factor":  float(row["over_provision_factor"]),
        "storage_gb":             float(row["storage_gb"]),
    }


def run_calibration(
    db_path: str = DB_DEFAULT,
    n: int = 100,
    output_dir: str | None = None,
) -> dict:
    """
    Run calibration experiment and return metrics dict.
    Saves results/exp0_calibration.csv if output_dir is provided.
    """
    from simulation_engine.simulator import PreExecutionSimulator
    from evaluation.metrics import mae, rmse, bias, relative_rmse, summary_stats

    print(f"Loading {n} calibration samples from {db_path} ...")
    rows = load_calibration_sample(db_path, n)
    print(f"  Loaded {len(rows)} workloads")

    # Build simulator â€” using the KNN path so predictions come from real data
    sim = PreExecutionSimulator(db_path=db_path)

    records = []
    for row in rows:
        intent = build_intent(row)
        result = sim.simulate(intent)
        # Cost comparison: use actual_potential_cost from cost_records as ground truth.
        # potential_cost_usd in the DB is computed with actual_duration (which varies
        # from expected_duration due to runtime behaviour), so the simulator's use of
        # expected_duration gives a non-trivial, non-circular RMSE.
        expected_cost_db = float(row["actual_potential_cost"])
        records.append({
            "intent_id":            row["intent_id"],
            "workload_type":        row["workload_type"],
            "predicted_util":       round(result.predicted_utilization, 4),
            "actual_util":          round(float(row["actual_util"]), 4),
            "util_error":           round(result.predicted_utilization - float(row["actual_util"]), 4),
            "predicted_pot_cost":   round(result.potential_cost_usd, 4),
            "actual_pot_cost":      round(expected_cost_db, 4),
            "predicted_opt_nodes":  result.optimal_nodes,
            "actual_opt_nodes":     int(row["optimal_node_count"]),
            "intervention":         result.intervention,
        })

    predicted_utils = [r["predicted_util"] for r in records]
    actual_utils    = [r["actual_util"]    for r in records]
    predicted_costs = [r["predicted_pot_cost"] for r in records]
    actual_costs    = [r["actual_pot_cost"]    for r in records]

    util_mae   = mae(predicted_utils, actual_utils)
    util_rmse  = rmse(predicted_utils, actual_utils)
    util_bias  = bias(predicted_utils, actual_utils)
    cost_rrmse = relative_rmse(predicted_costs, actual_costs)

    # Per-type breakdown
    per_type: dict[str, list] = {}
    for r in records:
        per_type.setdefault(r["workload_type"], []).append(
            abs(r["predicted_util"] - r["actual_util"])
        )
    type_mae = {t: round(sum(errs) / len(errs), 4) for t, errs in per_type.items()}

    metrics = {
        "n":              len(records),
        "util_mae":       round(util_mae,   4),
        "util_rmse":      round(util_rmse,  4),
        "util_bias":      round(util_bias,  4),
        "cost_rel_rmse":  round(cost_rrmse, 4),
        "mae_by_type":    type_mae,
        "gate_util_mae":  util_mae < 0.10,
        "gate_cost_rmse": cost_rrmse < 0.40,
    }

    # -- Print ------------------------------------------------------------------
    print("\n-- Exp 0: Simulation Calibration -------------------------------------")
    print(f"  Samples:             {metrics['n']}")
    print(f"  Utilization MAE:     {metrics['util_mae']:.4f}  (gate < 0.10: {'PASS' if metrics['gate_util_mae'] else 'FAIL'})")
    print(f"  Utilization RMSE:    {metrics['util_rmse']:.4f}")
    print(f"  Utilization bias:    {metrics['util_bias']:+.4f}")
    print(f"  Cost relative RMSE:  {metrics['cost_rel_rmse']:.4f}  (gate < 0.40: {'PASS' if metrics['gate_cost_rmse'] else 'FAIL'})")
    print(f"\n  MAE by workload type:")
    for wtype, m in sorted(type_mae.items()):
        print(f"    {wtype:<15} {m:.4f}")

    # -- Save CSV ---------------------------------------------------------------
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / "exp0_calibration.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            w.writeheader()
            w.writerows(records)
        print(f"\n  Saved: {csv_path}")

        # -- Scatter plot -------------------------------------------------------
        try:
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))

            # Utilisation scatter
            ax = axes[0]
            colors = {"etl": "#1f77b4", "adhoc": "#ff7f0e", "ml_training": "#2ca02c",
                      "batch": "#d62728", "streaming": "#9467bd", "llm_pipeline": "#8c564b"}
            for r in records:
                c = colors.get(r["workload_type"], "#7f7f7f")
                ax.scatter(r["actual_util"], r["predicted_util"], color=c, alpha=0.6, s=40)
            lim = [0, 1]
            ax.plot(lim, lim, "k--", lw=1, label="y=x")
            ax.set_xlabel("Actual Utilisation")
            ax.set_ylabel("Predicted Utilisation")
            ax.set_title(f"Utilisation Calibration (MAE={metrics['util_mae']:.3f})")
            from matplotlib.patches import Patch
            ax.legend(handles=[Patch(color=c, label=t) for t, c in colors.items()],
                      fontsize=7, ncol=2)

            # Cost scatter
            ax2 = axes[1]
            for r in records:
                c = colors.get(r["workload_type"], "#7f7f7f")
                ax2.scatter(r["actual_pot_cost"], r["predicted_pot_cost"], color=c, alpha=0.6, s=40)
            mx = max(r["actual_pot_cost"] for r in records) * 1.05
            ax2.plot([0, mx], [0, mx], "k--", lw=1)
            ax2.set_xlabel("Actual Potential Cost ($)")
            ax2.set_ylabel("Predicted Potential Cost ($)")
            ax2.set_title(f"Cost Calibration (rel-RMSE={metrics['cost_rel_rmse']:.3f})")

            fig.tight_layout()
            fig_dir = out / "figures"
            fig_dir.mkdir(exist_ok=True)
            fig_path = fig_dir / "exp0_calibration.png"
            fig.savefig(fig_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"  Saved: {fig_path}")
        except ImportError:
            print("  (matplotlib not available â€” skipping plot)")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 0 â€” Simulation Calibration")
    parser.add_argument("--db",  default=DB_DEFAULT, help="Path to iacg.duckdb")
    parser.add_argument("--n",   type=int, default=100, help="Number of calibration samples")
    parser.add_argument("--out", default="results", help="Output directory")
    args = parser.parse_args()

    metrics = run_calibration(db_path=args.db, n=args.n, output_dir=args.out)

    if not metrics["gate_util_mae"] or not metrics["gate_cost_rmse"]:
        print("\n[WARN] One or more calibration gates FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
