# Pre-Billing Cost Prevention Framework (PBCP)
## System Design Document — IACG v2.0

**Version:** 2.0.0
**Status:** Active Design
**Last Updated:** April 2026
**Authors:** Keerthi Rapolu (First Author) · Sreeja Katta (Second Author)

> **System Evolution Notice:** This document supersedes the v1.0 IACG design. The system has been repositioned from a post-execution governance framework to an **autonomous pre-billing cost prevention system**. Every component has been upgraded or replaced to enforce prevention at the earliest possible decision point.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Design Goals & Principles](#3-design-goals--principles)
4. [System Architecture](#4-system-architecture)
5. [Component Design](#5-component-design)
   - 5.1 [Intent Modeling Layer](#51-intent-modeling-layer)
   - 5.2 [Pre-Execution Simulation Engine](#52-pre-execution-simulation-engine)
   - 5.3 [Intent → Policy Learning System](#53-intent--policy-learning-system)
   - 5.4 [Policy-Driven Pre-Provisioning Guardrails](#54-policy-driven-pre-provisioning-guardrails)
   - 5.5 [Auto-Correcting Runtime Optimizer](#55-auto-correcting-runtime-optimizer)
   - 5.6 [Cost Prevention Score (CPS)](#56-cost-prevention-score-cps)
   - 5.7 [Cross-Cloud Normalization Layer](#57-cross-cloud-normalization-layer)
   - 5.8 [ML-Based Resource Attribution](#58-ml-based-resource-attribution)
   - 5.9 [Semantic Anomaly Detection & Root Cause Analysis](#59-semantic-anomaly-detection--root-cause-analysis)
   - 5.10 [AI Workload Governance Module](#510-ai-workload-governance-module)
6. [Data Model](#6-data-model)
7. [Experiments & Evaluation Plan](#7-experiments--evaluation-plan)
8. [Repository Structure](#8-repository-structure)
9. [Authorship & Contribution Map](#9-authorship--contribution-map)
10. [Design Decisions & Open Questions](#10-design-decisions--open-questions)
11. [References](#11-references)

---

## 1. Executive Summary

Modern cloud cost governance has a fundamental architecture flaw: it is built entirely around detection and response, not prevention. Billing systems fire after waste has accumulated. Anomaly detectors trigger after hours of inefficient resource consumption. Governance dashboards surface insights with no enforcement path. The result is a structural lag between cloud activity and cost accountability that compounds at scale.

The **Pre-Billing Cost Prevention Framework (PBCP)** — evolved from the Intent-Aware Cloud Governance (IACG) research line — eliminates this lag by repositioning every governance action to occur *before* billing is incurred. The system operates at three enforcement points:

1. **Pre-provisioning stage** — evaluate workload intent against a learned policy registry and a cross-cloud cost model; block or auto-correct over-provisioned configurations before any resource is created.
2. **Pre-execution simulation stage** — run a full cost and utilization simulation on the exact requested workload; if predicted waste exceeds a threshold, trigger BLOCK, AUTO-CORRECT, or SUGGEST before the first instruction executes.
3. **Runtime adaptive correction stage** — during execution, continuously monitor and autonomously take corrective actions (downscale, terminate, migrate to spot) while logging every dollar of cost prevented.

A novel **Cost Prevention Score (CPS)** metric — defined as `CPS = Prevented_Cost / Potential_Cost_Without_System` — provides a single measurable output that quantifies the system's economic value at every stage and enables direct comparison across workload types and cloud providers.

This document describes the full system design, data model, experimental plan, and authorship breakdown for the PBCP research implementation.

---

## 2. Problem Statement

### 2.1 The Pre-Billing Gap

Every cloud cost governance system in production today operates on the same flawed premise: it analyzes costs *after they appear in a billing report*. The architectural consequence is unavoidable:

```
Resource Provisioned → Resource Runs → Billing Period Closes → Report Generated → Action Taken
         ↑                                                                              ↓
         └─────────────────────── waste already incurred ──────────────────────────────┘
```

Even the most aggressive post-billing optimization cannot recover cost that was already spent. The only path to genuine prevention is moving every decision point to the left of the billing event.

### 2.2 Limitations of Current Approaches

| Approach | When It Acts | Core Limitation |
|---|---|---|
| Static provisioning policies | Pre-provision | Ignores workload semantics; over-provisions by default |
| Threshold-based anomaly detection | Post-execution | Fires after waste has occurred; high false-positive rate |
| Rule-based cost governance | Pre-provision | Brittle; requires manual maintenance as workloads evolve |
| FinOps dashboards / recommendations | Post-billing | Provides insight with no enforcement path |
| Cloud-native advisors (Trusted Advisor, Azure Advisor) | Post-billing | Advisory only; no learned policy; no intent context |

### 2.3 Positioning Against Cloud-Native Advisors

AWS Trusted Advisor, Azure Advisor, and GCP Recommender represent the current state of the art in cloud cost governance. All three share a fundamental architectural constraint: they operate on billing and utilization data that is already 24–72 hours old, produce advisory recommendations with no enforcement mechanism, and have no knowledge of *why* a workload was provisioned the way it was. A recommendation to "resize this EC2 instance" is generated without any context about whether the instance is serving a latency-sensitive API, running a one-time ETL job, or sitting idle after a project was cancelled.

PBCP differs on every dimension: it acts before execution rather than after billing, it enforces decisions rather than suggesting them, and it grounds every governance action in structured workload intent — the declared purpose, team, expected duration, and resource requirements that a cloud-native advisor never sees. The result is a system that prevents waste rather than reporting it.

### 2.4 Why Workload Semantics Matter

Static rules — "use spot for batch jobs", "cap node count at 10" — fail because they treat all workloads of a given type as identical. A 4-hour ETL job processing 50 GB of data has fundamentally different optimal resource requirements than a 4-hour ETL job processing 500 GB, even though both would match the same rule. Without capturing the *intent* behind a workload — its data volume expectations, team history, priority level, and run frequency — any governance system is operating on incomplete information.

Intent modeling closes this gap: by structuring the semantic properties of a workload at submission time, the system can match it against historically optimal configurations for *similar* workloads rather than applying one-size-fits-all rules. This is what makes learned policies more accurate than static thresholds, and what makes the simulation engine's utilization estimates workload-specific rather than class-generic.

### 2.5 The Three Failure Modes PBCP Addresses

**1. Pre-provisioning blindness:** Users select configurations without context-aware guidance. Without a simulation layer, there is no mechanism to predict that a 20-node cluster will run at 15% CPU utilization before it is provisioned.

**2. No cost prediction before execution:** Existing systems cannot answer "what will this workload cost?" before it runs. A pre-execution simulation engine closes this gap.

**3. Advisory-only governance:** Current systems produce recommendations that can be ignored. PBCP replaces advisory guardrails with enforceable policies derived from learned optimal behavior, and replaces runtime monitoring with autonomous corrective actions.

### 2.6 Scope

PBCP governs the following workload types across AWS, Azure, and GCP:

- **ETL Pipelines** — batch transformation and data validation jobs
- **Ad Hoc Analytics** — interactive and exploratory queries
- **Machine Learning** — model training, fine-tuning, and batch inference
- **AI / LLM Pipelines** — vector database operations, RAG pipelines, token-intensive LLM calls
- **Streaming Jobs** — continuous event-processing workloads

---

## 3. Design Goals & Principles

### 3.1 Goals

| ID | Goal | Success Metric |
|---|---|---|
| G1 | Prevent cloud waste before billing occurs | Valid CPS ≥ 0.30 across all workload types (CPS × ESR, with ESR ≥ 0.95) |
| G2 | Reduce over-provisioning at provisioning time | ≥ 40% reduction in over-provisioning rate vs. baseline |
| G3 | Improve resource utilization during execution | ≥ 20% improvement in avg CPU/memory utilization |
| G4 | Enforce governance decisions, not just recommend them | ≥ 85% of triggered policies result in enforced action |
| G5 | Detect anomalies before billing cycle closes | Mean Time to Detection < 15 minutes |
| G6 | Reduce AI workload (LLM) token waste | ≥ 25% token cost reduction per LLM pipeline |
| G7 | Attribute untagged resources automatically | ≥ 90% attribution accuracy on untagged resource set |

### 3.2 Design Principles

- **Prevention over Detection** — every component is designed to act before cost is incurred, not after.
- **Enforceability over Advisory** — every governance decision must produce a binding action (BLOCK, AUTO-CORRECT, TERMINATE), not just a suggestion.
- **Measurability** — every decision contributes to a tracked CPS score; unmeasured savings do not count.
- **Explainability** — every action must include a human-readable rationale, a confidence score, and a counterfactual (what would have been spent without the action).
- **Cross-Cloud Parity** — all cost reasoning operates over a normalized, cloud-agnostic representation; AWS, Azure, and GCP are treated equivalently.
- **Closed-Loop Learning** — execution outcomes feed back into the policy registry and simulation models, enabling continuous improvement without explicit retraining.

---

## 4. System Architecture

```
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                  Pre-Billing Cost Prevention Framework (PBCP)                │
 │                                                                              │
 │  STAGE 0 ─ NORMALIZATION                                                     │
 │  ┌─────────────────────────────────────────────────────────────────────────┐ │
 │  │  cost_normalizer/  ←  AWS / Azure / GCP billing                        │ │
 │  │  Unified Cost Representation (UCR) — cloud-agnostic compute unit       │ │
 │  └─────────────────────────────────────────────────────────────────────────┘ │
 │                                       │                                      │
 │  STAGE 1 ─ INTENT CAPTURE                                                    │
 │  ┌─────────────────────────────────────────────────────────────────────────┐ │
 │  │  intent_model/  ←  workload metadata + description + resource request  │ │
 │  │  WorkloadIntent → structured representation + workload_type vector     │ │
 │  └─────────────────────────────────────────────────────────────────────────┘ │
 │                                       │ WorkloadIntent                       │
 │  STAGE 2 ─ PRE-EXECUTION SIMULATION (CRITICAL)                               │
 │  ┌─────────────────────────────────────────────────────────────────────────┐ │
 │  │  simulation_engine/                                                     │ │
 │  │  Input: WorkloadIntent + UCR pricing                                   │ │
 │  │  Output: predicted_cost · predicted_utilization · predicted_waste      │ │
 │  │                                                                         │ │
 │  │  waste > 50%  →  BLOCK                                                 │ │
 │  │  waste > 30%  →  AUTO-CORRECT (right-size + resubmit)                 │ │
 │  │  waste > 15%  →  SUGGEST (advisory)                                    │ │
 │  │  else         →  APPROVE                                               │ │
 │  └─────────────────────────────────────────────────────────────────────────┘ │
 │                                       │                                      │
 │  STAGE 3 ─ POLICY ENFORCEMENT                                                │
 │  ┌─────────────────────────────────────────────────────────────────────────┐ │
 │  │  policy_engine/ + guardrails/                                           │ │
 │  │  Intent → PolicyRegistry lookup → enforced action                      │ │
 │  │  Policies learned from historical optimal workloads                    │ │
 │  └─────────────────────────────────────────────────────────────────────────┘ │
 │                                       │ approved + right-sized config        │
 │  STAGE 4 ─ RUNTIME AUTO-CORRECTION                                           │
 │  ┌─────────────────────────────────────────────────────────────────────────┐ │
 │  │  runtime_optimizer/                                                     │ │
 │  │  Monitor: CPU/memory utilization, idle time, spot availability         │ │
 │  │  Act:     downscale · terminate · spot-migrate · enforce runtime limit  │ │
 │  │  Log:     action_taken · cost_prevented → CPS record                   │ │
 │  └─────────────────────────────────────────────────────────────────────────┘ │
 │                                       │ runtime actuals                      │
 │  STAGE 5 ─ MEASUREMENT & LEARNING                                            │
 │  ┌─────────────────────────────────────────────────────────────────────────┐ │
 │  │  cps_metrics/   → CPS per workload · total prevented · % reduction     │ │
 │  │  policy_engine/ → update policy registry from outcomes                 │ │
 │  │  anomaly_rca/   → detect intent-behavior mismatch → prevention feedback│ │
 │  └─────────────────────────────────────────────────────────────────────────┘ │
 │                                                                              │
 │  INTELLIGENCE LAYER (Sreeja)                                                 │
 │  ┌───────────────┐  ┌────────────────────┐  ┌──────────────────────────────┐ │
 │  │ ml_attribution│  │   anomaly_rca/     │  │    ai_governance/            │ │
 │  │ Auto-tag       │  │ RAG-based RCA      │  │ Token budget enforcement     │ │
 │  │ untagged       │  │ Anomaly → CPS loop │  │ LLM policy enforcement       │ │
 │  │ resources      │  │                    │  │                              │ │
 │  └───────────────┘  └────────────────────┘  └──────────────────────────────┘ │
 └──────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary

```
Workload Submission
      │
      ▼
[cost_normalizer] → Unified Cost Representation (UCR)
      │
      ▼
[intent_model] → WorkloadIntent (structured)
      │
      ▼
[simulation_engine] → SimulationResult {predicted_cost, predicted_waste, intervention}
      │
      ├── BLOCK ──────────────────────────────────────────────────→ [cps_metrics] record
      │
      ├── AUTO-CORRECT → right-sized WorkloadIntent
      │         │
      │         ▼
      └── APPROVE → [policy_engine / guardrails] → final enforcement check
                          │
                          ▼
                  Resource provisioned & running
                          │
                          ▼
                  [runtime_optimizer] → autonomous corrections → [cps_metrics]
                          │
                          ▼
                  [anomaly_rca / ml_attribution / ai_governance] → intelligence layer
                          │
                          ▼
                  [policy_engine] → policy registry update (closed loop)
```

---

## 5. Component Design

### 5.1 Intent Modeling Layer

**Owner:** Keerthi Rapolu
**Location:** `/intent_model/`

#### Purpose

Parse and structure workload submission metadata into a `WorkloadIntent` object — the canonical input to every downstream component. In v2.0, the intent model's primary output is a structured data record rather than a raw embedding vector; the policy engine and simulation engine consume structured fields, not similarity scores.

#### Core Data Types

```python
WorkloadType = Literal["etl", "llm_pipeline", "adhoc", "streaming", "ml_training", "batch", "serving"]
CloudProvider = Literal["aws", "azure", "gcp"]
Environment = Literal["sandbox", "dev", "test", "staging", "prod"]
Priority = Literal["low", "medium", "high", "critical"]

@dataclass
class ResourceConfig:
    cloud_provider: CloudProvider
    instance_type: str            # e.g., "m5.xlarge", "n2-standard-4"
    node_count: int
    vcpu_per_node: int
    memory_gb_per_node: float
    storage_gb: float
    region: str
    use_spot: bool = False
    auto_shutdown_hours: Optional[float] = None

@dataclass
class WorkloadIntent:
    intent_id: str                # UUID, auto-generated
    workload_type: WorkloadType
    requested_resources: ResourceConfig
    duration_hours: float
    team: str
    environment: Environment
    priority: Priority = "medium"
    token_budget: Optional[int] = None   # Required for llm_pipeline
    tags: dict[str, str] = field(default_factory=dict)
    raw_intent: str = ""          # original description or config blob
    submitted_at: datetime = field(default_factory=datetime.utcnow)
```

#### Intent Catalog

A built-in `INTENT_CATALOG` stores typical profiles per workload type, used by the simulation engine as utilization priors:

| Workload Type | Typical Utilization | Optimal Node Range | Auto-Shutdown Required | Spot Eligible |
|---|---|---|---|---|
| `etl` | 55% | 2–10 | Yes (≤ 4 hr) | Yes |
| `adhoc` | 30% | 1–5 | Yes (≤ 2 hr) | Yes |
| `llm_pipeline` | 80% | 1–4 | Yes (≤ 8 hr) | No |
| `ml_training` | 85% | 2–16 | Yes (≤ 24 hr) | Yes |
| `batch` | 60% | 2–8 | Yes (≤ 6 hr) | Yes |
| `streaming` | 65% | 2–8 | No | No |
| `serving` | 40% | 2–10 | No | No |

---

### 5.2 Pre-Execution Simulation Engine

**Owner:** Keerthi Rapolu
**Location:** `/simulation_engine/`

> **This is the most critical new component in v2.0.** The simulation engine is the system's first line of prevention. It runs synchronously before any resource is provisioned or any job is launched.

#### Purpose

Given a `WorkloadIntent`, predict the cost, utilization, and waste that will result if the workload runs as-requested. If predicted waste exceeds a threshold, trigger an intervention before execution begins.

#### Pipeline

```
WorkloadIntent
      │
      ▼
[cost_model] ─── instance_type × node_count × duration × UCR pricing
      │
      ▼
predicted_baseline_cost: float
      │
      ▼
[utilization estimator] ─── workload_type catalog prior
                         +── over-provisioning adjustment
                             (if node_count > optimal_range.max,
                              utilization ∝ 1 / over_factor)
      │
      ▼
predicted_utilization: float
predicted_waste: float = baseline_cost × (1 − utilization)
waste_fraction: float = 1 − utilization
      │
      ▼
[right-sizer] ─── target_utilization = 0.70
               ── right_sized_nodes = ceil(current_nodes × utilization / target)
               ── enable spot if workload_type is spot_eligible
      │
      ▼
right_sized_cost: float
prevented_cost: float = baseline_cost − right_sized_cost
      │
      ▼
[intervention engine]
      ├── waste_fraction > 0.50  →  BLOCK       (refuse execution as-requested)
      ├── waste_fraction > 0.30  →  AUTO-CORRECT (resubmit with right-sized config)
      ├── waste_fraction > 0.15  →  SUGGEST      (advisory warning)
      └── else                   →  APPROVE
```

#### SimulationResult Schema

```python
@dataclass
class SimulationResult:
    simulation_id: str
    intent_id: str
    predicted_cost: float             # cost if run as-requested
    predicted_utilization: float      # 0.0–1.0
    predicted_waste: float            # USD wasted if not corrected
    waste_fraction: float             # predicted_waste / predicted_cost
    intervention: Literal["BLOCK", "AUTO_CORRECT", "SUGGEST", "APPROVE"]
    right_sized_resources: Optional[ResourceConfig]
    right_sized_cost: Optional[float]
    prevented_cost: Optional[float]   # predicted_cost − right_sized_cost
    explanation: str                  # human-readable rationale
    confidence: float                 # 0.0–1.0
    simulated_at: datetime
```

#### CloudCostModel

The cost model maintains a YAML-backed pricing table per cloud provider, covering the most common instance types. For unknown instance types, it falls back to a default hourly rate derived from vCPU count × standard rate. Spot/preemptible discounts are applied as a configurable multiplier per provider.

```python
class CloudCostModel:
    def compute_cost(resources: ResourceConfig, duration_hours: float) -> float:
        base_rate = pricing_table[resources.cloud_provider][resources.instance_type]
        if resources.use_spot:
            base_rate *= (1.0 - spot_discount[resources.cloud_provider])
        return base_rate * resources.node_count * duration_hours

    def storage_cost(storage_gb: float, cloud_provider: CloudProvider, hours: float) -> float:
        return storage_per_gb_hour[cloud_provider] * storage_gb * hours
```

#### Thresholds (configurable in `config/simulation_config.yml`)

| Parameter | Default | Meaning |
|---|---|---|
| `block_fraction` | 0.50 | waste > 50% → BLOCK |
| `auto_correct_fraction` | 0.30 | waste > 30% → AUTO_CORRECT |
| `suggest_fraction` | 0.15 | waste > 15% → SUGGEST |
| `target_utilization` | 0.70 | right-sizing target after correction |

#### Latency & Feasibility

The simulation engine runs synchronously at submission time. Target latency is **< 2 seconds** for all standard workload types, achieved because the engine performs no network I/O — cost model data is loaded from YAML at startup, utilization priors are in-memory, and right-sizing is an arithmetic computation.

For low-risk workload types (environment = `sandbox` or `dev`, waste confidence < 0.60), an **async approval path** is available: the workload is provisioned immediately at the right-sized configuration while the full simulation report is generated in the background. This ensures governance never becomes a hard blocker for development workflows.

| Path | Trigger | Latency |
|---|---|---|
| Synchronous (default) | All `prod`/`staging` workloads | < 2 sec |
| Async | `sandbox`/`dev` + low confidence | < 50 ms (non-blocking) |
| Human escalation | `BLOCK` with low simulation confidence | Up to 15 min (manual review) |

---

### 5.3 Intent → Policy Learning System

**Owner:** Keerthi Rapolu
**Location:** `/policy_engine/`

#### Purpose

Replace static rule-based guardrails with a **learned policy registry** derived from historically optimal workloads. Policies are not advisory — they are enforced before provisioning.

#### Evolution from v1.0

| v1.0 (Advisory) | v2.0 (Enforced) |
|---|---|
| Intent → similarity search → recommendation | Intent → policy lookup → enforced action |
| Guardrails suggest optimal config | Policy engine blocks or auto-corrects |
| Thresholds set manually | Policies derived from historical optimal workloads |
| Single enforcement path | REJECT / AUTO_CORRECT / SUGGEST per policy |

#### Policy Schema

```python
@dataclass
class Policy:
    policy_id: str
    workload_type: str             # applies to this workload type ("*" = all)
    condition: str                 # "node_count_exceeds" | "auto_shutdown_hours_exceeds"
                                   # | "token_budget_missing" | "spot_not_enabled" | ...
    threshold: float               # condition parameter (e.g., 5 for node count)
    action: Literal["REJECT", "AUTO_CORRECT", "SUGGEST"]
    description: str
    source: Literal["builtin", "learned"]   # origin of the policy
    confidence: float              # 1.0 for builtin; learned from data for derived
    created_at: datetime
```

#### Built-In Policies (from `config/policy_config.yml`)

| Policy ID | Workload Type | Condition | Threshold | Action |
|---|---|---|---|---|
| `etl_auto_shutdown` | `etl` | `auto_shutdown_hours_exceeds` | 4.0 hrs | REJECT |
| `adhoc_max_nodes` | `adhoc` | `node_count_exceeds` | 5 nodes | AUTO_CORRECT |
| `llm_token_budget_required` | `llm_pipeline` | `token_budget_missing` | — | REJECT |
| `adhoc_spot_required` | `adhoc` | `spot_not_enabled` | — | SUGGEST |
| `etl_spot_required` | `etl` | `spot_not_enabled` | — | SUGGEST |
| `batch_auto_shutdown` | `batch` | `auto_shutdown_hours_exceeds` | 6.0 hrs | REJECT |
| `ml_training_auto_shutdown` | `ml_training` | `auto_shutdown_hours_exceeds` | 24.0 hrs | REJECT |

#### Policy Learner

The `PolicyLearner` derives new policies from historical workload data:

```
Historical Workload Records (past 90 days)
        │
        ▼
Group by workload_type
        │
        ▼
For each numeric feature (node_count, duration_hours, auto_shutdown_hours):
    Compute p25 of COST-EFFICIENT workloads (cost_efficiency_score > threshold)
        │
        ▼
If p25 differs significantly from current policy threshold:
    Emit new Policy(source="learned", confidence=derived_from_sample_size)
        │
        ▼
PolicyRegistry.upsert(learned_policy)  ← only if confidence ≥ 0.80
```

The current implementation uses percentile statistics as a transparent, auditable baseline. This is intentional: for an enforcement system, interpretability of the policy derivation process is as important as accuracy.

**Future direction — RL-based policy optimization:** The percentile approach is a strong baseline but does not account for the sequential nature of policy updates or the delayed reward signal (a policy set today may prevent waste two weeks from now). A natural extension is to model policy threshold selection as a multi-armed bandit problem, where each policy parameter choice is an arm and the reward is the CPS improvement observed over the following N days. This would allow thresholds to adapt to shifting workload patterns without manual recalibration. The `Policy.source` field already distinguishes `"builtin"` from `"learned"`, and a `"rl_optimized"` source value is reserved for this extension.

#### PolicyRegistry

```python
class PolicyRegistry:
    def get_policies(workload_type: str) -> list[Policy]
    def add(policy: Policy) -> None
    def upsert(policy: Policy) -> None      # update if exists, insert if new
    def remove(policy_id: str) -> None
    def export() -> list[dict]              # for persistence / audit
```

---

### 5.4 Policy-Driven Pre-Provisioning Guardrails

**Owner:** Keerthi Rapolu
**Location:** `/guardrails/`

#### Purpose

Integrate the simulation engine and policy engine into a single pre-provisioning decision gate. Every workload must pass through this gate before resources are created.

#### Decision Flow

```
WorkloadIntent submitted
        │
        ▼
[PolicyEnforcer] ── check all policies for workload_type
        │
        ├── REJECT violation found  →  return PolicyViolation; abort
        │
        ├── AUTO_CORRECT violations →  mutate WorkloadIntent; log correction
        │
        └── No REJECT violations
                  │
                  ▼
        [SimulationEngine.simulate(intent)]
                  │
                  ├── BLOCK          →  return SimulationResult; abort
                  ├── AUTO_CORRECT   →  use right_sized_resources; log prevention
                  ├── SUGGEST        →  surface suggestion; allow as-requested
                  └── APPROVE        →  allow as-requested
                  │
                  ▼
        Approved WorkloadIntent → resource provisioning
```

#### Guardrail Output Per Decision

```python
@dataclass
class GuardrailDecision:
    intent_id: str
    approved: bool
    final_resources: ResourceConfig    # may differ from requested if corrected
    policy_violations: list[PolicyViolation]
    simulation_result: SimulationResult
    total_prevented_cost: float        # sum of policy + simulation prevention
    explanation: str
    decision_at: datetime
```

---

### 5.5 Auto-Correcting Runtime Optimizer

**Owner:** Keerthi Rapolu
**Location:** `/runtime_optimizer/`

#### Purpose

Monitor active workloads and autonomously take corrective actions during execution. The system does not emit recommendations — it takes action and logs the cost prevented.

#### Evolution from v1.0

| v1.0 | v2.0 |
|---|---|
| Detect underutilization | Detect + downscale automatically |
| Alert on idle cluster | Alert + terminate idle cluster |
| Recommend spot migration | Execute spot migration automatically |
| Log anomaly | Log action + cost prevented → CPS record |

#### Monitored Signals and Responses

| Signal | Trigger Condition | Action Taken | Cost Prevention Mechanism |
|---|---|---|---|
| CPU underutilization | avg CPU < 25% for ≥ 15 min | Downscale cluster by 30–50% | Eliminated idle node-hours |
| Memory underutilization | avg memory < 20% for ≥ 15 min | Resize to smaller instance class | Smaller instance billing rate |
| Idle cluster | no active tasks for ≥ 10 min + past auto_shutdown_hours | Terminate | All remaining provisioned cost |
| Runtime overrun | actual_runtime > 2× expected_duration | Alert + enforce hard limit | Runaway job termination |
| Spot interruption | spot interruption signal received | Checkpoint + restart on on-demand | Job completion without full re-provision |

#### CorrectionAction Schema

```python
@dataclass
class CorrectionAction:
    action_id: str
    intent_id: str
    run_id: str
    action_type: Literal["downscale", "terminate", "spot_migrate", "enforce_limit", "escalate"]
    trigger_signal: str              # what signal caused this action
    before_config: ResourceConfig
    after_config: Optional[ResourceConfig]
    cost_at_trigger: float           # cost accrued up to this point
    projected_remaining_cost: float  # what would have been spent without action
    cost_prevented: float            # projected_remaining_cost − actual_remaining_cost
    executed_at: datetime
    explanation: str
```

#### Simulation Design (for experiments)

For evaluation against synthetic data, the runtime optimizer runs as an event-driven simulator:
- Workloads are assigned utilization time-series sampled from workload-type distributions (e.g., underutilized jobs use `Beta(2, 5)` for CPU)
- The simulator steps through time in 5-minute intervals, evaluating each signal
- Actions are applied deterministically when triggers are met
- Baseline: static system holds original configuration for full declared duration

---

### 5.6 Cost Prevention Score (CPS)

**Owner:** Keerthi Rapolu
**Location:** `/cps_metrics/`

#### Definition

```
CPS = Prevented_Cost / Potential_Cost_Without_System
```

Where:
- `Potential_Cost_Without_System` = cost if the workload ran as-requested for its full declared duration with no corrections
- `Prevented_Cost` = `Potential_Cost_Without_System` − `Actual_Cost_With_System`

A CPS of 0.35 means the system prevented 35% of what would have been billed without it.

#### Execution Success Rate (ESR) — Constraint Metric

CPS alone is gameable: a system that blocks every workload trivially achieves CPS = 1.0 while delivering no business value. To prevent this, PBCP introduces a mandatory constraint metric:

```
ESR = Workloads_Completed_Successfully / Workloads_Submitted
```

A workload is considered successfully completed if it finishes within 120% of its declared expected duration without failure. Blocked workloads that are resubmitted with corrected configurations and then complete successfully count as ESR successes.

The primary reporting metric for all experiments is **Valid CPS**, defined as:

```
Valid CPS = CPS × ESR
```

This ensures that prevention value is only counted when workloads actually complete. A system that blocks aggressively will have low ESR and therefore low Valid CPS, regardless of its raw CPS score. The target Valid CPS for this system is ≥ 0.30, with ESR ≥ 0.95 as a hard constraint — meaning at most 5% of submitted workloads may fail or be permanently blocked without successful resubmission.

Both CPS and ESR are tracked per workload and reported in every experiment summary.

#### CPS Tracked at Three Stages

| Stage | Prevention Source | Example |
|---|---|---|
| `pre_provision` | Simulation engine BLOCK/AUTO-CORRECT | Reduced 20-node cluster to 8 nodes before provisioning |
| `runtime` | Runtime optimizer downscale/terminate | Terminated idle cluster 2 hours early |
| `ai_workload` | AI governance token/embedding reduction | Compressed prompt; reduced tokens by 40% |

#### CPSRecord Schema

```python
@dataclass
class CPSRecord:
    record_id: str
    intent_id: str
    run_id: Optional[str]
    stage: Literal["pre_provision", "runtime", "ai_workload"]
    potential_cost: float            # cost without system
    actual_cost: float               # cost with system
    prevented_cost: float            # potential − actual
    cps: float                       # prevented / potential
    workload_type: str
    cloud_provider: str
    team: str
    environment: str
    recorded_at: datetime
    source_action: str               # e.g., "AUTO_CORRECT", "terminate", "token_budget"
    explanation: str
```

#### Aggregate CPS Reporting

The `PreventionTracker` accumulates `CPSRecord` entries and exposes:

```python
class PreventionTracker:
    def add(record: CPSRecord) -> None
    def total_prevented(stage: Optional[str] = None) -> float
    def aggregate_cps(stage: Optional[str] = None) -> float
    def by_workload_type() -> dict[str, dict]   # type → {cps, prevented, count}
    def by_team() -> dict[str, dict]
    def summary() -> dict                        # full roll-up for experiment output
```

#### CPS Exposure

CPS is exposed at three levels:
- **Per-workload** — attached to every `SimulationResult` and `CorrectionAction`
- **Per-experiment** — summarized in experiment output CSVs
- **System-level** — rolling 30-day aggregate surfaced in evaluation reports

---

### 5.7 Cross-Cloud Normalization Layer

**Owner:** Keerthi Rapolu
**Location:** `/cost_normalizer/`

#### Purpose

Translate cloud-specific billing units, instance families, and pricing structures into a single **Unified Cost Representation (UCR)** that all downstream components can reason over without cloud-specific logic.

#### Normalization Scope

| Dimension | AWS | Azure | GCP | UCR |
|---|---|---|---|---|
| Compute pricing | instance_type × hourly rate | vm_size × hourly rate | machine_type × hourly rate | `cost_per_vcpu_hour`, `cost_per_gb_hour` |
| Storage pricing | S3/EBS $/GB/month | Blob/Disk $/GB/month | GCS/PD $/GB/month | `storage_usd_per_gb_hour` |
| Spot/preemptible discount | ~70% | ~60% | ~80% | `spot_discount_fraction` |
| Commitment/RI pricing | Reserved Instances / Savings Plans | Reserved VMs / Savings Plans | CUDs / SUDs | `commitment_discount_fraction` |

#### UnifiedCostRecord Schema

```python
@dataclass
class UnifiedCostRecord:
    resource_id: str
    cloud_provider: CloudProvider
    instance_type: str
    vcpu_count: int
    memory_gb: float
    on_demand_hourly_usd: float       # base on-demand rate
    spot_hourly_usd: float            # on_demand × (1 − spot_discount)
    storage_usd_per_gb_hour: float
    cost_per_vcpu_hour: float         # on_demand / vcpu_count
    cost_per_gb_memory_hour: float    # on_demand / memory_gb
    normalized_at: datetime
```

#### Cross-Cloud Comparability

The normalizer enables the simulation engine to compare equivalent workloads across providers:

```python
class CrossCloudNormalizer:
    def normalize(resources: ResourceConfig) -> UnifiedCostRecord
    def cheapest_equivalent(intent: WorkloadIntent, providers: list[CloudProvider]) -> dict
    def cost_comparison(intent: WorkloadIntent) -> dict[CloudProvider, float]
```

---

### 5.8 ML-Based Resource Attribution

**Owner:** Sreeja Katta
**Location:** `/ml_attribution/`

#### Purpose

Automatically assign `team` and `workload_type` labels to untagged cloud resources using a trained classifier, enabling cost attribution, anomaly detection, and guardrail enforcement even for resources that lack governance metadata.

#### Feature Set

| Feature Group | Features |
|---|---|
| Instance characteristics | `instance_type`, `vcpu_count`, `memory_gb`, `cloud_provider` |
| Usage patterns | `cpu_util_avg`, `memory_util_avg`, `idle_hours_fraction`, `runtime_hours` |
| Cost patterns | `hourly_cost_usd`, `total_cost_usd`, `cost_per_vcpu_hour` |
| Naming patterns | Bag-of-words on `resource_name` (TF-IDF encoded, top 50 tokens) |
| Temporal | `hour_of_day_median`, `day_of_week_mode`, `run_frequency` |

#### Model Architecture

```
ResourceFeatureExtractor → feature_vector (numeric)
        │
        ▼
ResourceAttributionClassifier
  ├── Model: RandomForestClassifier (baseline)
  │          n_estimators=200, max_depth=15, class_weight="balanced"
  ├── Target 1: predicted_team  (multiclass)
  └── Target 2: predicted_workload_type  (multiclass)
        │
        ▼
AttributionResult:
  predicted_team: str
  predicted_workload_type: WorkloadType
  team_confidence: float          # P(predicted_team)
  workload_type_confidence: float
  feature_importances: dict[str, float]
```

#### Integration Points

The attribution module exposes a single `classify(resource_record)` interface consumed by:

1. **Guardrails** — enforce policies on auto-attributed workload types
2. **Cost attribution** — assign team cost even without tags
3. **Anomaly RCA** — provide workload context for anomaly analysis
4. **CPS tracking** — attribute prevented cost to the correct team

#### Training Data

- Labeled training set: tagged historical workloads from the synthetic dataset (300 labeled examples per workload type)
- Features extracted per workload using `ResourceFeatureExtractor`
- 5-fold stratified cross-validation for evaluation
- Feature importances exported for explainability reports

---

### 5.9 Semantic Anomaly Detection & Root Cause Analysis

**Owner:** Sreeja Katta
**Location:** `/anomaly_rca/`

#### Purpose

Detect workloads whose runtime behavior does not match their declared intent, generate explainable root cause analysis using retrieval-augmented reasoning, and feed anomaly signals back into the prevention system to continuously improve policies.

#### Evolution from v1.0

| v1.0 | v2.0 |
|---|---|
| Intent vs. behavior cosine distance | Same, plus ML attribution context |
| RAG-based root cause analysis | Same, plus structured cause categories |
| Anomaly alert emitted | Anomaly → prevention feedback loop → policy update |
| Threshold detector as baseline | ML attribution model improves untagged anomaly precision |

#### Anomaly Detection Model

```
Intent Vector (pre-execution)
        +
Behavior Vector (post-execution: normalize runtime metrics → vector)
        │
        ▼
cosine_distance(intent_vector, behavior_vector)
        │
  distance > θ_anomaly  →  AnomalyRecord (flagged)
  distance ≤ θ_anomaly  →  normal execution
```

**Behavior vector** encodes:
```python
f(cpu_util_avg, memory_util_avg, runtime_minutes, idle_time_ratio,
  cost_delta_pct, actual_vs_expected_duration_ratio)
```

#### ML Attribution Integration

For untagged resources, anomaly detection incorporates the ML attribution label and confidence score:

```python
@dataclass
class AnomalyRecord:
    anomaly_id: str
    intent_id: str
    run_id: str
    anomaly_score: float              # cosine distance (intent vs. behavior)
    is_anomaly: bool
    attributed_team: str              # from tags OR ml_attribution
    attributed_workload_type: str
    attribution_confidence: float     # 1.0 if tagged, ML confidence if untagged
    root_cause_category: str          # from RAG-RCA
    estimated_cost_impact: float
    detection_lag_minutes: int
    prevention_feedback_generated: bool
```

#### RAG-Based Root Cause Analysis

```
AnomalyRecord
      │
      ▼
Encode anomaly metrics → behavior vector
      │
      ▼
Retrieve Top-K similar historical incidents (FAISS index over incident store)
      │
      ▼
Compose RAG prompt: anomaly_description + retrieved_incidents
      │
      ▼
LLM (GPT-3.5-turbo / local Mistral-7B)
      │
      ▼
RCAReport:
  root_cause_category: str     # "over_provisioned" | "data_volume_spike" | ...
  probable_cause: str          # free-text explanation
  recommended_action: str
  confidence: float
  estimated_cost_impact: float
  historical_precedents: list[str]
```

#### Prevention Feedback Loop

When a runtime anomaly is flagged, the system generates a `PolicySuggestion` and submits it to the policy registry:

```
Anomaly detected (type: over_provisioned, workload_type: etl)
      │
      ▼
[AnomalyPreventionFeedback]
  - Compare anomaly conditions against existing policies
  - If no policy covers this scenario → generate PolicySuggestion
  - PolicySuggestion → PolicyLearner.evaluate() → PolicyRegistry.upsert()
      │
      ▼
Future identical workloads caught by pre-execution simulation
```

This closes the loop: runtime anomalies improve pre-execution prevention.

---

### 5.10 AI Workload Governance Module

**Owner:** Sreeja Katta
**Location:** `/ai_governance/`

#### Purpose

Extend governance to AI-specific workloads — LLM inference pipelines, RAG systems, and embedding generation — where cost inefficiencies manifest as token waste, oversized models, and redundant embedding computation rather than CPU or memory waste.

#### Token Budget Enforcement

```python
class TokenBudgetTracker:
    def check_budget(intent: WorkloadIntent) -> TokenBudgetResult:
        # For llm_pipeline workloads: token_budget is required (enforced by policy)
        # Estimate token consumption from prompt template + expected output length
        # Return: within_budget bool, estimated_tokens int, estimated_cost_usd float

    def enforce(intent: WorkloadIntent) -> WorkloadIntent:
        # If estimated_tokens > token_budget: truncate prompt, compress system prompt
        # Return modified WorkloadIntent with token-safe configuration
```

#### LLM Policy Enforcement

The `LLMPolicyEnforcer` applies AI-specific policies:

| Policy | Trigger | Action |
|---|---|---|
| Token budget declaration required | `token_budget` is None on `llm_pipeline` | REJECT |
| System prompt size limit | System prompt > 40% of declared token_budget | AUTO_CORRECT (compress prompt) |
| Embedding model oversize | 1536-dim embedding requested for retrieval-only task | SUGGEST (downgrade to 384-dim) |
| No result caching | Repeated identical queries detected in history | SUGGEST (add semantic cache) |
| Full-dataset embedding | num_vectors > threshold with no subset logic | SUGGEST (metadata-first filter) |

#### AI Workload Metrics

```python
@dataclass
class AIWorkloadMetrics:
    workload_id: str
    embedding_dim: int
    num_vectors: int
    token_budget_declared: Optional[int]
    token_usage_actual: int
    token_waste: int                   # budget − actual (if budget set)
    model_type: str
    rag_calls: int
    cache_hit_rate: float
    estimated_cost_usd: float
    optimized_cost_usd: float          # after AI governance actions
    cps_ai: float                      # prevented / potential for this workload
```

---

## 6. Data Model

### 6.1 Schema Overview

The synthetic dataset consists of eight interrelated tables. Tables 1–6 are shared infrastructure; Tables 7–8 are new in v2.0.

#### Table 1: `workload_intent`

| Column | Type | Description |
|---|---|---|
| `intent_id` | UUID | Primary key |
| `workload_name` | string | Human-readable name |
| `description` | text | Free-text workload purpose |
| `team` | string | Owning team |
| `workload_type` | enum | `etl`, `adhoc`, `ml_training`, `llm_pipeline`, `batch`, `streaming`, `serving` |
| `environment` | enum | `sandbox`, `dev`, `test`, `staging`, `prod` |
| `priority` | enum | `low`, `medium`, `high`, `critical` |
| `expected_duration_hours` | float | Expected runtime |
| `frequency` | enum | `hourly`, `daily`, `weekly`, `on_demand` |
| `token_budget` | int? | Required for `llm_pipeline` |
| `submitted_at` | timestamp | Submission time |

#### Table 2: `provisioned_config`

| Column | Type | Description |
|---|---|---|
| `intent_id` | UUID | FK → workload_intent |
| `cloud_provider` | enum | `aws`, `azure`, `gcp` |
| `instance_type` | string | e.g., `m5.xlarge` |
| `node_count` | int | |
| `vcpu_per_node` | int | |
| `memory_gb_per_node` | float | |
| `storage_gb` | float | |
| `use_spot` | bool | |
| `auto_shutdown_hours` | float? | |
| `policy_type` | enum | `user_requested`, `auto_corrected`, `policy_enforced` |

#### Table 3: `runtime_metrics`

| Column | Type | Description |
|---|---|---|
| `run_id` | UUID | Primary key |
| `intent_id` | UUID | FK → workload_intent |
| `cpu_utilization_avg` | float | 0.0–1.0 |
| `memory_utilization_avg` | float | 0.0–1.0 |
| `actual_duration_hours` | float | |
| `idle_time_hours` | float | |
| `failure_flag` | bool | |
| `spot_interruption` | bool | |

#### Table 4: `cost_records`

| Column | Type | Description |
|---|---|---|
| `run_id` | UUID | FK → runtime_metrics |
| `intent_id` | UUID | FK → workload_intent |
| `potential_cost_usd` | float | Cost without system intervention |
| `actual_cost_usd` | float | Cost with system intervention |
| `prevented_cost_usd` | float | Derived: potential − actual |
| `stage` | enum | `pre_provision`, `runtime`, `ai_workload` |

#### Table 5: `historical_incidents`

| Column | Type | Description |
|---|---|---|
| `incident_id` | UUID | Primary key |
| `intent_id` | UUID | FK → workload_intent |
| `incident_type` | enum | `over_provisioned`, `runaway_job`, `spot_interruption`, `idle_cluster`, `token_waste` |
| `description` | text | Incident narrative |
| `fix_applied` | text | Remediation taken |
| `cost_impact_usd` | float | |
| `detection_lag_minutes` | int | Time from occurrence to detection |

#### Table 6: `ai_workload_metrics`

| Column | Type | Description |
|---|---|---|
| `intent_id` | UUID | FK → workload_intent (workload_type = `llm_pipeline`) |
| `embedding_dim` | int | |
| `num_vectors` | int | |
| `token_budget` | int? | |
| `token_usage_actual` | int | |
| `model_type` | string | |
| `rag_calls` | int | |
| `cache_hit_rate` | float | |
| `estimated_cost_usd` | float | |

#### Table 7: `cps_records` *(new in v2.0)*

| Column | Type | Description |
|---|---|---|
| `record_id` | UUID | Primary key |
| `intent_id` | UUID | FK → workload_intent |
| `run_id` | UUID? | FK → runtime_metrics |
| `stage` | enum | `pre_provision`, `runtime`, `ai_workload` |
| `potential_cost_usd` | float | |
| `actual_cost_usd` | float | |
| `prevented_cost_usd` | float | |
| `cps` | float | prevented / potential |
| `source_action` | string | e.g., `AUTO_CORRECT`, `terminate`, `token_budget` |
| `recorded_at` | timestamp | |

#### Table 8: `policy_registry` *(new in v2.0)*

| Column | Type | Description |
|---|---|---|
| `policy_id` | string | Primary key |
| `workload_type` | string | Target workload type |
| `condition` | string | Policy condition key |
| `threshold` | float | Condition threshold |
| `action` | enum | `REJECT`, `AUTO_CORRECT`, `SUGGEST` |
| `source` | enum | `builtin`, `learned` |
| `confidence` | float | 1.0 for builtin; data-derived for learned |
| `created_at` | timestamp | |
| `last_updated_at` | timestamp | |

### 6.2 Synthetic Data Generation

- **Total workloads:** 500 (200 ETL, 100 adhoc, 100 ml_training, 50 llm_pipeline, 30 batch, 20 streaming)
- **Runs per workload:** 30–90 historical runs
- **Anomaly injection rate:** ~20% of runs include injected inefficiencies
- **Over-provisioning injection:** 35% of ETL workloads provisioned with 2–3× optimal nodes
- **Idle cluster injection:** 25% of adhoc workloads have idle time > auto_shutdown threshold
- **LLM token waste injection:** 30% of llm_pipeline workloads have token_budget = None or usage > budget
- **Random seed:** fixed (42) for reproducibility
- **Generation script:** `/data/generate_dataset.py`

#### Real-World Fidelity

The synthetic dataset is explicitly modeled after the schemas and cost structures of production cloud billing systems to ensure practical credibility:

- **AWS CUR (Cost and Usage Report):** Instance types, pricing dimensions (on-demand, reserved, spot), and cost allocation tag fields are drawn directly from the AWS CUR v2 column specification. The `instance_type` values (`m5.xlarge`, `r5.2xlarge`, `p3.2xlarge`, etc.) and their hourly rates match current AWS us-east-1 on-demand pricing.
- **Azure Cost Management exports:** Resource SKU naming conventions (`Standard_D4s_v3`, `Standard_NC6`), amortized cost fields, and reservation utilization patterns follow the Azure Cost Management API export format.
- **GCP Billing exports:** Machine type naming (`n2-standard-4`, `a2-highgpu-1g`), committed use discount (CUD/SUD) credit structures, and BigQuery billing export schema conventions are replicated.

The workload distributions (over-provisioning rates, utilization variance by job type, idle cluster frequency) are parameterized to reflect enterprise-scale patterns reported in the Flexera 2024 State of the Cloud Report, which found that 32% of cloud spend is wasted and over-provisioning accounts for the largest share. This grounds the experiment results in realistic, externally validated waste rates rather than arbitrarily chosen anomaly injection frequencies.

---

## 7. Experiments & Evaluation Plan

### Experiment 1 — Pre-Provision Cost Prevention

**Goal:** Demonstrate that the simulation engine and policy guardrails prevent cost before any resource is provisioned.

**Owner:** Keerthi Rapolu

**Scenario:** Over-provisioned ETL workload (20 nodes requested, 6 nodes optimal)

| | Baseline (Static) | PBCP System |
|---|---|---|
| Config source | User-requested | Simulation engine + policy engine |
| Nodes provisioned | 20 | 6 (AUTO-CORRECT) |
| Cost per run | $192.00 | $57.60 |
| Prevented cost | — | $134.40 |
| CPS | — | 0.70 |

**Metrics:**
- Prevented cost (USD) per run
- CPS at `pre_provision` stage
- Policy enforcement rate (% of submissions triggering AUTO_CORRECT or BLOCK)
- Over-provisioning rate before vs. after system

**Expected Result:** CPS ≥ 0.35 at pre-provision stage; over-provisioning rate reduced ≥ 40%.

---

### Experiment 2 — Runtime Cost Prevention

**Goal:** Demonstrate autonomous runtime correction preventing cost that escaped pre-provisioning.

**Owner:** Keerthi Rapolu

**Scenario A:** Idle cluster (adhoc job completes early; cluster runs idle for 3 hours)
**Scenario B:** Underutilized ETL (CPU avg 18%; cluster not scaled down without system)
**Scenario C:** Runaway ML job (actual runtime 3× expected; no hard limit enforced without system)

| Scenario | Baseline Cost | System Cost | Prevented | CPS |
|---|---|---|---|---|
| Idle cluster | $96.00 (8 hr idle) | $32.00 (terminated at 2 hr) | $64.00 | 0.67 |
| Underutilized ETL | $120.00 | $72.00 (downscaled 40%) | $48.00 | 0.40 |
| Runaway ML job | $612.00 (3× runtime) | $204.00 (terminated at 1×) | $408.00 | 0.67 |

**Metrics:**
- CPS at `runtime` stage per scenario
- Time-to-action (minutes from trigger signal to corrective action)
- Utilization improvement (CPU/memory avg before vs. after correction)

---

### Experiment 3 — Anomaly Detection with ML Attribution

**Goal:** Show that intent-behavior mismatch detection with ML attribution outperforms threshold-based detection.

**Owner:** Sreeja Katta

| | Threshold Detector | PBCP Semantic Detector |
|---|---|---|
| Signal | CPU < 30% OR idle > 20 min | Cosine distance (intent vs. behavior) > θ |
| Untagged resource handling | Ignored | ML attribution label + confidence |
| Attribution-aware detection | No | Yes |

**Metrics:**
- Precision, Recall, F1 on injected anomaly set
- Mean Time to Detection (MTTD, minutes)
- Attribution accuracy on untagged subset (target ≥ 90%)
- False positive rate

---

### Experiment 4 — AI Workload Governance

**Goal:** Measure token and embedding cost reduction through LLM-specific policy enforcement.

**Owner:** Sreeja Katta

**Scenario:** LLM pipeline without token budget declaration

| | Baseline | With AI Governance |
|---|---|---|
| Token budget declared | No | Enforced by policy |
| Estimated token usage | Unbounded | Capped at declared budget |
| Cost per pipeline run | $4.50 (avg) | $2.80 (avg) |
| Prevented cost | — | $1.70/run |
| CPS | — | 0.38 |

**Injected anti-patterns:**
- Token budget missing (30% of LLM workloads)
- System prompt > 40% of token budget (25%)
- Oversized embedding model for low-complexity retrieval (40%)
- No result caching for repeated queries (50%)

**Metrics:**
- CPS at `ai_workload` stage
- Token reduction % per policy type
- Embedding cost reduction %
- RAG call efficiency (precision@K)

---

### Experiment 5 — System-Level CPS Roll-Up

**Goal:** Report aggregate CPS across all stages and workload types to establish the system's total economic impact.

**Owner:** Joint (Keerthi + Sreeja)

**Output:**
```
Total workloads evaluated:        500
  Pre-provision interventions:    175  (35%)
  Runtime corrections:            112  (22%)
  AI governance actions:           48   (9%)

Total potential cost:          $94,200
Total actual cost:             $61,230
Total prevented cost:          $32,970
System-level CPS:                0.35
Execution Success Rate (ESR):    0.97   ← constraint: must be ≥ 0.95
Valid CPS (CPS × ESR):           0.34

CPS by stage:
  pre_provision:   0.40
  runtime:         0.31
  ai_workload:     0.27

CPS by workload type:
  etl:             0.42
  adhoc:           0.38
  llm_pipeline:    0.33
  ml_training:     0.28
```

---

### Baselines Summary

| Baseline | Description | Used in Experiments |
|---|---|---|
| **Static Provisioning** | User-requested config; no system intervention | Exp 1, 2 |
| **Rule-Based Policies** | Fixed rules (e.g., "large cluster for ML"); no learning | Exp 1, 3 |
| **Threshold Anomaly Detector** | Flag when CPU < 30% OR idle > 20 min | Exp 3 |
| **No AI Governance** | LLM pipelines run without token budget enforcement | Exp 4 |

---

## 8. Repository Structure

```
iacg/
├── README.md
├── IACG_Design_Document.md          ← this document
├── requirements.txt
│
├── config/
│   ├── simulation_config.yml        # waste thresholds, right-sizing targets
│   ├── policy_config.yml            # built-in policy definitions
│   ├── cps_config.yml               # CPS tracking configuration
│   └── cost_config.yml              # per-cloud instance pricing tables
│
├── data/
│   ├── generate_dataset.py          # Synthetic data generation (shared)
│   ├── schema.sql                   # Table definitions
│   ├── sample/                      # Committed sample (100 workloads)
│   └── full/                        # .gitignore'd; generated locally
│
├── intent_model/                    # Keerthi — workload intent parsing
│   ├── workload_intent.py           # WorkloadIntent, ResourceConfig data types
│   ├── intent_catalog.py            # IntentProfile, INTENT_CATALOG
│   └── __init__.py
│
├── simulation_engine/               # Keerthi — pre-execution simulation (CRITICAL)
│   ├── cost_model.py                # CloudCostModel; per-provider pricing logic
│   ├── simulator.py                 # PreExecutionSimulator; full simulation pipeline
│   ├── intervention.py              # InterventionEngine; BLOCK/AUTO_CORRECT/SUGGEST
│   └── __init__.py
│
├── policy_engine/                   # Keerthi — learned policy registry + enforcement
│   ├── policy_registry.py           # Policy dataclass; PolicyRegistry CRUD
│   ├── policy_learner.py            # PolicyLearner; derives policies from history
│   ├── policy_enforcer.py           # PolicyEnforcer; evaluates intent against registry
│   └── __init__.py
│
├── guardrails/                      # Keerthi — unified pre-provision decision gate
│   ├── pre_provision_guard.py       # GuardrailDecision; integrates policy + simulation
│   └── __init__.py
│
├── runtime_optimizer/               # Keerthi — autonomous runtime correction
│   ├── adaptive_optimizer.py        # RuntimeAdaptiveOptimizer; monitors + acts
│   ├── action_log.py                # CorrectionAction; ActionLogger
│   └── __init__.py
│
├── cost_normalizer/                 # Keerthi — cross-cloud cost normalization
│   ├── normalizer.py                # CrossCloudNormalizer; UnifiedCostRecord
│   └── __init__.py
│
├── cps_metrics/                     # Keerthi — Cost Prevention Score tracking
│   ├── cps_calculator.py            # CPSCalculator; per-record CPS computation
│   ├── prevention_tracker.py        # PreventionTracker; aggregate roll-up
│   └── __init__.py
│
├── ml_attribution/                  # Sreeja — ML-based resource tagging
│   ├── feature_extractor.py         # ResourceFeatureExtractor
│   ├── resource_classifier.py       # ResourceAttributionClassifier (RandomForest)
│   └── __init__.py
│
├── anomaly_rca/                     # Sreeja — anomaly detection + RCA
│   ├── anomaly_detector.py          # Intent vs. behavior mismatch detection
│   ├── rag_rca.py                   # RAG-based root cause analysis
│   ├── prevention_feedback.py       # AnomalyPreventionFeedback → PolicySuggestion
│   └── __init__.py
│
├── ai_governance/                   # Sreeja — LLM + embedding governance
│   ├── token_tracker.py             # TokenBudgetTracker; token budget enforcement
│   ├── llm_policy.py                # LLMPolicyEnforcer; AI-specific policies
│   └── __init__.py
│
├── evaluation/                      # Shared
│   ├── metrics.py                   # All metrics: CPS, precision/recall, MTTD, util
│   ├── benchmark.py                 # BenchmarkRunner; orchestrates all experiments
│   └── __init__.py
│
└── experiments/                     # Shared
    ├── exp1_pre_provision.py        # Keerthi — over-provisioned ETL scenario
    ├── exp2_runtime_prevention.py   # Keerthi — idle cluster + underutil + runaway
    ├── exp3_anomaly_detection.py    # Sreeja  — anomaly detection + ML attribution
    ├── exp4_ai_workload.py          # Sreeja  — LLM token governance
    ├── exp5_system_cps_rollup.py    # Joint   — aggregate CPS across all stages
    └── baselines/
        ├── static_provisioning.py
        ├── rule_based_policies.py
        └── threshold_detector.py
```

---

## 9. Authorship & Contribution Map

### Keerthi Rapolu — First Author

**Core Framework & Prevention Systems**

| Module | Ownership | Description |
|---|---|---|
| `intent_model/` | Full | Workload intent parsing, ResourceConfig, IntentCatalog |
| `simulation_engine/` | Full | Pre-execution simulation; BLOCK/AUTO_CORRECT/SUGGEST engine |
| `policy_engine/` | Full | Policy schema, PolicyRegistry, PolicyLearner, PolicyEnforcer |
| `guardrails/` | Full | Pre-provisioning decision gate integrating policy + simulation |
| `runtime_optimizer/` | Full | Autonomous runtime correction; downscale/terminate/migrate |
| `cost_normalizer/` | Full | Cross-cloud UCR; pricing normalization across AWS/Azure/GCP |
| `cps_metrics/` | Full | CPS definition, CPSRecord schema, PreventionTracker roll-up |
| System architecture | Primary | Overall PBCP framework design and component interfaces |
| Experiments 1 & 2 | Primary | Pre-provision prevention + runtime prevention scenarios |
| Experiment 5 | Joint | System-level CPS aggregate |

**Key Research Contributions:**
- Definition and formalization of the Cost Prevention Score (CPS) metric
- Pre-execution simulation methodology for cloud workload cost prediction
- Intent → learned policy framework with enforcement semantics

---

### Sreeja Katta — Second Author

**Intelligence, Detection & AI Governance**

| Module | Ownership | Description |
|---|---|---|
| `ml_attribution/` | Full | RandomForest-based resource tagging; untagged attribution |
| `anomaly_rca/` | Full | Intent-behavior mismatch detection; RAG-based RCA; prevention feedback loop |
| `ai_governance/` | Full | Token budget enforcement; LLM-specific policy engine |
| Experiments 3 & 4 | Primary | Anomaly detection + AI workload governance scenarios |
| Experiment 5 | Joint | System-level CPS aggregate |

**Key Research Contributions:**
- ML attribution pipeline for untagged resource governance
- Anomaly-to-prevention feedback loop (anomaly detection informs policy updates)
- RAG-based root cause analysis with structured incident retrieval
- AI workload cost modeling (token waste, embedding efficiency)

---

### Shared Responsibilities

| Area | Description |
|---|---|
| `/data/` | Dataset generation, schema design, seed management |
| `/evaluation/` | Metrics framework, benchmark orchestration |
| `/experiments/baselines/` | All baseline implementations |
| Experiment 5 | System-level CPS roll-up |
| `/docs/` | Documentation, architecture diagrams |

---

### Interface Contract Between Authors

The following interfaces define the boundary between Keerthi's prevention modules and Sreeja's intelligence modules. Neither author duplicates logic across this boundary.

| Interface | From | To | Contract |
|---|---|---|---|
| `WorkloadIntent` | `intent_model/` (K) | `ml_attribution/`, `anomaly_rca/`, `ai_governance/` (S) | Read-only input |
| `CPSRecord` | `cps_metrics/` (K) | `anomaly_rca/prevention_feedback.py` (S) | S reads; K writes |
| `PolicySuggestion` | `anomaly_rca/prevention_feedback.py` (S) | `policy_engine/policy_registry.py` (K) | S writes; K consumes |
| `AttributionResult` | `ml_attribution/` (S) | `guardrails/` (K) | K reads; S writes |
| `UnifiedCostRecord` | `cost_normalizer/` (K) | `anomaly_rca/`, `ai_governance/` (S) | S reads; K writes |

---

## 10. Design Decisions & Open Questions

### Resolved Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Simulation engine is synchronous for prod, async for dev/sandbox | Synchronous for `prod`/`staging`; async non-blocking for `dev`/`sandbox` | Synchronous prevention is essential for high-stakes workloads; async path avoids friction in development workflows. Target: < 2 sec synchronous, < 50 ms async. |
| Policy enforcement is hard, not soft | REJECT and AUTO_CORRECT have binding effect | Advisory-only governance is the existing failed approach; enforcement is the core contribution |
| CPS is the primary metric | Defined as prevented / potential | Provides a single comparable number across stages, providers, and workload types |
| Right-sizing targets 70% utilization | Configurable; default 70% | 70% leaves headroom for load spikes while eliminating gross over-provisioning |
| Policy source tracked (`builtin` vs `learned`) | Field on Policy schema | Enables ablation: evaluate system with only builtin, only learned, or combined policies |
| Behavior vector space | Normalized numeric features | Avoids cross-modal alignment problem of embedding text and metrics in same space |
| ML attribution uses RandomForest | Baseline model | Interpretable feature importances; explainability is a first-class requirement |

### Open Questions

1. **Simulation accuracy vs. cold-start:** The utilization estimator relies on workload type priors from `INTENT_CATALOG`. For novel workload types not in the catalog, utilization estimates will be inaccurate. Consider adding a "low confidence" flag to `SimulationResult` when the workload type is unseen, and routing these to a human review path.

2. **Policy learning convergence:** The `PolicyLearner` requires `min_samples_to_learn = 10` historical workloads per type before emitting a learned policy. In early deployment (sparse history), the system relies entirely on built-in policies. This should be documented as a deployment ramp-up constraint.

3. **CPS gaming risk — resolved via ESR:** The Execution Success Rate (ESR) constraint metric directly addresses this. Valid CPS = CPS × ESR means that aggressive blocking lowers ESR and therefore lowers Valid CPS. The hard constraint ESR ≥ 0.95 is reported in every experiment alongside CPS; a result that achieves high CPS but violates the ESR constraint is considered a failed configuration, not a success.

4. **Cross-team policy sharing:** The policy registry is currently global (shared across teams). This enables broader learning but may surface organization-specific constraints as false violations. Consider a `scope` field on `Policy` (`global` vs `team_scoped`).

5. **RAG-RCA LLM dependency:** The RAG-based root cause analysis requires an LLM at inference time. For fully offline evaluation, Mistral-7B (local) should be the default; the design should not require OpenAI API availability for reproducibility.

### Suggested Additions for Final Paper

- **Confidence intervals on all metrics** — run each experiment 5× with different random seeds (42, 43, 44, 45, 46) and report mean ± std. Required for publication-grade claims.
- **Ablation study** — evaluate the system with individual components disabled: (a) simulation only, no policy engine; (b) policy only, no simulation; (c) no runtime optimizer; (d) no ML attribution. This isolates each component's CPS contribution.
- **Latency overhead measurement** — report p50/p99 latency of the pre-execution simulation gate; this is a practical adoption barrier worth quantifying.
- **Policy coverage analysis** — what fraction of workloads are governed by at least one active policy? Low coverage = low prevention potential.

---

## 11. References

> *(To be populated during paper writing. Suggested areas to cite:)*

- Pre-billing cost management in cloud systems (distinguish from post-billing FinOps)
- Cloud cost waste studies (AWS Trusted Advisor, Azure Advisor aggregate reports)
- Workload-aware resource provisioning (Kubernetes VPA, YARN autoscaling)
- Retrieval-Augmented Generation foundations (Lewis et al., 2020)
- Anomaly detection in distributed systems and MTTD benchmarks
- Random Forest for classification in system management (interpretability literature)
- LLM inference cost optimization (token efficiency, prompt compression)
- Synthetic workload benchmarking methodology

---

*Document maintained at `/IACG_Design_Document.md`. Update before merging changes to any component interface, experiment design, or CPS metric definition.*
