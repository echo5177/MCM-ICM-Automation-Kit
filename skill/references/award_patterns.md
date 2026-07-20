# Award Patterns — What O-Award Papers Actually Do

Empirical reference derived by reading recent Outstanding-award papers, not opinion.
Use it when planning the paper skeleton, judging figure density, or reviewing a draft.

## Evidence base

Six confirmed Outstanding (O) papers, three years, four problem types:

| Year | Problem | Team | Pages | Images | Images/page | Pages with a figure |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 2025 | C | 2500759 | 26 | 33 | 1.27 | 62% |
| 2025 | C | 2501869 | 25 | 15 | 0.60 | 60% |
| 2025 | C | 2503389 | 26 | 21 | 0.81 | 50% |
| 2023 | A | 2300336 | 25 | 23 | 0.92 | 68% |
| 2023 | C | 2300348 | 26 | 28 | 1.08 | 58% |
| 2023 | F | 2305794 | 25 | 15 | 0.60 | 48% |

Contrast case: a public 2024 Problem C submission (not a confirmed O paper) has a
comparable figure density (0.60/page) but **lacks** the section skeleton below — no
Sensitivity Analysis, Notation, or Restatement section. Density alone does not make a
paper competitive; the skeleton is what separated the confirmed O papers.

## The invariant section skeleton (present in all six)

Wording varies; the *function* does not. In order:

1. **Introduction**
   - Background / Problem Background
   - **Restatement of the Problem** — restate each task in your own words (5/6 have this
     as a named subsection). This is where "problem fit" is won or lost.
   - Literature Overview — optional, but grounds the approach in prior work.
   - **Our Work** — a bulleted list of contributions, usually beside a global flowchart
     of the whole solution path (5/6).
2. **Assumptions and Justification** — every assumption carries its justification (6/6).
3. **Notations** — a dedicated symbol table, usually its own top-level section (5/6).
   Treat this as expected, not optional.
4. **Data processing / cleaning** — when the problem ships data.
5. **A model section per sub-problem**, each typically opening with **"Reasons for Model
   Selection"** or "Description of the X Algorithm". Judges reward a *justified* model
   choice, not merely a correct one.
6. **Sensitivity Analysis** — a dedicated top-level section in **all six**.
7. **Model Evaluation / Strengths and Weaknesses** — a dedicated section in **all six**.
8. **Letter / Memorandum / one-page article** when the problem asks for one (2023 C ends
   with "11 Letter"; 2025 C with "8 Memorandum"). This is a graded deliverable, never
   filler.
9. Conclusion, References, then the AI Use Report (2026: excluded from the page count).

## Figure density

O papers run **0.60–1.27 images per page**, with **48–68% of pages carrying at least one
figure**. Roughly half to two-thirds of pages are visual.

The Kit enforces **0.60 figures per page** as a floor — the observed minimum, not a soft
target. A paper below it is visually thinner than every O paper we measured and should add
evidence-carrying figures (not decoration). Counting caveat: the Kit counts figure
*environments* in the source while the band above was measured from rendered *images*, so a
float holding subfigures counts once; treat the floor as a lower bound.

## Summary Sheet anatomy

Observed in the O papers:

- Official three-column header (Problem Chosen / Year MCM/ICM Summary Sheet / Team
  Control Number), then a centered **Summary** heading.
- Often a **named framework or model title** above the summary — e.g. "Olympic
  Multi-dimensional Predictive Integrator". Naming the approach signals a designed
  system rather than a pile of methods.
- A narrative arc through the sub-problems: "First, we ... Subsequently, we ... Finally,
  we ...", each step naming its method **and its numeric result**.
- Hard numbers in the summary itself (e.g. "84.7% and 68.4%", "MAPE 6.53%", "95%
  confidence interval"), not just method names.
- An honest limitation stated in the summary.
- A **Keywords** line at the end.

## Sensitivity analysis: how the good ones do it

The pattern is not "we perturbed it and the model is robust". In the O papers each
sensitivity subsection:

- perturbs one named parameter and says **why that range matters** (e.g. too small a
  noise variance cannot represent the effect; too large corrupts the process);
- shows a **figure** of the response;
- interprets *why* the response is small or large, mechanistically;
- ends in a **consequence or limitation** — what the model cannot yet do, or what a
  practitioner should therefore watch.

A sensitivity section that ends without a consequence is not finished.

## Running header

O papers carry a per-page header with the team control number and page position, e.g.
`Team #2300336 Page 3 of 24`. Cheap to add, and it reads as contest-native.
