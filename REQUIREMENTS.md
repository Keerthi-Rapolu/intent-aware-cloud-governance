# PBCP / IACG v2.0 — Software & Tool Requirements

**Project:** Pre-Billing Cost Prevention Framework  
**Scope:** Full system implementation + experiments

---

## 1. Python Environment

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10.x | 3.11 also acceptable; avoid 3.12 (torch compatibility) |
| Virtual environment | `venv` or `conda` | Use one per project; never install globally |

**Create environment:**
```bash
python -m venv .venv
source .venv/bin/activate       # Mac/Linux
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

---

## 2. Core Python Packages

### Machine Learning & NLP

| Package | Version | Purpose |
|---|---|---|
| `torch` | ≥ 2.1.0 | Contrastive embedding training (IFS encoders f + g) |
| `transformers` | ≥ 4.38.0 | DistilBERT 6-class workload type classifier (IntentInferenceEngine) |
| `sentence-transformers` | ≥ 2.6.0 | Pre-trained sentence embeddings as feature input alternative |
| `scikit-learn` | ≥ 1.4.0 | RandomForest for ML attribution; cross-validation; precision/recall metrics |
| `numpy` | ≥ 1.26.0 | Numerical operations throughout |
| `scipy` | ≥ 1.12.0 | Statistical tests (Mann-Whitney for convergence analysis in Exp 6) |

### Vector Search

| Package | Version | Purpose |
|---|---|---|
| `faiss-cpu` | ≥ 1.8.0 | FAISS KNN index for WorkloadEmbeddingModel and RAG-RCA incident retrieval |

> **Note:** Use `faiss-gpu` if a CUDA GPU is available; `faiss-cpu` is sufficient for 500-workload dataset. Install via `pip install faiss-cpu` — do **not** install both.

### Data Processing

| Package | Version | Purpose |
|---|---|---|
| `pandas` | ≥ 2.2.0 | Dataset manipulation, experiment result aggregation |
| `pyarrow` | ≥ 15.0.0 | Parquet file I/O for large intermediate datasets |
| `pyyaml` | ≥ 6.0.1 | Load all config files (simulation_config.yml, policy_config.yml, etc.) |
| `pydantic` | ≥ 2.6.0 | Data validation on WorkloadIntent, SimulationResult, and all API boundaries |

### Database

| Package | Version | Purpose |
|---|---|---|
| `duckdb` | ≥ 0.10.0 | Primary analytical database for synthetic dataset; schema inferred from DataFrames — no DDL required |

> DuckDB is already installed. Connect with `duckdb.connect("data/full/iacg.duckdb", read_only=True)` and use `.df()` to get a pandas DataFrame. No SQLite or SQLAlchemy needed.

### Visualization

| Package | Version | Purpose |
|---|---|---|
| `matplotlib` | ≥ 3.8.0 | All charts (calibration scatter, CPS bars, convergence curves) |
| `seaborn` | ≥ 0.13.0 | Statistical plot styling; IFS distribution histogram |
| `plotly` | ≥ 5.20.0 | Optional interactive dashboard version of Experiment 5 roll-up |

> **Print quality:** set `dpi=300` and `figsize=(8, 5)` (single column) or `(14, 5)` (double column) for paper figures. Use vector format (`savefig("fig.pdf")`) for camera-ready submission.

### Configuration & Utilities

| Package | Version | Purpose |
|---|---|---|
| `python-dotenv` | ≥ 1.0.0 | Load environment variables (API keys if cloud pricing APIs are used) |
| `click` | ≥ 8.1.0 | CLI for `evaluation/benchmark.py` (`--experiment`, `--seed`, `--output`) |
| `tqdm` | ≥ 4.66.0 | Progress bars for dataset generation and experiment loops |
| `loguru` | ≥ 0.7.0 | Structured logging throughout all modules |
| `pydantic` | ≥ 2.6.0 | Data validation on WorkloadIntent, SimulationResult, and all API boundaries |

### Testing

| Package | Version | Purpose |
|---|---|---|
| `pytest` | ≥ 8.0.0 | All unit tests; parametrize for multi-seed experiment validation |
| `pytest-cov` | ≥ 4.1.0 | Coverage reporting; target ≥ 80% for core modules |
| `hypothesis` | ≥ 6.100.0 | Property-based testing for EV formula edge cases (CostOfCorrectionModel) |

### LLM / RAG (for RAG-RCA in `anomaly_rca/`)

| Package | Version | Purpose | Owner |
|---|---|---|---|
| `langchain` | ≥ 0.1.0 | RAG pipeline orchestration | Sreeja |
| `mistralai` or `llama-cpp-python` | latest | Local Mistral-7B inference (offline eval; no OpenAI dependency) | Sreeja |
| `openai` | ≥ 1.12.0 | Optional GPT-3.5-turbo fallback for RAG-RCA | Sreeja |

> **Reproducibility note:** the paper must not require an OpenAI API key to reproduce results. Mistral-7B (local) must be the default for all evaluations. OpenAI is optional/secondary.

---

## 3. `requirements.txt` Template

```
# Core ML
torch>=2.1.0
transformers>=4.38.0
sentence-transformers>=2.6.0
scikit-learn>=1.4.0
numpy>=1.26.0
scipy>=1.12.0

# Vector search
faiss-cpu>=1.8.0

# Data / Database
pandas>=2.2.0
duckdb>=0.10.0
pyarrow>=15.0.0
pyyaml>=6.0.1
pydantic>=2.6.0

# Visualization
matplotlib>=3.8.0
seaborn>=0.13.0
plotly>=5.20.0

