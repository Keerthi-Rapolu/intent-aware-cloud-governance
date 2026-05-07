# Experiments

This repository is positioned as a controlled research prototype and benchmark. The README surfaces only the headline outcomes below.

| Experiment | Result |
| --- | --- |
| Calibration | Utilization MAE 0.054 |
| Pre-Provision | Showcase CPS 0.500 |
| Runtime | $97.92 prevented in runaway ML scenario |
| IBD Detection | IFS F1 0.761 vs CPU baseline 0.605 |
| System Roll-up | Valid CPS 0.559 · ESR 0.981 |
| Convergence | Peak CPS 0.733 · 58× vs no-Phase-3 |

## Reproduction

```bash
python data/generate_dataset.py
python -m evaluation.benchmark
streamlit run app/app.py
```

## Supporting Artifacts

- Tables: `results/tables/`
- Figures: `results/figures/`
- Benchmark entry point: `evaluation/benchmark.py`

## Scope

The evaluation covers:

- simulation calibration
- pre-provision prevention
- runtime prevention
- intent-behavior deviation detection
- system roll-up metrics
- policy-learning convergence
