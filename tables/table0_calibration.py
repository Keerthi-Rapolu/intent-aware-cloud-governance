"""
Table 1 — Simulation Calibration (Exp 0)

Per-workload-type calibration metrics + overall row.
Columns: Workload Type | n | MAE | RMSE | Bias | Rel-RMSE (cost)
95 % CI on MAE/RMSE via bootstrap (1 000 resamples).

Outputs:
    results/tables/table0_calibration.tex
    results/tables/table0_calibration.csv

Run:
    python tables/table0_calibration.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results"
TABLES_DIR  = RESULTS_DIR / "tables"

N_BOOT = 1_000
RNG    = np.random.default_rng(0)


def bootstrap_ci(values: np.ndarray, stat_fn, n: int = N_BOOT) -> tuple[float, float]:
    stats = [stat_fn(RNG.choice(values, size=len(values), replace=True)) for _ in range(n)]
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def compute_stats(grp: pd.DataFrame) -> dict:
    err = grp["predicted_util"] - grp["actual_util"]
    mae  = err.abs().mean()
    rmse = np.sqrt((err ** 2).mean())
    bias = err.mean()

    cost_err = grp["predicted_pot_cost"] - grp["actual_pot_cost"]
    rel_rmse = (np.sqrt((cost_err ** 2).mean()) / grp["actual_pot_cost"].mean()
                if grp["actual_pot_cost"].mean() > 0 else 0.0)

    ci_lo, ci_hi = bootstrap_ci(err.abs().values, np.mean)
    return {
        "n":        len(grp),
        "mae":      mae,
        "ci_lo":    ci_lo,
        "ci_hi":    ci_hi,
        "rmse":     rmse,
        "bias":     bias,
        "rel_rmse": rel_rmse,
    }


def make_table(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    type_order = ["etl", "adhoc", "ml_training", "llm_pipeline", "batch", "streaming"]
    for wtype in type_order:
        grp = df[df["workload_type"] == wtype]
        if len(grp) == 0:
            continue
        s = compute_stats(grp)
        rows.append({"Workload type": wtype.replace("_", "\\_"), **s})

    # Overall row
    s_all = compute_stats(df)
    rows.append({"Workload type": r"\textbf{Overall}", **s_all})
    tbl = pd.DataFrame(rows)

    # --- LaTeX ------------------------------------------------------------------
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Simulation calibration results (Exp\,0). "
        r"Utilisation metrics compare predicted vs.\ actual CPU utilisation "
        r"across 96 workloads (seed 42). "
        r"Cost rel-RMSE compares predicted vs.\ actual potential cost. "
        r"95\,\% CI on MAE computed via 1\,000 bootstrap resamples.}",
        r"\label{tab:calibration}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Workload type & $n$ & MAE & 95\,\%\,CI & RMSE & Bias \\",
        r"\midrule",
    ]
    for _, row in tbl.iterrows():
        if row["Workload type"] == r"\textbf{Overall}":
            lines.append(r"\midrule")
        ci = f"[{row['ci_lo']:.4f},\\ {row['ci_hi']:.4f}]"
        lines.append(
            f"{row['Workload type']} & {int(row['n'])} "
            f"& {row['mae']:.4f} & {ci} "
            f"& {row['rmse']:.4f} & {row['bias']:+.4f} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    tex = "\n".join(lines)

    # CSV display
    display = tbl.copy()
    display["MAE [95% CI]"] = display.apply(
        lambda r: f"{r['mae']:.4f} [{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]", axis=1)
    display = display.rename(columns={"rmse": "RMSE", "bias": "Bias",
                                       "rel_rmse": "Rel-RMSE (cost)"})
    return display[["Workload type", "n", "MAE [95% CI]", "RMSE", "Bias"]], tex


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RESULTS_DIR / "exp0_calibration.csv")
    display, tex = make_table(df)

    print(display.to_string(index=False))

    csv_path = TABLES_DIR / "table0_calibration.csv"
    tex_path = TABLES_DIR / "table0_calibration.tex"
    display.to_csv(csv_path, index=False, encoding="utf-8")
    tex_path.write_text(tex, encoding="utf-8")
    print(f"\nSaved: {csv_path}")
    print(f"Saved: {tex_path}")


if __name__ == "__main__":
    main()