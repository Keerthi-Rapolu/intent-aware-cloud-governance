# Why Cloud Cost Governance Acts Too Late: A Pre-Billing Prevention Approach

*Draft for Medium — story-first, non-academic*

---

A data engineering team provisions a 20-node Spark cluster for a nightly ETL job expected to finish in two hours. It finishes in 37 minutes. The cluster sits idle overnight. By morning, hundreds of dollars in compute charges have already cleared.

A few hours later, a cloud cost advisor flags the cluster as underutilized.

The waste already happened.

---

## The Problem Isn't Monitoring — It's Timing

Most cloud governance tools are built around the same assumption: you run the workload, collect telemetry, analyze it, and recommend changes. The optimization loop runs *after* billing.

This isn't a monitoring failure. The data was there. The detection was accurate. The recommendation was correct.

The problem is that by the time any of that happens, you're managing the receipt, not the cost.

The question we wanted to answer was: **what if the intervention happened before the cluster was ever provisioned?**

---

## What We Built

We built **PBCP — Pre-Billing Cost Prevention** — a cloud governance framework that moves the intervention point to *before* execution.

When a workload is submitted, PBCP:

1. **Infers intent** from the natural-language job description using a hybrid NLP pipeline (keyword extraction + DistilBERT embeddings)
2. **Retrieves similar historical workloads** using FAISS vector search across a 64-dimensional embedding space
3. **Simulates likely utilization and cost** before any resource is provisioned
4. **Makes an intervention decision** — BLOCK, AUTO_CORRECT, SUGGEST, or PASS — using an expected-value model that weighs predicted waste against the cost of intervention

The decision happens in the submission path, not in a post-hoc analytics dashboard.

---

## The 20-Node Example

In our benchmark, a workload arrives requesting a 20-node ETL cluster for a job described as a "large-scale data transformation pipeline." PBCP infers the intent, retrieves 7 similar historical workloads, runs a pre-execution simulation, and determines that the job is likely to complete with 10 nodes at 57% utilization.

Before any resource is provisioned, PBCP issues an AUTO_CORRECT: 20 nodes → 10 nodes. The job runs successfully. $15.36 is prevented before billing begins.

That's not the interesting number. The interesting thing is the timing: the waste path was altered *before the cluster existed*.

---

## Runtime Governance Is Still Necessary

Pre-billing intervention doesn't solve everything. Some failure modes only become visible after launch.

In our evaluation, the most dramatic case was a runaway ML training job. It was submitted with reasonable parameters, passed pre-billing review, and then began accumulating cost at 3× the expected rate after an unexpected model divergence. PBCP's runtime monitor detected the anomaly at hour 4, intervened, and stopped $97.92 of additional cost accumulation.

The pre-billing system couldn't have caught this. The information didn't exist yet. Runtime governance isn't redundant with pre-billing — it's the fallback for what pre-billing can't see.

---

## Why IFS Matters for Anomaly Detection

One of the things we wanted to test was whether a simple CPU utilization threshold — the kind of thing most monitoring tools use — is sufficient for detecting cloud waste anomalies.

It isn't.

A workload can maintain 60% CPU utilization and still be deeply misaligned with its declared intent: it said it would process data for 2 hours and is now running for 18. It said it was batch but is behaving like streaming. The resource footprint looks normal; the behavior isn't.

We built **Intent-Fit Score (IFS)** — a measure of alignment between what a workload *said* it would do and what it's *actually doing*, computed as cosine similarity between intent and behavior embeddings.

In a controlled comparison, the IFS-based detector improved anomaly detection F1 from 0.6054 (CPU threshold) to **0.7608** — a 26% improvement. The recall improvement was larger: semantic alignment catches divergence that single-metric thresholds miss by design.

---

## The Learning Loop: 56× Improvement

The part that surprised us most was the policy learning result.

PBCP learns from intervention outcomes. When a failure pattern recurs three or more times — same workload type, same divergence signature — the system synthesizes a prevention rule and adds it to the governance layer.

In our Exp 6 evaluation, we ran an ablation across four configurations:
- **No Phase 3** (no learning): peak CPS = 0.013
- **Static rules only**: marginal improvement
- **Embedding retrieval only**: useful but insufficient
- **Full PBCP** (retrieval + intervention + learning): peak CPS = **0.733**

That's a **56× improvement** at peak. The learning loop isn't a nice-to-have. It's what makes governance improve over time instead of staying static.

---

## What the Numbers Mean

Across a controlled benchmark of 500 workloads and 28,423 runs:

| Metric | Value |
|--------|-------|
| Utilization MAE (simulation calibration) | 0.054 |
| IFS-based anomaly detection F1 | 0.7608 |
| Valid CPS (with execution success penalty) | 0.5585 |
| Execution Success Rate | 0.9809 |
| Peak CPS with policy learning | 0.733 |

**Valid CPS** is the metric we care most about. Raw CPS can be gamed by aggressively blocking workloads — that looks like a lot of prevented cost, but it breaks things. Valid CPS multiplies CPS by Execution Success Rate, so the system only gets credit for preventing waste *while workloads still complete successfully*.

ESR of 0.9809 means PBCP successfully completes 98% of workloads while achieving Valid CPS of 0.5585. That's not a tradeoff between governance and reliability — it's both.

---

## Why Timing Is the Core Insight

The framing that drove everything in this project is simple:

**Cloud waste is created before billing. Governance that acts after billing is correcting history, not preventing cost.**

The billing cycle is a hard boundary. Once a provisioning decision is made, most of the economic outcome is locked in. Post-billing optimization can inform the next decision, but it can't undo the current one.

Moving governance earlier — to the submission path, to the pre-provisioning decision point — changes what's possible. Not all waste can be prevented before billing. But a significant fraction can, and it's the fraction that's hardest to recover from.

---

## The Architecture in Three Phases

**PREVENT** — Pre-billing intervention. Intent inference, FAISS retrieval, pre-execution simulation, EV-based decision engine. Runs before any resource is provisioned.

**CORRECT** — Runtime governance. Continuous telemetry monitoring, anomaly detection, mid-execution right-sizing. Catches what PREVENT can't.

**LEARN** — Policy synthesis. IFS tracking, recurring pattern detection, automated rule generation, embedding updates. Makes the system improve over time.

Each phase handles what the others can't. The combination is what makes the benchmark results defensible.

---

## What's Next

The system is a research prototype. It runs on a controlled synthetic benchmark calibrated to match cloud pricing and behavior patterns — not a production deployment. But the intervention architecture, the metrics, and the evaluation methodology are the real contribution.

The next round of work focuses on:
- Sensitivity analysis (how do results change with benchmark parameters?)
- Stronger baselines (comparison against a real reactive system, not just a CPU threshold)
- Real-trace calibration (small real workload traces to test the simulation model against actual cloud telemetry)

---

The code, experiments, and a live interactive demo are all available:

- GitHub: [https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance](https://github.com/Keerthi-Rapolu/intent-aware-cloud-governance)
- Live demo: [https://intent-aware-cloud-governance.streamlit.app/](https://intent-aware-cloud-governance.streamlit.app/)
- Run the experiments yourself: `bash reproduce.sh`

---

*Sreeja Katta and Keerthi Rapolu*
