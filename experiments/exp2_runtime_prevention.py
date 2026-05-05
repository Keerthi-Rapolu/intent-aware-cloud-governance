"""
Exp 2 — Runtime Cost Prevention (3 Scenarios)

Demonstrates AdaptiveOptimizer's runtime signals on three canonical workloads:

  Scenario A — Idle adhoc cluster (3 h idle after completion)
  Scenario B — Underutilised ETL (CPU avg 18%, 20 nodes)
  Scenario C — Runaway ML training job (3× expected duration)

Reports: signals fired, action taken, cost prevented, time-to-action.

Run:
    python experiments/exp2_runtime_prevention.py
    python experiments/exp2_runtime_prevention.py --out results
"""
from __future__ import annotations

import sys
import argparse
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results"

# -- Scenario definitions ------------------------------------------------------

SCENARIO_A: dict = {
    "run_id":                    "exp2-a-idle-adhoc",
    "cloud_provider":            "aws",
    "instance_type":             "m5.xlarge",
    "node_count":                6,
    "use_spot":                  True,
    "actual_duration_hours":     2.0,    # finished at 2 h
    "expected_duration_hours":   2.0,
    "auto_shutdown_hours":       6.0,    # cluster left running
    "idle_time_hours":           3.0,    # 3 h idle after completion
    "cpu_utilization_avg":       0.05,
    "memory_utilization_avg":    0.08,
    "is_runaway":                False,
    "spot_interruption":         False,
}

SCENARIO_B: dict = {
    "run_id":                    "exp2-b-underutil-etl",
    "cloud_provider":            "aws",
    "instance_type":             "m5.xlarge",
    "node_count":                20,
    "use_spot":                  False,
    "actual_duration_hours":     8.0,
    "expected_duration_hours":   8.0,
    "auto_shutdown_hours":       10.0,
    "idle_time_hours":           0.0,
    "cpu_utilization_avg":       0.18,   # well below 40% threshold
    "memory_utilization_avg":    0.22,
    "is_runaway":                False,
    "spot_interruption":         False,
}

SCENARIO_C: dict = {
    "run_id":                    "exp2-c-runaway-ml",
    "cloud_provider":            "aws",
    "instance_type":             "p3.2xlarge",
    "node_count":                4,
    "use_spot":                  False,
    "actual_duration_hours":     12.0,   # 3× expected — runaway
    "expected_duration_hours":    4.0,
    "auto_shutdown_hours":        6.0,
    "idle_time_hours":            0.0,
    "cpu_utilization_avg":        0.85,
    "memory_utilization_avg":     0.80,
    "is_runaway":                 True,
    "spot_interruption":          False,
}

SCENARIOS = {
    "A_idle_adhoc":        (SCENARIO_A, "Idle adhoc cluster — 3h idle after completion"),
    "B_underutil_etl":     (SCENARIO_B, "Underutilised ETL — CPU avg 18%, 20 nodes"),
    "C_runaway_ml":        (SCENARIO_C, "Runaway ML training — 3x expected duration"),
}


def run_scenario(run_dict: dict, scenario_key: str, description: str) -> dict:
    """Run AdaptiveOptimizer on one scenario; return structured result dict."""
    from runtime_optimizer.adaptive_optimizer import AdaptiveOptimizer

    optimizer = AdaptiveOptimizer()
    actions = optimizer.simulate_run(run_dict)

    total_prevented = sum(a.cost_prevented_usd for a in actions)
    signals = [a.signal_type for a in actions]

    result = {
        "scenario":              scenario_key,
        "description":           description,
        "cloud":                 run_dict["cloud_provider"],
        "instance_type":         run_dict["instance_type"],
        "node_count":            run_dict["node_count"],
        "use_spot":              run_dict["use_spot"],
        "expected_duration_h":  run_dict["expected_duration_hours"],
        "actual_duration_h":    run_dict["actual_duration_hours"],
        "idle_time_h":          run_dict["idle_time_hours"],
        "cpu_util":              run_dict["cpu_utilization_avg"],
        "actions_fired":         len(actions),
        "signals":               ", ".join(signals) if signals else "none",
        "cost_prevented_usd":   round(total_prevented, 4),
        "action_detail":         [],
    }

    for action in actions:
        result["action_detail"].append({
            "signal_type":        action.signal_type,
            "action":             action.action,
            "nodes_before":       action.nodes_before,
            "nodes_after":        action.nodes_after,
            "trigger_minute":     action.trigger_minute,
            "cost_prevented_usd": round(action.cost_prevented_usd, 4),
            "detail":             action.detail,
        })

    return result


