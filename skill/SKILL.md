---
name: "mcm-icm-competition-paper"
description: "Use when planning, executing, reviewing, or repairing an MCM/ICM mathematical modeling paper or simulation workflow. This skill governs Codex behavior for contest-style papers: problem interpretation, external data acquisition, model design, figure/table planning, LaTeX/PDF production, visual QA, judge-style review, and release readiness. It is especially relevant when the user asks to run an MCM/ICM project end-to-end, improve a poor paper, create a workflow diagram, or decide whether an automation Kit pass is enough."
metadata:
  short-description: "Build and review contest-grade MCM/ICM papers"
---
# MCM/ICM Competition Paper

Use this skill to make Codex behave like a disciplined MCM/ICM paper builder, not a fast artifact generator. The goal is a contest-grade paper with traceable computation, credible modeling, high-information figures, strong visual presentation, and judge-facing argument quality.

## Core Doctrine

- A workflow pass is not a final-paper pass.
- Do not lower gates to match weak output. Improve the output or record the block.
- Do not generate the final paper in one jump. Move through checkpoints.
- Treat the opening Summary Sheet and first workflow/model figure as scoring-critical artifacts.
- Prefer real data, calibrated parameters, and explicit limitations over impressive but unsupported simulations.
- Keep deterministic scripts and Kit checks, but use this Skill to control judgment, sequencing, and quality.

## Required Execution Sequence

When asked to run an MCM/ICM project end-to-end, follow this order unless the user explicitly asks for a narrower task.

1. Inspect the repository, problem statement, available data, prior notes, and workflow config.
2. Produce or update a pre-execution plan with modeling route, data route, figure/table route, paper route, validation route, and commit batches.
3. Build a data-needs document before acquiring external data.
4. Acquire or create accepted data/parameter sources with roles clearly separated: official problem data, true dataset, documentation source, parameter source, validation source, and scenario assumption.
5. Implement model code and focused tests before writing the paper.
6. Generate planned figures, tables, key results, manifests, and visual source files.
7. Render and visually inspect the first pages of the PDF and every critical figure.
8. Run deterministic workflow checks.
9. Run a multi-role judge-style review using the rubric in `references/judge_rubric.md`: at minimum a **verifier** pass that re-derives the key numbers and applies the `references/modeling_methods.md` anti-error checklist (see `nodes/paper_reviewer/prompt_verifier.md`), plus a harsh-judge pass on the modeling story. Write the scores to `reports/workflow/judge_review.md`.
10. Revise until both deterministic checks and judge-style review are acceptable. When review finds a missing analysis (thin sensitivity, no out-of-sample validation, a missing baseline/ablation), **generate that analysis and fold it in — do not merely flag it**. Treat review as a loop: re-score after each revision; the Kit's `review_trajectory` node records the round history and warns if a revision lowered the average score. Iterate until scores clear the minimum and stop improving.
11. Only then create a release packet or final commit.

## Non-Negotiable Stop Conditions

Pause, report the issue, and do not claim final success when any of these occur:

- The paper is only a scaffold, lecture note, or technical memo rather than a contest paper.
- The Summary Sheet does not use a credible MCM/ICM-style format.
- The primary workflow/model figure is sparse, generic, or only boxes and arrows.
- External sources are only source cards but are presented as if they were datasets.
- Model parameters are mostly hard-coded assumptions without a parameter table, rationale, or calibration/validation path.
- Page target, warning rules, or quality gates were weakened to make the current output pass.
- The PDF has not been visually inspected after rendering.
- The paper has not been reviewed from a judge perspective.

## Paper Standards

Read `references/paper_standards.md` when drafting or reviewing a paper. In short:

- Use an MCM/ICM-style Summary Sheet, not a generic article title page.
- Hide link borders and remove visually distracting compile artifacts.
- The summary must state the problem, model idea, data, key quantitative results, recommendations, and limitations in one page.
- The main text must have a clear narrative: assumptions, notation, data, model, solution, validation, uncertainty, sensitivity, results, recommendations, limitations.
- Equations must be connected to data, parameters, and outputs.
- Every major numeric claim must be traceable to generated artifacts.
- Final page count should normally aim near the contest limit when the problem is substantial; do not set the target equal to a short weak draft.

## Figure Standards

Read `references/figure_standards.md` before making the first conceptual diagram or any major figure.

The first figure should be designed before rendering. It should include enough information for a judge to understand the whole solution path without reading the full paper. At minimum, include data inputs, preprocessing/parameterization, state variables, governing equations, numerical solver, validation, uncertainty/sensitivity, outputs, and recommendations. Include visual hierarchy, grouping, and labels that carry content.

## Data And Source Standards

Read `references/data_standards.md` when the problem uses external data or public parameters.

Never treat documentation pages or local source cards as datasets. If no true dataset is used, say so plainly and strengthen the parameter justification. A source manifest can prove provenance, but it cannot prove modeling adequacy.

## Modeling Methods And Anti-Error

Read `references/modeling_methods.md` while building or reviewing the model. It is an
anti-error reference, not a model-selection mandate: decide the mathematical model from
the problem, then use this to avoid known traps (objective-sign and constraint-direction
bugs, data leakage, integer feasibility, conserved quantities, double-counting in
evaluation models, etc.), to remember that sensitivity analysis is mandatory, and to
match MCM/ICM 2026 norms (25-page rule excluding the AI report, scoring dimensions,
visualization expectations).

## Quality Gates

Use the local Kit if present, but remember what it can and cannot prove. Deterministic checks prove artifact existence, traceability, hashes, compile success, and some consistency. They do not prove contest quality.

Before finalizing, explicitly report:

- deterministic checks run and results;
- visual QA performed, including rendered PDF pages and critical figures inspected;
- judge-style review outcome, including the verifier's re-derivations and the score trajectory across review rounds (`reports/workflow/review_trajectory_report.md`);
- remaining risks, especially data limitations and model assumptions.

## Commit Discipline

For substantial work, batch commits by phase:

1. planning/source/data records;
2. model code and tests;
3. generated artifacts and paper draft;
4. QA fixes and final release records.

Do not commit a final-paper artifact merely because it compiles. Commit it when it has passed visual and judge-style review or when clearly labeled as a draft.
