from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import csv
import hashlib
from typing import Any
from urllib.parse import urlparse

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


REQUIRED_COLUMNS = [
    "source_id",
    "dataset_name",
    "source_type",
    "publisher",
    "url",
    "access_date",
    "license_or_terms",
    "retrieval_method",
    "local_path",
    "sha256",
    "why_needed",
    "paper_usage",
    "citation_key",
]

CRITICAL_COLUMNS = {"source_id", "dataset_name", "source_type", "local_path"}
METADATA_COLUMNS = {
    "publisher",
    "url",
    "access_date",
    "license_or_terms",
    "retrieval_method",
    "why_needed",
    "paper_usage",
}
VALID_SOURCE_TYPES = {"official_problem", "external", "derived", "synthetic", "manual"}
VALID_URL_SCHEMES = {"http", "https", "file", "local"}
NEEDS_PLACEHOLDERS = ("TODO", "TBD", "[fill", "<fill")


@dataclass(frozen=True)
class SourceCheckResult:
    messages: list[CheckMessage]
    source_rows: list[dict[str, Any]]
    needs_document: str
    external_sources: int

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def calculate_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader], list(reader.fieldnames or [])


def _valid_access_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() in VALID_URL_SCHEMES and bool(parsed.path or parsed.netloc)


def _source_label(row: dict[str, str], index: int) -> str:
    source_id = row.get("source_id", "").strip()
    return source_id or f"row {index}"


def _check_needs_document(
    project_root: Path,
    config: WorkflowConfig,
    messages: list[CheckMessage],
) -> str:
    needs_path = resolve_project_path(project_root, config.external_data_needs)
    if not needs_path.exists():
        level = "fail" if config.external_data_required else "warn"
        messages.append(CheckMessage(level, f"External data needs document missing: {needs_path}"))
        return str(needs_path)

    text = needs_path.read_text(encoding="utf-8")
    lowered = text.lower()
    placeholder_hits = [
        placeholder for placeholder in NEEDS_PLACEHOLDERS if placeholder.lower() in lowered
    ]
    if placeholder_hits:
        messages.append(
            CheckMessage(
                "warn",
                "External data needs document still has placeholders: "
                + ", ".join(placeholder_hits),
            )
        )
    return str(needs_path)


def _check_manifest_schema(
    manifest_path: Path,
    fieldnames: list[str],
    config: WorkflowConfig,
    messages: list[CheckMessage],
) -> bool:
    if not manifest_path.exists():
        level = "fail" if config.source_manifest_required else "warn"
        messages.append(CheckMessage(level, f"Data source manifest missing: {manifest_path}"))
        return False

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing_columns:
        messages.append(
            CheckMessage(
                "fail",
                "Data source manifest missing columns: " + ", ".join(missing_columns),
            )
        )
        return False
    return True


