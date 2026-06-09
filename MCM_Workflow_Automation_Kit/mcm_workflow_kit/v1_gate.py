from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


@dataclass(frozen=True)
class V1GateResult:
    messages: list[CheckMessage]
    node_rows: list[dict[str, Any]]
    known_warnings: list[str]

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def _node_rows(nodes: Sequence[object]) -> list[dict[str, Any]]:
    return [
        {
            "name": str(getattr(node, "name", "")),
            "status": str(getattr(node, "status", "")),
            "detail": str(getattr(node, "detail", "")),
        }
        for node in nodes
    ]


def _team_placeholders(project_root: Path, config: WorkflowConfig) -> list[str]:
    tex_path = resolve_project_path(project_root, config.paper_tex)
    if not tex_path.exists():
        return []
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    return [
        placeholder
        for placeholder in config.team_control_number_placeholders
        if placeholder and placeholder in text
    ]


def run_v1_gate(
    project_root: str | Path,
    config: WorkflowConfig,
    nodes: Sequence[object],
) -> V1GateResult:
    root = Path(project_root).resolve()
    rows = _node_rows(nodes)
    messages: list[CheckMessage] = []
    known_warnings: list[str] = []

    failed_nodes = [row["name"] for row in rows if row["status"] == "fail"]
    warned_nodes = [row["name"] for row in rows if row["status"] == "warn"]

    if failed_nodes:
        messages.append(
            CheckMessage("fail", "V1 gate blocked by failed nodes: " + ", ".join(failed_nodes))
        )
    if warned_nodes:
        messages.append(
            CheckMessage(
                "warn",
                "V1 gate has classified warnings from nodes: " + ", ".join(warned_nodes),
            )
        )

    team_placeholders = _team_placeholders(root, config)
    if team_placeholders:
        known_warnings.append(
            "Team control number placeholder remains pending: "
            + ", ".join(team_placeholders)
        )

    paper_report = resolve_project_path(root, config.workflow_reports_dir) / "paper_qa_report.md"
    if paper_report.exists():
        report_text = paper_report.read_text(encoding="utf-8", errors="replace")
        for line in report_text.splitlines():
            if "above target" in line and "above hard limit" not in line:
                known_warnings.append(line.removeprefix("- WARN: ").strip())

    if not messages:
        messages.append(CheckMessage("pass", "V1 gate checks passed."))

    return V1GateResult(
        messages=messages,
        node_rows=rows,
        known_warnings=known_warnings,
    )


def write_v1_gate_report(
    project_root: str | Path,
    config: WorkflowConfig,
    nodes: Sequence[object],
) -> V1GateResult:
    result = run_v1_gate(project_root, config, nodes)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "v1_gate_report.md",
        "Kit v1.0 Gate Report",
        render_v1_gate_markdown(result),
    )
    return result


def render_v1_gate_markdown(result: V1GateResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        "- Gate rule: no failed nodes; warnings must be classified and actionable.",
        "",
        "## Messages",
        "",
    ]
    lines.extend(
        f"- {message.level.upper()}: {message.message}" for message in result.messages
    )
    lines.extend(["", "## Known Warnings", ""])
    if result.known_warnings:
        lines.extend(f"- {warning}" for warning in result.known_warnings)
    else:
        lines.append("- None.")
    lines.extend(["", "## Node Summary", "", "| Node | Status | Detail |", "| --- | --- | --- |"])
    for row in result.node_rows:
        lines.append(f"| {row['name']} | {row['status']} | {row['detail']} |")
    return lines