# Utilities
python-dotenv>=1.0.0
click>=8.1.0
tqdm>=4.66.0
loguru>=0.7.0

# Testing
pytest>=8.0.0
pytest-cov>=4.1.0
hypothesis>=6.100.0

# LLM / RAG (Sreeja — optional for Keerthi's modules)
langchain>=0.1.0
llama-cpp-python>=0.2.0   # local Mistral-7B
openai>=1.12.0             # optional
```

---

## 4. External Data Sources

| Source | Use | Access |
|---|---|---|
| **Google Cluster Trace 2019** | Calibrate utilization distributions (Experiment 0); replace synthetic Beta distributions with real job data | Free download: `github.com/google/cluster-data` |
| **Alibaba Cluster Trace 2018** | Calibrate streaming/adhoc distributions | Free download: `github.com/alibaba/clusterdata` |
| **AWS us-east-1 On-Demand Pricing** | Validate `cost_config.yml` instance pricing | Public: `aws.amazon.com/ec2/pricing/on-demand/` |
| **Azure VM Pricing** | Validate Azure pricing in cost normalizer | Public: `azure.microsoft.com/en-us/pricing/details/virtual-machines/` |
| **GCP Compute Pricing** | Validate GCP pricing in cost normalizer | Public: `cloud.google.com/compute/all-pricing` |

> **Required for publication:** Experiments 0 and 5 must be re-run with Google Cluster Trace distributions to satisfy SoCC reviewer expectations (see Section 6.2 of design doc).

---

## 5. Development Tools

| Tool | Version | Purpose |
|---|---|---|
| **VS Code** | Latest | Primary IDE; install Python + Pylance extensions |
| **Git** | ≥ 2.40 | Version control; use `.gitignore` to exclude `data/full/`, model checkpoints, `.env` |
| **Jupyter Notebook** | via `jupyter` package | Exploratory data analysis on synthetic dataset; experiment result inspection |
| **DuckDB CLI** | Latest | Inspect and query generated DuckDB database: `duckdb data/full/iacg.duckdb` |

---

## 6. Hardware Recommendations

| Workload | Minimum | Recommended |
|---|---|---|
| Synthetic data generation (500 workloads) | 8 GB RAM, any CPU | Same — fast on any modern machine |
| DistilBERT fine-tuning (IntentInferenceEngine) | 8 GB RAM, CPU | 16 GB RAM + GPU (4 GB VRAM) for faster training |
| FAISS index build (500 workloads × 64-dim) | 4 GB RAM | Same — small index, CPU is fine |
| Contrastive embedding training (IFS encoders) | 8 GB RAM, CPU | 16 GB RAM + GPU (Sreeja's task) |
| All 6 experiments (synthetic dataset) | 16 GB RAM, 4-core CPU | Same — no GPU required for evaluation |
| Google Cluster Trace processing | 32 GB RAM | Required for the full 2019 trace (raw files are ~100 GB compressed) |

> **Practical note:** all of Keerthi's modules (Phases 0–6 in `KEERTHI_TASKS.md`) run on CPU-only hardware. GPU is optional for DistilBERT fine-tuning and can be replaced by loading a pre-trained checkpoint. The contrastive embedding training (IFS encoders) is Sreeja's task and is the only GPU-intensive step.

---

## 7. DistilBERT Model Checkpoint

The `IntentInferenceEngine` in `intent_model/intent_inference.py` uses a 6-class DistilBERT classifier. Two options:

**Option A — Fine-tune on synthetic descriptions (recommended):**
```python
from transformers import DistilBertForSequenceClassification, Trainer
# Fine-tune on 400 examples per class from generate_dataset.py descriptions
# Save checkpoint to: intent_model/checkpoints/workload_type_classifier/
```

**Option B — Use pre-trained DistilBERT with few-shot prompting:**
```python
from transformers import pipeline
classifier = pipeline("zero-shot-classification", model="cross-encoder/nli-distilroberta-base")
# Candidate labels: ["etl", "adhoc", "ml_training", "llm_pipeline", "batch", "streaming", "serving"]
```

> Option A produces better results (6-class, domain-specific). Option B requires no training data but has lower accuracy on novel descriptions. Use Option A for final paper results.

---

## 8. File Size & Storage Estimates

| Artifact | Estimated Size |
|---|---|
| Synthetic dataset (500 workloads, DuckDB) | ~32 MB |
| Sample dataset (100 workloads, committed) | ~10 MB |
| DistilBERT fine-tuned checkpoint | ~250 MB |
| FAISS index (500 workloads × 64-dim) | ~1 MB |
| Google Cluster Trace 2019 (raw) | ~100 GB compressed |
| Google Cluster Trace 2019 (processed subset) | ~500 MB |
| Experiment results CSVs (all 6 experiments) | ~5 MB |
| Figures (PNG + PDF, all experiments) | ~20 MB |

> **`.gitignore` must exclude:** `data/full/`, `intent_model/checkpoints/`, `*.pt` model files, `.env`

---

## 9. Environment Variables (`.env`)

```
# Required only if using AWS/Azure/GCP pricing APIs directly (optional — YAML fallback available)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AZURE_SUBSCRIPTION_ID=
GCP_PROJECT_ID=

# Required only if using OpenAI for RAG-RCA (optional — Mistral-7B local is default)
OPENAI_API_KEY=

# Experiment settings
RANDOM_SEED=42
RESULTS_DIR=results/
```

---

*Last updated: 2026-05-04. Install `requirements.txt` into a clean virtual environment before starting Phase 0 of `KEERTHI_TASKS.md`.*
