from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
PAPER_DIR = REPO_ROOT / "paper"
FIGURES_DIR = PAPER_DIR / "figures"
TABLES_DIR = PAPER_DIR / "tables"
RESULTS_DIR = REPO_ROOT / "results"
RESULTS_FIGURES = RESULTS_DIR / "figures"
RESULTS_TABLES = RESULTS_DIR / "tables"


def ensure_dirs() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def build_architecture_figure() -> None:
    fig, ax = plt.subplots(figsize=(12, 3.8))
    ax.axis("off")

    groups = [
        ("Prevent", 0.05, 0.57, 0.52, 0.28, "#d9dee5"),
        ("Correct", 0.59, 0.57, 0.16, 0.28, "#e4e8ec"),
        ("Learn", 0.77, 0.57, 0.18, 0.28, "#dde4e9"),
    ]
    for label, x, y, w, h, color in groups:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="#7a8793", linewidth=1.0))
        ax.text(x + 0.01, y + h + 0.015, label, fontsize=11, fontweight="bold", color="#334155")

    labels = [
        "Natural Language\nWorkload",
        "Intent Inference",
        "Historical Similarity\nRetrieval (FAISS)",
        "Pre-Execution\nSimulation",
        "EV Decision\nEngine",
        "Runtime\nGovernance",
        "CPS / ESR\nTracking",
        "Policy Learning\nLoop",
    ]
    x_positions = np.linspace(0.08, 0.92, len(labels))
    y = 0.68
    box_w = 0.1
    box_h = 0.1

    for i, (x, label) in enumerate(zip(x_positions, labels)):
        ax.add_patch(
            Rectangle(
                (x - box_w / 2, y - box_h / 2),
                box_w,
                box_h,
                facecolor="#ffffff",
                edgecolor="#4b5563",
                linewidth=1.1,
            )
        )
        ax.text(x, y, label, ha="center", va="center", fontsize=9, color="#111827")
        if i < len(labels) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + box_w / 2, y),
                    (x_positions[i + 1] - box_w / 2, y),
                    arrowstyle="-|>",
                    mutation_scale=12,
                    linewidth=1.2,
                    color="#4b5563",
                )
            )

    ax.text(0.50, 0.38, "Prevent -> Correct -> Learn pipeline", ha="center", fontsize=10, color="#475569")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "architecture_overview.pdf", bbox_inches="tight")
    plt.close(fig)


