# Paper Standards

## MCM/ICM Format

A contest paper should look like a submission, not a generic article. Use a clean Summary Sheet, team number treatment, professional spacing, hidden link borders, consistent captions, and dense but readable pages.

Minimum checks:

- Summary Sheet appears before the table of contents.
- The first page is not a generic title page.
- Hyperlinks do not show colored boxes in the PDF.
- Section titles are compact and professional.
- Captions name the figure or table. O papers: median 7 words; 15% add a second sentence
  and 13% run past 40 words, so a one-line takeaway is acceptable, but the interpretation
  belongs in the text that leads into the figure.
- Tables fit the page and avoid excessive empty space.
- References and AI-use disclosure are present when required.

## Official Template and Length (mandatory)

- If the repository contains an official COMAP template (e.g. `MCM-ICM_Summary.tex`,
  `summary.tex`, or `MCM-ICM_Summary.docx`), BUILD ON IT. Reuse its Summary Sheet header
  (the three-column "Problem Chosen / 2026 MCM/ICM Summary Sheet / Team Control Number"
  block) and its preamble; do not hand-roll a substitute summary page.
- A substantial problem warrants a paper that fills most of the page allowance: target
  roughly 20-25 pages of solution. A 12-15 page paper is a red flag of under-development,
  not concision. Do NOT treat a "below target pages" warning as acceptable; deepen the
  paper with real substance (derivations, data treatment, validation, discussion, a
  quality-control/reproducibility section) until it is genuinely full.
- If the problem asks for a letter, memorandum, one-page article, or similar artifact,
  it is a **graded deliverable, not page filler**. Write it as its own clearly labelled
  section, addressed to the stated audience, carrying the model's actual numbers. O papers
  end with exactly this section when the problem requests it (2023 C "Letter", 2025 C
  "Memorandum"). Omitting it forfeits problem-fit credit no matter how good the model is.
- **Recommendations must be decisions, not topics.** "Strengthen reserve management",
  "optimize transport", and "plan tourist routes" are subject headings, not advice — a
  decision-maker cannot act on them, and award papers lose points here. Every recommendation
  needs: the specific action; the model threshold that triggers it; its priority order; who
  owns it; the time horizon; the quantified expected effect on the model's own headline
  metric; the resources it costs; the conditions under which the recommendation fails; and
  what to monitor afterwards. If a recommendation cannot be tied back to a number the model
  produced, it is an opinion and does not belong in a modeling paper.
- Reach the page count with substance the problem rewards, never with filler.

## Layout, floats, and captions (mandatory)

- **Summary placement.** Page-one order is: title first, then a centered **Summary** heading,
  then the summary body. Never place the word "Summary" (or the summary text) above the title.
- **Fill every page.** Outstanding papers have no half-empty pages. Use float placement
  `[htbp]`, not `[H]`, so LaTeX flows text around figures/tables and fills the page; reserve
  `[H]` for a rare figure that must sit exactly in place. A page left half-empty because a
  figure jumped to the next page is a defect: resize the figure, reorder, or change placement.
- **Tune float parameters** to prevent sparse *float pages* (two figures batched onto one page
  with gaps between them). In the preamble set, e.g., `\renewcommand{\topfraction}{0.92}`,
  `\renewcommand{\bottomfraction}{0.85}`, `\renewcommand{\textfraction}{0.06}`,
  `\renewcommand{\floatpagefraction}{0.88}`, and `\setcounter{totalnumber}{4}`. This forces
  floats onto text pages rather than near-empty float-only pages.
- **Verify visually.** Render the whole PDF to a contact sheet (e.g. `pdftoppm` + a tiled
  image) and confirm that no page except the table of contents is left half-empty, page by
  page. Do not rely on the deterministic gate alone for whitespace.
- **Page count.** The contest limit (e.g. 25 pages) counts the summary sheet, table of
  contents, solution, and references, but NOT the AI Use Report. Fill the counted allowance;
  configure the Kit's page checks to subtract the AI-report pages.
