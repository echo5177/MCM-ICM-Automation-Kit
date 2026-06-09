# Paper Standards

## MCM/ICM Format

A contest paper should look like a submission, not a generic article. Use a clean Summary Sheet, team number treatment, professional spacing, hidden link borders, consistent captions, and dense but readable pages.

Minimum checks:

- Summary Sheet appears before the table of contents.
- The first page is not a generic title page.
- Hyperlinks do not show colored boxes in the PDF.
- Section titles are compact and professional.
- Captions explain the point of the figure/table, not only its contents.
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
  quality-control/reproducibility section, a memo or letter) until it is genuinely full.
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

## Summary Sheet

The Summary Sheet should answer, in one page:

- What problem was solved?
- What is the model family and why is it appropriate?
- What data or parameters support it?
- What are the main quantitative results?
- What decisions or recommendations follow?
- What are the key limitations?

Avoid generic prose. Use topic sentences and numbers. A judge should be able to understand the solution's value from this page alone.

## Content Depth

A strong paper usually contains:

- problem restatement tied to tasks;
- assumptions with consequences, not boilerplate;
- notation table only when it saves reading time;
- data and parameter provenance;
- model derivation and algorithm;
- validation or sanity checks;
- sensitivity and uncertainty analysis;
- interpretation of results;
- limitations and extensions.

Equations alone are not depth. They need parameter definitions, solution method, and evidence that they answer the problem.

## Common Failure Patterns

- The paper reads like a code report or lecture note.
- The model is plausible but not tied to data.
- Generated figures exist but do not carry argument weight.
- The Summary repeats methods but does not sell results.
- The workflow gate passes because its thresholds were lowered.
- The paper is far shorter than the problem warrants.