def stage_exp0_figure() -> None:
    src = RESULTS_FIGURES / "exp0_calibration.pdf"
    raster = RESULTS_FIGURES / "exp0_calibration_patched.png"
    dst = FIGURES_DIR / "exp0_calibration.pdf"
    if not src.exists():
        raise FileNotFoundError(f"Missing source figure: {src}")

    pdftocairo = shutil.which("pdftocairo")
    if not pdftocairo:
        raise FileNotFoundError("pdftocairo is required to patch exp0_calibration.pdf")

    subprocess.run(
        [pdftocairo, "-png", "-singlefile", "-r", "300", str(src), str(raster.with_suffix(""))],
        check=True,
    )

    image = plt.imread(raster)
    height, width = image.shape[:2]
    fig, ax = plt.subplots(figsize=(width / 300, height / 300), dpi=300)
    ax.imshow(image)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")

    overlays = [
        (900, 20, 1180, 95),
        (1860, 150, 980, 90),
        (1750, 245, 600, 85),
    ]
    for x, y, w, h in overlays:
        ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor="none", zorder=3))

    ax.text(width / 2, 68, "Simulation Calibration (Exp 0)", ha="center", va="center", fontsize=24, color="black", zorder=4)
    ax.text(2350, 195, "(b) Potential cost - rel-RMSE = 0.306", ha="center", va="center", fontsize=18, color="black", zorder=4)
    ax.text(2050, 292, "rel-RMSE = 0.306", ha="center", va="center", fontsize=18, color="#333333", zorder=4)

    fig.savefig(dst, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def _extract_showcase_metrics() -> dict[str, str]:
    tex = (RESULTS_TABLES / "table1_pre_provision.tex").read_text(encoding="utf-8")
    match = re.search(
        r"\\textbf\{Full PBCP\}\s*&\s*(\d+)\s*->\s*(\d+)\s*&\s*([0-9.]+)\s*&\s*([0-9.]+)\s*&\s*([0-9.]+)",
        tex,
    )
    if not match:
        raise ValueError("Could not extract showcase row from table1_pre_provision.tex")
    requested, corrected, right_sized_cost, prevented, cps = match.groups()
    return {
        "requested": requested,
        "corrected": corrected,
        "right_sized_cost": right_sized_cost,
        "prevented": prevented,
        "cps": cps,
    }


def build_exp1_figure() -> None:
    metrics = _extract_showcase_metrics()
    requested = int(metrics["requested"])
    corrected = int(metrics["corrected"])
    prevented = float(metrics["prevented"])
    cps = float(metrics["cps"])

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bars = ax.bar(
        ["Requested", "Auto-corrected"],
        [requested, corrected],
        color=["#cbd5e1", "#64748b"],
        edgecolor="white",
        linewidth=1.0,
        width=0.55,
    )
    for bar, value in zip(bars, [requested, corrected]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.4, f"{value} nodes", ha="center", fontsize=10)

    ax.annotate(
        "",
        xy=(1, corrected + 0.2),
        xytext=(0, requested - 0.2),
        arrowprops=dict(arrowstyle="->", lw=1.6, color="#1f2937"),
    )
    ax.text(
        0.5,
        requested + 1.6,
        f"AUTO_CORRECT\nPrevented cost = ${prevented:.2f}\nCPS = {cps:.3f}",
        ha="center",
        va="bottom",
        fontsize=10,
        color="#111827",
    )
    ax.set_ylabel("Allocated nodes")
    ax.set_ylim(0, requested + 5)
    ax.set_title("Showcase pre-billing intervention: ETL cluster right-sizing", fontsize=11)
    ax.grid(axis="y", linewidth=0.4, alpha=0.35)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "exp1_preprovision.pdf", bbox_inches="tight")
    plt.close(fig)


def build_exp2_figure() -> None:
    df = pd.read_csv(RESULTS_TABLES / "table2_runtime.csv")
    row = df[df["Scenario"].str.startswith("C - Runaway ML")].iloc[0]
    prevented = float(row["Prevented"])
    cps = float(row["CPS"])
    trigger_min = int(str(row["Trigger (min)"]).split(",")[0])
    unchanged_cost = float(row["Unchanged cost"])
    actual_cost = unchanged_cost - prevented

    end_no_intervention = 720
    x = np.array([0, trigger_min, end_no_intervention])
    y_baseline = np.array([0.0, actual_cost, unchanged_cost])
    y_intervened = np.array([0.0, actual_cost, actual_cost])

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(8.0, 5.4), sharex=True, gridspec_kw={"height_ratios": [1, 1.2]})

    ax0.hlines(0.5, 0, trigger_min, color="#64748b", linewidth=7, label="Runaway execution")
    ax0.hlines(0.5, trigger_min, end_no_intervention, color="#cbd5e1", linewidth=7, linestyle="--", label="Cost avoided window")
    ax0.axvline(trigger_min, color="#b91c1c", linewidth=1.6, linestyle="--")
    ax0.text(10, 0.8, "Launch", fontsize=9)
    ax0.text(trigger_min + 8, 0.8, "CHECKPOINT intervention", fontsize=9, color="#7f1d1d")
    ax0.set_yticks([])
    ax0.set_ylim(0.2, 1.0)
    ax0.set_title("Runtime governance during runaway ML training", fontsize=11)
    ax0.legend(loc="upper right", fontsize=8, frameon=False)

    ax1.plot(x, y_baseline, color="#94a3b8", linewidth=2.0, label="No intervention")
    ax1.plot(x, y_intervened, color="#1f2937", linewidth=2.2, label="With runtime governance")
    ax1.fill_between([trigger_min, end_no_intervention], [actual_cost, actual_cost], [unchanged_cost, unchanged_cost], color="#cbd5e1", alpha=0.45)
    ax1.annotate(
        f"Prevented = ${prevented:.2f}\nCPS = {cps:.3f}",
        xy=(trigger_min + 70, actual_cost + prevented * 0.45),
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#94a3b8"),
    )
    ax1.set_xlabel("Elapsed time (minutes)")
    ax1.set_ylabel("Accumulated cost ($)")
    ax1.grid(linewidth=0.4, alpha=0.35)
    ax1.legend(loc="upper left", fontsize=8, frameon=False)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "exp2_runtime_timeline.pdf", bbox_inches="tight")
    plt.close(fig)


