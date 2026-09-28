"""Kit v2.0 gate.

v1_gate only checked that nodes did not fail. v2_gate is the consolidated
contest-readiness verdict over the stronger quality nodes (mcm_format_checker,
source_role_checker, diagram_quality_checker, visual_qa_packet, judge_review_gate).

The teeth are mostly in those nodes (they emit `fail`, and the orchestrator marks the
whole run failed if any node fails). v2_gate makes the verdict explicit and lists the
exact blocking reasons so a low-quality paper cannot be quietly wrapped as "passed".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


# Nodes whose failure blocks contest readiness.
QUALITY_NODES = (
    "mcm_format_checker",
    "submission_checker",
    "source_role_checker",
    "diagram_quality_checker",
    "experiment_audit",
    "visual_qa_packet",
    "judge_review_gate",
)


@dataclass(frozen=True)
class V2GateResult:
    messages: list[CheckMessage]
    node_rows: list[dict[str, Any]] = field(default_factory=list)
    contest_ready: bool = False
    stage: str = "final"

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


def run_v2_gate(
    project_root: str | Path,
    config: WorkflowConfig,
    nodes: Sequence[object],
) -> V2GateResult:
    rows = _node_rows(nodes)
    by_name = {row["name"]: row for row in rows}
    messages: list[CheckMessage] = []

    failed = [row["name"] for row in rows if row["status"] == "fail"]
    warned = [row["name"] for row in rows if row["status"] == "warn"]

    # Quality nodes must have actually run.
    missing_quality = [name for name in QUALITY_NODES if name not in by_name]
    if missing_quality:
        messages.append(
            CheckMessage(
                "fail",
                "v2 gate is missing required quality nodes: " + ", ".join(missing_quality),
            )
        )

    failed_quality = [name for name in QUALITY_NODES if by_name.get(name, {}).get("status") == "fail"]
    if failed_quality:
        messages.append(
            CheckMessage(
                "fail",
                "Contest-quality nodes failed: " + ", ".join(failed_quality),
            )
        )

    other_failed = [name for name in failed if name not in QUALITY_NODES]
    if other_failed:
        messages.append(
            CheckMessage("fail", "Other nodes failed: " + ", ".join(other_failed))
        )

    if warned:
        messages.append(
            CheckMessage("warn", "Nodes with warnings: " + ", ".join(warned))
        )

    contest_ready = not failed and not missing_quality
    if contest_ready and not any(m.level == "fail" for m in messages):
        messages.append(CheckMessage("pass", "Contest-readiness gate passed."))

    if not config.is_final:
        # A draft gets the list of what would block, never a verdict.
        messages = [CheckMessage(
            "warn",
            "release_stage=draft: no contest-readiness verdict on a draft. Items below "
            "marked (blocks at final) must be cleared after switching to final.",
        )] + [
            CheckMessage("warn", f"(blocks at final) {m.message}") if m.level == "fail" else m
            for m in messages if m.level != "pass"
        ]
        return V2GateResult(messages=messages, node_rows=rows, contest_ready=False, stage="draft")

    return V2GateResult(messages=messages, node_rows=rows, contest_ready=contest_ready)


def render_v2_gate_markdown(result: V2GateResult) -> list[str]:
    if result.stage == "draft":
        verdict = "DRAFT (no contest-readiness verdict on a draft)"
    else:
        verdict = "CONTEST-READY" if result.contest_ready else "NOT READY"
    lines = [
        f"- Status: {result.status}",
        f"- Verdict: {verdict}",
        "- Gate rule: all quality nodes present and passing; no failed nodes anywhere.",
        "",
        "## Messages",
        "",
    ]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    lines.extend(["", "## Node Summary", "", "| Node | Status | Detail |", "| --- | --- | --- |"])
    for row in result.node_rows:
        lines.append(f"| {row['name']} | {row['status']} | {row['detail']} |")
    return lines


def write_v2_gate_report(
    project_root: str | Path,
    config: WorkflowConfig,
    nodes: Sequence[object],
) -> V2GateResult:
    result = run_v2_gate(project_root, config, nodes)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "v2_gate_report.md",
        "Kit v2.0 Gate Report",
        render_v2_gate_markdown(result),
    )
    return result
