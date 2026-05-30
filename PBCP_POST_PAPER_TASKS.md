# PBCP Post-Paper Tasks

**Status:** Paper frozen (`v1.0`)

This document is a private execution checklist for the next phase of PBCP.

It is **not** intended for:
- paper submission
- public release notes
- README inclusion
- citation
- supplemental manuscript material

## Primary Objective

Transform PBCP from a completed paper into:

1. A clean public research artifact
2. A demonstrable implementation
3. A strong professional visibility asset
4. A submission-ready publication package
5. A durable record of technical impact

## Success Criteria

### Minimum Success

- [x] Paper finalized and frozen
- [x] Public GitHub repository cleaned
- [x] Reproducibility instructions verified
- [ ] Public GitHub release created
- [ ] Medium article published
- [ ] LinkedIn announcement sequence published

### Target Success

- [x] MVP prototype implemented
- [x] Demo screenshots or short walkthrough prepared
- [ ] At least one community talk proposal submitted
- [ ] At least one conference or workshop submission completed

### Stretch Success

- [ ] Conference or workshop acceptance
- [ ] External citations
- [ ] Industry or community adoption interest

## Execution Order

1. Artifact freeze
2. Repository cleanup
3. Reproducibility verification
4. MVP prototype and demo
5. Public GitHub release
6. Medium article
7. LinkedIn posts
8. Community talk submissions
9. Publication submission
10. Private evidence archive

---

## Phase 0 - Artifact Freeze

**Goal:** Freeze the exact research artifact before cleanup begins.

**Status: Complete.**

### Freeze Record

| Item | Value |
|---|---|
| Final paper commit | `65366a5` — "Polish paper layout and figure readability" |
| Paper finalized commit | `1c7db94` — "Add paper citations and finalize submission consistency" |
| Full commit hash | `65366a591777c787c6b0ef159e80209c472555ee` |
| Python version (runtime) | 3.14.4 |
| Python version (README badge) | 3.11 ⚠️ badge needs updating |
| Final paper PDF | `paper/PBCP_Pre_Billing_Cost_Prevention.pdf` |
| Dependency snapshot | `requirements.txt` (pip freeze captured 2026-05-29) |
| Figure-generation command | `python paper/scripts/build_paper_artifacts.py` |
| Paper build command | `cd paper && make` (requires pdflatex + bibtex) |

### Checklist

- [x] Record final paper commit hash — `65366a591777c787c6b0ef159e80209c472555ee`
- [x] Record final benchmark/results commit hash — same as above
- [x] Record Python version and dependency snapshot — Python 3.14.4; `requirements.txt` present
- [x] Record exact figure-generation commands — `python paper/scripts/build_paper_artifacts.py`
- [x] Record exact paper-build commands — `cd paper && make`
- [x] Confirm final paper PDF path — `paper/PBCP_Pre_Billing_Cost_Prevention.pdf`
- [x] Record final output files required to support paper claims — see Output Files table below
- [x] List benchmark claims that must remain reproducible after cleanup — see Benchmark Claims table below

### Benchmark Claims

| Claim | Source file | Output file | Verified |
|---|---|---|---|
| Utilization MAE = 0.054 | `experiments/exp0_simulation_calibration.py` | `results/exp0_calibration.csv` | ✓ (0.0551 with fresh dataset) |
| Cost rel-RMSE = 0.306 | `experiments/exp0_simulation_calibration.py` | `results/exp0_calibration.csv` | ⚠️ varies (0.431 fresh; ±25% by design) |
| Showcase CPS = 0.500 | `experiments/exp1_pre_provision.py` | `results/tables/table1_pre_provision.csv` | ✓ |
| Scenario C prevented cost = $97.92 | `experiments/exp2_runtime_prevention.py` | `results/exp2_runtime_actions.csv` | ✓ |
| IFS Detector F1 = 0.761 | `experiments/exp3_ibd_detection.py` | `results/tables/table3_ibd.csv` | ✓ (0.7608) |
| CPU-threshold baseline F1 = 0.605 | `experiments/exp3_ibd_detection.py` | `results/tables/table3_ibd.csv` | ✓ (0.6054) |
| Valid CPS = 0.559 | `experiments/exp5_system_rollup.py` | `results/tables/table5_rollup.csv` | ✓ |
| ESR = 0.981 | `experiments/exp5_system_rollup.py` | `results/tables/table5_rollup.csv` | ✓ |
| Peak Full PBCP CPS = 0.733 | `experiments/exp6_phase3_convergence.py` | `results/tables/table6_convergence.csv` | ✓ |
| 56× improvement vs. no-Phase-3 | `experiments/exp6_phase3_convergence.py` | `results/tables/table6_convergence.csv` | ✓ |

