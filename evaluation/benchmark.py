"""
Evaluation Benchmark — CLI orchestrator for PBCP experiments.

Usage:
    python evaluation/benchmark.py --experiment 0,1,2,3,5,6
    python evaluation/benchmark.py --experiment 0 --db data/full/iacg.duckdb --out results
    python evaluation/benchmark.py --list

Experiments:
    0  — Simulation Calibration    (gate: util MAE < 0.10, cost RMSE < 0.40)
    1  — Pre-Provision Prevention  (gate: Full PBCP CPS >= 0.35)
    2  — Runtime Prevention        (gate: all 3 scenarios fire >= 1 action)
    3  — IBD Detection (Sreeja)    (gate: IFS F1 >= threshold F1; mismatch anomaly rate higher)
    5  — System Roll-up (Sreeja)   (gate: Valid CPS >= 0.30, ESR >= 0.95, mean IFS >= 0.60)
    6  — Phase 3 Convergence       (gate: Full PBCP peak CPS >= 1.5x No Phase 3)
"""
from __future__ import annotations

import sys
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_DEFAULT = str(Path(__file__).parent.parent / "data" / "full" / "iacg.duckdb")
OUT_DEFAULT = str(Path(__file__).parent.parent / "results")

EXPERIMENT_REGISTRY = {
    "0": {
        "name": "Simulation Calibration",
        "gate": "util MAE < 0.10; cost rel-RMSE < 0.15",
        "module": "experiments.exp0_simulation_calibration",
        "fn":     "run_calibration",
    },
    "1": {
        "name": "Pre-Provision Prevention",
        "gate": "Full PBCP CPS >= 0.35",
        "module": "experiments.exp1_pre_provision",
        "fn":     "run_exp1",
    },
    "2": {
        "name": "Runtime Prevention",
        "gate": "All 3 scenarios fire at least one action",
        "module": "experiments.exp2_runtime_prevention",
        "fn":     "run_exp2",
    },
    "3": {
        "name": "IBD Detection (Sreeja)",
        "gate": "IFS detector F1 >= threshold F1; type_mismatch anomaly rate >= non-mismatch",
        "module": "experiments.exp3_ibd_detection",
        "fn":     "run_exp3",
    },
    "5": {
        "name": "System Roll-up (Dual-Metric CPS + IFS)",
        "gate": "Valid CPS >= 0.30, ESR >= 0.95, mean IFS >= 0.60",
        "module": "experiments.exp5_system_rollup",
        "fn":     "run_exp5",
    },
    "6": {
        "name": "Phase 3 Convergence",
        "gate": "Full PBCP peak CPS >= 1.5x No Phase 3 peak CPS",
        "module": "experiments.exp6_phase3_convergence",
        "fn":     "run_exp6",
    },
}


def _import_and_run(reg_entry: dict, db_path: str, out_dir: str) -> dict | list | None:
    import importlib
    mod = importlib.import_module(reg_entry["module"])
    fn  = getattr(mod, reg_entry["fn"])

    fn_name = reg_entry["fn"]
    # Match each function's signature
    if fn_name in ("run_calibration", "run_exp1", "run_exp3", "run_exp5"):
        return fn(db_path=db_path, output_dir=out_dir)
    elif fn_name in ("run_exp2", "run_exp6"):
        return fn(output_dir=out_dir)
    return fn()


def run_experiments(
    experiment_ids: list[str],
    db_path: str = DB_DEFAULT,
    out_dir: str = OUT_DEFAULT,
) -> dict[str, bool]:
    """
    Run requested experiments; return dict of {exp_id: gate_passed}.
    """
    results: dict[str, bool] = {}
    total_start = time.perf_counter()

    for exp_id in experiment_ids:
        if exp_id not in EXPERIMENT_REGISTRY:
            print(f"[ERROR] Unknown experiment '{exp_id}'. Use --list to see available.")
            results[exp_id] = False
            continue

        entry = EXPERIMENT_REGISTRY[exp_id]
        print(f"\n{'='*70}")
        print(f"Experiment {exp_id}: {entry['name']}")
        print(f"Gate: {entry['gate']}")
        print(f"{'='*70}")
        t0 = time.perf_counter()

        try:
            result = _import_and_run(entry, db_path, out_dir)
            elapsed = time.perf_counter() - t0

            # Determine gate pass/fail from result structure
            gate_passed = True
            if isinstance(result, dict):
                if "gate_pass" in result:
                    gate_passed = bool(result["gate_pass"])
                elif "gate_util_mae" in result and "gate_cost_rmse" in result:
                    gate_passed = result["gate_util_mae"] and result["gate_cost_rmse"]
                elif exp_id == "5":
                    gate_passed = (
                        result.get("gate_valid_cps", False)
                        and result.get("gate_esr", False)
                        and result.get("mean_ifs", 0.0) >= 0.60
                    )
            elif isinstance(result, list):
                if exp_id == "2":
                    # Exp 2: all scenarios must fire at least one action
                    gate_passed = all(r.get("actions_fired", 0) >= 1 for r in result)
                elif exp_id == "6":
                    # Gate: Full PBCP peak CPS must be >= 1.5x No Phase 3 peak CPS
                    # (checking peak, not last generation, since gen 9 has no non-baseline records)
                    if result:
                        peak_full = max(r.get("full_pbcp_cps_mean", 0.0) for r in result)
                        peak_no3  = max(r.get("no_phase3_cps_mean",  0.0) for r in result)
                        gate_passed = (peak_full >= peak_no3 * 1.5) and (peak_full > 0.05)

            results[exp_id] = gate_passed
            status = "PASS" if gate_passed else "FAIL"
            print(f"\n  [{status}] Exp {exp_id} completed in {elapsed:.1f}s")

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(f"\n  [ERROR] Exp {exp_id} raised {type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()
            results[exp_id] = False

    total_elapsed = time.perf_counter() - total_start
    print(f"\n{'='*70}")
    print(f"Summary ({total_elapsed:.1f}s total):")
    for exp_id, passed in results.items():
        name = EXPERIMENT_REGISTRY.get(exp_id, {}).get("name", exp_id)
        print(f"  Exp {exp_id} ({name}): {'PASS' if passed else 'FAIL'}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PBCP Evaluation Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--experiment", "-e",
        default="0,1,2,3,5,6",
        help="Comma-separated experiment IDs to run (default: 0,1,2,3,5,6)",
    )
    parser.add_argument(
        "--db",
        default=DB_DEFAULT,
        help="Path to iacg.duckdb",
    )
    parser.add_argument(
        "--out",
        default=OUT_DEFAULT,
        help="Output directory for CSVs and figures",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available experiments and exit",
    )
    args = parser.parse_args()

    if args.list:
        print("Available experiments:")
        for exp_id, entry in EXPERIMENT_REGISTRY.items():
            print(f"  {exp_id}  {entry['name']}")
            print(f"     Gate: {entry['gate']}")
        return

    exp_ids = [e.strip() for e in args.experiment.split(",") if e.strip()]
    results = run_experiments(exp_ids, db_path=args.db, out_dir=args.out)

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()