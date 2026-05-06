"""
Fig 5 — System Roll-up Dashboard (Exp 5)

4-panel figure:
  Panel 1 (top-left):   CPS by stage — grouped bar (pre_provision / runtime / ai_workload)
  Panel 2 (top-right):  CPS by workload type — horizontal bar, sorted descending
  Panel 3 (bottom-left):  IFS distribution — histogram with 4 colour bands
  Panel 4 (bottom-right): IBD pie — well_aligned / minor / significant / severe

Input:  results/exp5_rollup.csv
Output: results/figures/exp5_dashboard.pdf + .png at 300 dpi

Run:
    python visualization/exp5_dashboard.py
    python visualization/exp5_dashboard.py --results results --out results/figures
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

STAGE_COLORS = {
    "pre_provision": "#1f77b4",
    "runtime":       "#ff7f0e",
    "ai_workload":   "#9467bd",
    "baseline":      "#d3d3d3",
}
WORKLOAD_COLORS = {
    "etl":          "#1f77b4",
    "adhoc":        "#ff7f0e",
    "ml_training":  "#2ca02c",
    "llm_pipeline": "#9467bd",
    "batch":        "#8c564b",
    "streaming":    "#e377c2",
}
IFS_BAND_COLORS = {
    "well_aligned": "#2ca02c",
    "minor":        "#98df8a",
    "significant":  "#ffbb78",
    "severe":       "#d62728",
}
IFS_BANDS = [
    (0.85, 1.00, "well_aligned",  "#2ca02c"),
    (0.70, 0.85, "minor",         "#98df8a"),
    (0.50, 0.70, "significant",   "#ffbb78"),
    (0.00, 0.50, "severe",        "#d62728"),
]


def load_data(results_dir: Path) -> pd.DataFrame:
    return pd.read_csv(results_dir / "exp5_rollup.csv")


def _compute_stage_cps(df: pd.DataFrame) -> dict[str, float]:
    """Compute CPS per stage from per-workload data (intervention proxy)."""
    stage_map = {
        "AUTO_CORRECT": "pre_provision",
        "REJECT":       "pre_provision",
        "SUGGEST":      "pre_provision",
        "PASS":         "baseline",
    }
    by_stage: dict[str, dict[str, float]] = {}
    for _, row in df.iterrows():
        stage = stage_map.get(row.get("intervention", "PASS"), "baseline")
        if stage not in by_stage:
            by_stage[stage] = {"prevented": 0.0, "potential": 0.0}
        by_stage[stage]["prevented"] += float(row.get("prevented_cost_usd", 0))
        by_stage[stage]["potential"] += float(row.get("potential_cost_usd", 0))

    result = {}
    for stage, vals in by_stage.items():
        result[stage] = round(vals["prevented"] / vals["potential"], 4) \
            if vals["potential"] > 0 else 0.0
    return result


def _compute_type_cps(df: pd.DataFrame) -> pd.Series:
    def _cps(g):
        pot = g["potential_cost_usd"].sum()
        return g["prevented_cost_usd"].sum() / pot if pot > 0 else 0.0
    return df.groupby("workload_type").apply(_cps).rename("cps")


def make_figure(df: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # -- Panel 1: CPS by stage --
    ax = axes[0, 0]
    stage_cps = _compute_stage_cps(df)
    active_stages = {s: v for s, v in stage_cps.items() if s != "baseline"}
    if not active_stages:
        active_stages = {"pre_provision": 0.0, "runtime": 0.0}

    stage_names = sorted(active_stages.keys())
    cps_vals    = [active_stages[s] for s in stage_names]
    colors      = [STAGE_COLORS.get(s, "#7f7f7f") for s in stage_names]
    bars = ax.bar(range(len(stage_names)), cps_vals, color=colors, edgecolor="white",
                  linewidth=0.8, zorder=2)
    for bar, val in zip(bars, cps_vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(len(stage_names)))
    ax.set_xticklabels([s.replace("_", "\n") for s in stage_names], fontsize=9)
    ax.set_ylabel("CPS (Cost Prevention Score)", fontsize=10)
    ax.set_title("(a) CPS by intervention stage", fontsize=10)
    ax.set_ylim(0, max(cps_vals + [0.1]) * 1.35)
    ax.grid(axis="y", linewidth=0.5, alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    # -- Panel 2: CPS by workload type --
    ax = axes[0, 1]
    type_cps = _compute_type_cps(df).sort_values(ascending=True)
    bar_colors = [WORKLOAD_COLORS.get(t, "#7f7f7f") for t in type_cps.index]
    bars2 = ax.barh(range(len(type_cps)), type_cps.values,
                    color=bar_colors, edgecolor="white", linewidth=0.8, zorder=2)
    for bar, val in zip(bars2, type_cps.values):
        ax.text(val + 0.002, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=8.5)
    ax.set_yticks(range(len(type_cps)))
    ax.set_yticklabels(type_cps.index, fontsize=9)
    ax.set_xlabel("CPS", fontsize=10)
    ax.set_title("(b) CPS by workload type", fontsize=10)
    ax.set_xlim(0, max(type_cps.values.tolist() + [0.1]) * 1.35)
    ax.grid(axis="x", linewidth=0.5, alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    # -- Panel 3: IFS distribution histogram --
    ax = axes[1, 0]
    ifs_vals = df["ifs"].dropna().values
    bins = np.linspace(0, 1, 21)
    n_total = len(ifs_vals)

    for lo, hi, label, color in IFS_BANDS:
        mask = (ifs_vals >= lo) & (ifs_vals < hi)
        if label == "well_aligned":
            mask = (ifs_vals >= lo) & (ifs_vals <= hi)
        band_vals = ifs_vals[mask]
        band_bins = [b for b in bins if lo <= b <= hi]
        if len(band_bins) < 2:
            band_bins = [lo, hi]
        ax.hist(band_vals, bins=band_bins, color=color, edgecolor="white",
                linewidth=0.5, label=f"{label} ({len(band_vals)/n_total:.0%})", zorder=2)

    ax.axvline(0.70, color="black", linestyle="--", linewidth=1.0, label="IBD threshold (0.70)")
    ax.set_xlabel("IFS (Intent-Fit Score)", fontsize=10)
    ax.set_ylabel("Workload count", fontsize=10)
    ax.set_title("(c) IFS distribution", fontsize=10)
    ax.set_xlim(0, 1)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", linewidth=0.5, alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    # -- Panel 4: IBD category pie --
    ax = axes[1, 1]
    cat_order  = ["well_aligned", "minor", "significant", "severe"]
    cat_labels = ["Well-aligned\n(≥0.85)", "Minor\n(0.70–0.85)",
                  "Significant\n(0.50–0.70)", "Severe\n(<0.50)"]
    cat_counts = [int((df["ifs_category"] == c).sum()) for c in cat_order]
    cat_colors = [IFS_BAND_COLORS[c] for c in cat_order]
    non_zero   = [(c, l, col) for c, l, col in zip(cat_counts, cat_labels, cat_colors) if c > 0]

    if non_zero:
        counts, labels, colors_pie = zip(*non_zero)
        wedges, texts, autotexts = ax.pie(
            counts, labels=labels, colors=colors_pie,
            autopct="%1.1f%%", startangle=90,
            textprops={"fontsize": 8.5},
            wedgeprops={"edgecolor": "white", "linewidth": 1.0},
        )
        for at in autotexts:
            at.set_fontsize(8)
    ax.set_title("(d) Intent-Behavior Deviation (IBD) breakdown", fontsize=10)

    fig.suptitle("Figure 5 — System Roll-up: Dual-Metric Evaluation (Exp 5)", fontsize=12, y=1.01)
    fig.tight_layout()
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 5 dashboard")
    parser.add_argument("--results", default=str(RESULTS_DIR))
    parser.add_argument("--out",     default=str(FIGURES_DIR))
    args = parser.parse_args()

    results_dir = Path(args.results)
    out_dir     = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df  = load_data(results_dir)
    fig = make_figure(df)

    pdf_path = out_dir / "exp5_dashboard.pdf"
    png_path = out_dir / "exp5_dashboard.png"
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")


if __name__ == "__main__":
    main()