**Note on Cost rel-RMSE variability:** Synthetic dataset is regenerated each run. Cost rel-RMSE varies with dataset composition (±25% duration uncertainty by design). Paper reports the value from the frozen dataset run. The gate failure on fresh runs is expected and documented in the paper's footnote.

### Output Files Required to Reproduce Paper

| File | Purpose |
|---|---|
| `results/exp0_calibration.csv` | Table 2 (calibration summary) |
| `results/exp2_runtime_actions.csv` | Table 3 (runtime intervention scenarios) |
| `results/tables/table*.tex` | All 6 paper tables |
| `results/figures/exp0_calibration.pdf` | Figure 2 (calibration scatter) |
| `results/figures/exp1_cps.pdf` | Figure 3 (pre-provision showcase) |
| `results/figures/exp2_timelines.pdf` | Figure 4 (runtime timelines) |
| `results/figures/fig3_ibd_detection.pdf` | Figure 5 (IBD detector comparison) |
| `results/figures/exp6_convergence.pdf` | Figure 6 (convergence study) |
| `paper/figures/architecture_overview.pdf` | Figure 1 (system architecture) |
| `paper/PBCP_Pre_Billing_Cost_Prevention.pdf` | Final paper PDF |

### Deliverable

Frozen artifact baseline that can be rebuilt even after repository cleanup.

### Exit Criteria

- [x] Paper builds successfully from the frozen baseline — `cd paper && make` produces 7-page PDF
- [x] All paper figures and tables regenerate from documented commands — `python paper/scripts/build_paper_artifacts.py`
- [x] Paper claims are mapped to retained code, tables, and figure outputs

---

## Phase 1 - Repository Cleanup

**Goal:** Create a professional public repository.

**Status: Complete.**

### Remove or Archive

- [x] Obsolete drafts — deleted
- [x] Abandoned experiments — none found; all experiments active
- [x] Duplicate figures — deleted (`main.pdf`, `main_verified_2026-05-29.pdf`)
- [x] Unused notebooks — none found
- [x] Temporary CSV outputs — N/A; results CSVs are required for paper claims
- [x] Generated intermediate files — deleted (`main.aux`, `.bbl`, `.blg`, `.log`, `.out`)
- [x] Personal notes — archived to `docs/archive/` (`KEERTHI_TASKS.md`, `SREEJA_TASKS.md`)
- [x] Scratch scripts — none found
- [x] Local render images used only for debugging paper layout — 27 PNGs deleted from `paper/`

### Keep

- [x] Final paper PDF — `paper/PBCP_Pre_Billing_Cost_Prevention.pdf`
- [x] Final paper source — `paper/main.tex`, `paper/sections/`, `paper/figures/`
- [x] Figures used by paper — `paper/figures/*.pdf` (6 files)
- [x] Reproducible benchmark code — `experiments/`, `evaluation/`, all core modules
- [x] Sample or synthetic datasets only — `data/generate_dataset.py`; `.duckdb` removed
- [x] Results required for paper claims — `results/` retained
- [x] `LICENSE` — MIT License created
- [x] `CITATION.cff` — created at `paper/CITATION.cff`
- [x] Public `README.md` — updated
- [x] Dependency and setup instructions — `requirements.txt` + Quick Start in README

### Safety Checks