def run_exp2(output_dir: str | None = None) -> list[dict]:
    print("-- Exp 2: Runtime Prevention -----------------------------------------")

    all_results = []
    for key, (run_dict, desc) in SCENARIOS.items():
        r = run_scenario(run_dict, key, desc)
        all_results.append(r)

        print(f"\n  {key}: {desc}")
        print(f"    Actions fired:    {r['actions_fired']}")
        print(f"    Signals:          {r['signals']}")
        print(f"    Cost prevented:   ${r['cost_prevented_usd']:.2f}")
        for ad in r["action_detail"]:
            print(f"      [{ad['trigger_minute']:>5} min] {ad['signal_type']:<18} "
                  f"{ad['action']:<12} nodes {ad['nodes_before']}->{ad['nodes_after']}  "
                  f"${ad['cost_prevented_usd']:.2f}")

    # -- Baseline comparison (no optimizer) ------------------------------------
    print("\n  Comparison: static vs. runtime-optimised cost")
    from simulation_engine.cost_model import CloudCostModel
    cost_model = CloudCostModel()
    for key, (run_dict, desc) in SCENARIOS.items():
        r = next(x for x in all_results if x["scenario"] == key)
        # Static cost: submitted nodes × actual duration
        static_cost = cost_model.compute_cost(
            run_dict["cloud_provider"],
            run_dict["instance_type"],
            run_dict["node_count"],
            run_dict["actual_duration_hours"],
            use_spot=run_dict["use_spot"],
        )
        print(f"  {key:<22} static=${static_cost:.2f}  prevented=${r['cost_prevented_usd']:.2f}"
              f"  CPS={r['cost_prevented_usd']/static_cost:.3f}" if static_cost > 0 else "")

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        flat_rows = []
        for r in all_results:
            for ad in r["action_detail"]:
                flat_rows.append({
                    "scenario":          r["scenario"],
                    "description":       r["description"],
                    "node_count":        r["node_count"],
                    "instance_type":     r["instance_type"],
                    "total_prevented":   r["cost_prevented_usd"],
                    **ad,
                })
            if not r["action_detail"]:
                flat_rows.append({
                    "scenario":          r["scenario"],
                    "description":       r["description"],
                    "node_count":        r["node_count"],
                    "instance_type":     r["instance_type"],
                    "total_prevented":   r["cost_prevented_usd"],
                    "signal_type": "none", "action": "none",
                    "nodes_before": r["node_count"], "nodes_after": r["node_count"],
                    "trigger_minute": 0, "cost_prevented_usd": 0.0, "detail": "",
                })

        # Strip non-ASCII from detail strings so CSV writes cleanly on Windows
        for row in flat_rows:
            if "detail" in row and isinstance(row["detail"], str):
                row["detail"] = row["detail"].encode("ascii", "replace").decode("ascii")

        csv_path = out / "exp2_runtime_actions.csv"
        if flat_rows:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(flat_rows[0].keys()))
                w.writeheader()
                w.writerows(flat_rows)
            print(f"\n  Saved: {csv_path}")

        # -- Timeline chart -----------------------------------------------------
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches

            fig, axes = plt.subplots(1, 3, figsize=(15, 4))
            scenario_keys = ["A_idle_adhoc", "B_underutil_etl", "C_runaway_ml"]
            titles = [
                "Scenario A: Idle Adhoc (6 nodes, spot)",
                "Scenario B: Underutil ETL (20 nodes)",
                "Scenario C: Runaway ML (4×p3.2xlarge)",
            ]
            action_colors = {
                "SCALE_DOWN":  "#1f77b4",
                "TERMINATE":   "#d62728",
                "CHECKPOINT":  "#ff7f0e",
                "MIGRATE":     "#9467bd",
            }

            for ax, skey, title in zip(axes, scenario_keys, titles):
                r = next(x for x in all_results if x["scenario"] == skey)
                run = SCENARIOS[skey][0]
                duration = run["actual_duration_hours"] * 60

                # Timeline bar: run duration
                ax.barh(0, duration, height=0.4, color="#aec7e8", label="Run active")
                # Idle period
                idle_mins = run["idle_time_hours"] * 60
                if idle_mins > 0:
                    ax.barh(0, idle_mins, left=run["actual_duration_hours"] * 60,
                            height=0.4, color="#ffbb78", label="Idle period")

                for ad in r["action_detail"]:
                    c = action_colors.get(ad["action"], "#7f7f7f")
                    ax.axvline(ad["trigger_minute"], color=c, linewidth=2, linestyle="--")
                    ax.text(ad["trigger_minute"] + 2, 0.22,
                            f"{ad['action']}\n${ad['cost_prevented_usd']:.0f}",
                            fontsize=7, color=c, va="bottom")

                if not r["action_detail"]:
                    ax.text(duration / 2, 0, "No action fired",
                            ha="center", va="center", fontsize=9, color="grey")

                ax.set_xlim(0, max(duration + idle_mins + 30, 50))
                ax.set_ylim(-0.3, 0.5)
                ax.set_xlabel("Minutes")
                ax.set_yticks([])
                ax.set_title(title, fontsize=9)
                ax.set_title(f"{title}\n(prevented=${r['cost_prevented_usd']:.2f})", fontsize=8)

            legend_patches = [
                mpatches.Patch(color=c, label=a) for a, c in action_colors.items()
            ]
            fig.legend(handles=legend_patches, loc="lower center",
                       ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.05))
            fig.suptitle("Exp 2 — Runtime Prevention Timelines", fontsize=11)
            fig.tight_layout()

            fig_dir = out / "figures"
            fig_dir.mkdir(exist_ok=True)
            fig_path = fig_dir / "exp2_runtime_timelines.png"
            fig.savefig(fig_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"  Saved: {fig_path}")
        except ImportError:
            print("  (matplotlib not available — skipping plot)")

    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 2 — Runtime Prevention")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    run_exp2(output_dir=args.out)


if __name__ == "__main__":
    main()