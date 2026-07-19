from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import traceback
from typing import Callable

from .config import KIT_ROOT, WorkflowConfig, load_config, resolve_project_path
from .data_auditor import write_data_audit_outputs
from .diagram_checker import write_diagram_qa_report
from .diagram_quality_checker import write_diagram_quality_report
from .judge_review_gate import write_judge_review_gate_report
from .mcm_format_checker import write_mcm_format_report
from .paper_qa import write_paper_qa_report
from .reporting import write_markdown_report
from .result_checker import write_result_check_report
from .review_rounds import write_review_trajectory_report
from .source_checker import write_source_vetting_report
from .source_role_checker import write_source_role_report
from .v1_gate import write_v1_gate_report
from .v2_gate import write_v2_gate_report
from .visual_qa_packet import write_visual_qa_report


@dataclass
class NodeRun:
    name: str
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    detail: str
    stdout_log: str = ""
    stderr_log: str = ""


@dataclass
class WorkflowRun:
    mode: str
    project_root: str
    run_dir: str
    started_at: str
    finished_at: str
    status: str
    nodes: list[NodeRun]


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node_status_from_result(result: object) -> str:
    return str(getattr(result, "status", "pass"))


def run_callable_node(
    name: str,
    func: Callable[[], object],
    run_dir: Path,
) -> NodeRun:
    started = _utc_now()
    start_time = time.perf_counter()
    stderr_log = run_dir / f"{name}.stderr.log"
    stdout_log = run_dir / f"{name}.stdout.log"
    try:
        result = func()
        status = _node_status_from_result(result)
        detail = f"{name} completed with status {status}."
        stdout_log.write_text(detail + "\n", encoding="utf-8")
        stderr_log.write_text("", encoding="utf-8")
    except Exception:
        status = "fail"
        detail = f"{name} raised an exception."
        stdout_log.write_text("", encoding="utf-8")
        stderr_log.write_text(traceback.format_exc(), encoding="utf-8")
    finished = _utc_now()
    duration = time.perf_counter() - start_time
    return NodeRun(
        name=name,
        status=status,
        started_at=started,
        finished_at=finished,
        duration_seconds=round(duration, 3),
        detail=detail,
        stdout_log=str(stdout_log),
        stderr_log=str(stderr_log),
    )


def run_external_command_node(
    name: str,
    command: list[str],
    cwd: str | Path,
    run_dir: Path,
) -> NodeRun:
    started = _utc_now()
    start_time = time.perf_counter()
    stdout_log = run_dir / f"{name}.stdout.log"
    stderr_log = run_dir / f"{name}.stderr.log"
    completed = subprocess.run(
        command,
        cwd=Path(cwd),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout_log.write_text(completed.stdout or "", encoding="utf-8")
    stderr_log.write_text(completed.stderr or "", encoding="utf-8")
    status = "pass" if completed.returncode == 0 else "fail"
    finished = _utc_now()
    duration = time.perf_counter() - start_time
    return NodeRun(
        name=name,
        status=status,
        started_at=started,
        finished_at=finished,
        duration_seconds=round(duration, 3),
        detail=f"Command exited with code {completed.returncode}.",
        stdout_log=str(stdout_log),
        stderr_log=str(stderr_log),
    )


def render_workflow_summary(run: WorkflowRun) -> list[str]:
    lines = [
        f"- Status: {run.status}",
        f"- Mode: {run.mode}",
        f"- Project root: {run.project_root}",
        f"- Run directory: {run.run_dir}",
        f"- Started: {run.started_at}",
        f"- Finished: {run.finished_at}",
        "",
        "## Nodes",
        "",
        "| Node | Status | Duration | Detail |",
        "| --- | --- | ---: | --- |",
    ]
    for node in run.nodes:
        lines.append(
            f"| {node.name} | {node.status} | {node.duration_seconds:.3f}s | {node.detail} |"
        )
    return lines


def run_workflow(
    project_root: str | Path,
    mode: str = "check",
    config_path: str | Path | None = None,
) -> WorkflowRun:
    if mode not in {"check", "full"}:
        raise ValueError(f"Unsupported workflow mode: {mode}")

    config = load_config(config_path or KIT_ROOT / "workflow_config.json")
    root = Path(project_root).resolve()
    run_dir = KIT_ROOT / "runs" / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = resolve_project_path(root, config.workflow_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    started = _utc_now()
    nodes: list[NodeRun] = []

    if mode == "full":
        nodes.append(
            run_external_command_node(
                "project_pipeline",
                config.project_pipeline_command,
                root,
                run_dir,
            )
        )

    nodes.append(
        run_callable_node(
            "source_checker",
            lambda: write_source_vetting_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "source_role_checker",
            lambda: write_source_role_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "data_auditor",
            lambda: write_data_audit_outputs(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "result_checker",
            lambda: write_result_check_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "diagram_checker",
            lambda: write_diagram_qa_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "diagram_quality_checker",
            lambda: write_diagram_quality_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "paper_qa",
            lambda: write_paper_qa_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "mcm_format_checker",
            lambda: write_mcm_format_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "visual_qa_packet",
            lambda: write_visual_qa_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "judge_review_gate",
            lambda: write_judge_review_gate_report(root, config),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "v1_gate",
            lambda: write_v1_gate_report(root, config, nodes),
            run_dir,
        )
    )
    nodes.append(
        run_callable_node(
            "v2_gate",
            lambda: write_v2_gate_report(root, config, list(nodes)),
            run_dir,
        )
    )
    # Observability only: records the judge-review round and reports the score
    # trajectory. Appended after the gates so it can never change a verdict; it
    # never emits `fail`.
    nodes.append(
        run_callable_node(
            "review_trajectory",
            lambda: write_review_trajectory_report(root, config),
            run_dir,
        )
    )

    finished = _utc_now()
    status = "fail" if any(node.status == "fail" for node in nodes) else "pass"
    run = WorkflowRun(
        mode=mode,
        project_root=str(root),
        run_dir=str(run_dir),
        started_at=started,
        finished_at=finished,
        status=status,
        nodes=nodes,
    )

    (run_dir / "state.json").write_text(
        json.dumps(asdict(run), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_markdown_report(
        reports_dir / "workflow_run_summary.md",
        "Workflow Run Summary",
        render_workflow_summary(run),
    )
    return run
