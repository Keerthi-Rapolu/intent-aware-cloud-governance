"""
Table 2 — Pre-Provision Prevention (Exp 1)

Two sub-tables:
  (a) Paper showcase scenario — 20-node ETL, 4 methods side-by-side
  (b) System-wide summary — 500 workloads, 4 methods + CPS by workload type

95 % CI on system-wide CPS via bootstrap (1 000 resamples over per-workload data).

Outputs:
    results/tables/table1_pre_provision.tex
    results/tables/table1_pre_provision.csv

Run:
    python tables/table1_pre_provision.py
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

# Showcase scenario results (from exp1 run, seed 42)
SHOWCASE = [
    {"Method": "Static",       "Nodes": "20 -> 20", "Pot. cost": 30.72, "Prevented": 0.00,  "CPS": 0.000, "Action": "PASS"},
    {"Method": "Rule-based",   "Nodes": "20 -> 20", "Pot. cost": 30.72, "Prevented": 0.00,  "CPS": 0.000, "Action": "SUGGEST"},
    {"Method": "No Phase 3",   "Nodes": "20 -> 20", "Pot. cost": 30.72, "Prevented": 0.15,  "CPS": 0.005, "Action": "AUTO\\_CORRECT"},
    {"Method": "Full PBCP",    "Nodes": "20 -> 10", "Pot. cost": 15.36, "Prevented": 15.36, "CPS": 0.500, "Action": "AUTO\\_CORRECT"},
]

METHOD_LABELS = {
    "static":     "Static",
    "rule_based": "Rule-based",
    "no_phase3":  "No Phase 3",
    "full_pbcp":  "Full PBCP",
}
METHOD_ORDER = ["static", "rule_based", "no_phase3", "full_pbcp"]


def bootstrap_cps_ci(pot: np.ndarray, prev: np.ndarray, n: int = N_BOOT) -> tuple[float, float]:
    idx = np.arange(len(pot))
    stats = []
    for _ in range(n):
        s = RNG.choice(idx, size=len(idx), replace=True)
        p_sum = pot[s].sum()
        stats.append(prev[s].sum() / p_sum if p_sum > 0 else 0.0)
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def make_system_table(summary: pd.DataFrame, per_wl: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    for m in METHOD_ORDER:
        r = summary[summary["method"] == m].iloc[0]
        row = {
            "Method":       METHOD_LABELS[m],
            "n":            int(r["n"]),
            "Pot. cost":    r["potential_cost"],
            "Prevented":    r["prevented_cost"],
            "CPS":          r["cps"],
            "Valid CPS":    r["valid_cps"],
            "ESR":          r["esr"],
        }
        # CI only meaningful for full_pbcp (others are ~0)
        if m == "full_pbcp":
            pot  = per_wl["potential_cost_usd"].values
            prev = per_wl["prevented_cost_usd"].values
            ci_lo, ci_hi = bootstrap_cps_ci(pot, prev)
            row["CPS CI"] = f"[{ci_lo:.4f}, {ci_hi:.4f}]"
        else:
            row["CPS CI"] = "--"
        rows.append(row)

    tbl = pd.DataFrame(rows)

    # --- LaTeX ------------------------------------------------------------------
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{System-wide pre-provision prevention results (Exp\,1, $n=500$, seed 42). "
        r"CPS\,=\,prevented\,/\,potential cost. "
        r"Valid CPS\,=\,CPS\,$\times$\,ESR. "
        r"95\,\%\,CI on Full PBCP CPS via 1\,000 bootstrap resamples over per-workload data.}",
        r"\label{tab:pre_provision}",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Method & $n$ & Pot.\ cost (\$) & Prevented (\$) & CPS & 95\,\%\,CI & Valid CPS \\",
        r"\midrule",
    ]
    for _, row in tbl.iterrows():
        is_full = row["Method"] == "Full PBCP"
        m_fmt = r"\textbf{Full PBCP}" if is_full else row["Method"]
        lines.append(
            f"{m_fmt} & {row['n']} "
            f"& {row['Pot. cost']:,.2f} "
            f"& {row['Prevented']:,.2f} "
            f"& {row['CPS']:.4f} "
            f"& {row['CPS CI']} "
            f"& {row['Valid CPS']:.4f} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return tbl, "\n".join(lines)


def make_showcase_tex() -> str:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Paper showcase scenario: 20-node ETL job (8\,h, medium priority, "
        r"AWS m5.xlarge, optimal\,=\,10 nodes). "
        r"Full PBCP detects 3.3$\times$ over-provisioning via KNN prior + EV model.}",
        r"\label{tab:showcase}",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Method & Nodes & Pot.\ cost (\$) & Prevented (\$) & CPS & Action \\",
        r"\midrule",
    ]
    for row in SHOWCASE:
        m_fmt = r"\textbf{Full PBCP}" if row["Method"] == "Full PBCP" else row["Method"]
        lines.append(
            f"{m_fmt} & {row['Nodes']} "
            f"& {row['Pot. cost']:.2f} "
            f"& {row['Prevented']:.2f} "
            f"& {row['CPS']:.3f} "
            f"& {row['Action']} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(RESULTS_DIR / "exp1_summary.csv")
    per_wl  = pd.read_csv(RESULTS_DIR / "exp1_per_workload.csv")

    print("=== Showcase scenario ===")
    sc_df = pd.DataFrame(SHOWCASE)
    print(sc_df.to_string(index=False))

    sys_tbl, sys_tex = make_system_table(summary, per_wl)
    print("\n=== System-wide summary ===")
    print(sys_tbl.to_string(index=False))

    sc_tex  = make_showcase_tex()
    full_tex = sc_tex + "\n\n" + sys_tex

    csv_path = TABLES_DIR / "table1_pre_provision.csv"
    tex_path = TABLES_DIR / "table1_pre_provision.tex"
    sys_tbl.to_csv(csv_path, index=False, encoding="utf-8")
    tex_path.write_text(full_tex, encoding="utf-8")
    print(f"\nSaved: {csv_path}")
    print(f"Saved: {tex_path}")


if __name__ == "__main__":
    main()