def run_source_checks(
    project_root: str | Path,
    config: WorkflowConfig,
) -> SourceCheckResult:
    root = Path(project_root).resolve()
    messages: list[CheckMessage] = []
    source_rows: list[dict[str, Any]] = []
    needs_document = _check_needs_document(root, config, messages)
    manifest_path = resolve_project_path(root, config.data_source_manifest)
    rows, fieldnames = _read_manifest(manifest_path)
    schema_ok = _check_manifest_schema(manifest_path, fieldnames, config, messages)
    external_sources = 0

    if schema_ok and not rows:
        level = "fail" if config.source_manifest_required else "warn"
        messages.append(CheckMessage(level, "Data source manifest has no rows."))

    if schema_ok:
        for index, row in enumerate(rows, start=1):
            label = _source_label(row, index)
            source_type = row.get("source_type", "").strip().lower()
            local_rel = row.get("local_path", "").strip()
            expected_hash = row.get("sha256", "").strip().lower()
            local_path = resolve_project_path(root, local_rel) if local_rel else root
            file_exists = bool(local_rel) and local_path.exists()
            computed_hash = ""
            hash_status = "not_checked"

            if source_type == "external":
                external_sources += 1
            if source_type and source_type not in VALID_SOURCE_TYPES:
                messages.append(
                    CheckMessage(
                        "warn",
                        f"{label} has unrecognized source_type: {source_type}",
                    )
                )

            for column in CRITICAL_COLUMNS:
                if not row.get(column, "").strip():
                    messages.append(CheckMessage("fail", f"{label} missing {column}."))
            for column in METADATA_COLUMNS:
                if not row.get(column, "").strip():
                    messages.append(CheckMessage("warn", f"{label} missing {column}."))

            url = row.get("url", "").strip()
            if url and not _valid_url(url):
                messages.append(CheckMessage("warn", f"{label} has nonstandard URL: {url}"))

            access_date = row.get("access_date", "").strip()
            if access_date and not _valid_access_date(access_date):
                messages.append(
                    CheckMessage("warn", f"{label} access_date is not YYYY-MM-DD: {access_date}")
                )

            if not local_rel:
                hash_status = "missing_local_path"
            elif not file_exists:
                messages.append(CheckMessage("fail", f"{label} local file missing: {local_rel}"))
                hash_status = "missing_file"
            elif local_path.is_dir():
                messages.append(CheckMessage("fail", f"{label} local path is a directory: {local_rel}"))
                hash_status = "directory"
            else:
                computed_hash = calculate_sha256(local_path)
                if expected_hash:
                    if computed_hash.lower() == expected_hash:
                        hash_status = "match"
                    else:
                        messages.append(CheckMessage("fail", f"{label} sha256 mismatch: {local_rel}"))
                        hash_status = "mismatch"
                else:
                    messages.append(CheckMessage("warn", f"{label} missing sha256."))
                    hash_status = "not_recorded"

            if source_type == "external" and not row.get("citation_key", "").strip():
                messages.append(CheckMessage("warn", f"{label} external source has no citation_key."))

            source_rows.append(
                {
                    "source_id": label,
                    "dataset_name": row.get("dataset_name", "").strip(),
                    "source_type": source_type,
                    "publisher": row.get("publisher", "").strip(),
                    "local_path": local_rel,
                    "file_exists": file_exists,
                    "sha256": expected_hash,
                    "computed_sha256": computed_hash,
                    "hash_status": hash_status,
                    "paper_usage": row.get("paper_usage", "").strip(),
                }
            )

    if config.external_data_required and external_sources == 0:
        messages.append(CheckMessage("fail", "External data is required but no external source rows were declared."))

    if not messages:
        messages.append(CheckMessage("pass", "All source provenance checks passed."))

    return SourceCheckResult(
        messages=messages,
        source_rows=source_rows,
        needs_document=needs_document,
        external_sources=external_sources,
    )


def write_source_vetting_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> SourceCheckResult:
    result = run_source_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "source_vetting_report.md",
        "Source Vetting Report",
        render_source_vetting_markdown(result),
    )
    return result


def _md(value: object) -> str:
    return str(value).replace("|", "\\|")


def render_source_vetting_markdown(result: SourceCheckResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Needs document: {result.needs_document}",
        f"- Sources declared: {len(result.source_rows)}",
        f"- External sources declared: {result.external_sources}",
        "",
        "## Messages",
        "",
    ]
    lines.extend(
        f"- {message.level.upper()}: {message.message}" for message in result.messages
    )
    lines.extend(
        [
            "",
            "## Source Rows",
            "",
            "| Source | Type | Dataset | Publisher | Local Path | File | Hash | Paper Usage |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in result.source_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(row["source_id"]),
                    _md(row["source_type"]),
                    _md(row["dataset_name"]),
                    _md(row["publisher"]),
                    _md(row["local_path"]),
                    "yes" if row["file_exists"] else "no",
                    _md(row["hash_status"]),
                    _md(row["paper_usage"]),
                ]
            )
            + " |"
        )
    return lines