def build_exp3_figure() -> None:
    df = pd.read_csv(RESULTS_TABLES / "table3_ibd.csv")
    metrics = df[df["sub_table"] == "a"].copy()
    metrics["Detector"] = metrics["detector"].map({"threshold": "CPU threshold", "ifs": "IFS detector"})

    categories = ["precision", "recall", "f1"]
    labels = ["Precision", "Recall", "F1"]
    x = np.arange(len(labels))
    width = 0.34

    thresh = metrics[metrics["detector"] == "threshold"].iloc[0]
    ifs = metrics[metrics["detector"] == "ifs"].iloc[0]

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    bars1 = ax.bar(x - width / 2, [thresh[c] for c in categories], width, color="#cbd5e1", label="CPU threshold")
    bars2 = ax.bar(x + width / 2, [ifs[c] for c in categories], width, color="#475569", label="IFS detector")

    for bars in (bars1, bars2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.015, f"{bar.get_height():.3f}", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Score")
    ax.set_title("Detector comparison for intent-behavior divergence", fontsize=11)
    ax.grid(axis="y", linewidth=0.4, alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "exp3_detector_comparison.pdf", bbox_inches="tight")
    plt.close(fig)


def build_exp6_figure() -> None:
    df = pd.read_csv(RESULTS_TABLES / "table6_convergence.csv")
    gens = df["generation"].to_numpy()
    full = df["full_pbcp_cps_mean"].to_numpy()
    no_phase3 = df["no_phase3_cps_mean"].to_numpy()

    full_peak = float(full.max())
    no3_peak = float(no_phase3.max())
    peak_gen = int(df.loc[df["full_pbcp_cps_mean"].idxmax(), "generation"])
    ratio = round(full_peak / no3_peak) if no3_peak > 0 else np.nan

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.plot(gens, full, color="#1f2937", linewidth=2.3, marker="o", label="Full PBCP")
    ax.plot(gens, no_phase3, color="#94a3b8", linewidth=2.0, linestyle="--", marker="s", label="No Phase 3")
    ax.axvline(3.5, color="#cbd5e1", linewidth=1.0, linestyle="--")
    ax.axvline(7.5, color="#cbd5e1", linewidth=1.0, linestyle="--")
    ax.annotate(
        f"Peak CPS = {full_peak:.3f}\n{ratio:.0f}x vs No Phase 3",
        xy=(peak_gen, full_peak),
        xytext=(peak_gen + 0.6, full_peak - 0.12),
        arrowprops=dict(arrowstyle="->", lw=1.2, color="#111827"),
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#cbd5e1"),
    )
    ax.set_xlabel("Policy learning iteration")
    ax.set_ylabel("CPS")
    ax.set_xticks(gens)
    ax.set_ylim(0, max(full_peak * 1.15, 0.8))
    ax.set_title("Policy learning convergence under Full PBCP and No Phase 3", fontsize=11)
    ax.grid(linewidth=0.4, alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "exp6_convergence.pdf", bbox_inches="tight")
    plt.close(fig)


def build_related_work_table() -> None:
    tex = r"""
\begin{tabular}{p{3.4cm}p{2.2cm}p{2.4cm}p{2.3cm}p{2.7cm}}
\toprule
System Category & Timing & Semantic Intent & Runtime Correction & Pre-Billing Governance \\
\midrule
Reactive cloud optimization & Post-billing & No & Limited & No \\
Utilization anomaly detection & Post-execution & No & No & No \\
Policy governance systems & Pre-execution & Limited & No & Partial \\
AIOps systems & Runtime & No & Yes & No \\
\textbf{PBCP} & \textbf{Pre-billing} & \textbf{Yes} & \textbf{Yes} & \textbf{Yes} \\
\bottomrule
\end{tabular}
"""
    write_text(TABLES_DIR / "related_work.tex", tex)


def build_exp0_table() -> None:
    tex = r"""
\begin{tabular}{lcc}
\toprule
Metric & Value & Gate \\
\midrule
Utilization MAE & 0.054 & $< 0.10$ \\
Cost rel-RMSE & 0.306 & $< 0.40$ \\
\bottomrule
\end{tabular}
"""
    write_text(TABLES_DIR / "exp0_results.tex", tex)


def build_exp2_table() -> None:
    df = pd.read_csv(RESULTS_TABLES / "table2_runtime.csv")
    rows = []
    for _, row in df.iterrows():
        workload = str(row["Scenario"]).replace(" - ", " ")
        action = str(row["Action(s)"]).replace("_", r"\_")
        rows.append(
            f"{workload} & {action} & ${float(row['Prevented']):.2f}$ & {float(row['CPS']):.3f} \\\\"
        )
    tex = "\n".join(
        [
            r"\begin{tabular}{p{4.2cm}p{3.1cm}cc}",
            r"\toprule",
            r"Workload & Intervention & Prevented cost & CPS \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    write_text(TABLES_DIR / "exp2_runtime_cases.tex", tex)


def build_exp3_table() -> None:
    df = pd.read_csv(RESULTS_TABLES / "table3_ibd.csv")
    df = df[df["sub_table"] == "a"].copy()
    names = {"threshold": "CPU threshold", "ifs": "IFS detector"}
    rows = []
    for _, row in df.iterrows():
        rows.append(
            f"{names[row['detector']]} & {float(row['precision']):.4f} & {float(row['recall']):.4f} & {float(row['f1']):.4f} \\\\"
        )
    tex = "\n".join(
        [
            r"\begin{tabular}{lccc}",
            r"\toprule",
            r"Detector & Precision & Recall & F1 \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    write_text(TABLES_DIR / "exp3_detector_metrics.tex", tex)


def build_exp6_table() -> None:
    df = pd.read_csv(RESULTS_TABLES / "table6_convergence.csv")
    variants = [
        ("Full PBCP", "full_pbcp_cps_mean"),
        ("No Phase 3", "no_phase3_cps_mean"),
        ("Policy-only", "policy_only_cps_mean"),
        ("Embedding-only", "embedding_only_cps_mean"),
    ]
    rows = []
    for label, col in variants:
        peak_idx = df[col].idxmax()
        peak_val = float(df.loc[peak_idx, col])
        peak_gen = int(df.loc[peak_idx, "generation"])
        rows.append(f"{label} & {peak_val:.3f} & {peak_gen} \\\\")
    tex = "\n".join(
        [
            r"\begin{tabular}{lcc}",
            r"\toprule",
            r"Variant & Peak CPS & Peak generation \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    write_text(TABLES_DIR / "exp6_ablation.tex", tex)


def main() -> None:
    ensure_dirs()
    build_architecture_figure()
    stage_exp0_figure()
    build_exp1_figure()
    build_exp2_figure()
    build_exp3_figure()
    build_exp6_figure()
    build_related_work_table()
    build_exp0_table()
    build_exp2_table()
    build_exp3_table()
    build_exp6_table()
    print("Paper artifacts generated.")


if __name__ == "__main__":
    main()
