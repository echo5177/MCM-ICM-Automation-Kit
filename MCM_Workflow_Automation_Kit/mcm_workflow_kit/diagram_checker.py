from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import struct
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class DiagramCheckResult:
    messages: list[CheckMessage]
    diagram_checks: list[dict[str, Any]]

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def read_png_dimensions(path: str | Path) -> tuple[int, int] | None:
    with Path(path).open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or not header.startswith(PNG_SIGNATURE):
        return None
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def _read_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        return {row.get("figure_id", ""): row for row in rows}


def _check_file(path: Path, label: str, messages: list[CheckMessage]) -> bool:
    if not path.exists():
        messages.append(CheckMessage("fail", f"{label} missing: {path}"))
        return False
    if path.is_file() and path.stat().st_size == 0:
        messages.append(CheckMessage("fail", f"{label} is empty: {path}"))
        return False
    return True


def run_diagram_checks(
    project_root: str | Path,
    config: WorkflowConfig,
) -> DiagramCheckResult:
    root = Path(project_root).resolve()
    manifest = _read_manifest(resolve_project_path(root, config.figure_manifest))
    messages: list[CheckMessage] = []
    checks: list[dict[str, Any]] = []

    if not config.diagram_sources:
        messages.append(CheckMessage("warn", "No diagram sources configured."))

    for source in config.diagram_sources:
        figure_id = str(source.get("figure_id", ""))
        png_rel = str(source.get("png", ""))
        svg_rel = str(source.get("svg", ""))
        json_rel = str(source.get("json", ""))
        expected_source = str(source.get("expected_source", "")).strip()
        min_width = int(source.get("min_width", 0))
        min_height = int(source.get("min_height", 0))

        png_path = resolve_project_path(root, png_rel)
        svg_path = resolve_project_path(root, svg_rel)
        json_path = resolve_project_path(root, json_rel)
        dimensions: tuple[int, int] | None = None

        png_ok = _check_file(png_path, "Diagram PNG", messages)
        _check_file(svg_path, "Diagram SVG source", messages)
        _check_file(json_path, "Diagram JSON source", messages)

        if png_ok:
            dimensions = read_png_dimensions(png_path)
            if dimensions is None:
                messages.append(CheckMessage("fail", f"Diagram PNG is not valid PNG: {png_rel}"))
            else:
                width, height = dimensions
                if width < min_width or height < min_height:
                    messages.append(
                        CheckMessage(
                            "warn",
                            f"Diagram PNG below target size: {png_rel} is {width}x{height}, target {min_width}x{min_height}.",
                        )
                    )

        manifest_row = manifest.get(figure_id)
        manifest_source = ""
        if manifest_row is None:
            messages.append(CheckMessage("fail", f"Diagram figure not in manifest: {figure_id}"))
        else:
            manifest_path = manifest_row.get("path", "")
            manifest_source = manifest_row.get("source_script", "")
            if manifest_path != png_rel:
                messages.append(
                    CheckMessage(
                        "fail",
                        f"Manifest path mismatch for {figure_id}: {manifest_path} != {png_rel}.",
                    )
                )
            if "ai-generated" in manifest_source.lower():
                messages.append(
                    CheckMessage(
                        "warn",
                        f"Manifest still marks {figure_id} as AI-generated concept figure.",
                    )
                )
            if expected_source and expected_source not in manifest_source:
                messages.append(
                    CheckMessage(
                        "warn",
                        f"Manifest source for {figure_id} does not include expected source: {expected_source}.",
                    )
                )

        checks.append(
            {
                "figure_id": figure_id,
                "png": png_rel,
                "svg": svg_rel,
                "json": json_rel,
                "dimensions": f"{dimensions[0]}x{dimensions[1]}" if dimensions else "unknown",
                "manifest_source": manifest_source,
            }
        )

    if not messages:
        messages.append(CheckMessage("pass", "All diagram checks passed."))

    return DiagramCheckResult(messages=messages, diagram_checks=checks)


def write_diagram_qa_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> DiagramCheckResult:
    result = run_diagram_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "diagram_qa_report.md",
        "Diagram QA Report",
        render_diagram_qa_markdown(result),
    )
    return result


def render_diagram_qa_markdown(result: DiagramCheckResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
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
            "## Diagram Sources",
            "",
            "| Figure | PNG | SVG | JSON | Dimensions | Manifest Source |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for check in result.diagram_checks:
        lines.append(
            f"| {check['figure_id']} | {check['png']} | {check['svg']} | {check['json']} | {check['dimensions']} | {check['manifest_source']} |"
        )
    return lines
