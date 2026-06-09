"""Source-role gate.

The original `source_checker` only verified that files listed in the manifest exist
and that their SHA-256 matches. That let Markdown "source cards" masquerade as real
datasets: ProbA registered Android/CALCE/NASA as `external` data, but the local files
were `*_source.md` notes, and the model still ran on hard-coded parameters.

This node classifies each registered source by what it actually is on disk and fails
when a card or document is presented as data/validation/calibration evidence.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


REAL_DATA_EXTENSIONS = {
    ".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet", ".zip",
    ".mat", ".h5", ".hdf5", ".nc", ".dat", ".npy", ".npz",
}
DOCUMENT_EXTENSIONS = {".pdf"}
CARD_EXTENSIONS = {".md", ".markdown", ".rst"}

# Words that imply a source is being used as actual data/calibration/validation
# evidence rather than as background documentation.
DATA_CLAIM_KEYWORDS = [
    "dataset", "data set", "evidence", "validation", "validate", "calibrat",
    "measurement", "profile", "impedance", "capacity", "aging", "fade",
    "observed", "fit ", "estimate parameters", "parameter estimation",
]

# Words that signal an open / freely reusable license, as the problem requires.
OPEN_LICENSE_KEYWORDS = [
    "open", "public", "cc-", "cc0", "creative commons", "mit", "bsd",
    "apache", "free", "gpl", "odbl", "public domain", "open access",
]


@dataclass(frozen=True)
class SourceRoleResult:
    messages: list[CheckMessage]
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def classify_artifact(local_path: str) -> str:
    suffix = Path(local_path).suffix.lower()
    if suffix in REAL_DATA_EXTENSIONS:
        return "data"
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    if suffix in CARD_EXTENSIONS:
        return "card"
    return "other"


def _has_keyword(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in keywords)


def read_manifest_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate_rows(
    rows: list[dict[str, str]],
    config: WorkflowConfig,
) -> tuple[list[CheckMessage], list[dict[str, Any]]]:
    messages: list[CheckMessage] = []
    summary: list[dict[str, Any]] = []
    real_dataset_count = 0
    external_count = 0

    for row in rows:
        source_id = row.get("source_id", "")
        source_type = (row.get("source_type", "") or "").strip().lower()
        role = (row.get("role", "") or "").strip().lower()
        local_path = row.get("local_path", "") or ""
        usage_text = " ".join(
            [row.get("why_needed", ""), row.get("paper_usage", ""), row.get("dataset_name", "")]
        )
        license_text = row.get("license_or_terms", "") or ""
        artifact = classify_artifact(local_path)
        is_external = source_type == "external"
        if is_external:
            external_count += 1

        declared_data_role = role in {"true_dataset", "validation_source"}
        claims_data = _has_keyword(usage_text, DATA_CLAIM_KEYWORDS)

        if artifact == "data":
            real_dataset_count += 1

        # Rule A: explicit data role but the file is not data.
        if declared_data_role and artifact != "data":
            messages.append(
                CheckMessage(
                    "fail",
                    f"{source_id}: role '{role}' implies a real dataset but the local file "
                    f"is a {artifact} ({local_path}). Download the actual data or reclassify.",
                )
            )
        # Rule B (legacy/heuristic): external card used as data/validation evidence.
        elif is_external and artifact in {"card", "document"} and claims_data:
            messages.append(
                CheckMessage(
                    "fail",
                    f"{source_id}: registered as external and described as data/validation "
                    f"evidence, but the local artifact is a {artifact} ({local_path}). A source "
                    f"card cannot stand in for a dataset; download the open dataset or "
                    f"reclassify it as documentation_source.",
                )
            )
        elif is_external and artifact == "card":
            messages.append(
                CheckMessage(
                    "warn",
                    f"{source_id}: external source resolves only to a card ({local_path}); "
                    f"acceptable only as documentation_source.",
                )
            )

        # Open-license expectation for anything used as data.
        if artifact == "data" and not _has_keyword(license_text, OPEN_LICENSE_KEYWORDS):
            messages.append(
                CheckMessage(
                    "warn",
                    f"{source_id}: dataset license/terms do not clearly state open/free reuse "
                    f"('{license_text[:60]}'). The problem requires open-licensed data.",
                )
            )

        summary.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "role": role or "(unspecified)",
                "artifact": artifact,
                "local_path": local_path,
                "claims_data": claims_data,
            }
        )

    # Rule C: external data required but nothing real was actually downloaded.
    if config.external_data_required and external_count > 0 and real_dataset_count == 0:
        messages.append(
            CheckMessage(
                "fail",
                "external_data_required is true and external sources are listed, but none "
                "resolve to an actual dataset file (only cards/documents).",
            )
        )

    return messages, summary


def run_source_role_checks(
    project_root: str | Path,
    config: WorkflowConfig,
) -> SourceRoleResult:
    root = Path(project_root).resolve()
    manifest_path = resolve_project_path(root, config.data_source_manifest)
    rows = read_manifest_rows(manifest_path)

    messages: list[CheckMessage] = []
    summary: list[dict[str, Any]] = []
    if not rows:
        if config.source_manifest_required:
            messages.append(
                CheckMessage("fail", f"Source manifest missing or empty: {config.data_source_manifest}")
            )
        else:
            messages.append(CheckMessage("warn", "No source manifest rows to classify."))
    else:
        messages, summary = evaluate_rows(rows, config)

    if not messages:
        messages.append(CheckMessage("pass", "Source roles are consistent with on-disk artifacts."))

    return SourceRoleResult(messages=messages, rows=summary)


def render_source_role_markdown(result: SourceRoleResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        "",
        "## Messages",
        "",
    ]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    lines.extend(
        ["", "## Sources", "", "| Source | Type | Role | On-disk | Path |", "| --- | --- | --- | --- | --- |"]
    )
    for row in result.rows:
        lines.append(
            f"| {row['source_id']} | {row['source_type']} | {row['role']} | "
            f"{row['artifact']} | {row['local_path']} |"
        )
    return lines


def write_source_role_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> SourceRoleResult:
    result = run_source_role_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "source_role_report.md",
        "Source Role Report",
        render_source_role_markdown(result),
    )
    return result
