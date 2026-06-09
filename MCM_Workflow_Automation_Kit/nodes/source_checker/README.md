# source_checker

Validates the project data source manifest before modeling begins.

Inputs are configured through `workflow_config.json`:

- `data_source_manifest`
- `external_data_needs`
- `external_data_dir`
- `external_data_required`
- `source_manifest_required`

The node checks manifest schema, source metadata, local file existence, and
SHA-256 hashes. It writes:

```text
reports/workflow/source_vetting_report.md
```

It does not search the web by itself. Codex or a human declares accepted
sources in the manifest; this node verifies that the local evidence trail is
complete enough to support reproducible modeling.
