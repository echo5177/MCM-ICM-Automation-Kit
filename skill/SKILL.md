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

0. **Official rules preflight.** Confirm the *current* contest rules from the official COMAP
   instructions rather than from memory or from this Skill's snapshot: contest year and
   window, page limit and exactly what it counts, minimum font size, per-page team-number
   and page-number requirements, anonymity, AI disclosure and where the AI report goes, file
   naming and size. Record them in `reports/rules_snapshot.md` with source URL and access
   date. Rules change between cycles; a hardcoded snapshot is a submission risk, and the
   official rules always win over `references/modeling_methods.md`.
1. Inspect the repository, problem statement, available data, prior notes, and workflow config.
2. Produce or update a pre-execution plan with modeling route, data route, figure/table route, paper route, validation route, and commit batches.
3. Build a data-needs document before acquiring external data.
4. Acquire or create accepted data/parameter sources with roles clearly separated: official problem data, true dataset, documentation source, parameter source, validation source, and scenario assumption.
5. Implement model code and focused tests before writing the paper.
6. Generate planned figures, tables, key results, manifests, and visual source files. When a
   teammate hands over a flowchart they drew (expect it; ask early), import it with
   `import_flowchart.py` and place it as an ordinary portrait figure, never on a landscape page
   (`references/figure_standards.md`, "A flowchart a teammate drew").
7. Render and visually inspect the first pages of the PDF and every critical figure.
8. Run deterministic workflow checks. Keep `release_stage: draft` in `workflow_config.json` while
   drafting: the judge review is bound to the PDF's SHA-256 and every rebuild voids it, so a
   draft only warns about a missing or stale review and v2 gives no contest-ready verdict.
9. Run a multi-role judge-style review using the rubric in `references/judge_rubric.md`: at minimum a **verifier** pass that re-derives the key numbers and applies the `references/modeling_methods.md` anti-error checklist (see `nodes/paper_reviewer/prompt_verifier.md`), a **construct-validity** pass that checks each quantity actually measures what it claims (`references/model_semantic_audit.md`, `nodes/paper_reviewer/prompt_construct_validity.md`), plus a harsh-judge pass on the modeling story. Write the scores to `reports/workflow/judge_review.md`.
10. Revise until both deterministic checks and judge-style review are acceptable. When review finds a missing analysis (thin sensitivity, no out-of-sample validation, a missing baseline/ablation), **generate that analysis and fold it in — do not merely flag it**. Treat review as a loop: re-score after each revision; the Kit's `review_trajectory` node records the round history and warns if a revision lowered the average score. Iterate until scores clear the minimum and stop improving.
11. Only then set `release_stage: final`, run the judge review once on the final PDF (write its
    `PAPER_SHA256` into `reports/workflow/judge_review.md`), and create the release packet or
    final commit.

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

## Competition Operations

Read `references/competition_operations.md` when running an actual contest rather than
repairing an existing paper. It covers the three work lanes and why the writing lane must
start before the modeling lane finishes, the handoff contract that keeps a number from
being mis-stated (units, provenance, draft/final status, uncertainty), contest-clock
milestones expressed as fractions of the real contest window, and freeze discipline. A
correct model that reaches the writer too late still produces a thin paper.

## Award Patterns

Read `references/award_patterns.md` before planning the paper outline. It records what
recent Outstanding papers actually do, measured rather than assumed: the invariant section
skeleton (Restatement, Our Work, Assumptions and Justification, Notation, reasons for model
selection, a dedicated Sensitivity Analysis, Strengths and Weaknesses, and the
letter/memorandum when the problem asks for one), the observed figure density
(0.60-1.27 images per page), and the Summary Sheet anatomy. Plan the outline against that
skeleton instead of inventing one.

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

## Model Semantics

Read `references/model_semantic_audit.md` whenever the model introduces an index, weight,
score, utility, or any quantity standing in for a real-world concept. `modeling_methods.md`
catches math that is computed wrongly; this catches math that is computed correctly and
measures the wrong thing — invalid proxies, unjustified functional forms, arbitrary
thresholds, correlation used as cause. A published award paper set its AHP criteria weights
from Google Scholar hit counts; the arithmetic was correct and the construct was not, and it
still won. Do not assume this class of defect gets caught for you.

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
