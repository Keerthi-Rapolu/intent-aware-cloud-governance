# Reproducibility Guide — PBCP

This document describes how to reproduce the experimental results reported in the paper:

> **PBCP: Pre-Billing Cost Prevention for Intent-Aware Cloud Governance**
> Sreeja Katta, Keerthi Rapolu

---

## Expected Outputs

| Experiment | Description | Metric | Reported Value |
|------------|-------------|--------|----------------|
| Exp 0 | Simulation calibration | Utilization MAE | 0.054 |
| Exp 3 | IBD anomaly detection | IFS F1 | 0.7608 |
| Exp 6 | Policy learning convergence | Peak CPS | 0.733 |

Secondary metrics:
- Exp 0: Cost rel-RMSE 0.306
- Exp 3: CPU-threshold baseline F1 0.6054
- Exp 5: Valid CPS 0.5585, ESR 0.9809
- Exp 6: No-Phase-3 baseline peak CPS 0.013 (56× gap)

---

## Requirements

```
Python >= 3.11
pip install -r requirements.txt
```

All experiments run entirely on local CPU. No cloud credentials or external services are required.

---

## Quick Reproduction

```bash
bash reproduce.sh
```

This runs all six experiments and writes outputs to `results/`.

---

## Step-by-Step Reproduction

### Exp 0 — Simulation Calibration

```bash
python experiments/exp0_simulation_calibration.py
```

Outputs:
- `results/figures/exp0_calibration.png`
- `results/tables/table0_calibration.csv`

### Exp 1 — Pre-Provision Intervention

```bash
python experiments/exp1_pre_provision.py
```

Outputs:
- `results/figures/exp1_cps.png`
- `results/tables/table1_pre_provision.csv`

### Exp 2 — Runtime Governance

```bash
python experiments/exp2_runtime_prevention.py
```

Outputs:
- `results/figures/exp2_timelines.png`
- `results/tables/table2_runtime.csv`

### Exp 3 — IBD Anomaly Detection

```bash
python experiments/exp3_ibd_detection.py
```

Outputs:
- `results/figures/fig3_ibd_detection.png`
- `results/tables/table3_ibd.csv`

### Exp 5 — System Roll-Up

```bash
python experiments/exp5_system_rollup.py
```

Outputs:
- `results/exp5_rollup.csv`
- `results/tables/table5_rollup.csv`

### Exp 6 — Policy Learning Convergence

```bash
python experiments/exp6_phase3_convergence.py
```

Outputs:
- `results/figures/exp6_convergence.png`
- `results/tables/table6_convergence.csv`

---

## Benchmark

The controlled benchmark spans 500 workloads and 28,423 runs across six workload classes:
`etl`, `ml_training`, `analytics`, `batch`, `streaming`, `inference`.

Workload generation is seeded for determinism. Re-running experiments should reproduce
the reported values within floating-point tolerance.

---

## Results Directory

After running all experiments, `results/` should contain:

```
results/
  exp5_rollup.csv
  figures/
    exp0_calibration.png
    exp1_cps.png
    exp2_timelines.png
    fig3_ibd_detection.png
    exp5_dashboard.png
    exp6_convergence.png
  tables/
    table0_calibration.csv
    table1_pre_provision.csv
    table2_runtime.csv
    table3_ibd.csv
    table5_rollup.csv
    table6_convergence.csv
```

---

## Paper Source

The LaTeX source for the paper is in `paper/`. To build the PDF:

```bash
cd paper && make
```

Requires a TeX distribution (e.g., TeX Live or MacTeX) with `pdflatex` and the ACM `acmart` class.

---

## Live Demo

A hosted Streamlit demo is available at:
[https://intent-aware-cloud-governance.streamlit.app/](https://intent-aware-cloud-governance.streamlit.app/)

To run the demo locally:

```bash
streamlit run app/app.py
```
