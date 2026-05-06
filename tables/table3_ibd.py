"""
Table 3 — IBD Detection: IFS vs CPU-Threshold Detector (Exp 3)

Two sub-tables in booktabs LaTeX format for Section 7 of the paper:
  (a) Detector comparison — Precision, Recall, F1, FPR
  (b) type_mismatch subgroup — anomaly rate, mean IFS, over-prov rate

Input:  results/exp3_per_run.csv
Output: results/tables/table3_ibd.tex + .csv

Run:
    python tables/table3_ibd.py
    python tables/table3_ibd.py --csv results/exp3_per_run.csv
"""
from __future__ import annotations

import sys
import csv as csv_mod
import argparse
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results"
TABLES_DIR  = RESULTS_DIR / "tables"
CSV_DEFAULT = str(RESULTS_DIR / "exp3_per_run.csv")


# ── Metrics ────────────────────────────────────────────────────────────────────

def _detector_metrics(df: pd.DataFrame) -> dict:
    def _m(pred_col: str) -> dict:
        tp = int(((df["gt_anomaly"]) & (df[pred_col])).sum())
        fp = int(((~df["gt_anomaly"]) & (df[pred_col])).sum())
        tn = int(((~df["gt_anomaly"]) & (~df[pred_col])).sum())
        fn = int(((df["gt_anomaly"]) & (~df[pred_col])).sum())
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr  = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        return {
            "precision": round(prec, 4),
            "recall":    round(rec,  4),
            "f1":        round(f1,   4),
            "fpr":       round(fpr,  4),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        }
    return {
        "threshold": _m("threshold_detected"),
        "ifs":       _m("ifs_detected"),
    }


def _mismatch_stats(df: pd.DataFrame) -> dict:
    m  = df[df["type_mismatch"]]
    nm = df[~df["type_mismatch"]]

    def _anomaly_rate(sub): return round(sub["gt_anomaly"].mean(), 4)   if len(sub) > 0 else 0.0
    def _mean_ifs(sub):     return round(sub["ifs"].mean(),        4)   if len(sub) > 0 else 0.0
    def _overprov(sub):
        if len(sub) == 0:
            return 0.0
        return round((sub["over_provision_factor"] >= 1.5).mean(), 4)

    return {
        "mismatch_n":               len(m),
        "non_mismatch_n":           len(nm),
        "mismatch_anomaly_rate":    _anomaly_rate(m),
        "non_mismatch_anomaly_rate": _anomaly_rate(nm),
        "mismatch_mean_ifs":        _mean_ifs(m),
        "non_mismatch_mean_ifs":    _mean_ifs(nm),
        "mismatch_overprov_rate":   _overprov(m),
        "non_mismatch_overprov_rate": _overprov(nm),
    }


# ── LaTeX builders ─────────────────────────────────────────────────────────────

def _booktabs_header(cols: list[str]) -> str:
    return (
        "\\begin{tabular}{" + "l" + "r" * (len(cols) - 1) + "}\n"
        "\\toprule\n"
        + " & ".join(f"\\textbf{{{c}}}" for c in cols) + " \\\\\n"
        "\\midrule\n"
    )


def _booktabs_footer() -> str:
    return "\\bottomrule\n\\end{tabular}\n"


def _gate_cell(val: float, threshold: float, higher_better: bool = True) -> str:
    passed = val >= threshold if higher_better else val <= threshold
    mark   = "\\checkmark" if passed else "\\times"
    return f"{val:.4f} ${mark}$"


