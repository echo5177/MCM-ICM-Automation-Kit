# Judge-Style Review — Problem [X] ([short title])

Reviewer perspective: MCM triage + final judge. Apply skill/references/judge_rubric.md
AFTER the deterministic checks pass and AFTER visually inspecting the rendered pages
(use the visual_qa_packet output and a page-by-page contact sheet). Run the verifier pass
first (re-derive the key numbers; apply modeling_methods.md) before scoring modeling/data/
results. Scores 0-5; release requires every category >= 4 and no critical defect. Overwrite
this file each review round — the review_trajectory node records the score history.

The Kit's `judge_review_gate` parses the machine-readable lines below. `PAPER_SHA256` binds the
review to the PDF it judged: at `release_stage: final` a rebuilt PDF voids the approval, in
`draft` it only warns. It does NOT
verify that the scores are honest — that is on the reviewer (agent + human). Do not
inflate scores to make the gate green; the gate is a floor, not a certificate.

PAPER_SHA256: <sha256 of the paper PDF you reviewed; judge_review_gate_report.md prints it>
RELEASE: BLOCKED

SCORE format_presentation: 0
SCORE problem_fit: 0
SCORE modeling_quality: 0
SCORE data_evidence: 0
SCORE results_interpretation: 0
SCORE originality_insight: 0

## Justification
- **Format & presentation (?).** [Official template? Title-first summary? Full pages, no
  half-empty pages (verified by contact sheet)? Captions below + width-limited? Page count?]
- **Problem fit (?).** [Are all required tasks answered, plus sensible extensions?]
- **Modeling quality (?).** [Is the model physically/mathematically grounded and derived?]
- **Data & evidence (?).** [Real/cited data; calibration; out-of-sample validation; cross-checks.]
- **Results & interpretation (?).** [Headline numbers prominent and traceable; figures carry argument.]
- **Originality & insight (?).** [A reframing or insight beyond the obvious approach.]

## Residual risks (disclosed, not blocking)
- [Honest caveats.]

## Verdict
[When ready: set every SCORE to its real value (>= 4 to pass) and RELEASE: APPROVED.]
