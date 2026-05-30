# Sreeja — Task Checkpoint Document
## PBCP / IACG v2.0 — Co-Author Deliverables

**Legend:** `[ ]` not started · `[~]` in progress · `[x]` done  
**Bold** = blocks something downstream · *(Keerthi)* = coordinate before marking done

---

## Quick Start

```bash
cd c:\Projects\IACG
python -m pytest tests/ -v          # should show 62/62 PASS before you touch anything
python evaluation/benchmark.py --experiment 0,1,2,6   # Keerthi's 4 experiments all PASS
```

The full DB is at `data/full/iacg.duckdb` (28 k run records, 500 workloads, seeds 42–46).  
All of Keerthi's modules (Phases 0–6) are complete. Your work plugs into them — do not modify Keerthi's files.

---

## Viewing the Paper (LaTeX Setup)

To compile and read `paper/main.pdf` locally you need two things:

**1. Install MiKTeX** (LaTeX distribution for Windows)
- Download from: https://miktex.org/download
- During first run, choose **Remote package repository (Internet)** when prompted
- MiKTeX auto-installs missing packages on the fly

**2. Install LaTeX Workshop in VS Code**
- Extensions panel → search "LaTeX Workshop" → install
- Open `paper/main.tex` → press `Ctrl+Alt+B` to build, then `Ctrl+Alt+V` to view PDF in the side panel

**3. Compile from the terminal** (alternatively)
```bash
cd c:\Projects\IACG\paper
make all          # runs pdflatex + bibtex + pdflatex + pdflatex
```
Or just:
```bash
latexmk -pdf paper/main.tex
```

> **Note:** `main.tex` already contains `\PassOptionsToPackage{expansion=false}{microtype}` at the top — this is required for MiKTeX on Windows and must stay in place.

---

## What the System Does (1-minute version)

PBCP prevents cloud over-provisioning **before billing** happens. When a team submits a workload:

1. **Intent inference** (`intent_model/`) — parses the job description, infers workload type, detects mismatches
2. **Simulation** (`simulation_engine/`) — predicts utilization, right-sizes nodes, runs EV decision model
3. **Guardrail** (`guardrails/`) — applies policies, blocks or auto-corrects the submission
4. **Runtime optimizer** (`runtime_optimizer/`) — monitors CPU/memory/idle during the run, fires corrections
5. **CPS tracker** (`cps_metrics/`) — aggregates Cost Prevention Score and Intent-Fit Score across all workloads

**Your two modules** sit between steps 4 and 5:
- `ifs/` — computes how well the declared intent matched what actually happened (Intent-Fit Score)
- `anomaly_rca/` — analyzes historical incidents to suggest new policies back into step 3

---

## Key Data Structures (from Keerthi's modules)

### WorkloadIntent  *(intent_model/workload_intent.py)*
```python
@dataclass
class WorkloadIntent:
    intent_id: str
    workload_name: str
    description: str
    team: str
    workload_type: Literal["etl","adhoc","ml_training","llm_pipeline","batch","streaming"]
    environment: Literal["prod","staging","dev","sandbox"]
    priority: Literal["low","medium","high","critical"]
    expected_duration_hours: float
    frequency: str
    submitted_at: str
    resource_config: ResourceConfig      # node_count, instance_type, use_spot, etc.
    inferred: InferredIntentFields       # type_mismatch, pii_signal, recurrence_signal, etc.
    token_budget: Optional[int]          # LLM pipelines only
```

### SimulationResult  *(simulation_engine/simulator.py)*
```python
@dataclass
class SimulationResult:
    intent_id: str
    workload_type: str
    submitted_nodes: int
    optimal_nodes: int
    predicted_utilization: float         # 0–1
    potential_cost_usd: float
    right_sized_cost_usd: float
    prevented_cost_usd: float
    intervention: str                    # BLOCK | AUTO_CORRECT | SUGGEST | PASS
    stage: str                           # pre_provision | runtime | ai_workload
    ev_block: float
    ev_auto_correct: float
```

