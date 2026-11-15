# MCM-ICM Automation Kit

A reusable, one-click-migratable template for producing **contest-grade MCM/ICM (美赛)
papers** with a deterministic quality gate. It packages the hard-won pieces from building
Problem A end-to-end so any new problem starts from the same floor instead of from zero.

It is a **template**, not a one-button paper generator. It raises the floor and bakes in
the conventions; it does not replace modeling judgment or a human's final eye.

## The three layers

| Layer | What it is | What it guarantees |
| --- | --- | --- |
| **Kit** (`MCM_Workflow_Automation_Kit/`) | Deterministic v2-gate, 20 nodes | A floor: no *known* defect (thin paper, lowered thresholds, sparse diagram, fake data, missing sections, unrendered PDF, no judge sign-off) can pass quietly. |
| **Skill** (`skill/`) | The `mcm-icm-competition-paper` Skill: paper/figure/data standards, judge rubric | The brain: conventions and judgment the agent follows while writing. |
| **Agent visual QA + human eye** | Contact-sheet review + a real person | The ceiling: aesthetics, prose, and whether the modeling is actually right. |

A green gate means "no known defect," **not** "this will win." The last 20% is human.

## Repo layout

```
MCM-ICM-Automation-Kit/
├── README.md
├── environment.yml                     # the 'mcm' conda env
├── MCM_Workflow_Automation_Kit/        # the canonical Kit (deterministic v2 gate)
│   ├── run_workflow.py                 #   entry point: --mode check | full
│   ├── import_flowchart.py             #   import a teammate's PPTX/PDF/SVG flowchart as a cropped vector PDF
│   ├── workflow_config.json            #   GENERIC starter config (per-problem copy)
│   ├── mcm_workflow_kit/               #   the 20 nodes + orchestrator
│   ├── nodes/  docs/  scripts/         #   node docs + create_release_packet.py
├── templates/
│   ├── MCM-ICM_Summary.tex             # official COMAP summary template
│   ├── paper_main.template.tex         # starter paper: official header + layout lessons baked in
│   ├── workflow_config.template.json   # reference copy of the generic config
│   ├── run_all.template.py             # starter pipeline (writes key_results / figure_manifest)
│   ├── judge_review.template.md        # judge-review stub the gate parses
│   └── gitignore.template
├── scripts/
│   ├── new_problem.py                  # scaffold a whole new problem repo
│   ├── sync_kit.py                     # update the Kit in an existing problem repo
│   └── build_ai_report.py              # build the Report on Use of AI from reports/ai_use_log.csv
├── checklists/
│   └── NEW_PROBLEM_CHECKLIST.md        # human inputs + build + verify + release run-sheet
├── skill/                              # copy of the mcm-icm-competition-paper Skill
└── tests/
    └── test_workflow_kit.py            # 40+ self-contained Kit tests
```

## Quick start

### Start a new problem

```bash
python scripts/new_problem.py --name ProbB --problem-letter B
cd ../Simulation_2027MCM-ICM_ProbB         # prefix = the next contest's year (--year overrides)
conda env create -f environment.yml        # or reuse the shared 'mcm' env
# then follow NEW_PROBLEM_CHECKLIST.md
python MCM_Workflow_Automation_Kit/run_workflow.py --project-root . --mode check
```

The scaffold's gate is **red on purpose** — there is no paper, no results, and no honest
judge review yet. It goes green only when the real work exists.

### Update the Kit in an existing problem

When the Kit improves, push the new code into a problem repo **without** clobbering its
per-problem config or run history:

```bash
python scripts/sync_kit.py --target ../Simulation_2026MCM-ICM_ProbA --dry-run
python scripts/sync_kit.py --target ../Simulation_2026MCM-ICM_ProbA
```

## The v2 gate (20 nodes)

`run_workflow.py` runs these in order; any `fail` fails the run. `--mode full` runs your
`scripts/run_all.py` first.

1. **source_checker** — source manifest schema, metadata, local files, SHA-256 hashes. FAILS on a
   source taken from a platform where contest problems are discussed (CSDN, Zhihu, ...).
2. **source_role_checker** — fails when an external "dataset" is actually a prose card
   (`.md`) rather than real data.
3. **data_auditor** — profiles the raw CSVs (rows, missing, duplicates, summaries).
   **param_ledger** (runs next) — reads `reports/param_ledger.csv`: every number the model
   takes as given, with its unit, origin (statement, dataset, literature, calibrated, assumed)
   and source. FAILS at `final` on a missing unit or a source that does not exist; warns on an
   assumed value that no sensitivity test varies.
4. **result_checker** — every number the paper cites must trace to `key_results.csv`;
   figures/tables in the manifest must exist; no placeholder strings. Reads the paper with
   its `\input` files expanded.
5. **experiment_audit** — parameter sweeps, random seeds, and template text left in figures.
   **model_ladder** (runs next) — reads `reports/model_ladder.csv`: the naive baseline and each
   added component on one metric. FAILS at `final` when a modeling requirement has no baseline,
   or when the model the paper keeps loses to a simpler rung with no reason recorded.
