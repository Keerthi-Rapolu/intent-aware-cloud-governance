"""
Simulation Calibration (Exp 0)

Two-panel figure:
  Left  - scatter: predicted vs. actual utilization, coloured by workload type
  Right - scatter: predicted vs. actual potential cost, coloured by workload type

Both panels include a y=x identity line and per-type legend.

Run:
    python visualization/exp0_calibration_plot.py
    python visualization/exp0_calibration_plot.py --results results --out results/figures
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

WORKLOAD_COLORS = {
    "etl": "#1f77b4",
    "adhoc": "#ff7f0e",
    "ml_training": "#2ca02c",
    "llm_pipeline": "#9467bd",
    "batch": "#8c564b",
    "streaming": "#e377c2",
}


def load_data(results_dir: Path) -> pd.DataFrame:
    return pd.read_csv(results_dir / "exp0_calibration.csv")


def _identity_line(ax, lo: float, hi: float) -> None:
    ax.plot([lo, hi], [lo, hi], color="black", linewidth=1.0, linestyle="--", label="y = x", zorder=1)


def make_figure(df: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    ax = axes[0]
    for wtype, grp in df.groupby("workload_type"):
        color = WORKLOAD_COLORS.get(wtype, "#7f7f7f")
        ax.scatter(grp["actual_util"], grp["predicted_util"], color=color, label=wtype, s=28, alpha=0.75, edgecolors="none")

    lo, hi = 0.0, 1.05
    _identity_line(ax, lo, hi)
    mae = (df["predicted_util"] - df["actual_util"]).abs().mean()
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("Actual utilization", fontsize=10)
    ax.set_ylabel("Predicted utilization", fontsize=10)
    ax.set_title(f"(a) Utilization - MAE = {mae:.4f}", fontsize=10)
    ax.annotate(f"MAE = {mae:.4f}", xy=(0.05, 0.92), xycoords="axes fraction", fontsize=9, color="#333333")

    ax = axes[1]
    for wtype, grp in df.groupby("workload_type"):
        color = WORKLOAD_COLORS.get(wtype, "#7f7f7f")
        ax.scatter(grp["actual_pot_cost"], grp["predicted_pot_cost"], color=color, label=wtype, s=28, alpha=0.75, edgecolors="none")

    cost_lo = 0.0
    cost_hi = max(df["actual_pot_cost"].max(), df["predicted_pot_cost"].max()) * 1.08
    _identity_line(ax, cost_lo, cost_hi)
    rel_rmse = np.sqrt(((df["predicted_pot_cost"] - df["actual_pot_cost"]) ** 2).mean()) / df["actual_pot_cost"].mean()
    ax.set_xlim(cost_lo, cost_hi)
    ax.set_ylim(cost_lo, cost_hi)
    ax.set_xlabel("Actual potential cost ($)", fontsize=10)
    ax.set_ylabel("Predicted potential cost ($)", fontsize=10)
    ax.set_title(f"(b) Potential cost - rel-RMSE = {rel_rmse:.4f}", fontsize=10)
    ax.annotate(f"rel-RMSE = {rel_rmse:.4f}", xy=(0.05, 0.92), xycoords="axes fraction", fontsize=9, color="#333333")

    handles = [
        mlines.Line2D([], [], color=color, marker="o", linestyle="None", markersize=6, label=wtype)
        for wtype, color in WORKLOAD_COLORS.items()
    ]
    handles.append(mlines.Line2D([], [], color="black", linestyle="--", linewidth=1.0, label="y = x"))
    fig.legend(handles=handles, loc="lower center", ncol=7, fontsize=8, bbox_to_anchor=(0.5, -0.06))

    fig.suptitle("Simulation Calibration (Exp 0)", fontsize=11, y=1.01)
    fig.tight_layout()
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 0 calibration figure")
    parser.add_argument("--results", default=str(RESULTS_DIR))
    parser.add_argument("--out", default=str(FIGURES_DIR))
    args = parser.parse_args()

    results_dir = Path(args.results)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(results_dir)
    fig = make_figure(df)

    pdf_path = out_dir / "exp0_calibration.pdf"
    png_path = out_dir / "exp0_calibration.png"
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")


if __name__ == "__main__":
    main()
