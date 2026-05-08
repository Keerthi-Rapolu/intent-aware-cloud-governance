"""
Table 3 - Runtime Prevention (Exp 2)

One row per scenario. Columns:
  Scenario | Instance | Nodes | Unchanged cost | Prevented | CPS | Action(s) | Trigger (min)

Unchanged costs are computed as the cost of running the submitted configuration
without intervention, including idle or overrun time when applicable.

Outputs:
    results/tables/table2_runtime.tex
    results/tables/table2_runtime.csv

Run:
    python tables/table2_runtime.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.exp2_runtime_prevention import SCENARIOS
from simulation_engine.cost_model import CloudCostModel

RESULTS_DIR = Path(__file__).parent.parent / "results"
TABLES_DIR = RESULTS_DIR / "tables"

SCENARIO_LABELS = {
    "A_idle_adhoc": "A - Idle adhoc",
    "B_underutil_etl": "B - Underutil ETL",
    "C_runaway_ml": "C - Runaway ML",
}

SCENARIO_NOTES = {
    "A_idle_adhoc": "6 nodes, spot, 3\\,h idle",
    "B_underutil_etl": "20 nodes, CPU avg 18\\,\\%",
    "C_runaway_ml": "4 nodes p3.2xlarge, 3$\\times$ duration",
}


def unchanged_cost(skey: str) -> float:
    run = SCENARIOS[skey][0]
    hours = float(run["actual_duration_hours"]) + float(run.get("idle_time_hours", 0.0))
    cost_model = CloudCostModel()
    return round(
        cost_model.compute_cost(
            run["cloud_provider"],
            run["instance_type"],
            int(run["node_count"]),
            hours,
            use_spot=bool(run["use_spot"]),
        ),
        2,
    )


def make_table(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    for skey, label in SCENARIO_LABELS.items():
        grp = df[df["scenario"] == skey]
        actions_grp = grp[grp["action"] != "none"]

        exposure = unchanged_cost(skey)
        prevented = grp["total_prevented"].iloc[0] if len(grp) else 0.0
        cps = prevented / exposure if exposure > 0 else 0.0
        actions = ", ".join(actions_grp["action"].tolist()) if len(actions_grp) else "-"
        triggers = ", ".join(str(int(t)) for t in actions_grp["trigger_minute"].tolist()) if len(actions_grp) else "-"
        instance = grp["instance_type"].iloc[0] if len(grp) else "-"
        nodes = int(grp["node_count"].iloc[0]) if len(grp) else 0

        rows.append(
            {
                "Scenario": label,
                "Note": SCENARIO_NOTES[skey],
                "Instance": instance,
                "Nodes": nodes,
                "Unchanged cost": exposure,
                "Prevented": round(prevented, 2),
                "CPS": round(cps, 3),
                "Action(s)": actions,
                "Trigger (min)": triggers,
            }
        )

    tbl = pd.DataFrame(rows)

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Runtime cost prevention results (Exp\,2). "
        r"Unchanged cost = cost of running the submitted configuration without intervention, "
        r"including idle or overrun time; "
        r"Prevented = cost saved by optimizer action(s); "
        r"CPS = prevented\,/\,unchanged cost, which keeps runtime CPS bounded by 1.}",
        r"\label{tab:runtime}",
        r"\begin{tabular}{llrrrrl}",
        r"\toprule",
        r"Scenario & Config & Unchanged (\$) & Prevented (\$) & CPS & Action(s) & Trigger (min) \\",
        r"\midrule",
    ]
    for _, row in tbl.iterrows():
        lines.append(
            f"{row['Scenario']} & {row['Note']} "
            f"& {row['Unchanged cost']:.2f} "
            f"& {row['Prevented']:.2f} "
            f"& {row['CPS']:.3f} "
            f"& {row['Action(s)']} "
            f"& {row['Trigger (min)']} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return tbl, "\n".join(lines)


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RESULTS_DIR / "exp2_runtime_actions.csv")

    tbl, tex = make_table(df)
    print(tbl.to_string(index=False))

    csv_path = TABLES_DIR / "table2_runtime.csv"
    tex_path = TABLES_DIR / "table2_runtime.tex"
    tbl.to_csv(csv_path, index=False, encoding="utf-8")
    tex_path.write_text(tex, encoding="utf-8")
    print(f"\nSaved: {csv_path}")
    print(f"Saved: {tex_path}")


if __name__ == "__main__":
    main()