6. **diagram_checker** — concept figure's PNG/SVG/JSON exist and are large enough.
7. **diagram_quality_checker** — inspects the figure's structured JSON *content* so a
   sparse boxes-and-arrows diagram cannot pass (>= 8 nodes, >= 3 stages, >= 60% content).
8. **paper_qa** — LaTeX/PDF QA; page count is computed as `pages - ai_report_pages` and
   compared to the contest limit and the serious-length floor (a thin paper FAILS).
9. **mcm_format_checker** — official-template structure (Summary / ToC / References / AI
   Use Report), `hyperref` must use `hidelinks`, layout checks (`[H]` overuse, missing
   width-limited captions), and **gate-lowering detection** (a config that lowers the
   page target below the floor FAILS).
    Also warns when the first model section starts after page 7.
    **requirement_checker** (runs next) — reads `reports/requirements.csv`, one row per
    requirement of the problem: what it turns on, the answer, the section that holds it, the
    figures and tables behind it. At `final` an open requirement, an answer with no section,
    or an evidence label that is no longer in the paper FAILS; an answer missing from the
    Summary Sheet and body sections no requirement points to warn. COMAP defines Honorable
    Mention by "addressing all problem requirements".
10. **paper_hygiene_checker** — writing problems a judge sees within pages: notes to the
    team and tool traces left in the paper (FAIL), a heading with nothing under it (FAIL),
    a Summary Sheet promising two or more analyses the body barely mentions (FAIL),
    program-log phrases, defensive disclaimers, a dashed or overlong title, a Summary Sheet
    without numbers, over-dense pages, landscape pages. Every line is measured on the O
    corpus (`scripts/measure_award_corpus.py`).
11. **submission_checker** — what COMAP checks before a judge reads a word: the Summary
    Sheet's control number equals the one in every page header (and is not the template's
    1111111 at final); no names, school or e-mail; font at least 12pt; the Report on Use of
    AI after the references, with its real page count; the upload named `<control>.pdf`,
    under 20 MB (the instructions say 25, COMAP's tips say 20; the Kit takes the smaller).
    **ai_use_checker** (runs next) — checks the paper's Report on Use of AI against
    `reports/ai_use_log.csv`, the log kept while working (`scripts/build_ai_report.py` builds the
    report from it). A logged tool missing from the report FAILS at `final`.
12. **visual_qa_packet** — renders PDF pages so they can be eyeballed.
13. **judge_review_gate** — parses `reports/workflow/judge_review.md`; needs every
    category score >= 4, `RELEASE: APPROVED`, and `PAPER_SHA256` equal to the current PDF
    (at `release_stage: final`; a draft only warns).
14. **v1_gate** — node-status roll-up + known-warning classification.
15. **v2_gate** — the verdict over the quality nodes: NO KNOWN DEFECTS or DEFECTS FOUND, with the
    base rate you recorded. It is not a forecast of the award (a draft gets
    the list of blockers, not a verdict).
16. **review_trajectory** — records each judge-review round and warns if a revision lowered
    the average score; never changes a verdict.

## Hard-won rules this template encodes

These are the failures from the first ProbA pass, now turned into teeth or starter defaults:

- **Use the page allowance on the answers.** Under the 25-page rule no O paper in the corpus has
  fewer than 22 pages and most have exactly 25. A short paper has answered something thinly;
  develop that answer rather than adding topics the problem did not ask for.
  The first model section should start by about page 7 (O papers: page 4 at the median).
- **The AI Use Report does NOT count toward 25.** The config subtracts `ai_report_pages`
  before checking the contest limit. Put the report AFTER references.
- **Build on the official template.** The starter paper reuses the COMAP Summary Sheet
  header; don't hand-roll a substitute summary page.
- **Layout.** Title-first Summary (title → centered "Summary" → body); captions BELOW
  floats, small, bold label, width-limited; `[htbp]` not `[H]`; float parameters tuned so
  figures land on text pages instead of near-empty float-only pages.
- **Verify whitespace visually, every page** — the deterministic gate cannot see a
  half-empty page; render a contact sheet.
- **Honest provenance.** Real or cited data only; a prose card is not a dataset; report
  honest residuals instead of faking a fix.
- **Don't lower the gate to pass.** Lowering the page target below the floor is itself a
  FAIL.

## What the gate canNOT do

- Judge aesthetics, prose, or modeling correctness.
- Verify that the judge review's scores are honest (it parses; it does not re-grade).
- Invent data, assumptions, or modeling direction.

Per-problem thresholds (page targets, diagram minimums) live in each repo's
`MCM_Workflow_Automation_Kit/workflow_config.json` and may need tuning per problem.

## Tests

```bash
pytest tests/
```

The tests are self-contained (synthetic fixtures, no project data) and cover the gate
logic, including the regression teeth added after the ProbA failure.
