"""
Exp 6 — Phase 3 Convergence

Measures CPS improvement over 10 generations for 4 scenarios:

  1. Full PBCP         — KNN priors + learned policies (read from cps_ifs_records)
  2. No Phase 3        — catalog priors only, no learning (no_phase3_frozen evaluator)
  3. Policy-only       — rule-based policies, no KNN (rule_based_policies evaluator)
  4. Embedding-only    — KNN priors, no policy enforcement (simulator direct)

Runs across 5 seeds (42–46); reports mean ± std per generation.

Each "generation" = a batch of workloads in cps_ifs_records.generation column.
The batches are processed in chronological order so that Full PBCP benefits from
growing KNN training data — exactly the Phase 3 learning curve.

Run:
    python experiments/exp6_phase3_convergence.py
    python experiments/exp6_phase3_convergence.py --seeds 42,43 --out results
"""
from __future__ import annotations

import sys
import argparse
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_DIR = Path(__file__).parent.parent / "data" / "full"
RESULTS_DIR = Path(__file__).parent.parent / "results"

SEEDS = [42, 43, 44, 45, 46]
GENERATIONS = 10


def db_path_for_seed(seed: int) -> str:
    if seed == 42:
        return str(DB_DIR / "iacg.duckdb")
    return str(DB_DIR / f"iacg_s{seed}.duckdb")


def load_generation_workloads(db_path: str, generation: int) -> list[dict]:
    """
    Load workload intents for a specific generation batch.
    Workloads are assigned to generations via cps_ifs_records.generation.
    Returns deduplicated intent dicts (one per intent_id).
    """
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT DISTINCT
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
            pc.auto_shutdown_hours,
            wi.recurrence_signal,
            wi.pii_signal,
            wi.token_budget
        FROM cps_ifs_records ci
        JOIN workload_intent wi   ON ci.intent_id = wi.intent_id
        JOIN provisioned_config pc ON wi.intent_id = pc.intent_id
        WHERE ci.generation = ?
    """, [generation]).fetchall()
    con.close()
    cols = [
        "intent_id", "workload_type", "environment", "priority",
        "expected_duration_hours", "cloud_provider", "instance_type",
        "node_count", "optimal_node_count", "use_spot", "over_provision_factor",
        "storage_gb", "auto_shutdown_hours", "recurrence_signal", "pii_signal",
        "token_budget",
    ]
    return [dict(zip(cols, r)) for r in rows]


def read_full_pbcp_generation(db_path: str, generation: int) -> tuple[float, float]:
    """
    Read mean CPS and mean IFS from cps_ifs_records for the Full PBCP scenario.
    Uses non-baseline records (system intervened / evaluated).
    """
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    row = con.execute("""
        SELECT AVG(cps), AVG(ifs)
        FROM cps_ifs_records
        WHERE generation = ? AND stage != 'baseline'
    """, [generation]).fetchone()
    con.close()
    if row and row[0] is not None:
        return round(float(row[0]), 4), round(float(row[1]), 4)
    # Fall back to all records if no non-baseline records in this generation
    con = duckdb.connect(db_path, read_only=True)
    row2 = con.execute("""
        SELECT AVG(cps), AVG(ifs)
        FROM cps_ifs_records WHERE generation = ?
    """, [generation]).fetchone()
    con.close()
    if row2 and row2[0] is not None:
        return round(float(row2[0]), 4), round(float(row2[1]), 4)
    return 0.0, 0.0


def evaluate_batch_cps(results: list) -> float:
    """Compute CPS from a list of SimulationResult objects."""
    prevented = sum(r.prevented_cost_usd for r in results)
    potential = sum(r.potential_cost_usd  for r in results)
    return prevented / potential if potential > 0 else 0.0


def run_no_phase3(batch: list[dict]) -> float:
    import experiments.baselines.no_phase3_frozen as nf
    results = nf.evaluate_batch(batch)
    return evaluate_batch_cps(results)


def run_policy_only(batch: list[dict]) -> float:
    import experiments.baselines.rule_based_policies as rb
    results = rb.evaluate_batch(batch)
    return evaluate_batch_cps(results)


def run_embedding_only(batch: list[dict], db_path: str) -> float:
    """KNN priors via simulator's EV decision — no policy registry enforcement."""
    from simulation_engine.simulator import PreExecutionSimulator
    sim = _get_embedding_only_sim(db_path)
    results = [sim.simulate(intent) for intent in batch]
    return evaluate_batch_cps(results)


_EMB_SIM_CACHE: dict[str, object] = {}


def _get_embedding_only_sim(db_path: str):
    if db_path not in _EMB_SIM_CACHE:
        from simulation_engine.simulator import PreExecutionSimulator
        _EMB_SIM_CACHE[db_path] = PreExecutionSimulator(db_path=db_path)
    return _EMB_SIM_CACHE[db_path]