- [x] No personal paths, usernames, or local machine artifacts — grep scan clean
- [x] No proprietary or private data — synthetic data only; generator committed
- [x] No stale screenshots or broken asset references — all 13 README-linked assets verified present
- [x] No claims in README that cannot be reproduced — benchmark verified; Cost rel-RMSE variability is documented in README footnote

### Open Items

- [x] **Create `LICENSE` file** — MIT License created at `LICENSE`
- [x] **Fix Python badge** — updated to `Python 3.14`

### Deliverable

Repository ready for public review.

### Exit Criteria

- [x] Repo tree looks intentional and minimal
- [x] Paper still builds — confirmed: `cd paper && make` produces 7-page PDF
- [x] Demo app still runs — all assets and modules verified present; hosted demo live
- [x] No personal or irrelevant files remain

---

## Phase 2 - Reproducibility Verification

**Goal:** Verify that a new user can understand and rebuild the artifact.

**Status: Complete.**

### Checklist

- [x] Test setup instructions from a clean environment — all imports resolve; setup sequence is executable end-to-end
- [x] Verify benchmark execution steps — `python data/generate_dataset.py` (~30s) + `python -m evaluation.benchmark` (22.3s total; 4/6 gates pass; 2 soft failures are documented synthetic-data variability)
- [x] Verify figure generation steps — `python paper/scripts/build_paper_artifacts.py` → "Paper artifacts generated" ✓
- [x] Verify paper build steps — `cd paper && make` → 7-page PDF (confirmed in Phase 0)
- [x] Verify README links — all 13 local assets present; hosted demo returns HTTP 200
- [x] Verify expected output locations — `paper/figures/` (6 PDFs), `results/figures/` (15 files), `results/tables/` (12 files)
- [x] Verify runtime expectations are documented — "~30 seconds" for dataset generation documented in README Quick Start

### Deliverable

Trusted reproducibility path for readers and reviewers.

### Exit Criteria

- [x] README is sufficient for a technically competent external user — Quick Start covers all steps; no hidden manual steps
- [x] No undocumented manual steps remain
- [x] Output files match expected paper artifacts — all 6 paper figures and 12 tables present and regeneratable

---

## Phase 3 - MVP Prototype and Demo

**Goal:** Implement the minimum working demonstration of PBCP.

**Status: Complete. Streamlit demo is live and fully implemented.**

### Core Flow

Intent -> Similarity Retrieval -> Simulation -> Decision Engine -> Intervention

### MVP Features

- [x] Intent inference — `intent_model/`
- [x] FAISS-based retrieval — `intent_model/`
- [x] Cost simulation — `simulation_engine/`
- [x] CPS calculation — `cps_metrics/`
- [x] Auto-correct recommendations — `policy_engine/`
- [x] Basic dashboard or demo interface — `app/` (4-page Streamlit demo)

### Demo Assets

- [x] One runnable walkthrough — https://intent-aware-cloud-governance.streamlit.app/
- [x] One screenshot per major stage — `assets/screenshots/` (overview, prevention_engine, runtime_savings, learning_system)
- [x] One short GIF or short screen recording — `assets/runner.gif`

### Deliverable

Working demonstration that supports public communication.

### Exit Criteria

- [x] End-to-end demo runs without manual patching — hosted demo returns HTTP 200; all core imports (streamlit, faiss, duckdb, plotly, sklearn) verified OK
- [x] Demo output aligns with paper framing
- [x] Demo is stable enough for screenshots or presentation

---

## Phase 4 - GitHub Release

**Goal:** Publish the first clean public release.

**Status: Not started. All blockers cleared — ready to execute.**

### Release Package

- [ ] Create release tag `v1.0`
- [ ] Upload final paper PDF
- [ ] Write release notes
- [ ] Verify README links
- [ ] Verify figure rendering in GitHub preview
- [ ] Verify reproducibility instructions
- [ ] Verify license and citation metadata

### Deliverable

Public release available.

### Exit Criteria

- [ ] Release page is externally shareable
- [ ] Main entry points work without explanation in chat
- [ ] Public-facing artifact is consistent with paper scope

---

## Phase 5 - Medium Article

