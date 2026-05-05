"""
Fig 4 — Phase 3 Convergence (Exp 6)

Single figure: 4 curves (Full PBCP / No Phase 3 / Policy-only / Embedding-only)
with +/-1 std shaded bands, over 10 generations (x-axis) and 5 seeds.

Vertical dividers show where the stage changes:
  Gens 0-3  -> pre_provision stage
  Gens 4-7  -> runtime stage
  Gens 8-9  -> baseline records only (CPS=0 expected)

Run:
    python visualization/exp6_convergence_chart.py
    python visualization/exp6_convergence_chart.py --results results --out results/figures
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

CURVES = [
    ("full_pbcp",       "Full PBCP",       "#1f77b4", "-",  2.0),
    ("no_phase3",       "No Phase 3",      "#ff7f0e", "--", 1.5),
    ("policy_only",     "Policy-only",     "#2ca02c", ":",  1.5),
    ("embedding_only",  "Embedding-only",  "#9467bd", "-.", 1.5),
]


def load_data(results_dir: Path) -> pd.DataFrame:
    return pd.read_csv(results_dir / "exp6_convergence.csv")


def make_figure(df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    gens = df["generation"].values

    for key, label, color, ls, lw in CURVES:
        mean_col = f"{key}_cps_mean"
        std_col  = f"{key}_cps_std"
        if mean_col not in df.columns:
            continue
        mean = df[mean_col].values
        std  = df[std_col].values if std_col in df.columns else np.zeros_like(mean)

        ax.plot(gens, mean, color=color, linestyle=ls, linewidth=lw, label=label, zorder=3)
        ax.fill_between(gens, mean - std, mean + std,
                        color=color, alpha=0.15, zorder=2)

    # Stage dividers
    ax.axvline(3.5, color="grey", linewidth=0.9, linestyle="--", alpha=0.6, zorder=1)
    ax.axvline(7.5, color="grey", linewidth=0.9, linestyle="--", alpha=0.6, zorder=1)

    # Stage labels
    y_annot = ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 0.8
    ax.text(1.75, 0.02, "Pre-provision\ngens 0-3", ha="center", va="bottom",
            fontsize=7.5, color="grey", transform=ax.get_xaxis_transform())
    ax.text(5.75, 0.02, "Runtime\ngens 4-7", ha="center", va="bottom",
            fontsize=7.5, color="grey", transform=ax.get_xaxis_transform())
    ax.text(8.5,  0.02, "Baseline\ngens 8-9", ha="center", va="bottom",
            fontsize=7.5, color="grey", transform=ax.get_xaxis_transform())

    ax.set_xlabel("Generation", fontsize=10)
    ax.set_ylabel("Mean CPS (+/- 1 std, 5 seeds)", fontsize=10)
    ax.set_xticks(gens)
    ax.set_xlim(-0.3, len(gens) - 0.7)
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(linewidth=0.4, alpha=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Figure 4 — Phase 3 Convergence (Exp 6): Full PBCP vs. ablations",
                 fontsize=10)

    fig.tight_layout()
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 6 convergence chart")
    parser.add_argument("--results", default=str(RESULTS_DIR))
    parser.add_argument("--out",     default=str(FIGURES_DIR))
    args = parser.parse_args()

    results_dir = Path(args.results)
    out_dir     = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df  = load_data(results_dir)
    fig = make_figure(df)

    pdf_path = out_dir / "exp6_convergence.pdf"
    png_path = out_dir / "exp6_convergence.png"
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")


if __name__ == "__main__":
    main()