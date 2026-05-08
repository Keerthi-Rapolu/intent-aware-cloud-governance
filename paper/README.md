# Paper Workspace

This directory is the LaTeX source of truth for the PBCP paper.

## File Rules

- Main manuscript: `.tex`
- References: `.bib`
- Tables: standalone `.tex` fragments under `paper/tables/`
- Figures: prefer `.pdf` or `.svg` under `paper/figures/`
- Notes or scratch drafting: `.md` only as supporting material, not as the paper source

## Figure Rules

- Prefer vector output over raster screenshots
- Use `.pdf` or `.svg` whenever possible
- Do not rely on JPEG screenshots for final paper figures

## Writing Order

Draft in this order:

1. `evaluation.tex`
2. `system_design.tex`
3. `metrics.tex`
4. `related_work.tex`
5. `discussion.tex`
6. `introduction.tex`
7. `abstract.tex`

The experiments define the claims. Write the abstract only after the section text
and headline results are stable.

## Ownership

Keerthi default ownership:

- `paper/sections/introduction.tex`
- `paper/sections/motivation.tex`
- `paper/sections/system_design.tex`
- `paper/sections/metrics.tex`
- `paper/sections/evaluation.tex`

Sreeja-owned inserts:

- `paper/sections/ifs.tex`
- `paper/sections/anomaly_detection.tex`
- `paper/sections/rca.tex`

These inserts are merged through `\input{}` in the shared section files so the
paper keeps one story while preserving clear authorship boundaries.

## Drafting Discipline

- Do not chase perfect academic English in the first pass
- Write technically precise prose first
- Polish wording only after the structure and claims are stable
- Lean on systems thinking, architecture reasoning, and evaluation structure
