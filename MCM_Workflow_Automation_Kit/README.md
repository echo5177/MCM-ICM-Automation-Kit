# MCM Workflow Automation Kit

Local-first automation kit for reusable MCM/ICM project checks.

The kit does not replace Codex or human modeling judgment. It provides
deterministic workflow nodes for source provenance, data audit, result
consistency checks, paper QA, run logging, and release packet creation.

## Quick Start

```powershell
python MCM_Workflow_Automation_Kit/run_workflow.py --project-root . --mode check
```

Use `--mode full` after the project pipeline command in `workflow_config.json`
is ready to be run automatically.

Create a release packet:

```powershell
python MCM_Workflow_Automation_Kit/scripts/create_release_packet.py --project-root .
```

## Design

- Keep project-specific modeling code in the project repository.
- Keep reusable checks in this kit.
- Let Codex search for public data when needed, then record accepted sources in
  `reports/data_source_manifest.csv`.
- Write reports under `reports/workflow/`.
- Write transient state and logs under `MCM_Workflow_Automation_Kit/runs/`.
- Keep all text outputs UTF-8 encoded for Windows compatibility.

## Nodes

- `source_checker`: validates source manifest schema, metadata, local files, and
  SHA-256 hashes before modeling begins.
- `data_auditor`: profiles configured raw CSV files and writes JSON/Markdown
  audit reports.
- `result_checker`: compares the paper against `key_results.csv`,
  `figure_manifest.csv`, figure files, and table files.
- `diagram_checker`: verifies structured diagram source files, rendered PNGs,
  and manifest provenance for high-information concept figures.
- `paper_reviewer`: performs deterministic PDF/LaTeX QA and stores reviewer
  prompts for later AI review loops.
- `v1_gate`: summarizes node statuses and classifies known warnings for the
  reusable Kit v1.0 quality gate.
- `create_release_packet`: copies configured final artifacts into
  `release/<timestamp>/`.

## Reports

The command writes:

```text
reports/workflow/data_audit.json
reports/workflow/source_vetting_report.md
reports/workflow/data_audit_report.md
reports/workflow/result_consistency_report.md
reports/workflow/diagram_qa_report.md
reports/workflow/paper_qa_report.md
reports/workflow/v1_gate_report.md
reports/workflow/workflow_run_summary.md
```

Node execution logs and `state.json` are written under
`MCM_Workflow_Automation_Kit/runs/<timestamp>/`.

## External Data

When a problem requires public external data, use:

```powershell
python scripts/fetch_external_data.py --dry-run
python scripts/fetch_external_data.py --update-hashes
python MCM_Workflow_Automation_Kit/run_workflow.py --project-root . --mode check
```

See `docs/External_Data_Acquisition_Workflow.md` for the Codex web-search
boundary and the required evidence trail.
