"""
Table 4 — Phase 3 Convergence (Exp 6)

10 generations x 4 scenarios. Each cell: mean +/- 95% CI (from 5 seeds).
95% CI = mean +/- 1.96 * std / sqrt(5).

Gens 8-9 are baseline-only records (all zeros); included with a dagger note.

Outputs:
    results/tables/table6_convergence.tex
    results/tables/table6_convergence.csv

Run:
    python tables/table6_convergence.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results"
TABLES_DIR  = RESULTS_DIR / "tables"

N_SEEDS = 5
Z95     = 1.96

STAGE_MAP = {
    0: "pre-prov", 1: "pre-prov", 2: "pre-prov", 3: "pre-prov",
    4: "runtime",  5: "runtime",  6: "runtime",  7: "runtime",
    8: "baseline", 9: "baseline",
}

COLUMNS = [
    ("full_pbcp",      "Full PBCP"),
    ("no_phase3",      "No Phase 3"),
    ("policy_only",    "Policy-only"),
    ("embedding_only", "Embedding-only"),
]


def fmt_cell(mean: float, std: float) -> str:
    ci = Z95 * std / np.sqrt(N_SEEDS)
    if mean == 0.0 and std == 0.0:
        return "0.000"
    return f"{mean:.3f} $\\pm$ {ci:.3f}"


def make_table(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    display_rows = []
    for _, row in df.iterrows():
        gen   = int(row["generation"])
        stage = STAGE_MAP.get(gen, "")
        dagger = r"$^\dagger$" if gen >= 8 else ""
        dr = {"Gen": str(gen) + dagger, "Stage": stage}
        for key, _ in COLUMNS:
            mean = row.get(f"{key}_cps_mean", 0.0)
            std  = row.get(f"{key}_cps_std",  0.0)
            dr[key] = fmt_cell(mean, std)
        display_rows.append(dr)
    tbl = pd.DataFrame(display_rows)

    # --- LaTeX ------------------------------------------------------------------
    col_headers = " & ".join(label for _, label in COLUMNS)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Phase 3 convergence results (Exp\,6): mean CPS $\pm$ 95\,\%\,CI "
        r"across 5 seeds (42--46), 50 workloads per generation. "
        r"CI computed as $\bar{x} \pm 1.96\,\sigma/\sqrt{5}$. "
        r"$^\dagger$Gens 8--9 contain baseline-only records; "
        r"non-baseline CPS is 0 by construction.}",
        r"\label{tab:convergence}",
        r"\begin{tabular}{llcccc}",
        r"\toprule",
        f"Gen & Stage & {col_headers} \\\\",
        r"\midrule",
    ]

    prev_stage = None
    for _, row in tbl.iterrows():
        stage = row["Stage"]
        if prev_stage is not None and stage != prev_stage:
            lines.append(r"\midrule")
        prev_stage = stage

        cells = " & ".join(row[key] for key, _ in COLUMNS)
        lines.append(f"{row['Gen']} & {stage} & {cells} \\\\")

    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return tbl, "\n".join(lines)


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RESULTS_DIR / "exp6_convergence.csv")

    tbl, tex = make_table(df)

    # Plain-text display (strip LaTeX markup)
    plain = tbl.copy()
    for key, label in COLUMNS:
        plain[label] = plain[key].str.replace(r"\\pm", "±").str.replace(r"\$", "")
    print(plain[["Gen", "Stage"] + [label for _, label in COLUMNS]].to_string(index=False))

    csv_path = TABLES_DIR / "table6_convergence.csv"
    tex_path = TABLES_DIR / "table6_convergence.tex"

    # CSV: raw numeric values (not formatted cells)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    tex_path.write_text(tex, encoding="utf-8")
    print(f"\nSaved: {csv_path}")
    print(f"Saved: {tex_path}")


if __name__ == "__main__":
    main()