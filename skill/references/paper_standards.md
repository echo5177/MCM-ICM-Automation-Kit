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
- O papers under the 25-page rule run 22 to 26 pages in total, most of them exactly 25. A
  12-15 page paper is under-developed, not concise. COMAP sets no minimum length, so the
  point is not the count: a short paper has usually answered some requirement thinly. Find
  that requirement and develop its answer (its data treatment, its validation, its
  sensitivity). Pages spent on something the problem did not ask for are not depth; the
  CUMCM 2026 entry gave body pages to three analyses no question requested while its key
  question got three.
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
| Total pages (2021+, the 25-page rule) | 22 to 26; 51 of 70 exactly 25; none under 22 | fill the allowance by developing the thinnest answer, never by new topics |
| First model section starts on | page 4 at the median, 6 at P90, 9 at the latest (107 papers) | keep restatement, assumptions and notation short |
| Numbered figures per page | median 0.58, P25 0.42, P10 0.29 (113 papers) | a figure per result that needs one; none that is extraneous |
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

Write it last, and write it answer-first. COMAP's instructions say winning papers are often
distinguished by the summary. The judges' own advice ("20 Years of Good Advice", The UMAP
Journal) is specific: the summary must contain results and never say "read inside for
results"; it should not be overly technical, because "a long list of techniques can obscure
your results"; it gives the bottom line and the recommendation, not a chronological account
of what was done. A triage judge gives the whole paper 10 to 15 minutes, and a paper that is
otherwise strong can be eliminated in the early rounds on a weak summary.

For each requirement of the problem, in the order the problem lists them:

1. one plain sentence on what the requirement turns on: the trade-off, the quantity that
   decides the answer, or the ratio or penalty the statement gives and how it enters the
   decision;
2. the answer, with its number and unit;
3. the method in a clause, by its standard name.

Then the recommendation that follows from the answers, and one limitation, stated once.

Step 1 comes from the CUMCM 2026 post-mortem. That paper's abstract named seven methods and
never said what its second question turned on (how much to over-buy when a unit short costs
five times a unit over). Both showcased papers said it in one sentence and gave the resulting
quantile. A reader finished our abstract knowing which tools were used and not whether the
authors had seen the problem. The same sentence opens each task's section in the body.

O-paper conventions worth keeping (see `award_patterns.md`):

- A narrative through the requirements ("First ... Then ... Finally ..."), each step ending
  in a number.
- Hard numbers on the page: O summaries carry a median of 14.
- A **name** for the approach is common and optional. It helps when the paper is one designed
  system; it does not replace the answers.
- At most one limitation, once. Disclaimers belong in the evaluation section.
- A **Keywords** line at the end, with at least one word for the object studied, not only
  method names.

## One section per task, each complete

Organise the body by the problem's requirements, and keep everything a judge needs for one
requirement inside that requirement's section: what it turns on, the data or parameters and
where they come from, the model, the result, the check. "Make it clear where in the paper the
answers are" is the judges' wording, and papers missing several required elements are
eliminated quickly.

In the CUMCM 2026 entry the evidence for the question that carried seven of the thirteen
marking points sat in four different chapters, and the first question began on page 11 after
ten pages of restatement, assumptions, notation, preprocessing and a shared framework. In 107
O papers the first model section starts on page 4 at the median, page 6 at P90 and page 9 at
the latest; `mcm_format_checker` warns past page 7. Keep the framing short, and put a shared
framework inside the first task that uses it.

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
