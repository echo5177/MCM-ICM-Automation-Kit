# Judge-Style Review Rubric

Use this rubric after the deterministic workflow passes. Score each item from 0 to 5, then revise any item below 4 before final release unless the user explicitly accepts a draft.

Run this as a multi-role loop, not a single read. Before scoring `Modeling Quality`, `Data And Evidence`, and `Results And Interpretation`, run a **verifier pass** (`nodes/paper_reviewer/prompt_verifier.md`): re-derive the headline numbers and apply the `modeling_methods.md` anti-error checklist. An unresolved BLOCKING verifier finding (a wrong number, a sign/constraint/feasibility bug, data leakage, or a claimed-but-absent analysis) caps those categories below 4.

## Format And Presentation

- Does the first page look like a credible MCM/ICM Summary Sheet?
- Is the PDF visually clean, with no red link boxes, awkward whitespace, or broken layout?
- Are figures and tables professional and readable?

## Problem Fit

- Does the paper answer every task in the problem statement?
- Is there a **Restatement of the Problem** that shows each task was understood?
- If the problem requested a letter, memorandum, or one-page article, is it present as its own labelled section, addressed to the stated audience, carrying real numbers?
- Are assumptions justified and connected to the problem?
- Is the model appropriate for the requested type of solution, and is the **reason for choosing it** stated?

## Award Skeleton (see `award_patterns.md`)

- Does the paper carry the skeleton every sampled O paper had: Restatement, Our Work/contributions, Assumptions and Justification, Notation, a dedicated Sensitivity Analysis, and Strengths and Weaknesses?
- Is figure density in the O-paper band (roughly 0.6-1.3 per page; below ~0.45 is visually thin)?
- Does the Summary Sheet name the approach, carry hard numbers, admit one limitation, and end with Keywords?

## Modeling Quality

- Is the core model mathematically clear?
- Are variables, parameters, and solution methods defined?
- Does the model produce interpretable results, not only numbers?

## Data And Evidence

- Are data sources real, citable, and role-classified?
- Are parameters calibrated, derived, or honestly labeled as assumptions?
- Is validation meaningful rather than only internal consistency?

## Results And Interpretation

- Are key quantitative results prominent?
- Do figures and tables support the argument?
- Are uncertainty and sensitivity analyzed with consequences?

## Originality And Insight

- Is there a clear idea that distinguishes the solution?
- Are recommendations actionable and tied to model outputs?
- Are limitations honest without undermining the paper?

## Release Decision

Final release requires:

- deterministic workflow pass;
- visual QA pass;
- a verifier pass with no unresolved BLOCKING finding;
- judge-style scores mostly 4 or 5;
- every missing analysis the review surfaced (sensitivity, out-of-sample validation, baseline/ablation) was **generated and folded in, not just flagged**;
- a recorded review-round trajectory that is not regressing (`review_trajectory` warns if a revision lowered the average score);
- no critical format, data, or diagram defect;
- clear disclosure of unresolved risks.
