"""
Figure 3 — IBD Detection: IFS vs CPU-Threshold Comparison

Three-panel matplotlib figure saved as PDF + PNG:
  (a) Precision / Recall / F1 bar chart — IFS vs threshold detector
  (b) ROC-style scatter (FPR vs TPR)
  (c) type_mismatch subgroup: anomaly rate and mean IFS

Input:  results/exp3_per_run.csv
Output: results/figures/fig3_ibd_detection.{pdf,png}

Run:
    python visualization/exp3_ibd_chart.py
    python visualization/exp3_ibd_chart.py --csv results/exp3_per_run.csv --out results/figures
"""
from __future__ import annotations

import sys
import argparse
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
CSV_DEFAULT = str(RESULTS_DIR / "exp3_per_run.csv")

COLORS = {
    "threshold": "#E07B54",
    "ifs":       "#4C72B0",
    "mismatch":  "#DD8452",
    "non_mismatch": "#55A868",
}


# ── Metrics from CSV ───────────────────────────────────────────────────────────

def _compute_metrics(df: pd.DataFrame) -> dict:
    def _metrics(pred_col: str) -> dict:
        tp = int(((df["gt_anomaly"]) & (df[pred_col])).sum())
        fp = int(((~df["gt_anomaly"]) & (df[pred_col])).sum())
        tn = int(((~df["gt_anomaly"]) & (~df[pred_col])).sum())
        fn = int(((df["gt_anomaly"]) & (~df[pred_col])).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)
        fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        return {"precision": precision, "recall": recall, "f1": f1, "fpr": fpr,
                "tpr": recall}

    return {
        "threshold": _metrics("threshold_detected"),
        "ifs":       _metrics("ifs_detected"),
    }


def _mismatch_stats(df: pd.DataFrame) -> dict:
    m  = df[df["type_mismatch"]]
    nm = df[~df["type_mismatch"]]

    def _anomaly_rate(sub): return sub["gt_anomaly"].mean() if len(sub) > 0 else 0.0
    def _mean_ifs(sub):     return sub["ifs"].mean()        if len(sub) > 0 else 0.0

    return {
        "mismatch_anomaly_rate":     _anomaly_rate(m),
        "non_mismatch_anomaly_rate": _anomaly_rate(nm),
        "mismatch_mean_ifs":         _mean_ifs(m),
        "non_mismatch_mean_ifs":     _mean_ifs(nm),
        "n_mismatch":                len(m),
        "n_non_mismatch":            len(nm),
    }


# ── Plot builders ──────────────────────────────────────────────────────────────

def _panel_a(ax: plt.Axes, m: dict) -> None:
    """Bar chart: Precision, Recall, F1 for both detectors."""
    metrics   = ["Precision", "Recall", "F1"]
    thresh    = [m["threshold"]["precision"], m["threshold"]["recall"], m["threshold"]["f1"]]
    ifs_vals  = [m["ifs"]["precision"],       m["ifs"]["recall"],       m["ifs"]["f1"]]

    x     = np.arange(len(metrics))
    width = 0.32

    bars1 = ax.bar(x - width / 2, thresh,   width, label="CPU Threshold", color=COLORS["threshold"], alpha=0.88)
    bars2 = ax.bar(x + width / 2, ifs_vals, width, label="IFS Detector",  color=COLORS["ifs"],       alpha=0.88)

    for bar in list(bars1) + list(bars2):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.012,
                f"{h:.3f}", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Score")
    ax.set_title("(a) Detector Comparison", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)


def _panel_b(ax: plt.Axes, m: dict) -> None:
    """ROC-style scatter: FPR vs TPR for both detectors."""
    for name, label, color in [
        ("threshold", "CPU Threshold", COLORS["threshold"]),
        ("ifs",       "IFS Detector",  COLORS["ifs"]),
    ]:
        fpr = m[name]["fpr"]
        tpr = m[name]["tpr"]
        ax.scatter(fpr, tpr, s=120, color=color, zorder=5, label=label)
        ax.annotate(f"  {label}\n  F1={m[name]['f1']:.3f}",
                    (fpr, tpr), fontsize=7.5, va="center",
                    color=color)

    # diagonal reference
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, alpha=0.5)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate (Recall)")
    ax.set_title("(b) ROC-style View", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)