### CorrectionAction  *(runtime_optimizer/adaptive_optimizer.py)*
```python
@dataclass
class CorrectionAction:
    run_id: str
    signal_type: str    # cpu_underutil | mem_underutil | idle | overrun | spot_interruption
    action: str         # SCALE_DOWN | TERMINATE | CHECKPOINT | ALERT | MIGRATE
    nodes_before: int
    nodes_after: int
    trigger_minute: int
    cost_prevented_usd: float
    detail: str
```

### PreventionTracker.record_simulation  *(cps_metrics/prevention_tracker.py)*
```python
# You call this after computing IFS — pass ifs= as a keyword arg
tracker.record_simulation(simulation_result, ifs=0.82, succeeded=True)
tracker.record_runtime_actions(intent_id, workload_type, actions, potential_cost, ifs=0.75)
```

### Policy  *(policy_engine/policy_registry.py)*
```python
@dataclass
class Policy:
    policy_id: str
    workload_type: str        # "*" for all types
    condition: str
    threshold: float
    action: str               # REJECT | AUTO_CORRECT | SUGGEST
    description: str
    source: str               # use "learned" for RCA-suggested policies
    confidence: float = 1.0

# Add a policy:
registry.add(policy)
registry.remove(policy_id)
registry.list_policies(workload_type="etl")   # filter by type
```

---

## Database Tables (yours to read)

Connect: `duckdb.connect("data/full/iacg.duckdb", read_only=True)`

### `cps_ifs_records` — 28 k rows, pre-computed PBCP outputs
```
record_id, intent_id, run_id, stage, potential_cost_usd, actual_cost_usd,
prevented_cost_usd, cps, source_action, ifs, ifs_category,
intent_embedding (JSON string), behavior_embedding (JSON string),
generation, recorded_at
```
- `stage`: `pre_provision` (3896), `runtime` (840), `baseline` (23687)
- `ifs_category`: `well_aligned` (≥0.85), `minor` (0.70–0.85), `significant` (0.50–0.70), `severe` (<0.50)
- `intent_embedding` / `behavior_embedding`: JSON-encoded float lists — use these to compute alignment

### `ai_workload_metrics` — 50 rows, LLM pipeline specifics
```
metric_id, intent_id, model_type, embedding_dim, num_vectors,
token_budget_declared, token_usage_actual, token_waste, rag_calls,
cache_hit_rate, estimated_cost_usd, optimized_cost_usd, cps_ai
```
- `model_type`: claude-haiku, mistral-7b, etc.
- `token_waste = token_usage_actual - token_budget_declared` (negative = under-budget = good)

### `historical_incidents` — 100 rows, past cost incidents
```
incident_id, intent_id, workload_type, team, incident_type,
description, fix_applied, cost_impact_usd, detection_lag_minutes,
severity, occurred_at
```
- `incident_type`: `over_provisioned` (36), `idle_cluster` (34), `runaway_job` (20), `token_waste` (10)
- `severity`: `low | medium | high | critical`
- `fix_applied`: free-text description of what fixed it — use to generate policy suggestions

### `runtime_metrics` — 28 k rows, per-run telemetry
```
run_id, intent_id, run_index, cpu_utilization_avg, memory_utilization_avg,
expected_duration_hours, actual_duration_hours, idle_time_hours,
total_billed_hours, failure_flag, spot_interruption,
is_anomaly, is_runaway, is_idle_injected, run_start
```

### `workload_intent` — 500 rows, submitted workloads
```
intent_id, workload_name, description, team, workload_type, environment,
priority, expected_duration_hours, frequency, token_budget, submitted_at,
workload_type_inferred, data_volume_estimate, latency_sensitivity,
recurrence_signal, pii_signal, data_sensitivity,
type_mismatch, type_mismatch_confidence, inference_confidence
```

---

## Phase A — IFS Module  `ifs/`

> **This is your most important deliverable — Exp 5 and the paper's dual-metric claim depend on it.**

### A.1  `ifs/__init__.py`  — empty
- [x] Create file