- **Captions.** Captions go BELOW figures and tables, in a small font with a bold label
  ("Figure 1:"), and must be width-limited (e.g. `\captionsetup{width=0.86\textwidth}`) so they
  do not span the full text width.
- Treat a near-full page with figures placed at top/bottom as the target; treat large vertical
  gaps as something to fix before release, even if no automated check flags them.

## What O papers measure like (147 papers, 2018+)

`scripts/measure_award_corpus.py` measured the local O-award corpus; the report is
`reports/award_corpus_measurements.md`. Use these as the reference, not taste:

| Feature | O papers | What it means |
| --- | --- | --- |
| Title | median 8 words, P90 13; 35 of 94 use a colon; 1 of 94 has a dash, and it is an epigraph | name method and object; no dashed double titles |
| Summary Sheet | median 475 words, 14 numbers (only 4/147 under 3); keywords line in 80% | numbers on the page, not only methods |
| Acronyms in the summary | median 3, a quarter at 0-1 | use a model's standard name and acronym where it helps; not required |
| Words per body page | median 298; the densest paper 484 | let equations, figures and tables carry the argument |
| Defensive disclaimers | 110/147 use none; max 6 per 10k words | state each limitation once, in the evaluation |
| Control number on each page | median 100% of pages | a COMAP rule, checked by `submission_checker` |
| Notes to the team, tool names | 0/147 | never; `paper_hygiene_checker` fails on them |

Two rules follow. **Do not shrink fonts or spacing to fit 25 pages**: COMAP requires at
least 12-point type (`submission_checker` fails a document class below 12pt and warns on a
smaller `\fontsize`); cut repeated explanation instead. **No note to the team or program-log
phrasing** in the body: "in this version we fixed..." fails `paper_hygiene_checker`; "the
solver took 14 ms", `method="highs"` and script names warn.

## Summary Sheet

The Summary Sheet should answer, in one page:

- What problem was solved?
- What is the model family and why is it appropriate?
- What data or parameters support it?
- What are the main quantitative results?
- What decisions or recommendations follow?
- What are the key limitations?

Avoid generic prose. Use topic sentences and numbers. A judge should be able to understand the solution's value from this page alone.

O-paper conventions worth copying (see `award_patterns.md`):

- Give the approach a **name** (e.g. "Olympic Multi-dimensional Predictive Integrator") and
  put it above the Summary heading. It signals a designed system, not a pile of methods.
- Structure the summary as a narrative through the sub-problems ("First ... Subsequently ...
  Finally ..."), each step naming its method **and its numeric result**.
- Put hard numbers in the summary itself, not just method names.
- State at most one limitation, once. Disclaimers belong in the evaluation section.
- End with a **Keywords** line.

## Content Depth

Follow the O-paper section skeleton in `award_patterns.md`, which is invariant across the
recent Outstanding papers we sampled. A strong paper contains:

- a named **Restatement of the Problem** subsection tied to every task;
- an **Our Work** subsection: bulleted contributions plus a global flowchart of the solution path;
- **Assumptions and Justification** — each assumption with its justification, not boilerplate;
- a **Notation** section with a symbol table (expected, not optional — 5 of 6 O papers make it its own section);
- data and parameter provenance;
- **reasons for model selection** before each model, not only the derivation;
- model derivation and algorithm;
- validation or sanity checks;
- a dedicated **Sensitivity Analysis** section that ends in a consequence or limitation;
- uncertainty analysis and interpretation of results;
- a dedicated **Strengths and Weaknesses** (or Model Evaluation) section;
- the **letter / memorandum / one-page article** whenever the problem requests one;
- limitations and extensions.

Equations alone are not depth. They need parameter definitions, solution method, and evidence that they answer the problem.

## Common Failure Patterns

- The paper reads like a code report or lecture note.
- The model is plausible but not tied to data.
- Generated figures exist but do not carry argument weight.
- The Summary repeats methods but does not sell results.
- The workflow gate passes because its thresholds were lowered.
- The paper is far shorter than the problem warrants.
