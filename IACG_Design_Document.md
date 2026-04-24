# Intent-Aware Cloud Governance (IACG) Framework
## System Design Document

**Version:** 1.0.0
**Status:** Draft
**Last Updated:** April 2025
**Authors:** Keerthi (First Author) · Sreeja Katta (Second Author)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Design Goals & Principles](#3-design-goals--principles)
4. [System Architecture](#4-system-architecture)
5. [Component Design](#5-component-design)
   - 5.1 [Intent Modeling Layer](#51-intent-modeling-layer)
   - 5.2 [Pre-Provisioning Guardrails](#52-pre-provisioning-guardrails)
   - 5.3 [Runtime Adaptive Optimization Engine](#53-runtime-adaptive-optimization-engine)
   - 5.4 [Semantic Anomaly Detection & Root Cause Analysis](#54-semantic-anomaly-detection--root-cause-analysis)
   - 5.5 [AI Workload Governance Module](#55-ai-workload-governance-module)
6. [Data Model](#6-data-model)
7. [Experiments & Evaluation Plan](#7-experiments--evaluation-plan)
8. [Repository Structure](#8-repository-structure)
9. [Authorship & Contribution Map](#9-authorship--contribution-map)
10. [Design Decisions & Open Questions](#10-design-decisions--open-questions)
11. [References](#11-references)

---

## 1. Executive Summary

Modern cloud environments suffer from a persistent optimization gap: governance systems are built to *react* to cost overruns rather than *prevent* them. Threshold-based alerting fires only after waste has accumulated. Static provisioning policies ignore the semantic meaning of the workload they govern. As cloud portfolios increasingly include heterogeneous workloads—ETL pipelines, ad hoc analytics, machine learning training, and LLM inference—the cost of this reactivity compounds.

The **Intent-Aware Cloud Governance (IACG)** framework addresses this gap by treating workload intent as a first-class signal in every governance decision. By embedding workload descriptions and metadata into a shared vector space, IACG can match new workloads to historically optimal configurations, enforce guardrails before resources are provisioned, adapt dynamically during execution, and explain anomalies using retrieval-augmented reasoning over past incidents.

This document describes the full system design, data model, experimental plan, and contribution breakdown for the IACG research implementation.

---

## 2. Problem Statement

### 2.1 Limitations of Current Approaches

| Approach | Limitation |
|---|---|
| Static provisioning policies | Ignores workload semantics; over-provisions by default |
| Threshold-based anomaly detection | Fires after waste has occurred; high false-positive rate |
| Rule-based cost governance | Brittle; requires manual rule maintenance as workloads evolve |
| Post-hoc cost analysis | Provides insights with no actionable prevention path |

### 2.2 The Core Gap

> Current systems know **what resources are running**. They do not know **why they were provisioned**, **what outcome was expected**, or **whether the configuration was ever appropriate for the intent**.

This missing semantic layer creates three compounding failure modes:

1. **Pre-provisioning blindness** — users select configurations without context-aware guidance, defaulting to familiar or conservative oversized clusters.
2. **Runtime passivity** — systems do not act on utilization signals until violations exceed static thresholds, which are often set too conservatively.
3. **Opaque anomaly attribution** — when cost spikes occur, engineers lack automated tooling to distinguish misconfiguration, data volume shifts, or code regressions as root causes.

### 2.3 Scope

IACG targets the following workload types:

- **ETL Pipelines** — batch transformation and validation jobs
- **Ad Hoc Analytics** — interactive and exploratory queries
- **Machine Learning** — model training, fine-tuning, and batch inference
- **AI / LLM Pipelines** — vector database operations, RAG pipelines, and token-intensive LLM calls

---

## 3. Design Goals & Principles

### 3.1 Goals

| ID | Goal | Success Metric |
|---|---|---|
| G1 | Reduce cloud cost waste through pre-provisioning prevention | ≥ 28% reduction vs. baseline |
| G2 | Lower over-provisioning rates via intent-aware recommendations | ≥ 40% reduction in over-provisioning rate |
| G3 | Improve overall resource utilization | ≥ 20% improvement in CPU/memory utilization |
| G4 | Detect cost anomalies earlier and more precisely than threshold rules | Higher precision/recall, earlier detection time |
| G5 | Extend governance to AI workloads (LLM + vector DB) | Measurable token and embedding cost reduction |

### 3.2 Design Principles

- **Intent-First** — every governance decision begins with semantic understanding of workload purpose.
- **Prevention over Detection** — enforce optimal configurations before execution, not after waste.
- **Closed-Loop** — outcomes feed back into the embedding store to continuously improve recommendations.
- **Explainability** — every recommendation, guardrail action, and anomaly alert must include a human-readable rationale.
- **Extensibility** — the framework is workload-agnostic at its core; new workload types should be addable without redesigning existing components.

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        IACG Framework                               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Layer 1: Intent Modeling                                    │  │
│  │  workload_name + description + metadata → embedding vector  │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │ intent vector                        │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │  Layer 2: Pre-Provisioning Guardrails                        │  │
│  │  similarity search → recommended config → enforce/suggest   │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │ approved config                      │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │  Layer 3: Runtime Adaptive Optimization Engine               │  │
│  │  monitor utilization → scale / terminate / migrate (spot)   │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │ runtime metrics + cost actuals       │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │  Layer 4: Semantic Anomaly Detection & RCA                   │  │
│  │  intent vs. behavior mismatch → RAG-based root cause        │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │ feedback loop                        │
│                              ▼                                      │
│                    Vector Store + Incident History                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────▼──────────────┐
              │  AI Workload Governance       │
              │  (LLM / Vector DB Extension)  │
              └──────────────────────────────┘
```

The framework operates as a **closed-loop system**. Execution outcomes are written back to the vector store and incident history, improving future similarity search results and anomaly detection without requiring explicit retraining.

---

## 5. Component Design

### 5.1 Intent Modeling Layer

**Owner:** Keerthi
**Location:** `/intent_model/`

#### Purpose
Transform unstructured workload metadata into dense vector embeddings that encode semantic workload intent, enabling similarity search against historically optimal configurations.

#### Input
- `workload_name` (string)
- `description` (free text)
- `team`, `job_type`, `frequency`, `expected_duration`

#### Process

```
Workload Metadata
      │
      ▼
  Text Composition
  (name + description + job_type + frequency)
      │
      ▼
  Embedding Model
  (sentence-transformers / OpenAI text-embedding-ada-002)
      │
      ▼
  Intent Vector  [dim: 384 or 1536]
      │
      ▼
  FAISS / ChromaDB Vector Index
```

#### Key Design Decisions

- **Embedding model choice:** `sentence-transformers/all-MiniLM-L6-v2` for local execution; OpenAI `text-embedding-ada-002` for production-grade quality. The system should be model-agnostic via an interface abstraction.
- **Composite text field:** Rather than embedding raw workload names alone, compose a single text block from all semantic fields before embedding. This produces richer, more distinguishable vectors.
- **Index type:** FAISS `IndexFlatIP` (inner product / cosine similarity) for initial experiments. Swap to HNSW for scalability.

#### Output
- Intent vector per workload
- Top-K similar historical workloads with cosine similarity scores

---

### 5.2 Pre-Provisioning Guardrails

**Owner:** Keerthi
**Location:** `/guardrails/`

#### Purpose
Evaluate workload intent *before* resources are provisioned and either recommend or enforce an optimal configuration, preventing over-provisioning at the source.

#### Process

```
New Workload Intent Vector
         │
         ▼
  Similarity Search → Top-K Historical Workloads
         │
         ▼
  Aggregate Optimal Configs
  (weighted by similarity score × cost efficiency)
         │
         ▼
  Compare vs. User-Selected Config
         │
    ┌────┴────┐
    │         │
  Match    Mismatch
    │         │
  Allow    Guardrail Action
             │
        ┌────┴────┐
        │         │
     Suggest    Enforce
     (warn)    (block + substitute)
```

#### Guardrail Actions

| Action | Trigger | Behavior |
|---|---|---|
| `SUGGEST` | Minor mismatch (similarity ≥ 0.85, config delta < 20%) | Recommendation surfaced; user can override |
| `WARN` | Moderate mismatch (similarity ≥ 0.70, config delta 20–50%) | Warning logged; execution proceeds |
| `ENFORCE` | Severe mismatch (similarity ≥ 0.70, config delta > 50%) | Configuration substituted automatically |
| `BLOCK` | Unknown intent (similarity < 0.50) | Escalate to human review |

> **Design Note:** Thresholds above are initial values to be calibrated during experiments. Consider exposing them as policy configuration rather than hardcoded constants.

#### Output
- Recommended configuration (cluster size, nodes, instance type, spot/on-demand, auto-shutdown)
- Estimated cost before vs. after guardrail
- Similarity trace (which historical workloads informed the recommendation)

---

### 5.3 Runtime Adaptive Optimization Engine

**Owner:** Keerthi
**Location:** `/runtime_optimizer/`

#### Purpose
Monitor active workloads in real time and take automated cost-saving actions—scaling, auto-termination, and spot instance migration—when utilization deviates from expectations.

#### Monitored Signals

| Signal | Optimization Trigger |
|---|---|
| CPU utilization avg < 25% for N minutes | Downscale cluster or terminate |
| Memory utilization avg < 20% | Resize or consolidate nodes |
| Idle time > auto-shutdown threshold | Auto-terminate cluster |
| Spot interruption detected | Migrate to on-demand or checkpoint + reschedule |
| Runtime > 2× expected_duration | Escalate; potential runaway job |

#### Optimization Actions

```python
class OptimizationAction(Enum):
    DOWNSCALE    = "downscale"        # Reduce node count
    AUTOTERMINATE = "auto_terminate"  # Shut down idle cluster
    SPOT_MIGRATE  = "spot_migrate"    # Move to different spot pool
    ONDEMAND_FALLBACK = "ondemand"    # Migrate off spot after interruption
    ESCALATE      = "escalate"        # Alert; requires human review
```

#### Simulation Design (for experiments)

Since the evaluation uses synthetic data, the runtime optimizer will be implemented as an **event-driven simulator**:

- Workloads are assigned utilization time series sampled from realistic distributions (e.g., underutilized jobs use Beta(2, 5) for CPU utilization)
- The simulator steps through time, applies optimization actions, and computes cost deltas
- Baseline comparison: static system holds original configuration for full runtime

---

### 5.4 Semantic Anomaly Detection & Root Cause Analysis

**Owner:** Sreeja Katta
**Location:** `/anomaly_rca/`

#### Purpose
Detect workloads whose runtime behavior does not match their declared intent, and provide explainable root cause analysis using RAG over historical incident records.

#### Anomaly Detection Model

Unlike threshold-based detection (e.g., CPU < 30% = anomaly), IACG uses **intent-vs-behavior mismatch** as the anomaly signal:

```
Intent Vector (pre-execution)
        +
Behavior Vector (post-execution: runtime metrics → embedding)
        │
        ▼
  Cosine Distance between intent and behavior vectors
        │
  If distance > θ_anomaly → flag as anomaly
```

**Behavior vector** is derived by encoding normalized runtime metrics:
```
f(cpu_util_avg, mem_util_avg, runtime_minutes, idle_time_ratio, cost_delta_pct)
```

#### RAG-Based Root Cause Analysis

When an anomaly is flagged:

1. Retrieve Top-K most similar historical incidents from incident store (by behavior vector similarity)
2. Compose a context prompt: `[anomaly description] + [retrieved incidents]`
3. Query LLM with RAG context to generate:
   - Probable root cause category
   - Recommended remediation steps
   - Estimated cost impact

```
Anomaly Event
     │
     ▼
Incident Vector Store (FAISS)
     │
  Top-K Similar Incidents
     │
     ▼
RAG Prompt Construction
     │
     ▼
LLM (GPT-3.5-turbo / local Mistral)
     │
     ▼
Root Cause Report + Remediation
```

#### Comparison Baseline

- **Threshold detector:** flags workloads where `cpu_utilization_avg < 30%` OR `idle_time_minutes > 20`
- **IACG detector:** intent-behavior cosine distance > learned threshold θ

Evaluate using precision, recall, F1, and mean time-to-detection (MTTD).

---

### 5.5 AI Workload Governance Module

**Owner:** Sreeja Katta
**Location:** `/ai_governance/`

#### Purpose
Extend the IACG framework to govern AI-specific workloads: vector database operations, embedding pipelines, and LLM inference calls, where cost inefficiencies manifest differently from traditional compute workloads.

#### AI Workload Cost Anti-Patterns

| Anti-Pattern | Description | Governance Action |
|---|---|---|
| Full-dataset embedding | Embedding all vectors when sparse metadata would suffice | Recommend metadata-only embedding |
| Oversized embedding model | Using 1536-dim embeddings for low-complexity retrieval | Downsize to 384-dim model |
| Inefficient RAG pipeline | High `rag_calls` with low retrieval precision | Suggest query caching or hybrid search |
| Token waste in LLM calls | System prompts exceed 40% of total token budget | Compress system prompt; suggest structured output |
| No result caching | Repeated identical LLM queries | Flag; recommend semantic cache layer |

#### Metrics Tracked

```python
@dataclass
class AIWorkloadMetrics:
    embedding_size: int          # Vector dimensionality
    num_vectors: int             # Total vectors in index
    token_usage: int             # Tokens consumed per pipeline run
    model_type: str              # e.g., "gpt-4", "ada-002", "mistral-7b"
    rag_calls: int               # Retrieval calls per run
    cache_hit_rate: float        # Optional: if caching is instrumented
    estimated_cost_usd: float    # Derived from token usage × model price
```

#### Optimization Targets (Experiment 4)

- **Token reduction %** — before vs. after prompt compression + caching
- **Embedding cost reduction** — before vs. after dimension/model downgrade
- **RAG efficiency** — retrieval precision at K before vs. after pipeline redesign

---

## 6. Data Model

### 6.1 Schema Overview

The synthetic dataset consists of six interrelated tables designed to be realistic in distribution while remaining fully reproducible from a fixed random seed.

#### Table 1: `workload_intent`

| Column | Type | Description |
|---|---|---|
| `workload_id` | UUID | Primary key |
| `workload_name` | string | Human-readable name (e.g., `daily_etl_validation`) |
| `description` | text | Free-text description of workload purpose |
| `team` | string | Owning team |
| `job_type` | enum | `etl`, `adhoc`, `ml`, `dashboard`, `llm_pipeline` |
| `expected_duration_min` | int | Expected runtime in minutes |
| `frequency` | enum | `hourly`, `daily`, `weekly`, `on_demand` |

#### Table 2: `provisioned_config`

| Column | Type | Description |
|---|---|---|
| `workload_id` | UUID | FK → workload_intent |
| `cluster_size` | enum | `small`, `medium`, `large`, `xlarge` |
| `num_nodes` | int | Node count |
| `auto_shutdown_minutes` | int | Idle shutdown threshold |
| `instance_type` | string | e.g., `m5.xlarge`, `r5.2xlarge` |
| `spot_or_ondemand` | enum | `spot`, `on_demand` |
| `policy_type` | enum | `auto`, `manual`, `enforced` |

#### Table 3: `runtime_metrics`

| Column | Type | Description |
|---|---|---|
| `workload_id` | UUID | FK → workload_intent |
| `run_id` | UUID | Unique execution ID |
| `cpu_utilization_avg` | float | 0.0–1.0 |
| `memory_utilization_avg` | float | 0.0–1.0 |
| `runtime_minutes` | int | Actual runtime |
| `idle_time_minutes` | int | Idle time during run |
| `failure_flag` | bool | Whether the run failed |

#### Table 4: `cost_records`

| Column | Type | Description |
|---|---|---|
| `workload_id` | UUID | FK → workload_intent |
| `run_id` | UUID | FK → runtime_metrics |
| `hourly_cost_usd` | float | Cluster hourly rate |
| `total_cost_usd` | float | Actual total spend |
| `optimal_cost_usd` | float | Cost if optimally provisioned |
| `wasted_cost_usd` | float | Derived: total − optimal |

#### Table 5: `historical_incidents`

| Column | Type | Description |
|---|---|---|
| `incident_id` | UUID | Primary key |
| `workload_id` | UUID | FK → workload_intent |
| `incident_type` | enum | `over_provisioned`, `runaway_job`, `spot_interruption`, `idle_cluster`, `token_waste` |
| `description` | text | Incident narrative |
| `fix_applied` | text | Remediation taken |
| `cost_impact_usd` | float | Total cost impact of incident |
| `detection_lag_minutes` | int | Time from occurrence to detection |

#### Table 6: `ai_workload_metrics`

| Column | Type | Description |
|---|---|---|
| `workload_id` | UUID | FK → workload_intent (job_type = `llm_pipeline`) |
| `embedding_size` | int | Vector dimensionality |
| `num_vectors` | int | Vectors in index |
| `token_usage` | int | Tokens per pipeline run |
| `model_type` | string | Model identifier |
| `rag_calls` | int | Retrieval calls per run |
| `estimated_cost_usd` | float | Derived from token pricing |

### 6.2 Synthetic Data Generation

- **Total workloads:** 500 (300 ETL/analytics, 150 ML, 50 LLM pipelines)
- **Runs per workload:** 30–90 historical runs
- **Anomaly injection rate:** ~15% of runs have injected inefficiencies
- **Random seed:** fixed (42) for reproducibility
- **Generation script:** `/data/generate_dataset.py`

> **Suggestion:** Consider publishing the dataset generation script as a standalone artifact so that the synthetic data pipeline is itself a contribution. Other researchers can adjust parameters (anomaly rate, workload mix) to test governance systems on different cloud environment profiles.

---

## 7. Experiments & Evaluation Plan

### Experiment 1 — Pre-Provisioning Cost Prevention

**Goal:** Demonstrate cost savings achieved by applying intent-aware guardrails before workload execution.

**Owner:** Keerthi

| | Baseline | IACG |
|---|---|---|
| Config source | User-selected | Guardrail-recommended |
| Selection method | Manual / rule-based | Vector similarity → optimal config |

**Metrics:**
- Cost difference (USD) between user config and recommended config
- Over-provisioning rate (% of runs where provisioned capacity > 1.5× utilized capacity)
- Configuration match rate (% of recommendations accepted without override)

**Expected Result:** IACG reduces average cost per run by 28–35% and over-provisioning rate by ≥ 40%.

---

### Experiment 2 — Runtime Adaptive Optimization

**Goal:** Demonstrate dynamic savings through real-time resource scaling and spot migration.

**Owner:** Keerthi

**Simulation Scenarios:**

| Scenario | Description |
|---|---|
| Underutilized cluster | CPU avg < 25%; cluster not scaled down |
| Spot interruption | Mid-run interruption; workload must recover |
| Runaway job | Runtime 3× expected; no auto-termination |

| | Static System | IACG Adaptive |
|---|---|---|
| Response to underutilization | None | Downscale after N minutes |
| Spot interruption handling | Manual failover | Automatic on-demand migration |
| Runaway job | Alert only | Alert + escalate + optional terminate |

**Metrics:**
- Cost saved per scenario (USD)
- Utilization improvement (CPU/memory avg before vs. after optimization)
- Recovery time for spot interruptions

---

### Experiment 3 — Semantic Anomaly Detection

**Goal:** Show that intent-behavior mismatch detection outperforms threshold-based rules.

**Owner:** Sreeja Katta

| | Threshold Detector | IACG Semantic Detector |
|---|---|---|
| Signal | CPU < 30% OR idle > 20 min | Cosine distance (intent vs. behavior) > θ |
| Context awareness | None | Full intent context |

**Metrics:**
- Precision, Recall, F1 on anomaly detection
- Mean Time to Detection (MTTD) — minutes from anomaly onset to flag
- False positive rate

**Hypothesis:** IACG achieves higher recall (catches more true anomalies) with comparable or better precision, and detects anomalies earlier due to pre-execution intent context.

---

### Experiment 4 — AI Workload Cost Governance

**Goal:** Measure token and embedding cost reduction achievable by AI governance recommendations.

**Owner:** Sreeja Katta

**Simulation Setup:**

| Anti-Pattern | Injection Rate |
|---|---|
| Full-dataset embedding (all vectors) | 30% of LLM pipeline workloads |
| Oversized embedding model (1536-dim) | 40% of LLM pipeline workloads |
| High token waste (system prompt > 40% of budget) | 25% of LLM pipeline workloads |
| No RAG caching | 50% of LLM pipeline workloads |

**Metrics:**
- Token reduction % (before vs. after prompt optimization)
- Embedding cost reduction % (before vs. after dimension/model downgrade)
- RAG call efficiency (precision@K before vs. after pipeline redesign)

---

### Baselines Summary

All experiments compare IACG against the following baselines:

| Baseline | Description |
|---|---|
| **Static Provisioning** | User-selected configuration; no automated adjustment |
| **Rule-Based Policies** | Predefined rules (e.g., "large cluster for ML jobs") |
| **Threshold Anomaly Detection** | Flag when CPU < 30% or idle > 20 min |

> **Note:** Including all three baselines is essential for credibility. Omitting any one of them significantly weakens the empirical claims.

---

## 8. Repository Structure

```
iacg/
├── README.md
├── DESIGN.md                        ← this document
├── requirements.txt
├── setup.py
│
├── data/
│   ├── generate_dataset.py          # Synthetic data generation (shared)
│   ├── schema.sql                   # Table definitions
│   ├── sample/                      # Committed sample data (100 workloads)
│   └── full/                        # .gitignore'd; generated locally
│
├── intent_model/                    # Keerthi
│   ├── embeddings.py                # Text → vector pipeline
│   ├── vector_store.py              # FAISS index wrapper
│   ├── similarity_search.py         # Top-K retrieval
│   └── tests/
│
├── guardrails/                      # Keerthi
│   ├── pre_provision.py             # Guardrail evaluation engine
│   ├── config_recommender.py        # Config aggregation from similar workloads
│   ├── policy_enforcer.py           # SUGGEST / WARN / ENFORCE / BLOCK logic
│   └── tests/
│
├── runtime_optimizer/               # Keerthi
│   ├── optimizer.py                 # Main optimization loop
│   ├── simulator.py                 # Event-driven runtime simulator
│   ├── actions.py                   # OptimizationAction definitions
│   └── tests/
│
├── anomaly_rca/                     # Sreeja Katta
│   ├── behavior_encoder.py          # Runtime metrics → behavior vector
│   ├── mismatch_detector.py         # Intent vs. behavior cosine distance
│   ├── rag_rca.py                   # RAG-based root cause analysis
│   └── tests/
│
├── ai_governance/                   # Sreeja Katta
│   ├── ai_workload_analyzer.py      # AI anti-pattern detection
│   ├── token_optimizer.py           # Token reduction recommendations
│   ├── embedding_advisor.py         # Embedding size / model recommendations
│   └── tests/
│
├── experiments/                     # Shared
│   ├── exp1_pre_provisioning.py
│   ├── exp2_runtime_optimization.py
│   ├── exp3_anomaly_detection.py
│   ├── exp4_ai_governance.py
│   └── baselines/
│       ├── static_provisioning.py
│       ├── rule_based_policies.py
│       └── threshold_detector.py
│
├── evaluation/                      # Shared
│   ├── metrics.py                   # Precision, recall, cost delta, utilization
│   ├── results/                     # Experiment output CSVs and plots
│   └── plots.py                     # Result visualization
│
└── docs/
    ├── DESIGN.md
    ├── figures/
    │   └── architecture_diagram.png
    └── paper/                       # LaTeX source (if applicable)
```

---

## 9. Authorship & Contribution Map

### Keerthi — First Author

**Core Framework & Prevention Systems**

| Component | Responsibility |
|---|---|
| Intent Modeling Layer | Full ownership |
| Pre-Provisioning Guardrails | Full ownership |
| Runtime Adaptive Optimization Engine | Full ownership |
| System architecture design | Primary |
| Experiments 1 & 2 | Primary |
| Dataset generation design | Joint with Sreeja |

### Sreeja Katta — Second Author

**Detection, Explainability & AI Governance**

| Component | Responsibility |
|---|---|
| Semantic Anomaly Detection | Full ownership |
| RAG-Based Root Cause Analysis | Full ownership |
| AI Workload Governance Module | Full ownership |
| Experiments 3 & 4 | Primary |
| Baseline comparisons (Exp 3 & 4) | Primary |
| Dataset generation | Joint with Keerthi |

### Shared Responsibilities

- `/data/` — dataset generation and schema
- `/experiments/` — experiment orchestration scripts
- `/evaluation/` — metrics and visualization
- `/docs/` — documentation and paper

---

## 10. Design Decisions & Open Questions

### Resolved Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Vector index backend | FAISS (initial) | Simple, fast, no external service dependency for research |
| Embedding model | sentence-transformers (local), ada-002 (optional) | Reproducible without API key requirement |
| Behavior encoding | Normalized numeric features → linear projection | Keeps behavior vector in same space as intent for meaningful cosine comparison |
| RAG LLM backend | GPT-3.5-turbo or local Mistral-7B | Flexibility; Mistral allows fully offline execution |
| Data generation | Python + Faker + NumPy | Reproducible with fixed seed; realistic distributions |

### Open Questions

1. **Behavior vector space alignment:** Intent and behavior vectors are derived from fundamentally different signals (text vs. metrics). Direct cosine comparison may not be meaningful without a learned alignment layer. Consider training a simple projection or using a shared embedding space.

   *Suggestion: Add a lightweight contrastive learning step that maps behavior vectors to the intent embedding space using historical (intent, behavior) pairs from successfully governed workloads.*

2. **Guardrail threshold calibration:** SUGGEST / WARN / ENFORCE thresholds (similarity scores, config delta percentages) are currently set heuristically. These should be empirically tuned, or at minimum, a sensitivity analysis should be reported.

3. **Feedback loop latency:** The closed-loop design assumes that execution outcomes are written back to the vector store in near-real-time. For the synthetic experiments this is trivially true, but the paper should acknowledge this as an implementation constraint in real deployments.

4. **AI workload token pricing:** Token costs change frequently across providers. The evaluation should either pin a specific pricing snapshot (with date) or express costs in relative terms (token reduction %) rather than absolute USD.

5. **Multi-tenant isolation:** The current design shares a single vector store across teams. Should similarity search be scoped to the requesting team's historical workloads, or should cross-team learning be allowed? This has both technical and organizational implications worth noting.

### Suggested Additions

- **Confidence intervals on all metrics** — run each experiment 5× with different random seeds and report mean ± std. This strengthens empirical claims significantly.
- **Ablation study** — evaluate IACG with individual layers disabled (e.g., guardrails only, no runtime optimizer) to isolate each component's contribution.
- **Latency overhead measurement** — report the p99 latency added by guardrail evaluation at pre-provisioning time, as this is a practical adoption concern.

---

## 11. References

> *(To be populated during paper writing. Suggested areas to cite:)*

- Vector embeddings for semantic search (SBERT, FAISS)
- Retrieval-Augmented Generation (RAG) foundations
- Cloud cost optimization literature (AWS Trusted Advisor, Azure Advisor, GCP Recommender)
- Anomaly detection in distributed systems (MTTD benchmarks)
- AI workload cost management (LLM inference optimization, token efficiency)
- Synthetic workload benchmarking methodology

---

*Document maintained in `/docs/DESIGN.md`. Update this document before merging changes to any component interface or experiment design.*