def _panel_c(ax: plt.Axes, tm: dict) -> None:
    """Grouped bar: anomaly rate and mean IFS for mismatch vs non-mismatch."""
    groups  = ["type_mismatch", "non-mismatch"]
    anomaly = [tm["mismatch_anomaly_rate"], tm["non_mismatch_anomaly_rate"]]
    mean_ifs = [tm["mismatch_mean_ifs"],    tm["non_mismatch_mean_ifs"]]

    x     = np.arange(len(groups))
    width = 0.32

    ax2 = ax.twinx()

    bars_a = ax.bar(x - width / 2, anomaly,  width, label="Anomaly Rate",
                    color=[COLORS["mismatch"], COLORS["non_mismatch"]], alpha=0.85)
    bars_i = ax2.bar(x + width / 2, mean_ifs, width, label="Mean IFS",
                     color=[COLORS["mismatch"], COLORS["non_mismatch"]], alpha=0.45,
                     hatch="//")

    for bar in bars_a:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.005,
                f"{h:.3f}", ha="center", va="bottom", fontsize=7.5)
    for bar in bars_i:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.005,
                 f"{h:.3f}", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylabel("Anomaly Rate", color=COLORS["mismatch"])
    ax2.set_ylabel("Mean IFS", color="gray")
    ax.set_ylim(0, max(anomaly) * 1.5 + 0.05)
    ax2.set_ylim(0, 1.0)
    ax.set_title("(c) type_mismatch Subgroup", fontsize=10, fontweight="bold")

    patch1 = mpatches.Patch(color=COLORS["mismatch"], alpha=0.85,  label="Anomaly Rate (solid)")
    patch2 = mpatches.Patch(color="gray",              alpha=0.45, hatch="//", label="Mean IFS (hatched)")
    ax.legend(handles=[patch1, patch2], fontsize=7.5, loc="upper right")
    ax.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)


# ── Main ───────────────────────────────────────────────────────────────────────

def make_figure(csv_path: str, out_dir: str | None = None) -> None:
    df = pd.read_csv(csv_path)
    df["gt_anomaly"]         = df["gt_anomaly"].astype(bool)
    df["threshold_detected"] = df["threshold_detected"].astype(bool)
    df["ifs_detected"]       = df["ifs_detected"].astype(bool)
    df["type_mismatch"]      = df["type_mismatch"].astype(bool)

    m  = _compute_metrics(df)
    tm = _mismatch_stats(df)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    fig.suptitle(
        "Figure 3 — IBD Detection: IFS-Based vs CPU-Threshold Detector",
        fontsize=12, fontweight="bold", y=1.01,
    )

    _panel_a(axes[0], m)
    _panel_b(axes[1], m)
    _panel_c(axes[2], tm)

    fig.tight_layout()

    out = Path(out_dir) if out_dir else FIGURES_DIR
    out.mkdir(parents=True, exist_ok=True)

    pdf_path = out / "fig3_ibd_detection.pdf"
    png_path = out / "fig3_ibd_detection.png"
    fig.savefig(pdf_path, bbox_inches="tight", dpi=300)
    fig.savefig(png_path, bbox_inches="tight", dpi=300)
    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")
    plt.close(fig)

    print(f"\nDetector metrics:")
    for det in ("threshold", "ifs"):
        dm = m[det]
        print(f"  {det:<10}  P={dm['precision']:.4f}  R={dm['recall']:.4f}  "
              f"F1={dm['f1']:.4f}  FPR={dm['fpr']:.4f}")
    print(f"\ntype_mismatch subgroup:")
    print(f"  mismatch      anomaly_rate={tm['mismatch_anomaly_rate']:.4f}  "
          f"mean_ifs={tm['mismatch_mean_ifs']:.4f}  n={tm['n_mismatch']}")
    print(f"  non-mismatch  anomaly_rate={tm['non_mismatch_anomaly_rate']:.4f}  "
          f"mean_ifs={tm['non_mismatch_mean_ifs']:.4f}  n={tm['n_non_mismatch']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Figure 3 — IBD Detection Chart")
    parser.add_argument("--csv", default=CSV_DEFAULT)
    parser.add_argument("--out", default=str(FIGURES_DIR))
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"[ERROR] {args.csv} not found — run exp3_ibd_detection.py first")
        sys.exit(1)

    make_figure(args.csv, args.out)


if __name__ == "__main__":
    main()
