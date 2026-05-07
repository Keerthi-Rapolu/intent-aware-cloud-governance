# PBCP — Pre-Billing Cost Prevention Framework

> **IACG v2.0** · Keerthi Rapolu (First Author) · Sreeja Katta (Second Author)

PBCP eliminates the structural lag between cloud activity and cost accountability by repositioning every governance action *before* any resource is billed. It infers workload intent from natural language, simulates predicted waste, applies decision-theoretic interventions (BLOCK / AUTO_CORRECT / SUGGEST / PASS), and tracks impact through a gaming-resistant dual metric — **CPS × ESR**.

---

## The Problem

Every cloud cost governance system in production today fires *after* billing:

```
Resource Provisioned → Resource Runs → Billing Period Closes → Report Generated → Action Taken
         ↑                                                                              ↓
         └───────────────────────── waste already incurred ────────────────────────────┘
```

A data engineering team spins up a 20-node cluster for a 3-hour ETL job. The job finishes. The cluster sits idle. Eight hours later — after $307 in idle compute on `m5.xlarge` — an alert fires. No billing system could recover that cost. PBCP would have auto-corrected the node count at submission time.

---

## Research Contributions

**1. Cost Prevention Score (CPS)** — the first gaming-resistant metric for pre-billing waste prevention:

```
CPS = Prevented_Cost / Potential_Cost_Without_System
Valid CPS = CPS × ESR   (ESR = Execution Success Rate)
```

ESR ensures a system that blocks aggressively earns low Valid CPS regardless of savings claimed. No existing cloud governance system defines a comparable metric.

**2. Intent Fidelity Score (IFS)** — a formal measure of the gap between declared intent and observed runtime behavior:

```
IFS = 0.35 × type_alignment + 0.25 × util_alignment
    + 0.20 × duration_alignment + 0.20 × resource_alignment
```

IFS captures the root cause of waste (intent-behavior divergence) and enables anomaly detection before the first billing event.

---

## Key Results

| Experiment | Metric | Value |
|---|---|---|
| Exp 0 — Calibration | Utilization MAE | 0.054 |
| Exp 0 — Calibration | Cost rel-RMSE | 0.306† |
| Exp 1 — Pre-Provision | Showcase CPS (20→10 nodes) | 0.500 |
| Exp 2 — Runtime | Scenario C prevented cost | $97.92 |
| Exp 3 — IBD Detection | IFS Detector F1 | 0.761 |
| Exp 3 — IBD Detection | CPU-threshold baseline F1 | 0.605 |
| Exp 5 — System Roll-up | Valid CPS | 0.559 |
| Exp 5 — System Roll-up | ESR | 0.981 |
| Exp 6 — Convergence | Peak Full PBCP CPS | 0.733 |
| Exp 6 — Convergence | Peak No-Phase-3 CPS | 0.090 |
| Exp 6 — Convergence | Improvement vs. baseline | **8.1× (58× vs no-Phase-3)** |

> † Cost rel-RMSE reflects submission-time duration uncertainty (±25% by design).
> Pre-execution cost prediction inherently carries this uncertainty; 0.306 is within
> the expected range for submission-time models.

---

## System Architecture

```
  Workload Description (natural language)
          │
          ▼
  [Intent Inference Engine]          ← DistilBERT 6-class classifier
          │                            + FAISS KNN (64-dim embeddings)
          ▼
  [Pre-Execution Simulator]          ← EV decision model
          │                            BLOCK / AUTO_CORRECT / SUGGEST / PASS
          ▼
  [Pre-Provision Guard]              ← Policy enforcement (policy_engine/)
          │
          ▼
  [Runtime Optimizer]                ← cpu_underutil | idle | overrun | spot_eviction
          │
          ▼
  [CPS + IFS Tracker]                ← Dual-metric reporting to DuckDB
```

**Three phases:**
- **Phase 1 — Simulate & Prevent** (pre-execution): intent inference → waste simulation → enforced intervention
- **Phase 2 — Monitor & Correct** (runtime): continuous monitoring → autonomous right-sizing, spot migration
- **Phase 3 — Learn & Adapt** (post-execution): policy learning loop with measurable convergence

---

## PBCP vs. Prior Work

| Capability | PBCP | Sedai | AWS Compute Optimizer | Cloud-Native Advisors |
|---|---|---|---|---|
| Pre-billing prevention | **Yes** | No | No | No |
| Natural language intent | **Yes** | No | No | No |
| KNN workload matching | **Yes** | No | No | No |
| EV decision model | **Yes** | No | No | No |
| IFS alignment scoring | **Yes** | No | No | No |
| Enforcement (not advisory) | **Yes** | Yes | No | No |
| Gaming-resistant metric | **Yes (CPS×ESR)** | No | No | No |
| Multi-cloud | **Yes** | Yes | AWS only | Per-cloud |

---

## Repository Structure

