# MCM-ICM Automation Kit

A reusable, one-click-migratable template for producing **contest-grade MCM/ICM (美赛)
papers** with a deterministic quality gate. It packages the hard-won pieces from building
Problem A end-to-end so any new problem starts from the same floor instead of from zero.

It is a **template**, not a one-button paper generator. It raises the floor and bakes in
the conventions; it does not replace modeling judgment or a human's final eye.

## The three layers

| Layer | What it is | What it guarantees |
| --- | --- | --- |
| **Kit** (`MCM_Workflow_Automation_Kit/`) | Deterministic v2-gate, 12 nodes | A floor: no *known* defect (thin paper, lowered thresholds, sparse diagram, fake data, missing sections, unrendered PDF, no judge sign-off) can pass quietly. |
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
│   ├── workflow_config.json            #   GENERIC starter config (per-problem copy)
│   ├── mcm_workflow_kit/               #   the 12 nodes + orchestrator
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
│   └── sync_kit.py                     # update the Kit in an existing problem repo
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
cd ../Simulation_2026MCM-ICM_ProbB
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

## The v2 gate (15 nodes)

`run_workflow.py` runs these in order; any `fail` fails the run. `--mode full` runs your
`scripts/run_all.py` first.

1. **source_checker** — source manifest schema, metadata, local files, SHA-256 hashes.
2. **source_role_checker** — fails when an external "dataset" is actually a prose card
   (`.md`) rather than real data.
3. **data_auditor** — profiles the raw CSVs (rows, missing, duplicates, summaries).
4. **result_checker** — every number the paper cites must trace to `key_results.csv`;
   figures/tables in the manifest must exist; no placeholder strings. Reads the paper with
   its `\input` files expanded.
5. **experiment_audit** — parameter sweeps, random seeds, and template text left in figures.
6. **diagram_checker** — concept figure's PNG/SVG/JSON exist and are large enough.
7. **diagram_quality_checker** — inspects the figure's structured JSON *content* so a
   sparse boxes-and-arrows diagram cannot pass (>= 8 nodes, >= 3 stages, >= 60% content).
8. **paper_qa** — LaTeX/PDF QA; page count is computed as `pages - ai_report_pages` and
   compared to the contest limit and the serious-length floor (a thin paper FAILS).
9. **mcm_format_checker** — official-template structure (Summary / ToC / References / AI
   Use Report), `hyperref` must use `hidelinks`, layout checks (`[H]` overuse, missing
   width-limited captions), and **gate-lowering detection** (a config that lowers the
   page target below the floor FAILS).
10. **submission_checker** — what COMAP checks before a judge reads a word: the Summary
    Sheet's control number equals the one in every page header (and is not the template's
    1111111 at final); no names, school or e-mail; font at least 12pt; the Report on Use of
    AI after the references, with its real page count; the upload named `<control>.pdf`,
    under 25 MB.
11. **visual_qa_packet** — renders PDF pages so they can be eyeballed.
12. **judge_review_gate** — parses `reports/workflow/judge_review.md`; needs every
    category score >= 4, `RELEASE: APPROVED`, and `PAPER_SHA256` equal to the current PDF
    (at `release_stage: final`; a draft only warns).
13. **v1_gate** — node-status roll-up + known-warning classification.
14. **v2_gate** — explicit contest-readiness verdict over the quality nodes (a draft gets
    the list of blockers, not a verdict).
15. **review_trajectory** — records each judge-review round and warns if a revision lowered
    the average score; never changes a verdict.

## Hard-won rules this template encodes

These are the failures from the first ProbA pass, now turned into teeth or starter defaults:

- **Use the full page allowance.** A 12–15 page paper is under-development, not concision.
  Target ~20–25 counted pages of substance.
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