### A.2  `ifs/ifs_calculator.py`

**Purpose:** Given what a workload *declared* (intent) and what it *actually did* (runtime metrics + simulation), compute a 0–1 score of intent-behavior alignment.

**Output dataclass you must expose:**

```python
@dataclass
class IFSRecord:
    intent_id: str
    run_id: str
    ifs: float                          # 0–1; 1 = perfect alignment
    ifs_category: str                   # well_aligned | minor | significant | severe
    type_alignment: float               # sub-score: declared type vs. inferred type
    util_alignment: float               # sub-score: predicted vs. actual utilization
    duration_alignment: float           # sub-score: expected vs. actual duration
    resource_alignment: float           # sub-score: over-provision factor
    detail: str                         # human-readable explanation
```

**IFS formula (implement this exactly — it matches the DB data):**

```python
def compute_ifs(intent: WorkloadIntent, sim: SimulationResult,
                actual_util: float, actual_duration_hours: float) -> IFSRecord:
    # 1. Type alignment: 1.0 if no mismatch; penalise by mismatch confidence
    type_score = 1.0 - (intent.inferred.type_mismatch_confidence or 0.0) \
                 if intent.inferred.type_mismatch else 1.0

    # 2. Utilisation alignment: 1 - |predicted - actual| / max(predicted, actual)
    p, a = sim.predicted_utilization, actual_util
    util_score = 1.0 - abs(p - a) / max(p, a, 0.01)

    # 3. Duration alignment: 1 - |expected - actual| / max(expected, actual)
    e, d = intent.expected_duration_hours, actual_duration_hours
    dur_score = 1.0 - abs(e - d) / max(e, d, 0.01)
    dur_score = max(0.0, min(1.0, dur_score))

    # 4. Resource alignment: score based on over-provision factor (opf)
    opf = intent.resource_config.over_provision_factor
    resource_score = 1.0 / max(opf, 1.0)   # opf=1 → 1.0; opf=2 → 0.5; opf=3 → 0.33

    # Weighted combination
    ifs = (0.35 * type_score + 0.25 * util_score +
           0.20 * dur_score  + 0.20 * resource_score)
    ifs = round(max(0.0, min(1.0, ifs)), 4)

    if ifs >= 0.85:   category = "well_aligned"
    elif ifs >= 0.70: category = "minor"
    elif ifs >= 0.50: category = "significant"
    else:             category = "severe"

    return IFSRecord(
        intent_id=intent.intent_id, run_id=...,
        ifs=ifs, ifs_category=category,
        type_alignment=round(type_score, 4),
        util_alignment=round(util_score, 4),
        duration_alignment=round(dur_score, 4),
        resource_alignment=round(resource_score, 4),
        detail=f"type={type_score:.2f} util={util_score:.2f} dur={dur_score:.2f} res={resource_score:.2f}",
    )
```

**For LLM pipelines**, add a token-waste sub-score using `ai_workload_metrics`:
```python
# token_score: 1.0 if token_waste <= 0 (under budget), else penalise
token_score = 1.0 if token_waste <= 0 else max(0.0, 1.0 - token_waste / token_budget_declared)
# Then replace resource_score with 0.10*resource_score + 0.10*token_score (renormalise weights)
```

**Test gate:**
```
mean IFS across 500 workloads:  0.60 – 0.80
well_aligned fraction:          20 – 40%
severe fraction:                10 – 30%
```
Run `pytest tests/test_sreeja.py::TestIFSCalculator` to verify.

---

## Phase B — Anomaly RCA Module  `anomaly_rca/`

### B.1  `anomaly_rca/__init__.py`  — empty
- [x] Create file

### B.2  `anomaly_rca/root_cause_analyzer.py`

**Purpose:** Mine `historical_incidents` to detect recurring cost-waste patterns and produce `Policy` objects that can be added to `PolicyRegistry`.

**Interface you must expose:**

