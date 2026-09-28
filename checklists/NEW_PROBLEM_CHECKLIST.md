# New-Problem Checklist

A run-sheet for taking a fresh MCM/ICM problem from scaffold to a contest-grade,
gate-passing paper. The Kit is the **floor** (deterministic teeth); the Skill is the
**brain** (conventions/judgment); the agent's visual QA and a human's final eye are the
**ceiling**. None replaces the others.

## 0. Scaffold (once per problem)

```bash
python scripts/new_problem.py --name ProbB --problem-letter B
cd ../Simulation_2027MCM-ICM_ProbB     # the prefix carries the next contest's year; --year overrides
conda env create -f environment.yml    # or reuse the shared 'mcm' env
```

Load the Skill `mcm-icm-competition-paper` (copied under this repo's `skill/`) so the
agent follows the paper standards while writing.

## 1. Human inputs (you provide; the agent cannot invent these)

- [ ] **Problem statement.** Save the official PDF/text under `data/raw/` and restate the
      exact tasks the contest asks for.
- [ ] **Problem letter & team control number.** Set `\Problem` and `\Team` in
      `paper/main.tex` (only there: the Summary Sheet and every page header read `\Team`).
      `1111111` is the template placeholder: the gate warns while `release_stage` is `draft`
      and fails at `final`.
- [ ] **Data decision.** Decide whether the problem needs real external data. If yes, set
      `external_data_required: true` and `source_manifest_required: true` in
      `MCM_Workflow_Automation_Kit/workflow_config.json`, then record every accepted source
      in `reports/data_source_manifest.csv` (one row per real dataset, with SHA-256). The
      Kit fails if an external "dataset" is actually a prose card (`.md`), not data.
- [ ] **Modeling direction.** Pick the model family and the key assumptions. This is a
      human/agent judgment call, not something the gate decides.

## 2. Build (agent does most of this)

- [ ] Implement the modeling pipeline in `src/` and wire it into `scripts/run_all.py` so it
      regenerates every figure/table and writes `reports/key_results.csv` (every number the
      paper cites) and `reports/figure_manifest.csv`.
- [ ] Author the concept/workflow figure as structured JSON under `figures/concept_src/`,
      render it to `figures/concept/`, and register it in `diagram_sources` in the config.
      The diagram-quality gate rejects a sparse "boxes-and-arrows" figure (needs >= 8 nodes,
      >= 3 stages, >= 60% of nodes carrying content).
- [ ] A flowchart a teammate drew (PowerPoint, draw.io, Visio): ask for it early, import it
      with `python MCM_Workflow_Automation_Kit/import_flowchart.py flowchart.pptx --out
      figures/concept/workflow.pdf`, register it with `"origin": "user"`, and place it as an
      ordinary portrait figure. Never a landscape page.
- [ ] Write the paper on `paper/main.tex` (already built on the official template). Fill the
      full allowance with substance: aim for ~20-25 counted pages. Keep the AI Use Report
      AFTER references (it does NOT count toward 25; the config subtracts `ai_report_pages`).

## 3. Verify (this is where ProbA failed the first time)

- [ ] Run the gate: `python MCM_Workflow_Automation_Kit/run_workflow.py --project-root . --mode full`.
- [ ] **Visual QA, every page.** Render the whole PDF to a page-by-page contact sheet
      (`pdftoppm` + a tiled image) and confirm NO page except the ToC is half-empty. Fix
      sparse/float-only pages (resize, reorder, or change `[H]`->`[htbp]`); the float
      parameters in the starter preamble already help.
- [ ] **Alignment review from the first draft.** Before reading the paper, write down how the
      reference solution would treat each question (the values the problem states, the
      structure planted in the data, how each quantity should be forecast, what counts as
      using future data), then check the paper against it
      (`skill/references/judge_rubric.md`, "Two kinds of review").
- [ ] **Cutting pages?** Follow the page-cut triage in
      `skill/references/competition_operations.md`: never cut a result the Summary cites, and
      re-read the Summary against the body after every cut. No smaller fonts or spacing.
- [ ] **Honest judge review.** Fill `reports/workflow/judge_review.md` (stub provided) using
      `skill/references/judge_rubric.md`. Set real scores; release needs every category >= 4
      and `RELEASE: APPROVED`. Do not inflate scores to turn the gate green — the gate cannot
      check honesty; you must.

## 4. Release

- [ ] Set `release_stage: final` in the config and build the submission PDF.
- [ ] Judge review on that PDF, with its `PAPER_SHA256` written into
      `reports/workflow/judge_review.md` (the gate prints the current hash). Any rebuild voids it.
- [ ] `submission_checker` clean: one control number on the Summary Sheet and every page
      header, no names, school or e-mail (PDF properties included), the AI report after the
      references, at most 25 counted pages. Set `submission_pdf` to the file you will upload,
      named `<control number>.pdf` and under 25 MB.
- [ ] Whole gate green (`v2_gate` says CONTEST-READY) AND a human has eyeballed the PDF.
- [ ] `python MCM_Workflow_Automation_Kit/scripts/create_release_packet.py --project-root .`
- [ ] Commit. Keep the repo Private until after the contest.

## What the gate canNOT do for you

- Judge aesthetics, prose quality, or whether the modeling is actually correct.
- Verify the judge review is honest (it parses scores; it does not re-grade).
- Invent data, assumptions, or modeling direction.

Treat a green gate as "no known defect," not "this will win." The last 20% is human.