```
IACG/
├── intent_model/           # Intent inference: DistilBERT + FAISS KNN
│   ├── intent_inference.py     IntentInferenceEngine
│   ├── workload_embedding.py   WorkloadEmbeddingModel (64-dim, FAISS)
│   ├── intent_catalog.py       Workload type catalog + priors
│   └── workload_intent.py      WorkloadIntent dataclass
│
├── simulation_engine/      # Pre-execution cost simulation + EV model
│   ├── simulator.py            PreExecutionSimulator → SimulationResult
│   ├── cost_model.py           CloudCostModel (AWS / Azure / GCP)
│   └── correction_cost_model.py  CorrectionCostModel (EV formula)
│
├── guardrails/             # Pre-provisioning enforcement
│   └── pre_provision_guard.py  PreProvisionGuard → BLOCK / PASS
│
├── policy_engine/          # Policy registry + learner + enforcer
│   ├── policy_registry.py      PolicyRegistry (DuckDB-backed)
│   ├── policy_learner.py       PolicyLearner (incident → policy)
│   └── policy_enforcer.py      PolicyEnforcer
│
├── runtime_optimizer/      # Runtime anomaly detection + correction
│   └── adaptive_optimizer.py   AdaptiveOptimizer
│
├── cps_metrics/            # CPS + IFS tracking
│   └── prevention_tracker.py   PreventionTracker → DuckDB writes
│
├── cost_normalizer/        # Cross-cloud cost normalization
│   └── normalizer.py
│
├── ifs/                    # Intent-Fit Score calculator (stub → Sreeja)
│   └── ifs_calculator.py       IFSCalculator, IFSRecord
│
├── anomaly_rca/            # Root cause analysis (stub → Sreeja)
│   └── root_cause_analyzer.py  RootCauseAnalyzer
│
├── experiments/            # 4 experiment scripts
│   ├── exp0_simulation_calibration.py
│   ├── exp1_pre_provision.py
│   ├── exp2_runtime_prevention.py
│   ├── exp6_phase3_convergence.py
│   └── baselines/          no_phase3_frozen, rule_based, static
│
├── evaluation/
│   ├── benchmark.py        Full benchmark runner (all 4 experiments + gates)
│   └── metrics.py          Shared metric helpers + bootstrap CI
│
├── visualization/          # Paper figures (300 dpi PDF + PNG)
│   ├── exp0_calibration_plot.py
│   ├── exp1_cps_chart.py
│   ├── exp2_timeline_chart.py
│   └── exp6_convergence_chart.py
│
├── tables/                 # LaTeX paper tables (booktabs)
│   ├── table0_calibration.py
│   ├── table1_pre_provision.py
│   ├── table2_runtime.py
│   └── table6_convergence.py
│
├── tests/                  # 85 tests across 4 suites
│   ├── test_phase2.py      Core module tests (62)
│   ├── test_phase3.py      Policy engine + EV model
│   ├── test_integration.py Benchmark integration
│   └── test_phase7.py      IFS + RCA integration (23)
│
├── app/                    # Streamlit 4-page research demo
│   ├── app.py                  Entry point
│   ├── components/
│   │   ├── data_loader.py      Cached DuckDB queries (@st.cache_data)
│   │   └── charts.py           Plotly chart builders
│   └── pages/
│       ├── overview.py         Architecture, KPIs, comparison table
│       ├── prevention_engine.py  Live Demo + Workload Catalogue + Anomaly Detection
│       ├── runtime_savings.py  CPS/IFS dashboard + Intervention timeline
│       └── learning_system.py  Convergence study + Feedback loop
│
├── data/
│   └── generate_dataset.py  500-workload synthetic generator
│
├── config/
│   ├── cost_config.yml     AWS / Azure / GCP instance pricing
│   ├── simulation_config.yml
│   ├── policy_config.yml
│   └── cps_config.yml
│
├── results/
│   ├── figures/            PDF + PNG figures (committed)
│   └── tables/             .tex + .csv tables (committed)
│
├── IACG_Design_Document.md Full system design + related work
├── KEERTHI_TASKS.md        First-author task tracker
├── SREEJA_TASKS.md         Co-author interface spec
└── REQUIREMENTS.md         Full dependency list with version pinning
```

---

## Quick Start

```bash
# 1. Clone and set up environment
git clone https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance.git
cd intent-aware-cloud-governance
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
pip install -r requirements.txt

# 2. Generate the synthetic dataset (500 workloads → DuckDB)
python data/generate_dataset.py

# 3. Run the full benchmark (all 4 experiments)
python -m evaluation.benchmark

# 4. Launch the Streamlit demo app
streamlit run app/app.py
```

---

## Live Demo

The research demo is deployed at:
**https://intent-aware-cloud-governance.streamlit.app**

The app connects to a pre-generated DuckDB benchmark database (seed 42,
500 workloads, 28,423 runs). All charts and metrics are live — computed
from the database at render time. The Live Demo tab runs the actual
PBCP inference pipeline in real time.

> Note: The app uses controlled benchmark data with injected anomalies
> to evaluate governance effectiveness. IBD rates and IFS distributions
> reflect injected fault rates calibrated for stress-testing, not
> production baselines.

