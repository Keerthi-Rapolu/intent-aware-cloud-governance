# Post-Paper Launch Plan

**Correct execution order:** Paper PDF → GitHub clean → Medium → LinkedIn → Submit/Share

Do not post LinkedIn first. When people click, everything must already look ready.

---

## Priority Order for Improvements

When deciding what to work on next, follow this order. Do not jump ahead.

1. **Evaluation grounding** — sensitivity analysis, stronger baselines, real-trace calibration
2. **Reproducibility** — `reproduce.sh`, `REPRODUCIBILITY.md`, verified expected outputs
3. **References and baselines** — honest comparison against existing systems
4. **Venue submission** — workshop first, then full venue if ready
5. **Visibility expansion** — Medium, LinkedIn, GitHub promotion

This ordering matters. Promotion before grounding is a mistake.

---

## Scope Discipline

Do not continue expanding the architecture indefinitely.

The current contribution is strongest when centered on three things:
- governance timing
- pre-billing intervention
- intent-behavior divergence

Adding more dashboards, more AI components, or more metrics dilutes the core claim. Every addition must serve one of those three things or it does not belong in this project. New ideas should go in a separate future-work document, not into the current system.

---

## Step 1 — Freeze the paper draft

- [ ] Stop changing the story
- [ ] Fix only: formatting, citations, figures, references
- [ ] Export final PDF
- [ ] Save as `PBCP_paper_v1.pdf`

---

## Step 2 — Create reproducibility package

- [ ] Add `REPRODUCIBILITY.md`
- [ ] Add `reproduce.sh`
- [ ] Verify `results/`, `paper/`, `README.md` are all present and clean

Expected outputs to document:

| Experiment | Metric | Value |
|------------|--------|-------|
| Exp 0 | Utilization MAE | 0.054 |
| Exp 3 | IFS F1 | 0.7608 |
| Exp 6 | Peak CPS | 0.733 |

This must be done before any public promotion.

---

## Step 3 — Final GitHub cleanup

- [ ] Polish README
- [ ] Link paper PDF
- [ ] Link Streamlit demo
- [ ] Add reproducibility instructions
- [ ] Clean results folder
- [ ] Remove broken assets
- [ ] Remove any unverified claims

This is the public evidence base.

---

## Step 4 — Parallel Visibility Track

This project is unusually well-suited for public technical storytelling. Run this track in parallel with the submission track, not after it.

This matters beyond promotion. Documented public technical artifacts are evidence for:
- EB1A / NIW petitions (original contribution, recognition)
- Technical reputation and citations
- Open-source credibility
- Architecture leadership

**Visibility artifacts to build:**

- [ ] Medium article (see Step 5)
- [ ] LinkedIn technical posts (see Steps 7–8)
- [ ] GitHub Discussions or README FAQ for common questions
- [ ] Demo walkthrough — a short recorded or written narration of how PBCP intercepts a workload
- [ ] Architecture deep-dive article — separate from the Medium intro piece, aimed at practitioners who want implementation detail

---

## Step 5 — Write Medium article

Write after GitHub is clean, before major LinkedIn promotion.

- [ ] Draft non-academic article
- [ ] Keep it story-first, not mathematical

**Title idea:** *Why Cloud Cost Governance Acts Too Late: A Pre-Billing Prevention Approach*

**Structure:**
1. The 20-node cluster story
2. Why alerts arrive too late (the governance-timing gap)
3. What pre-billing governance means
4. PBCP architecture: Prevent → Correct → Learn
5. Key results
6. Links to GitHub + demo

Lead with the operational failure story, then demonstrate how PBCP intervenes before billing. Systems audiences care more about the operational pain and timing gap than the UI.

---

## Step 6 — LinkedIn post #1: Project launch

Post after Medium is published.

- [ ] Write short story opening
- [ ] State the problem
- [ ] Describe what you built
- [ ] Include: GitHub link, Streamlit demo link, Medium link

Tone: professional, not hype.

---

## Step 7 — Submit paper

### Mindset

A workshop, demo, or poster acceptance provides real academic and professional value — especially for a first systems-oriented research project. Treat SoCC as an ambitious target, not as the primary measure of project quality. The project has value independent of any single venue outcome.

Initial submission feedback should be treated as part of the research maturation process rather than a binary success/failure outcome. Systems-paper acceptance rates are brutal across all venues. Reviews are data, not verdicts.

### Paths

**Safer path — workshop first (recommended starting point):**
- HotCloud-style workshop
- Cloud systems workshop
- Poster/demo track at SoCC, OSDI, or similar

**Ambitious path — direct full-paper submission:**
- ACM SoCC (aligns well with cloud systems and governance themes commonly discussed at SoCC-style venues)
- USENIX ATC-style venue

**When presenting:**
Lead with the operational failure story, then show how PBCP intervenes before billing. Do not lead with the demo or the architecture diagram. The timing gap is the insight — make sure that lands first.

If rejected, read the reviews carefully and use them to improve evaluation grounding. That is the normal path for systems research.

---

## Step 8 — LinkedIn post #2: Technical deep dive

1–2 weeks after launch post.

- [ ] Topic: How CPS and ESR prevent gaming in cloud cost governance
- [ ] Demonstrates technical depth beyond the launch announcement

---

## Step 9 — LinkedIn post #3: Experiment results

After the technical post.

- [ ] Show Exp 3 detector comparison and Exp 6 convergence
- [ ] Use one clean figure (no dashboard screenshots unless clean)

---

## Step 10 — Add paper tab to Streamlit app

After paper PDF is stable.

- [ ] Add abstract
- [ ] Add PDF link
- [ ] Add BibTeX block
- [ ] Add GitHub link and Medium link

Makes the demo feel research-backed.

---

## Step 11 — Longer-term evaluation improvements

These are the highest-value improvements for any future resubmission. Do not skip directly to visibility work — evaluation grounding is what makes feedback actionable.

- [ ] Add sensitivity analysis
- [ ] Add a stronger baseline comparison (at minimum one non-trivial reactive system)
- [ ] Try small real-trace calibration
- [ ] Publish artifact on Zenodo
- [ ] Get a DOI

---

## Long-Term Leverage

Independent of any acceptance outcome, this project provides:

- a coherent systems-research narrative with a clearly scoped claim
- public technical artifacts that are independently verifiable
- reproducible experimentation across a controlled 500-workload benchmark
- open-source credibility with a live demo
- architecture leadership evidence (Prevent → Correct → Learn as a governance framing)
- a foundation for future papers on intent-aware resource management

The publication outcome is one data point. The artifacts, the narrative, and the demonstrated ability to build and evaluate a research system are durable regardless of where the paper lands.

---

## Timeline

| Timeframe | Action |
|-----------|--------|
| Week 1 | Freeze paper + GitHub cleanup |
| Week 2 | Reproducibility package |
| Week 3 | Medium article |
| Week 3–4 | LinkedIn launch post |
| Week 4 | Submit to workshop or conference |
| After submission | LinkedIn technical posts + architecture deep-dive |
| After feedback | Strengthen evaluation grounding |
