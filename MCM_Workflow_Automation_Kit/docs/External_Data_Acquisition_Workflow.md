# External Data Acquisition Workflow

This kit now treats external data as a first-class workflow stage. Codex can
search the web and download data, but the project should only accept data after
it has been recorded, hashed, and checked.

## Local Workflow

```text
problem statement
  -> external data needs
  -> Codex web search and source comparison
  -> manifest row
  -> manifest-driven download
  -> source_checker
  -> data_auditor
  -> modeling pipeline
  -> result_checker / paper_qa / v1_gate
```

## Files

| File | Role |
| --- | --- |
| `reports/external_data_needs.md` | Explains what external data is needed and why. |
| `reports/data_source_manifest.csv` | Records publisher, URL, access date, license/terms, local path, hash, and paper usage. |
| `data/raw/external/` | Stores downloaded external raw datasets. |
| `scripts/fetch_external_data.py` | Downloads manifest-declared external sources into local paths. |
| `reports/workflow/source_vetting_report.md` | Records source checker results. |

## Codex Capability Boundary

Codex can:

- read the problem statement and turn it into concrete data requirements;
- search the web when network/browsing access is available;
- compare candidate sources by publisher, coverage, recency, license, and
  reproducibility;
- download public files or call documented APIs when allowed;
- compute hashes, fill the source manifest, and update paper citations;
- explain uncertainty when sources disagree or when coverage is incomplete.

Codex should not be treated as a truth oracle. It cannot by itself guarantee
that a data source is authoritative, current, legally reusable, or statistically
appropriate. It also should not bypass paywalls, CAPTCHAs, logins, robots
restrictions, or private-data boundaries. Human judgment remains responsible
for accepting the source and deciding whether the data supports the model.

The kit is deterministic. It does not discover data by itself. It verifies the
evidence trail after Codex or a human has declared candidate sources.

## Source Selection Rules

Prefer sources in this order:

1. Official data from the contest packet or problem statement.
2. Official public agency, university, standards-body, or organization data.
3. Well-documented public repositories with clear license and versioning.
4. Secondary aggregators only when primary data is unavailable and the limitation
   is stated in the paper.

Every accepted source should have a clear reason to exist in the model. If a
dataset cannot be tied to a table, figure, parameter, validation step, or paper
claim, leave it out.

## Commands

Dry-run planned external downloads:

```powershell
python scripts/fetch_external_data.py --dry-run
```

Download declared external rows and fill missing hashes:

```powershell
python scripts/fetch_external_data.py --update-hashes
python MCM_Workflow_Automation_Kit/run_workflow.py --project-root . --mode check
```

Fetch one source only:

```powershell
python scripts/fetch_external_data.py --source-id world_bank_population --update-hashes
```

## Minimal Codex Prompt

```text
Read the problem statement and reports/external_data_needs.md. Search for
official public datasets that satisfy each need. For every candidate, compare
publisher, coverage, update date, license/terms, and reproducibility. Download
only accepted sources into data/raw/external/, update
reports/data_source_manifest.csv with access date and SHA-256, then run the
workflow source checker.
```