```python
class RootCauseAnalyzer:
    def __init__(self, db_path: str) -> None: ...

    def analyze(self, lookback_days: int = 90) -> list[Policy]:
        """
        Returns newly suggested policies based on incident patterns.
        Only returns policies with confidence >= 0.60.
        Does NOT write to DB or modify PolicyRegistry — caller does that.
        """

    def top_incidents(self, n: int = 10) -> list[dict]:
        """
        Returns the n highest-cost incidents sorted by cost_impact_usd desc.
        Each dict has: incident_id, workload_type, incident_type, severity,
                       cost_impact_usd, detection_lag_minutes, fix_applied
        """
```

**Policy generation logic (implement this):**

```python
# Pattern: if >= 3 incidents of same (workload_type, incident_type) in lookback window
# → suggest a policy with confidence = min(count / 10, 0.95)

# Mapping incident_type → Policy fields:
INCIDENT_TO_POLICY = {
    "over_provisioned": {
        "condition": "over_provision_factor",
        "threshold": 1.5,
        "action": "AUTO_CORRECT",
    },
    "idle_cluster": {
        "condition": "idle_time_hours",
        "threshold": 1.0,
        "action": "AUTO_CORRECT",
    },
    "runaway_job": {
        "condition": "actual_duration_hours > expected_duration_hours *",
        "threshold": 2.0,
        "action": "SUGGEST",
    },
    "token_waste": {
        "condition": "token_budget",
        "threshold": 0.0,   # token_budget not declared
        "action": "SUGGEST",
    },
}
```

**Test gate:**
```python
analyzer = RootCauseAnalyzer("data/full/iacg.duckdb")
policies = analyzer.analyze()
assert len(policies) >= 2          # at least 2 patterns found
assert all(p.source == "learned" for p in policies)
assert all(0.60 <= p.confidence <= 1.0 for p in policies)
```

---

## Phase C — Experiment 5  `experiments/exp5_system_rollup.py`

> **Joint with Keerthi — coordinate before running.**  
> This is the system-wide dual-metric result that goes in the paper's Section 7.

### C.1  Prerequisites
- [x] `ifs/ifs_calculator.py` complete and tested (Phase A)
- [x] `anomaly_rca/root_cause_analyzer.py` complete (Phase B)

### C.2  Implement `experiments/exp5_system_rollup.py`

**What it does:**
- Loads all 500 workloads from `data/full/iacg.duckdb`
- Runs the full PBCP pipeline (PreExecutionSimulator + PreProvisionGuard)
- Computes IFS for each workload using your `IFSCalculator`
- Computes `Valid CPS = CPS × ESR`; target ≥ 0.30
- Reports CPS by stage, CPS by workload type, IFS distribution, IBD-flagged %
- Saves `results/exp5_rollup.csv`

**Function signature to expose (the benchmark calls this):**
```python
def run_exp5(db_path: str = DB_DEFAULT, output_dir: str = None) -> dict:
    """
    Returns dict with keys:
        valid_cps, esr, system_cps, mean_ifs, ibd_fraction,
        n_workloads, total_prevented_usd, total_potential_usd,
        cps_by_stage (dict), cps_by_type (dict),
        gate_valid_cps (bool), gate_esr (bool)
    """
```

**Gates (both must pass for the paper claim to hold):**
```
Valid CPS >= 0.30    (CPS × ESR — anti-gaming constraint)
ESR >= 0.95         (no more than 5% of workloads failed)
mean IFS >= 0.60    (intent-behavior alignment healthy)
```

### C.3  Add Exp 5 to the benchmark
Once your script is ready, add it to `evaluation/benchmark.py` — copy the pattern used for Exp 1.

---

## Phase D — Visualization  `visualization/exp5_dashboard.py`

**Run after Exp 5 passes.** Produces the 4-panel Figure 5 for the paper.

```
Panel 1 (top-left):  CPS by stage — grouped bar (pre_provision / runtime / ai_workload)
Panel 2 (top-right): CPS by workload type — horizontal bar, sorted descending
Panel 3 (bottom-left):  IFS distribution — histogram with 4 colour bands
Panel 4 (bottom-right): IBD pie — well_aligned / minor / significant / severe
```

