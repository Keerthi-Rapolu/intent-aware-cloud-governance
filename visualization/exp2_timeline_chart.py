"""
Fig 3 — Runtime Prevention Timelines (Exp 2)

3-panel horizontal timeline — one per scenario.
Each panel shows:
  - Blue bar  : active run duration
  - Orange bar: idle period (if any)
  - Dashed vertical line + annotation: when action fires, action type, cost prevented

Run:
    python visualization/exp2_timeline_chart.py
    python visualization/exp2_timeline_chart.py --results results --out results/figures
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

ACTION_COLORS = {
    "SCALE_DOWN": "#1f77b4",
    "TERMINATE":  "#d62728",
    "CHECKPOINT": "#ff7f0e",
    "MIGRATE":    "#9467bd",
}

SCENARIO_META = {
    "A_idle_adhoc":    {"title": "Scenario A — Idle adhoc cluster (6 nodes, spot)",
                        "duration_h": 2.0, "idle_h": 3.0},
    "B_underutil_etl": {"title": "Scenario B — Underutilised ETL (20 nodes)",
                        "duration_h": 8.0, "idle_h": 0.0},
    "C_runaway_ml":    {"title": "Scenario C — Runaway ML training (4 x p3.2xlarge)",
                        "duration_h": 12.0, "idle_h": 0.0},
}


def load_data(results_dir: Path) -> pd.DataFrame:
    return pd.read_csv(results_dir / "exp2_runtime_actions.csv")


def make_figure(df: pd.DataFrame) -> plt.Figure:
    scenario_keys = ["A_idle_adhoc", "B_underutil_etl", "C_runaway_ml"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))

    for ax, skey in zip(axes, scenario_keys):
        meta     = SCENARIO_META[skey]
        dur_min  = meta["duration_h"] * 60
        idle_min = meta["idle_h"] * 60
        total_prevented = df.loc[df["scenario"] == skey, "total_prevented"].iloc[0] \
            if len(df[df["scenario"] == skey]) else 0.0

        # Run bar
        ax.barh(0, dur_min, height=0.45, color="#aec7e8", label="Run active", zorder=2)

        # Idle bar
        if idle_min > 0:
            ax.barh(0, idle_min, left=dur_min, height=0.45,
                    color="#ffbb78", label="Idle", zorder=2)

        # Action markers
        actions = df[df["scenario"] == skey]
        for _, row in actions.iterrows():
            if row["action"] == "none":
                continue
            c = ACTION_COLORS.get(row["action"], "#7f7f7f")
            ax.axvline(row["trigger_minute"], color=c, linewidth=2.0,
                       linestyle="--", zorder=3)
            label = f"{row['action']}\n${row['cost_prevented_usd']:.0f}"
            y_offset = 0.27 if (row["trigger_minute"] / (dur_min + idle_min + 30)) > 0.7 else 0.27
            ax.text(row["trigger_minute"] + (dur_min + idle_min) * 0.015, y_offset,
                    label, fontsize=7.5, color=c, va="bottom", zorder=4)

        x_max = max(dur_min + idle_min + dur_min * 0.25, 60)
        ax.set_xlim(0, x_max)
        ax.set_ylim(-0.35, 0.6)
        ax.set_xlabel("Minutes", fontsize=9)
        ax.set_yticks([])
        ax.set_title(f"{meta['title']}\n(prevented = ${total_prevented:.2f})", fontsize=8.5)
        ax.grid(axis="x", linewidth=0.4, alpha=0.4, zorder=0)
        ax.set_axisbelow(True)

    # Legend
    legend_handles = [
        mpatches.Patch(color="#aec7e8", label="Run active"),
        mpatches.Patch(color="#ffbb78", label="Idle period"),
    ] + [mpatches.Patch(color=c, label=a) for a, c in ACTION_COLORS.items()]

    fig.legend(handles=legend_handles, loc="lower center",
               ncol=6, fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.suptitle("Figure 3 — Runtime Prevention Timelines (Exp 2)", fontsize=11, y=1.01)
    fig.tight_layout()
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 2 timeline chart")
    parser.add_argument("--results", default=str(RESULTS_DIR))
    parser.add_argument("--out",     default=str(FIGURES_DIR))
    args = parser.parse_args()

    results_dir = Path(args.results)
    out_dir     = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df  = load_data(results_dir)
    fig = make_figure(df)

    pdf_path = out_dir / "exp2_timelines.pdf"
    png_path = out_dir / "exp2_timelines.png"
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")


if __name__ == "__main__":
    main()