# Technical Details

This note keeps the main README short. It captures the canonical research definitions and points to the implementation areas that back the PBCP workflow.

## Canonical Definitions

- **CPS**: cost prevention score for avoided waste before billing.
- **ESR**: execution success rate used to convert raw CPS into valid system-level roll-ups.
- **IFS**: cosine similarity between intent embeddings and behavior embeddings.

Dashboard sub-scores are interpretability aids. They are not the canonical research definition of IFS.

## Core Flow

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

## Intervention Surface

- `BLOCK`
- `AUTO_CORRECT`
- `SUGGEST`
- `PASS`

## Repository Mapping

Primary modules:

- `intent_model/`
- `simulation_engine/`
- `policy_engine/`
- `runtime_optimizer/`
- `cps_metrics/`
- `app/`
- `experiments/`
- `data/`
- `config/`

Additional implementation areas:

- `guardrails/`
- `ifs/`
- `anomaly_rca/`
- `evaluation/`
- `results/`
- `tests/`

## Data and Outputs

The project includes a synthetic benchmark generator, committed result tables under `results/tables/`, and figure outputs under `results/figures/`. The detailed design narrative remains in [../IACG_Design_Document.md](../IACG_Design_Document.md).

## Benchmark Data

The evaluation uses a synthetic benchmark generated with `data/generate_dataset.py` (seed 42, 500 workloads, 28,423 runs).

| Table | Rows | Description |
|---|---|---|
| `workload_intent` | 500 | Workload submissions with NL descriptions and intent labels |
| `provisioned_config` | 500 | Node counts, instance types, over-provision flags |
| `runtime_metrics` | 28,423 | Per-run CPU utilization, idle time, actual duration |
| `cost_records` | 28,423 | Per-run compute and storage cost breakdown |
| `cps_ifs_records` | 28,423 | CPS, IFS, stage, and intervention decision per run |
| `historical_incidents` | — | Injected anomaly ground-truth labels |
| `ai_workload_metrics` | — | LLM/ML-specific token budget and GPU utilization |
| `policy_registry` | 8 | Built-in and learned governance policies |

Stage breakdown (non-baseline runs): pre-provision 3,896 · runtime 840.
Workload mix: ETL 130 · Adhoc 95 · ML Training 98 · LLM Pipeline 50 · Batch 77 · Streaming 50.
