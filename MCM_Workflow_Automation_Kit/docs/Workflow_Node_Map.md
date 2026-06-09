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
