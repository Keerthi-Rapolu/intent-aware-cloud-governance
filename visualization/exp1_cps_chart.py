"""
Fig 2 — Pre-Provision Prevention (Exp 1)

Two-panel figure:
  Left  — grouped bar: CPS for each method (static / rule_based / no_phase3 / full_pbcp)
           with prevented-cost labels on bars
  Right — CPS by workload type (full_pbcp only), bar chart

Run:
    python visualization/exp1_cps_chart.py
    python visualization/exp1_cps_chart.py --results results --out results/figures
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

METHOD_COLORS = {
    "static":     "#d3d3d3",
    "rule_based": "#aec7e8",
    "no_phase3":  "#ffbb78",
    "full_pbcp":  "#1f77b4",
}
METHOD_LABELS = {
    "static":     "Static",
    "rule_based": "Rule-based",
    "no_phase3":  "No Phase 3",
    "full_pbcp":  "Full PBCP",
}
WORKLOAD_COLORS = {
    "etl":          "#1f77b4",
    "adhoc":        "#ff7f0e",
    "ml_training":  "#2ca02c",
    "llm_pipeline": "#9467bd",
    "batch":        "#8c564b",
    "streaming":    "#e377c2",
}


def load_data(results_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary    = pd.read_csv(results_dir / "exp1_summary.csv")
    per_workload = pd.read_csv(results_dir / "exp1_per_workload.csv")
    return summary, per_workload


def make_figure(summary: pd.DataFrame, per_workload: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # --- Panel A: CPS by method ---
    ax = axes[0]
    methods = ["static", "rule_based", "no_phase3", "full_pbcp"]
    method_order = [m for m in methods if m in summary["method"].values]
    cps_vals = [summary.loc[summary["method"] == m, "cps"].values[0] for m in method_order]
    prevented_vals = [summary.loc[summary["method"] == m, "prevented_cost"].values[0]
                      for m in method_order]

    colors = [METHOD_COLORS.get(m, "#999") for m in method_order]
    bars = ax.bar(range(len(method_order)), cps_vals, color=colors, edgecolor="white",
                  linewidth=0.8, zorder=2)

    for bar, pv in zip(bars, prevented_vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.0002,
                f"${pv:.0f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(range(len(method_order)))
    ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in method_order], fontsize=9)
    ax.set_ylabel("CPS (Cost Prevention Score)", fontsize=10)
    ax.set_title("(a) System-wide CPS by method (n=500)", fontsize=10)
    ax.set_ylim(0, max(cps_vals) * 1.35 if max(cps_vals) > 0 else 0.05)
    ax.grid(axis="y", linewidth=0.5, alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    # --- Panel B: CPS by workload type for full_pbcp ---
    ax = axes[1]
    full = per_workload.copy()

    type_cps = (
        full.groupby("workload_type")
        .apply(lambda g: g["prevented_cost_usd"].sum() / g["potential_cost_usd"].sum()
               if g["potential_cost_usd"].sum() > 0 else 0.0)
        .rename("cps")
        .reset_index()
    )
    type_n = full.groupby("workload_type").size().rename("n").reset_index()
    type_stats = type_cps.merge(type_n, on="workload_type").sort_values("cps", ascending=False)

    bar_colors = [WORKLOAD_COLORS.get(t, "#7f7f7f") for t in type_stats["workload_type"]]
    bars2 = ax.bar(range(len(type_stats)), type_stats["cps"],
                   color=bar_colors, edgecolor="white", linewidth=0.8, zorder=2)

    for bar, (_, row) in zip(bars2, type_stats.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.001,
                f"n={row['n']}", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(range(len(type_stats)))
    ax.set_xticklabels(type_stats["workload_type"], fontsize=9, rotation=20, ha="right")
    ax.set_ylabel("CPS", fontsize=10)
    ax.set_title("(b) Full PBCP — CPS by workload type", fontsize=10)
    ax.set_ylim(0, max(type_stats["cps"]) * 1.35 if max(type_stats["cps"]) > 0 else 0.2)
    ax.grid(axis="y", linewidth=0.5, alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    fig.suptitle("Figure 2 — Pre-Provision Prevention (Exp 1)", fontsize=11, y=1.01)
    fig.tight_layout()
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 1 CPS chart")
    parser.add_argument("--results", default=str(RESULTS_DIR))
    parser.add_argument("--out",     default=str(FIGURES_DIR))
    args = parser.parse_args()

    results_dir = Path(args.results)
    out_dir     = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary, per_workload = load_data(results_dir)
    fig = make_figure(summary, per_workload)

    pdf_path = out_dir / "exp1_cps.pdf"
    png_path = out_dir / "exp1_cps.png"
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")


if __name__ == "__main__":
    main()