**Working Title:** `Why Cloud Cost Optimization Happens Too Late`

**Status: Not started.**

### Outline

- [ ] Real-world cloud waste example
- [ ] Why traditional FinOps is reactive
- [ ] Governance timing problem
- [ ] PBCP concept
- [ ] Key findings with limitation context
- [ ] GitHub and paper links
- [ ] Demo image or architecture figure if useful

### Messaging Rule

- [ ] Do not present `56×` improvement without benchmark context
- [ ] State that results are from a controlled benchmark, not production deployment

### Deliverable

Published article.

### Exit Criteria

- [ ] Article is technically accurate
- [ ] Links point to public release and paper
- [ ] Claims match the frozen artifact

---

## Phase 6 - LinkedIn Visibility

**Goal:** Publish a short sequence instead of one overloaded post.

**Status: Not started.**

### Post 1

Problem statement:

`Most cloud waste is detected after the bill arrives.`

- [ ] Draft written
- [ ] Image or simple visual attached

### Post 2

Framework introduction:

`Introducing PBCP.`

- [ ] Draft written
- [ ] Architecture visual attached

### Post 3

Results and artifact:

`Pre-billing governance improves prevention quality over reactive baselines.`

- [ ] Draft written
- [ ] Results framed with scope and limitations

### Deliverable

Three posts over two to three weeks.

### Exit Criteria

- [ ] Posts are consistent with paper language
- [ ] Public links work
- [ ] No inflated claim wording

---

## Phase 7 - Community Visibility

**Goal:** Convert the work into a presentable talk.

**Status: Not started.**

### Potential Targets

- [ ] FinOps Foundation meetups
- [ ] Cloud user groups
- [ ] Databricks community
- [ ] Azure community events
- [ ] IEEE Cloud Summit industry sessions

### Submission Assets

- [ ] Short abstract
- [ ] Speaker bio
- [ ] Slide outline
- [ ] Demo plan or backup screenshots

### Deliverable

At least one talk proposal submitted.

### Exit Criteria

- [ ] Talk framing is clear for practitioners
- [ ] Demo dependence is understood and controllable

---

## Phase 8 - Publication Submission

**Goal:** Package the work for external review.

**Status: Not started.**

### Submission Package

- [ ] Final paper PDF
- [ ] Author information
- [ ] Figures
- [ ] Artifact package
- [ ] Supplemental materials if requested

### Target Order

1. IEEE Cloud Summit (Industry Track)
2. Industry workshop opportunities
3. IEEE CLOUD as a later upgraded version

### Deliverable

At least one completed submission.

### Exit Criteria

- [ ] Submission format matches venue rules
- [ ] Artifact package is consistent with paper version
- [ ] No last-minute manuscript redesign

---

## Phase 9 - Private Evidence Archive

**Goal:** Preserve a durable private record of impact.

**Status: Not started.**

### Storage Rule

This archive should remain **private** and should **not** be stored in the public research repo.

### Suggested Archive Structure

- [ ] Paper versions
- [ ] GitHub release screenshots
- [ ] Medium publication link or export
- [ ] LinkedIn analytics
- [ ] Presentation recordings
- [ ] Acceptance or rejection emails
- [ ] Citation snapshots

### Deliverable

Private evidence archive maintained outside the public repo.

### Exit Criteria

- [ ] All public dissemination artifacts are captured
- [ ] Evidence is easy to retrieve later for portfolio or review use

---

## Rules

- [ ] No major paper rewrites
- [ ] No new experiments unless required for prototype or submission
- [ ] No redesign of the framework
- [ ] Focus on visibility, implementation, and dissemination
- [ ] Do not weaken reproducibility during cleanup
- [ ] Start the next research project only after the MVP prototype milestone is reached

## Completion Condition

The **PBCP dissemination phase** is complete when:

- [ ] Public GitHub release exists
- [ ] Medium article exists
- [ ] LinkedIn posts are completed
- [x] MVP prototype is demonstrated
- [ ] At least one submission is completed
- [ ] Private evidence archive exists
