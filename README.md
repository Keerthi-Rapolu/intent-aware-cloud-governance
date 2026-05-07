# PBCP — Pre-Billing Cost Prevention Framework

> Intent-aware cloud governance system that prevents compute waste before billing using hybrid NLP, FAISS KNN retrieval, and decision-theoretic intervention.

<div align="center">

![Research Prototype](https://img.shields.io/badge/Research_Prototype-Evaluation-blue)
![Streamlit Demo](https://img.shields.io/badge/Streamlit-Demo-ff4b4b?logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-KNN-0b7285)
![DuckDB](https://img.shields.io/badge/DuckDB-Analytics-f7c948)
![Cloud Governance](https://img.shields.io/badge/Cloud-Governance-0f766e)

[![Live Demo](https://img.shields.io/badge/Live_Demo-Launch-0ea5e9?style=for-the-badge&logo=streamlit&logoColor=white)](https://intent-aware-cloud-governance.streamlit.app/)
[![Design Document](https://img.shields.io/badge/Design-Document-111827?style=for-the-badge)](IACG_Design_Document.md)
[![Experiments](https://img.shields.io/badge/Research-Experiments-1d4ed8?style=for-the-badge)](docs/EXPERIMENTS.md)
[![Source Code](https://img.shields.io/badge/Source-Code-059669?style=for-the-badge&logo=github&logoColor=white)](./)

</div>

> PBCP is a controlled cloud systems research prototype and evaluation benchmark. It is not a production governance platform. Production deployment would require calibration against an organization's own telemetry and enforcement stack.

[![Launch Live Demo](assets/pbcp_demo_banner.png)](https://intent-aware-cloud-governance.streamlit.app/)

## What PBCP Does

- Infers workload intent from natural-language descriptions.
- Predicts waste before provisioning through retrieval and pre-execution simulation.
- Applies `BLOCK` / `AUTO_CORRECT` / `SUGGEST` / `PASS` decisions before or during execution.
- Tracks impact using CPS, ESR, and IFS.

## Why This Matters

Traditional cloud governance systems detect waste after infrastructure has already been provisioned, used, and billed. PBCP shifts the decision point earlier: it infers workload intent, predicts likely waste, and applies governance intervention before cost is incurred.

Example: a team submits a 20-node cluster for a short ETL workload. The job finishes, but the cluster remains idle. A traditional FinOps alert arrives after the waste already exists; PBCP can block, suggest, or auto-correct the request before billing begins.

## Architecture

PBCP is organized around a simple loop: **Prevent -> Correct -> Learn**.

```text
Natural Language Workload
→ Intent Inference
→ FAISS KNN Retrieval
→ Pre-Execution Simulation
→ EV Decision Engine
→ Runtime Optimizer
→ CPS + IFS Tracking
→ Policy Learning Loop
```

- **Prevent**: infer workload intent, retrieve similar historical cases, simulate likely waste, and choose an intervention.
- **Correct**: apply runtime actions when observed behavior diverges from declared intent.
- **Learn**: update policies and improve prevention quality over repeated generations.

## Evaluation Notes

- **IFS** is the cosine similarity between intent embeddings and behavior embeddings.
- Dashboard sub-scores provide interpretability only.

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

## Dashboard

| Overview | Prevention Engine |
| --- | --- |
| [![Overview](assets/screenshots/overview.png)](https://intent-aware-cloud-governance.streamlit.app/) | [![Prevention Engine](assets/screenshots/prevention_engine.png)](https://intent-aware-cloud-governance.streamlit.app/) |

| Runtime & Savings | Learning System |
| --- | --- |
| [![Runtime Savings](assets/screenshots/runtime_savings.png)](https://intent-aware-cloud-governance.streamlit.app/) | [![Learning System](assets/screenshots/learning_system.png)](https://intent-aware-cloud-governance.streamlit.app/) |

| Page | Description |
|---|---|
| Overview | Architecture diagram, system KPIs, comparison table, metric definitions |
| Prevention Engine | Live Demo (default tab) · Workload Catalogue · Anomaly Detection (Exp 3) |
| Runtime & Savings | CPS/IFS dashboard · Intervention timeline · Stage and workload type breakdown |
| Learning System | Convergence study (Exp 6) · Policy synthesis feedback loop |

## Quick Start

```bash
git clone https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance.git
cd intent-aware-cloud-governance
pip install -r requirements.txt

# Generate dataset
python data/generate_dataset.py

# Run benchmark
python -m evaluation.benchmark

# Launch Streamlit
streamlit run app/app.py
```

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

## Repository Structure

```
IACG/
├── intent_model/           # Intent inference: DistilBERT + FAISS KNN
├── simulation_engine/      # Pre-execution cost simulation + EV model
├── policy_engine/          # Policy registry + learner + enforcer
├── runtime_optimizer/      # Runtime anomaly detection + correction
├── cps_metrics/            # CPS + IFS tracking
├── experiments/            # Exp 0, 1, 2, 3, 5, 6 scripts
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
├── data/                   # Synthetic 500-workload benchmark generator
└── config/                 # Cloud pricing, simulation, policy, CPS parameters
```

## Further Reading

- [Design Document](IACG_Design_Document.md)
- [Technical Details](docs/TECHNICAL_DETAILS.md)
- [Experiments](docs/EXPERIMENTS.md)
- [Dashboard Guide](docs/DASHBOARD_GUIDE.md)

## Authors

- **Keerthi Rapolu** — First Author; system architecture, intent inference, pre-execution simulation, EV intervention model, runtime optimizer, CPS/ESR evaluation, Streamlit research demo.
- **Sreeja Katta** — Second Author; Intent-Fit Score subsystem, anomaly RCA contributions, policy feedback loop support.

## Citation

```bibtex
@misc{rapolu2026pbcp,
  title  = {PBCP: A Pre-Billing Cost Prevention Framework for Intent-Aware Cloud Governance},
  author = {Rapolu, Keerthi and Katta, Sreeja},
  year   = {2026},
  note   = {IACG v2.0 Research Prototype. Manuscript under review.}
}
```