def make_latex(det: dict, tm: dict) -> str:
    lines = []

    # --- Sub-table (a): Detector comparison ---
    lines.append("% --- (a) IBD Detector Comparison ---")
    lines.append(_booktabs_header(
        ["Detector", "Precision", "Recall", "F1", "FPR",
         "TP", "FP", "TN", "FN"]))

    thresh_f1 = det["threshold"]["f1"]
    ifs_f1    = det["ifs"]["f1"]

    for name, label, gate_f1 in [
        ("threshold", "CPU Threshold ($<$0.30)", thresh_f1),
        ("ifs",       "IFS Detector ($<$0.65)",  ifs_f1),
    ]:
        d = det[name]
        f1_cell = (f"{d['f1']:.4f} $\\checkmark$"
                   if name == "ifs" and ifs_f1 >= thresh_f1
                   else f"{d['f1']:.4f}")
        lines.append(
            f"{label} & {d['precision']:.4f} & {d['recall']:.4f} & "
            f"{f1_cell} & {d['fpr']:.4f} & "
            f"{d['tp']} & {d['fp']} & {d['tn']} & {d['fn']} \\\\"
        )
    lines.append(_booktabs_footer())

    # --- Sub-table (b): type_mismatch subgroup ---
    lines.append("\n% --- (b) type\\_mismatch Subgroup Analysis ---")
    lines.append(_booktabs_header(
        ["Subgroup", "$n$", "Anomaly Rate", "Mean IFS", "Over-Prov Rate"]))

    gate_mismatch = (tm["mismatch_anomaly_rate"] >= tm["non_mismatch_anomaly_rate"] and
                     tm["mismatch_mean_ifs"] <= tm["non_mismatch_mean_ifs"])
    mark = "\\checkmark" if gate_mismatch else "\\times"

    lines.append(
        f"type\\_mismatch & {tm['mismatch_n']} & "
        f"{tm['mismatch_anomaly_rate']:.4f} ${mark}$ & "
        f"{tm['mismatch_mean_ifs']:.4f} & "
        f"{tm['mismatch_overprov_rate']:.4f} \\\\"
    )
    lines.append(
        f"non-mismatch & {tm['non_mismatch_n']} & "
        f"{tm['non_mismatch_anomaly_rate']:.4f} & "
        f"{tm['non_mismatch_mean_ifs']:.4f} & "
        f"{tm['non_mismatch_overprov_rate']:.4f} \\\\"
    )
    lines.append(_booktabs_footer())

    return "\n".join(lines)


# ── CSV output ─────────────────────────────────────────────────────────────────

def make_csv_rows(det: dict, tm: dict) -> list[dict]:
    rows = []
    for name in ("threshold", "ifs"):
        d = det[name]
        rows.append({
            "sub_table":  "a",
            "detector":   name,
            "precision":  d["precision"],
            "recall":     d["recall"],
            "f1":         d["f1"],
            "fpr":        d["fpr"],
            "tp": d["tp"], "fp": d["fp"], "tn": d["tn"], "fn": d["fn"],
        })
    for sub, label in [("mismatch", "type_mismatch"), ("non_mismatch", "non_mismatch")]:
        rows.append({
            "sub_table":        "b",
            "detector":         label,
            "anomaly_rate":     tm[f"{sub}_anomaly_rate"],
            "mean_ifs":         tm[f"{sub}_mean_ifs"],
            "overprov_rate":    tm[f"{sub}_overprov_rate"],
            "n":                tm[f"{sub}_n"],
        })
    return rows


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Table 3 — IBD Detection")
    parser.add_argument("--csv",     default=CSV_DEFAULT)
    parser.add_argument("--tables",  default=str(TABLES_DIR))
    args = parser.parse_args()

    csv_in = Path(args.csv)
    if not csv_in.exists():
        print(f"[ERROR] {csv_in} not found — run exp3_ibd_detection.py first")
        sys.exit(1)

    df = pd.read_csv(csv_in)
    df["gt_anomaly"]         = df["gt_anomaly"].astype(bool)
    df["threshold_detected"] = df["threshold_detected"].astype(bool)
    df["ifs_detected"]       = df["ifs_detected"].astype(bool)
    df["type_mismatch"]      = df["type_mismatch"].astype(bool)

    det = _detector_metrics(df)
    tm  = _mismatch_stats(df)

    tables_dir = Path(args.tables)
    tables_dir.mkdir(parents=True, exist_ok=True)

    # LaTeX
    tex_path = tables_dir / "table3_ibd.tex"
    with open(tex_path, "w") as f:
        f.write(make_latex(det, tm))
    print(f"Saved: {tex_path}")

    # CSV
    csv_path = tables_dir / "table3_ibd.csv"
    rows = make_csv_rows(det, tm)
    fieldnames = list({k for r in rows for k in r})
    fieldnames.sort()
    with open(csv_path, "w", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {csv_path}")

    # Summary
    t  = det["threshold"]
    iv = det["ifs"]
    print(f"\n  Threshold:  P={t['precision']:.4f}  R={t['recall']:.4f}  F1={t['f1']:.4f}  FPR={t['fpr']:.4f}")
    print(f"  IFS:        P={iv['precision']:.4f}  R={iv['recall']:.4f}  F1={iv['f1']:.4f}  FPR={iv['fpr']:.4f}")
    gate_f1 = iv["f1"] >= t["f1"]
    gate_tm = (tm["mismatch_anomaly_rate"] >= tm["non_mismatch_anomaly_rate"] and
               tm["mismatch_mean_ifs"] <= tm["non_mismatch_mean_ifs"])
    print(f"\n  Gate (IFS F1 >= threshold F1): {'PASS' if gate_f1 else 'FAIL'}")
    print(f"  Gate (mismatch higher anomaly + lower IFS): {'PASS' if gate_tm else 'FAIL'}")


if __name__ == "__main__":
    main()