---

## Running Experiments Individually

```bash
# Exp 0 — Simulation calibration (MAE / RMSE vs. historical actuals)
python experiments/exp0_simulation_calibration.py

# Exp 1 — Pre-provision CPS across methods and workload types
python experiments/exp1_pre_provision.py

# Exp 2 — Runtime prevention across 3 real-world scenarios
python experiments/exp2_runtime_prevention.py

# Exp 6 — Phase 3 convergence (10 generations × 5 seeds)
python experiments/exp6_phase3_convergence.py
```

## Generating Paper Figures and Tables

```bash
# Figures (saved to results/figures/)
python visualization/exp0_calibration_plot.py
python visualization/exp1_cps_chart.py
python visualization/exp2_timeline_chart.py
python visualization/exp6_convergence_chart.py

# LaTeX tables (saved to results/tables/)
python tables/table0_calibration.py
python tables/table1_pre_provision.py
python tables/table2_runtime.py
python tables/table6_convergence.py
```

---

## Test Suite

```bash
# Run all 85 tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run a specific suite
pytest tests/test_phase7.py -v     # IFS + RCA integration (23 tests)
```

**Coverage targets:** ≥ 80% for `simulation_engine/`, `intent_model/`, `cps_metrics/`, `policy_engine/`.

---

## Streamlit App

The 4-page app runs the full PBCP pipeline interactively — no setup beyond the dataset.

```bash
streamlit run app/app.py
```

| Page | Description |
|---|---|
| Overview | Architecture diagram, system KPIs, comparison table, metric definitions |
| Prevention Engine | Live Demo (default tab) · Workload Catalogue · Anomaly Detection (Exp 3) |
| Runtime & Savings | CPS/IFS dashboard · Intervention timeline · Stage and workload type breakdown |
| Learning System | Convergence study (Exp 6) · Policy synthesis feedback loop |

> **Streamlit Cloud deployment:** push to GitHub → connect at share.streamlit.io → set main file to `app/app.py`.

---

## Data Model

The DuckDB database (`data/full/iacg.duckdb`) contains 8 tables:

| Table | Rows | Description |
|---|---|---|
| `workload_intent` | 500 | Workload submissions with NL descriptions + declared intent |
| `cps_ifs_records` | 28,423 | Per-workload CPS + IFS for every run (pre_provision / runtime / baseline) |
| `cost_records` | ~28k | Cost tracking per workload/run |
| `runtime_metrics` | ~28k | CPU, memory, IO utilization per run |
| `provisioned_config` | ~28k | Submitted vs. right-sized configuration |
| `ai_workload_metrics` | ~500 | LLM / ML pipeline specific metrics |
| `historical_incidents` | ~500 | Past idle/over-provision incidents for RCA |
| `policy_registry` | ~50 | Learned policies by workload type + incident class |

**Stage breakdown (non-baseline records):**

| Stage | Records | Mean CPS |
|---|---|---|
| pre_provision | 3,896 | 0.4251 |
| runtime | 840 | 0.6027 |
| baseline | 23,687 | 0.0000 |

---

## Configuration

All pricing, thresholds, and model parameters live in `config/`:

| File | Controls |
|---|---|
| `cost_config.yml` | On-demand + spot hourly rates for AWS / Azure / GCP instance types |
| `simulation_config.yml` | EV model weights, intervention thresholds, correction cost factors |
| `policy_config.yml` | Policy learning confidence thresholds, lookback windows |
| `cps_config.yml` | CPS/IFS reporting parameters, IBD threshold (default 0.70) |

---

## Dependencies

Core stack: Python 3.10, PyTorch ≥ 2.1, Transformers ≥ 4.38, FAISS-CPU ≥ 1.8, DuckDB ≥ 0.10, Pandas ≥ 2.2, Plotly ≥ 5.20, Streamlit ≥ 1.32.

See [REQUIREMENTS.md](REQUIREMENTS.md) for the full pinned list including testing and optional LLM/RAG dependencies.

---

## Authors

| Author | Role | Modules |
|---|---|---|
| **Keerthi Rapolu** | First author | `intent_model/`, `simulation_engine/`, `guardrails/`, `policy_engine/`, `runtime_optimizer/`, `cps_metrics/`, `cost_normalizer/`, all experiments, evaluation benchmark, visualization, Streamlit app |
| **Sreeja Katta** | Second author | `ifs/ifs_calculator.py` (full implementation), `anomaly_rca/root_cause_analyzer.py` (RAG-RCA), Exp 5 system rollup, `table5_rollup.py`, `exp5_dashboard.py` |

Interface contracts for Sreeja's modules are documented in [SREEJA_TASKS.md](SREEJA_TASKS.md). Reference stub implementations in `ifs/` and `anomaly_rca/` satisfy all test interfaces until the real implementations land.

---

## Citation

> Rapolu, K., & Katta, S. (2026). *PBCP: A Pre-Billing Cost Prevention Framework
> for Intent-Aware Cloud Governance*. IACG v2.0. Manuscript under review.