def run_one_seed(seed: int) -> list[dict]:
    """Run Exp 6 for one seed; return list of per-generation dicts."""
    db_path = db_path_for_seed(seed)
    if not Path(db_path).exists():
        print(f"  [SKIP] {db_path} not found")
        return []

    print(f"  Seed {seed}: {db_path}")
    gen_records = []
    for g in range(GENERATIONS):
        batch = load_generation_workloads(db_path, g)
        if not batch:
            # No workloads assigned to this generation in this seed's DB
            gen_records.append({
                "seed": seed, "generation": g,
                "full_pbcp_cps": 0.0, "full_pbcp_ifs": 0.0,
                "no_phase3_cps": 0.0, "policy_only_cps": 0.0,
                "embedding_only_cps": 0.0,
            })
            continue

        full_cps, full_ifs = read_full_pbcp_generation(db_path, g)
        no_p3_cps          = run_no_phase3(batch)
        pol_cps             = run_policy_only(batch)
        emb_cps             = run_embedding_only(batch, db_path)

        gen_records.append({
            "seed":               seed,
            "generation":         g,
            "full_pbcp_cps":      full_cps,
            "full_pbcp_ifs":      full_ifs,
            "no_phase3_cps":      no_p3_cps,
            "policy_only_cps":    pol_cps,
            "embedding_only_cps": emb_cps,
        })
        print(f"    gen={g:2d}  n={len(batch):3d}  "
              f"full={full_cps:.3f}  no_p3={no_p3_cps:.3f}  "
              f"policy={pol_cps:.3f}  emb={emb_cps:.3f}")

    return gen_records


def aggregate_across_seeds(all_records: list[dict]) -> list[dict]:
    """
    For each generation, compute mean ± std across all seeds.
    Returns list of dicts with generation as key.
    """
    import math
    from collections import defaultdict

    buckets: dict[int, dict[str, list[float]]] = defaultdict(lambda: {
        "full_pbcp_cps": [], "full_pbcp_ifs": [],
        "no_phase3_cps": [], "policy_only_cps": [], "embedding_only_cps": [],
    })
    for rec in all_records:
        g = rec["generation"]
        for k in buckets[g]:
            buckets[g][k].append(rec[k])

    result = []
    for g in range(GENERATIONS):
        row: dict = {"generation": g}
        for metric, vals in buckets[g].items():
            if not vals:
                row[f"{metric}_mean"] = 0.0
                row[f"{metric}_std"]  = 0.0
                continue
            mean = sum(vals) / len(vals)
            std  = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)) if len(vals) > 1 else 0.0
            row[f"{metric}_mean"] = round(mean, 4)
            row[f"{metric}_std"]  = round(std,  4)
        result.append(row)
    return result


def run_exp6(
    seeds: list[int] = SEEDS,
    output_dir: str | None = None,
) -> list[dict]:
    print("-- Exp 6: Phase 3 Convergence ----------------------------------------")

    all_records: list[dict] = []
    for seed in seeds:
        records = run_one_seed(seed)
        all_records.extend(records)

    if not all_records:
        print("  No data produced (check DB paths)")
        return []

    agg = aggregate_across_seeds(all_records)

    print("\n-- Mean CPS per Generation (across seeds) ----------------------------")
    print(f"  {'Gen':>3}  {'Full PBCP':>10}  {'No Phase 3':>11}  {'Policy-only':>12}  {'Emb-only':>10}")
    for row in agg:
        print(f"  {row['generation']:>3}  "
              f"{row['full_pbcp_cps_mean']:>10.4f}  "
              f"{row['no_phase3_cps_mean']:>11.4f}  "
              f"{row['policy_only_cps_mean']:>12.4f}  "
              f"{row['embedding_only_cps_mean']:>10.4f}")

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Per-seed detail
        detail_path = out / "exp6_per_seed.csv"
        with open(detail_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_records[0].keys()))
            w.writeheader()
            w.writerows(all_records)
        print(f"\n  Saved: {detail_path}")

        # Aggregated convergence table
        agg_path = out / "exp6_convergence.csv"
        with open(agg_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(agg[0].keys()))
            w.writeheader()
            w.writerows(agg)
        print(f"  Saved: {agg_path}")

        # -- Convergence chart --------------------------------------------------
        try:
            import matplotlib.pyplot as plt
            import numpy as np

            generations = [row["generation"] for row in agg]
            scenarios = {
                "Full PBCP":      ("full_pbcp_cps",      "#2ca02c", "o-"),
                "Embedding-only": ("embedding_only_cps", "#1f77b4", "s--"),
                "Policy-only":    ("policy_only_cps",    "#ff7f0e", "^--"),
                "No Phase 3":     ("no_phase3_cps",      "#d62728", "x:"),
            }

            fig, ax = plt.subplots(figsize=(10, 6))
            for label, (key, color, style) in scenarios.items():
                means = [row[f"{key}_mean"] for row in agg]
                stds  = [row[f"{key}_std"]  for row in agg]
                ax.plot(generations, means, style, color=color, label=label, linewidth=2)
                ax.fill_between(
                    generations,
                    [m - s for m, s in zip(means, stds)],
                    [m + s for m, s in zip(means, stds)],
                    color=color, alpha=0.12,
                )

            ax.set_xlabel("Generation", fontsize=12)
            ax.set_ylabel("Mean CPS", fontsize=12)
            ax.set_title("Exp 6 — Phase 3 Convergence: CPS across Generations\n"
                         f"({len(seeds)} seeds, ±1 std band)", fontsize=11)
            ax.legend(fontsize=10)
            ax.set_xticks(generations)
            ax.set_ylim(bottom=0)
            ax.grid(axis="y", linestyle="--", alpha=0.4)

            fig_dir = out / "figures"
            fig_dir.mkdir(exist_ok=True)
            fig_path = fig_dir / "exp6_convergence.png"
            fig.savefig(fig_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"  Saved: {fig_path}")
        except ImportError:
            print("  (matplotlib not available — skipping plot)")

    return agg


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 6 — Phase 3 Convergence")
    parser.add_argument(
        "--seeds", default=",".join(str(s) for s in SEEDS),
        help="Comma-separated seed list, e.g. 42,43,44"
    )
    parser.add_argument("--out", default="results")
    args = parser.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(",")]
    run_exp6(seeds=seeds, output_dir=args.out)


if __name__ == "__main__":
    main()