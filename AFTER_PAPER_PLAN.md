# Post-Paper Launch Plan

**Correct execution order:** Paper PDF → GitHub clean → Medium → LinkedIn → Submit/Share

Do not post LinkedIn first. When people click, everything must already look ready.

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

## Step 4 — Write Medium article

Write after GitHub is clean, before major LinkedIn promotion.

- [ ] Draft non-academic article
- [ ] Keep it story-first, not mathematical

**Title idea:** *Why Cloud Cost Governance Acts Too Late: A Pre-Billing Prevention Approach*

**Structure:**
1. The 20-node cluster story
2. Why alerts arrive too late
3. What pre-billing governance means
4. PBCP architecture: Prevent → Correct → Learn
5. Key results
6. Links to GitHub + demo

---

## Step 5 — LinkedIn post #1: Project launch

Post after Medium is published.

- [ ] Write short story opening
- [ ] State the problem
- [ ] Describe what you built
- [ ] Include: GitHub link, Streamlit demo link, Medium link

Tone: professional, not hype.

---

## Step 6 — Submit paper

Choose one path:

**Safer path — workshop first:**
- HotCloud-style workshop
- Cloud systems workshop
- Poster/demo track

**Ambitious path — direct submission:**
- ACM SoCC
- USENIX ATC-style venue

If rejected, use reviews to improve. That is normal.

---

## Step 7 — LinkedIn post #2: Technical deep dive

1–2 weeks after launch post.

- [ ] Topic: How CPS and ESR prevent gaming in cloud cost governance
- [ ] Demonstrates technical depth beyond the launch announcement

---

## Step 8 — LinkedIn post #3: Experiment results

After the technical post.

- [ ] Show Exp 3 detector comparison and Exp 6 convergence
- [ ] Use one clean figure (no dashboard screenshots unless clean)

---

## Step 9 — Add paper tab to Streamlit app

After paper PDF is stable.

- [ ] Add abstract
- [ ] Add PDF link
- [ ] Add BibTeX block
- [ ] Add GitHub link and Medium link

Makes the demo feel research-backed.

---

## Step 10 — Longer-term evaluation improvements

For a stronger future submission:

- [ ] Add sensitivity analysis
- [ ] Add a stronger baseline comparison
- [ ] Try small real-trace calibration
- [ ] Publish artifact on Zenodo
- [ ] Get a DOI

---

## Timeline

| Timeframe | Action |
|-----------|--------|
| Week 1 | Freeze paper + GitHub cleanup |
| Week 2 | Reproducibility package |
| Week 3 | Medium article |
| Week 3–4 | LinkedIn launch post |
| Week 4 | Submit to workshop or conference |
| After submission | LinkedIn technical posts |
| After feedback | Strengthen evaluation |
