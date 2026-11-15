# Workflow Node Map

```text
run_workflow.py
  -> optional project pipeline
  -> source_checker
  -> data_auditor
  -> result_checker
  -> diagram_checker
  -> paper_reviewer
  -> v1_gate
  -> workflow_run_summary.md

create_release_packet.py
  -> release/<timestamp>/
  -> release_manifest.csv
  -> final_checklist.md
```

## v0.1 Commands

```powershell
python MCM_Workflow_Automation_Kit/run_workflow.py --project-root . --mode check
python MCM_Workflow_Automation_Kit/scripts/create_release_packet.py --project-root .
```

Use `--mode full` only when the configured project pipeline command should run
before checks.

## v1.0 Gate

The v1.0 gate treats the kit as a quality-control system, not only a command
runner. It passes only when no node fails and all warnings are classified.

| Node | Input | Output | Gate Role |
| --- | --- | --- | --- |
| `source_checker` | `external_data_needs.md`, `data_source_manifest.csv`, local raw files | `source_vetting_report.md` | confirms every accepted data source has provenance, local path, and hash evidence before modeling |
| `data_auditor` | configured raw CSV files | `data_audit.json`, `data_audit_report.md` | confirms data shape and missingness are recorded |
| `result_checker` | paper source, `key_results.csv`, `figure_manifest.csv`, tables | `result_consistency_report.md` | checks result traceability and figure/table consistency |
| `diagram_checker` | structured diagram JSON/SVG/PNG and manifest row | `diagram_qa_report.md` | prevents high-information workflow figures from becoming untraceable AI bitmaps |
| `paper_reviewer` | LaTeX source, PDF, LaTeX log | `paper_qa_report.md` | checks page target, hard limit, required sections, and LaTeX warnings |
| `param_ledger` | `reports/param_ledger.csv`, source manifest, the paper's reference list | `param_ledger_report.md` | every given parameter has a value, a unit and an origin; a dataset or calibrated value names a source_id that exists, a literature value a citation key that exists (fail at final); an assumed value nothing varies, and a ledger that is mostly assumed (warn) |
| `model_ladder` | `reports/model_ladder.csv`, `reports/requirements.csv`, paper text | `model_ladder_report.md` | every modeling requirement has a naive baseline (rung 0); the rung the paper keeps is not beaten by a simpler one without a recorded reason (fail); the baseline's score appears in the paper (warn) |
| `requirement_checker` | `reports/requirements.csv`, expanded LaTeX source, compiled PDF (table of contents, Summary Sheet) | `requirement_report.md` | every requirement of the problem has what it turns on, an answer, a section that exists and evidence labels that exist (fail at final); the answer's number is on the Summary Sheet and no body section answers nothing (warn) |
| `paper_hygiene_checker` | expanded LaTeX source (or the PDF text for a Word-built paper), compiled PDF | `paper_hygiene_report.md` | notes to the team and tool traces fail; program-log phrases, disclaimers, title, Summary numbers, page density and landscape pages warn, each line measured on 147 O papers |
| `submission_checker` | compiled PDF (text layer, properties), LaTeX preamble, config | `submission_report.md` | Summary Sheet control number = every page header (not the template placeholder at final), no identifying names, font >= 12pt, AI report after references with its measured page count, upload named `<control>.pdf` under 20 MB |
| `ai_use_checker` | `reports/ai_use_log.csv`, compiled PDF (Report on Use of AI, reference list) | `ai_use_report.md` | every tool in the log is named in the report (fail at final); each has a version and a verification note and appears in the reference list (warn) |
| `v1_gate` | prior node statuses and known warning rules | `v1_gate_report.md` | classifies remaining warnings and records v1.0 readiness |

## External Data Path

```text
reports/external_data_needs.md
  -> Codex web search and source comparison
  -> reports/data_source_manifest.csv
  -> scripts/fetch_external_data.py
  -> data/raw/external/
  -> source_checker
```

Codex can perform the web-search and download steps when network access is
available. The kit then checks the resulting evidence trail deterministically.
