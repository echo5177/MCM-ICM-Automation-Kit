# Judge-Style Review Rubric

Use this rubric after the deterministic workflow passes. Score each item from 0 to 5, then revise any item below 4 before final release unless the user explicitly accepts a draft.

Run this as a multi-role loop, not a single read. Before scoring `Modeling Quality`, `Data And Evidence`, and `Results And Interpretation`, run two passes:

- a **verifier pass** (`nodes/paper_reviewer/prompt_verifier.md`): re-derive the headline numbers and apply the `modeling_methods.md` anti-error checklist. An unresolved BLOCKING finding (a wrong number, a sign/constraint/feasibility bug, data leakage, or a claimed-but-absent analysis) caps those categories below 4.
- a **construct-validity pass** (`nodes/paper_reviewer/prompt_construct_validity.md`, applying `model_semantic_audit.md`): does each index, weight, and score actually measure what it claims? An unresolved INVALID finding that a conclusion depends on also caps those categories below 4.

The two catch different failures. Correct arithmetic on an invalid construct passes the verifier and still deserves to lose points.

## Two kinds of review: error-finding and alignment

**Error-finding** asks "is anything in the paper wrong?"; **alignment** asks "does what the
problem setter expects appear where a judge will see it?". The first raises rigor, the
second raises agreement with the marking. Neither replaces the other.

The CUMCM Kit measured this in 2026 against the official marking points published after
the contest: four formal error-finding rounds raised the internal score from 64 to 90 and
fixed real losses (a truncated required table, a formula error, an over-claimed bound), yet
the estimated marking-point score only rose from about 68 to about 79. One review that
questioned the reading of the problem (use the stated initial value, what an emergency
purchase may be used for) lifted it to about 88 in a single round. Four marking points were
never raised by any review, because they were not errors: they were expected things that
were absent.

**Run an alignment review on the first draft**, and again after each revision. Before
reading the paper, write a *reference-solution hypothesis* per question, then check the
paper against it and note hit / partial / missing and the page:

1. Are the values the problem states used as the baseline? (`modeling_methods.md`, audit 3)
2. What structure did the setter plant in the data? (audit 2)
3. How would the reference solution forecast each quantity? (audit 1)
4. Which choices count as using future data, including implicitly? (audit 4)
5. How should penalty ratios and similar parameters enter the model explicitly? (audit 5)
6. What validation and reliability will a judge expect for each strategy? (audit 6)
7. Does every question in the statement ("should ...", "determine ...") get a one-sentence
   answer a judge can find?

Calibration material for MCM: COMAP publishes **Judges' Commentaries** on each problem in
The UMAP Journal. The corpus root that `scripts/measure_award_corpus.py` reads holds the
2011-2017 issues under `原始文件/` (the 2014 and 2017 issues checked contain the
commentaries). Read the one for a similar past problem before writing the hypothesis.

Two disciplines: **page-cutting and polishing rounds may not delete evidence** (before
removing a figure or section, ask whether it is the only evidence for something the Summary
claims or a judge expects; the 2026 MCM A entry cut ten pages in the last half hour and its
section 6 collapsed to a heading while the Summary still promised a Monte Carlo sensitivity
study); and **a freeze does not freeze a strong signal** (see audit 1).

## Format And Presentation

- Does the first page look like a credible MCM/ICM Summary Sheet?
- Is the PDF visually clean, with no red link boxes, awkward whitespace, or broken layout?
- Are figures and tables professional and readable?
- Submission integrity: does the Summary Sheet's control number match every page header, with
  no names, school or e-mail anywhere, and the AI report after the references?
  (`submission_checker` reports these; any failure caps this category below 4.)
- Any note to the team or tool name in the body ("in this version we fixed...")? One caps this
  category below 4 (`paper_hygiene_checker` fails on it). Program-log phrasing ("took 14 ms",
  a script name) reads like a lab notebook; the checker warns.

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

## Construct Validity

- Does every index, weight, score, and composite measure what its name claims?
- Are proxies supported by evidence, or at least labelled as assumptions with a sensitivity test?
- Are functional forms and thresholds justified rather than convenient?
- Is any correlation being used as if it were a cause?

## Originality And Insight

- Is there a clear idea that distinguishes the solution?
- Are recommendations **decisions** — action, trigger threshold, owner, horizon, quantified effect, cost, failure conditions, monitoring — rather than topic headings?
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