**Input:** `results/exp5_rollup.csv`  
**Output:** `results/figures/exp5_dashboard.pdf` + `.png` at 300 dpi

Run: `python visualization/exp5_dashboard.py`

Follow the same pattern as the existing scripts in `visualization/` (argparse `--results`/`--out`, `matplotlib.use("Agg")`, save both PDF and PNG).

---

## Phase E — Paper Table  `tables/table5_rollup.py`

**Run after Exp 5 passes.**  
Produces booktabs LaTeX table for Section 7 of the paper.

**Table format (3 sub-tables):**

*(a) Dual-metric summary — full system*
| Metric | Value | Gate |
|--------|-------|------|
| System CPS | 0.XXX | — |
| ESR | 0.XXX | ≥ 0.95 |
| Valid CPS | 0.XXX | ≥ 0.30 |
| Mean IFS | 0.XXX | ≥ 0.60 |
| IBD-flagged % | XX.X% | — |

*(b) CPS by stage* — rows: pre_provision, runtime, ai_workload

*(c) IFS distribution* — rows: well_aligned, minor, significant, severe; columns: n, fraction, mean IFS

**Output:** `results/tables/table5_rollup.tex` + `.csv`

---

## Phase F — Integration Tests  `tests/test_sreeja.py`

Write tests that verify:
- [x] `IFSCalculator.compute_ifs()` returns `IFSRecord` with `0 <= ifs <= 1`
- [x] `IFSRecord.ifs_category` matches the threshold bands
- [x] LLM pipeline IFS uses token-waste sub-score
- [x] `RootCauseAnalyzer.analyze()` returns ≥ 2 policies (DB has 100 incidents)
- [x] All returned `Policy` objects have `source == "learned"` and `confidence >= 0.60`
- [x] `RootCauseAnalyzer.top_incidents(n=5)` returns exactly 5 rows sorted by cost desc
- [x] IFSRecord plugs into `PreventionTracker.record_simulation(sim, ifs=record.ifs)` without error
- [x] Suggested policies from RCA can be `registry.add()`-ed without `KeyError`

**Run:** `pytest tests/test_sreeja.py -v`  
**Full suite must stay 62+ passing:** `pytest tests/ -v` (your tests add to the 62, not replace them)

---

## Phase G - Phase 7 End-to-End Integration Test  *(Coordinate with Keerthi)*

Once Phases A–F are done, Keerthi will add tests to `tests/test_integration.py` that cover:

- WorkloadIntent passed read-only to `ifs/` and `anomaly_rca/` (no mutation)
- IFSRecord.ifs value fed back into `PreventionTracker` aggregation
- PolicySuggestions from RCA accepted by `PolicyRegistry.add()`
- Full pipeline: description → intent → simulation → guardrail → IFS → CPS

Coordinate with Keerthi on the final pipeline call sequence before writing test fixtures.

---

## Phase H - Paper Writing Contributions (Co-Author)

> **Your paper role is not "extra metrics."**  
> Your work explains the paper's second core idea: cloud waste is often an **intent-behavior divergence** problem, and IFS gives the system a way to detect that divergence early.

### H.1 Your Four Research-Story Anchors

- [ ] Keep the paper story aligned with Keerthi's lead framing:
  - existing systems act after billing
  - PBCP moves intervention before billing
  - waste is often caused by mismatch between declared intent and actual behavior
- [ ] Your two direct technical contributions must stay explicit:
  - Intent-Behavior Discrepancy (IBD) framework
  - IFS-based anomaly detection
- [ ] Your writing should strengthen the paper's causal story:
  - CPS explains **how much** waste was prevented
  - IFS explains **why** the waste existed

### H.2 Section Ownership for Your Writing

| Section / Subsection | Your responsibility |
|---|---|
| 5.7 Intent-Behavior Discrepancy | Define the concept and why it matters |
| Section 6 IFS text | Keep metric explanation short and principled |
| Exp 3 evaluation | Write the full anomaly-detection interpretation |
| Exp 5 IFS interpretation | Explain what system-wide IFS means and what it does not mean |
| RCA taxonomy / feedback loop support | Contribute supporting text to system design / discussion |
| Discussion limitations | Help write the honest limits around synthetic data and anomaly interpretation |

