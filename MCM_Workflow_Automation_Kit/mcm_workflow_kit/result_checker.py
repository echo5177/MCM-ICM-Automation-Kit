from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import pandas as pd

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


INCLUDEGRAPHICS_RE = re.compile(
    r"\\includegraphics(?:\[[^\]]*\])?\{(?P<path>[^}]+)\}"
)
TABLE_FILE_RE = re.compile(r"table_(?P<number>\d+)_.*\.tex$")


@dataclass(frozen=True)
class ResultCheckResult:
    messages: list[CheckMessage]
    figure_manifest_rows: int
    latex_figure_refs: list[str]
    key_result_checks: list[dict[str, Any]]
    table_numbers: list[int]

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def parse_latex_graphics(tex_text: str) -> list[str]:
    return [match.group("path").strip() for match in INCLUDEGRAPHICS_RE.finditer(tex_text)]


def scan_placeholders(text: str, patterns: list[str]) -> list[str]:
    found = []
    lowered = text.lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            found.append(pattern)
    return found


def _value_variants(value: str) -> set[str]:
    stripped = str(value).strip()
    variants = {stripped}
    try:
        number = float(stripped)
    except ValueError:
        return {variant for variant in variants if variant}

    if number.is_integer():
        variants.add(str(int(number)))
    for digits in (6, 4, 3, 2, 1):
        variants.add(f"{number:.{digits}f}")
    if abs(number) <= 1:
        percent = number * 100
        for digits in (2, 1, 0):
            variants.add(f"{percent:.{digits}f}%")
            variants.add(f"{percent:.{digits}f} percent")
    return {variant for variant in variants if variant}


def _normal_text(text: str) -> str:
    return text.replace(",", "").lower()


def check_key_results_in_text(
    key_results_path: str | Path,
    paper_text: str,
) -> list[dict[str, Any]]:
    key_results = pd.read_csv(key_results_path)
    if not {"metric", "value"}.issubset(key_results.columns):
        return [
            {
                "metric": "<schema>",
                "value": "",
                "status": "missing_columns",
                "matched_variant": "",
            }
        ]

    normalized = _normal_text(paper_text)
    checks = []
    for _, row in key_results.iterrows():
        value = str(row["value"])
        matched = ""
        for variant in sorted(_value_variants(value), key=len, reverse=True):
            if variant.lower().replace(",", "") in normalized:
                matched = variant
                break
        checks.append(
            {
                "metric": str(row["metric"]),
                "value": value,
                "status": "found" if matched else "not_found",
                "matched_variant": matched,
            }
        )
    return checks


def check_table_numbers(tables_dir: str | Path) -> list[int]:
    table_dir = Path(tables_dir)
    if not table_dir.exists():
        return []
    numbers = []
    for path in table_dir.glob("table_*.tex"):
        match = TABLE_FILE_RE.match(path.name)
        if match:
            numbers.append(int(match.group("number")))
    return sorted(numbers)


def missing_table_numbers(numbers: list[int]) -> list[int]:
    if not numbers:
        return []
    return [number for number in range(1, max(numbers) + 1) if number not in numbers]


def run_result_checks(
    project_root: str | Path,
    config: WorkflowConfig,
) -> ResultCheckResult:
    root = Path(project_root).resolve()
    paper_path = resolve_project_path(root, config.paper_tex)
    manifest_path = resolve_project_path(root, config.figure_manifest)
    key_results_path = resolve_project_path(root, config.key_results)
    tables_dir = resolve_project_path(root, config.tables_dir)

    messages: list[CheckMessage] = []
    paper_text = paper_path.read_text(encoding="utf-8")
    placeholder_hits = scan_placeholders(paper_text, config.placeholder_patterns)
    if placeholder_hits:
        messages.append(
            CheckMessage(
                "warn",
                "Placeholder patterns found in paper: " + ", ".join(placeholder_hits),
            )
        )

    if not manifest_path.exists():
        messages.append(CheckMessage("fail", f"Figure manifest missing: {manifest_path}"))
        manifest = pd.DataFrame(columns=["figure_id", "path"])
    else:
        manifest = pd.read_csv(manifest_path)

    manifest_paths = [Path(path) for path in manifest.get("path", [])]
    manifest_basenames = {path.name for path in manifest_paths}
    for path in manifest_paths:
        if not (root / path).exists():
            messages.append(CheckMessage("fail", f"Manifest figure missing: {path}"))

    latex_refs = parse_latex_graphics(paper_text)
    for ref in latex_refs:
        if Path(ref).name not in manifest_basenames:
            messages.append(
                CheckMessage(
                    "fail",
                    f"LaTeX figure reference is not listed in manifest: {ref}",
                )
            )

    key_result_checks = check_key_results_in_text(key_results_path, paper_text)
    missing_metrics = [
        check["metric"]
        for check in key_result_checks
        if check["status"] != "found"
    ]
    if missing_metrics:
        preview = ", ".join(missing_metrics[:8])
        suffix = "" if len(missing_metrics) <= 8 else f", +{len(missing_metrics) - 8} more"
        messages.append(
            CheckMessage(
                "warn",
                f"Key result values not found directly in paper: {preview}{suffix}",
            )
        )

    table_numbers = check_table_numbers(tables_dir)
    missing_tables = missing_table_numbers(table_numbers)
    if missing_tables:
        messages.append(
            CheckMessage(
                "warn",
                "Table file numbering has gaps: "
                + ", ".join(str(number) for number in missing_tables),
            )
        )

    if not messages:
        messages.append(CheckMessage("pass", "All result consistency checks passed."))

    return ResultCheckResult(
        messages=messages,
        figure_manifest_rows=int(len(manifest)),
        latex_figure_refs=latex_refs,
        key_result_checks=key_result_checks,
        table_numbers=table_numbers,
    )


def write_result_check_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> ResultCheckResult:
    result = run_result_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    lines = render_result_check_markdown(result)
    write_markdown_report(
        reports_dir / "result_consistency_report.md",
        "Result Consistency Report",
        lines,
    )
    return result


def render_result_check_markdown(result: ResultCheckResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Figure manifest rows: {result.figure_manifest_rows}",
        f"- LaTeX figure references: {len(result.latex_figure_refs)}",
        f"- Table files detected: {len(result.table_numbers)}",
        "",
        "## Messages",
        "",
    ]
    lines.extend(
        f"- {message.level.upper()}: {message.message}" for message in result.messages
    )
    lines.extend(["", "## Key Result Checks", "", "| Metric | Status | Matched Variant |"])
    lines.append("| --- | --- | --- |")
    for check in result.key_result_checks:
        lines.append(
            f"| {check['metric']} | {check['status']} | {check['matched_variant']} |"
        )
    return lines
