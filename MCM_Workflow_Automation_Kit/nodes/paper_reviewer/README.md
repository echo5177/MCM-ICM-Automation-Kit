# paper_reviewer

Paper QA scripts and reviewer prompts.

The deterministic checks inspect LaTeX/PDF artifacts. The prompts drive a
multi-role review loop after v0.1 is stable — each prompt is a distinct
perspective so a single reviewer's blind spot does not pass:

- `prompt_harsh_judge.md` — substance, traceability, contest readiness (the story).
- `prompt_summary_reviewer.md` — the Summary Sheet only.
- `prompt_submission_integrity_checker.md` — mechanical readiness (page limit,
  control number, ToC/References, placeholders).
- `prompt_verifier.md` — **re-derives the numbers** and hunts modeling/coding
  errors using `skill/references/modeling_methods.md`. This is the numerical
  verification role; it specifies the exact missing analysis rather than only
  flagging it.

Run the verifier and harsh judge together, fold their findings into the scores in
`skill/references/judge_rubric.md`, write `reports/workflow/judge_review.md`, and
let the Kit's `judge_review_gate` (floor) and `review_trajectory` (round history)
record the outcome. Iterate until scores clear the minimum and stop improving.