### H.3 How to Write Your Parts

- [ ] **Intent-Behavior Discrepancy subsection**:
  - define the problem cleanly
  - do not frame it as "another metric"
  - explain that low IFS is an early signal of semantic mismatch between submitted intent and runtime behavior
- [ ] **IFS subsection**:
  - keep the definition clear and compact
  - describe IFS as a semantic alignment signal between workload intent and runtime behavior
  - avoid turning the metrics section into a long math derivation
- [ ] **Exp 3 section**:
  - state the evaluation question explicitly:
    - Does IFS outperform CPU-threshold detection?
  - compare IFS detector vs CPU-threshold baseline directly
  - emphasize F1 improvement
  - discuss false-positive tradeoff honestly
- [ ] **Exp 5 support text**:
  - explain how IFS complements CPS and ESR in the roll-up
  - do not over-claim that IFS alone proves prevention quality
- [ ] **Discussion support**:
  - acknowledge benchmark is synthetic
  - acknowledge mismatch subgroup result is mixed
  - explain that Gate 2 miss is small enough to discuss as a nuance, not a hidden defect

### H.4 Experiment-to-Question Mapping (keep this language)

Use these question statements when writing results text:

| Experiment | Question |
|---|---|
| Exp 3 | Does IFS outperform CPU-threshold detection? |
| Exp 5 | What does the dual-metric system roll-up say about overall effectiveness? |

When writing Exp 3:

- [ ] Lead with the question
- [ ] Then the detector comparison
- [ ] Then the mismatch subgroup nuance
- [ ] Then the implication for early anomaly detection

### H.5 Writing Rules for Your Sections

- [ ] Be analytical, not promotional
- [ ] Avoid vendor-product descriptions unless needed for related work
- [ ] Avoid buzzwords like:
  - "revolutionary"
  - "next-generation"
  - "AI-powered intelligence platform"
- [ ] Use reviewer-facing language:
  - what signal is measured
  - what baseline is compared
  - what limitation remains
- [ ] Keep the central systems claim visible:
  - PBCP exists because current governance acts too late

### H.6 Deliverables to Hand Off to Keerthi

- [ ] Final draft paragraph for **Section 5.7 Intent-Behavior Discrepancy**
- [ ] Final draft paragraph for **Section 6 IFS metric explanation**
- [ ] Full write-up for **Exp 3 anomaly evaluation**
- [ ] Supporting interpretation bullets for **Exp 5 dual-metric roll-up**
- [ ] 3-5 sentence **Discussion limitations** text covering:
  - synthetic benchmark
  - no enterprise telemetry
  - mixed mismatch-subgroup result

### H.7 Do Not Let the Paper Drift

- [ ] Do not let the anomaly section become a dashboard tour
- [ ] Do not present UI pages as contributions
- [ ] Do not let IFS become disconnected from the main story
- [ ] Re-anchor each section to the core paper claim:
  - governance timing is the systems failure
  - intent-behavior divergence is the hidden cause
  - pre-billing intervention is the systems answer

### H.8 Paper Writing Format and Collaboration Rules

> **Use LaTeX for all manuscript writing.**  
> Do not write your final paper sections in Word, Google Docs, or a Markdown-only flow.

- [ ] Write your paper sections as `.tex` files only
- [ ] Do **not** deliver final manuscript text in:
  - `.docx`
  - Google Docs
  - standalone Markdown intended to be the paper source
- [ ] Coordinate with Keerthi inside the shared `paper/` directory structure

Use this paper layout:

```text
paper/
├── main.tex
├── sections/
├── figures/
├── tables/
├── bibliography.bib
└── Makefile
```

### H.9 Your File Ownership in LaTeX

- [ ] Draft your contributions as separate `.tex` files or clearly separated inserts
- [ ] Default ownership:

```text
paper/sections/ifs.tex
paper/sections/anomaly_detection.tex
paper/sections/rca.tex
```

- [ ] Hand those sections to Keerthi for integration into:
  - `system_design.tex`
  - `metrics.tex`
  - `evaluation.tex`
  - `discussion.tex`

### H.10 Figure and Table Format Rules

- [ ] Use vector outputs when possible
- [ ] Preferred figure formats:
  - `.pdf`
  - `.svg`
- [ ] Do not rely on screenshots for paper figures
- [ ] Keep paper tables as standalone `.tex` fragments for `\input{}`
- [ ] Keep captions and figure references consistent with the manuscript text

### H.11 Writing Order for Your Sections

- [ ] Write Exp 3 and Exp 5 interpretation before trying to polish introduction-style prose
- [ ] Start from evidence first:
  - detector comparison
  - mismatch subgroup nuance
  - IFS interpretation
  - RCA / feedback implications
- [ ] Only polish language after the technical claim is stable

### H.12 Collaboration Rules

- [ ] Use Git branches for your paper-writing work
- [ ] Keep your section diffs isolated and reviewable
- [ ] Do not rewrite Keerthi's lead sections unless coordinating explicitly
- [ ] Keep terminology consistent with the shared manuscript:
  - PBCP
  - IFS
  - IBD
  - CPS
  - ESR

---

## File Layout (what to create)

```
ifs/
  __init__.py
  ifs_calculator.py          ← IFSRecord dataclass + IFSCalculator class

anomaly_rca/
  __init__.py
  root_cause_analyzer.py     ← RootCauseAnalyzer class

experiments/
  exp5_system_rollup.py      ← run_exp5() function

visualization/
  exp5_dashboard.py          ← 4-panel Figure 5

tables/
  table5_rollup.py           ← LaTeX Table 5

tests/
  test_sreeja.py             ← your unit + integration tests
```

---

## Completion Gates

| Phase | Gate | Status |
|-------|------|--------|
| A — IFS module | mean IFS 0.60–0.80; ifs_category buckets populated | [x] |
| B — Anomaly RCA | ≥ 2 learned policies; confidence ≥ 0.60 | [x] |
| C — Exp 5 | Valid CPS ≥ 0.30; ESR ≥ 0.95; mean IFS ≥ 0.60 | [x] |
| D — Fig 5 | 4-panel figure saved as PDF + PNG at 300 dpi | [x] |
| E — Table 5 | 3-sub-table .tex + .csv in results/tables/ | [x] |
| F — Unit tests | All Sreeja tests pass; full suite ≥ 62 still passing | [x] 114 passing |
| G — Integration | End-to-end test passes (coordinate with Keerthi) | [ ] |

---

## What Keerthi Has Already Built (do not modify)

| Module | What it does |
|--------|-------------|
| `intent_model/` | Intent inference, KNN embedding (FAISS), workload type detection |
| `simulation_engine/` | Cost model, EV decision model, pre-execution simulator |
| `policy_engine/` | PolicyRegistry, PolicyEnforcer, PolicyLearner |
| `guardrails/` | PreProvisionGuard — blocks/auto-corrects submissions |
| `runtime_optimizer/` | AdaptiveOptimizer — fires runtime corrections |
| `cps_metrics/` | CPSCalculator, PreventionTracker |
| `experiments/exp0–2, exp6` | 4 experiments complete and passing |
| `visualization/exp0–2, exp6` | 4 figures generated |
| `tables/table0–2, table6` | 4 LaTeX tables generated |
| `evaluation/benchmark.py` | CLI orchestrator — add Exp 5 here when ready |
| `tests/test_phase2.py` | 22 unit tests — must stay passing |
| `tests/test_phase3.py` | 19 baseline tests — must stay passing |
| `tests/test_integration.py` | 21 integration tests — must stay passing |

---

*Created: 2026-05-05. Keerthi is at: [keerthiofrapolu@gmail.com](mailto:keerthiofrapolu@gmail.com)*
