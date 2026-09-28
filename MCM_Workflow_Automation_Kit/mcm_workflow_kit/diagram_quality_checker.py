"""Diagram-quality gate.

`diagram_checker` only proves the PNG/SVG/JSON exist and are big enough. That let
ProbA's first figure pass while being seven bare boxes (label/x/y only) with no bands,
no node content, no equations, no validation/output layers. This node inspects the
structured JSON *content* so a "boxes and arrows" diagram cannot pass.

Calibrated so the dense ProbC workflow figure passes and the thin ProbA one fails.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .diagram_checker import is_user_diagram, user_receipt_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


CONTENT_FIELDS = ("body", "description", "detail", "artifact", "equation", "formula", "content", "body_text")
BAND_KEYS = ("stages", "layers", "bands", "columns", "phases")

# Category -> keywords. A strong first figure covers most of these layers.
CATEGORY_KEYWORDS = {
    "data_input": ["data", "input", "raw", "dataset", "observation", "measurement"],
    "parameter": ["parameter", "estimat", "calibrat", "fit", "identif"],
    "model_state": ["model", "state", "equation", "variable", "ode", "dynamic", "constraint", "governing"],
    "solver": ["solver", "numeric", "integrat", "optimi", "simulat", "runge", "euler", "solve"],
    "validation": ["validat", "uncertaint", "sensitiv", "diagnostic", "baseline", "verif"],
    "output": ["output", "recommend", "result", "deliver", "policy", "decision", "predict"],
}


@dataclass(frozen=True)
class DiagramQualityResult:
    messages: list[CheckMessage]
    figures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def count_bands(data: dict[str, Any]) -> int:
    for key in BAND_KEYS:
        value = data.get(key)
        if isinstance(value, list) and value:
            return len(value)
    # Fall back to distinct stage/layer labels declared on nodes.
    nodes = data.get("nodes", [])
    labels = set()
    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict):
                for attr in ("stage", "layer", "band", "phase", "column"):
                    if node.get(attr):
                        labels.add(str(node[attr]))
    return len(labels)


def content_fraction(nodes: list[Any]) -> float:
    if not nodes:
        return 0.0
    with_content = 0
    for node in nodes:
        if isinstance(node, dict) and any(str(node.get(f, "")).strip() for f in CONTENT_FIELDS):
            with_content += 1
    return with_content / len(nodes)


def covered_categories(blob: str) -> list[str]:
    lowered = blob.lower()
    covered = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            covered.append(category)
    return covered


def has_feedback_edge(data: dict[str, Any]) -> bool:
    edges = data.get("edges", [])
    if not isinstance(edges, list):
        return False
    for edge in edges:
        if isinstance(edge, dict) and (
            str(edge.get("kind", "")).lower() == "feedback"
            or str(edge.get("type", "")).lower() == "feedback"
        ):
            return True
    return False


def evaluate_diagram_json(
    figure_id: str,
    data: dict[str, Any],
    config: WorkflowConfig,
) -> tuple[list[CheckMessage], dict[str, Any]]:
    messages: list[CheckMessage] = []
    nodes = data.get("nodes", []) if isinstance(data.get("nodes"), list) else []
    edges = data.get("edges", []) if isinstance(data.get("edges"), list) else []
    n_nodes = len(nodes)
    n_bands = count_bands(data)
    frac = content_fraction(nodes)
    blob = json.dumps(data, ensure_ascii=False)
    categories = covered_categories(blob)

    if n_nodes < config.diagram_min_nodes:
        messages.append(
            CheckMessage(
                "fail",
                f"{figure_id}: only {n_nodes} nodes (min {config.diagram_min_nodes}). "
                f"A first figure this sparse reads as boxes-and-arrows.",
            )
        )
    if n_bands < config.diagram_min_bands:
        messages.append(
            CheckMessage(
                "fail",
                f"{figure_id}: only {n_bands} grouped bands/stages (min {config.diagram_min_bands}). "
                f"Group the flow into labeled stages instead of floating boxes.",
            )
        )
    if frac < config.diagram_min_content_fraction:
        messages.append(
            CheckMessage(
                "fail",
                f"{figure_id}: only {frac:.0%} of nodes carry content "
                f"(body/artifact/equation); need >= {config.diagram_min_content_fraction:.0%}. "
                f"Nodes must say something, not just hold a label.",
            )
        )
    if len(categories) < config.diagram_min_categories:
        messages.append(
            CheckMessage(
                "warn",
                f"{figure_id}: covers {len(categories)} solution layers "
                f"({', '.join(categories) or 'none'}); aim for >= {config.diagram_min_categories} "
                f"of data/parameter/model/solver/validation/output.",
            )
        )
    if not has_feedback_edge(data):
        messages.append(
            CheckMessage("warn", f"{figure_id}: no feedback/iteration edge; workflows usually loop.")
        )

    summary = {
        "figure_id": figure_id,
        "nodes": n_nodes,
        "bands": n_bands,
        "content_fraction": round(frac, 2),
        "categories": ",".join(categories),
        "edges": len(edges),
    }
    return messages, summary


def evaluate_user_diagram(root: Path, figure_id: str, source: dict[str, Any]) -> tuple[list[CheckMessage], dict[str, Any]]:
    """A teammate's flowchart: the node/band/content checks target the Kit's JSON and do not
    apply. Surface what the import measured (text size after scaling, height, aspect, rasters)
    as warnings; it is the team's drawing, so the team decides."""
    summary = {"figure_id": figure_id, "nodes": "-", "bands": "-", "content_fraction": 0.0,
               "categories": "user-supplied", "edges": "-"}
    receipt_path = user_receipt_path(root, source)
    if receipt_path is None or not receipt_path.is_file():
        return [], summary        # diagram_checker already reported the missing receipt
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return [], summary
    return [CheckMessage("warn", f"{figure_id}: {w}") for w in receipt.get("warnings", []) if isinstance(w, str)], summary


def run_diagram_quality_checks(
    project_root: str | Path,
    config: WorkflowConfig,
) -> DiagramQualityResult:
    root = Path(project_root).resolve()
    messages: list[CheckMessage] = []
    figures: list[dict[str, Any]] = []

    if not config.diagram_sources:
        messages.append(CheckMessage("warn", "No diagram sources configured for quality review."))
        return DiagramQualityResult(messages=messages, figures=figures)

    for source in config.diagram_sources:
        figure_id = str(source.get("figure_id", "(unnamed)"))
        if is_user_diagram(source):
            figure_messages, summary = evaluate_user_diagram(root, figure_id, source)
            messages.extend(figure_messages)
            figures.append(summary)
            continue
        json_rel = str(source.get("json", ""))
        if not json_rel:
            messages.append(
                CheckMessage("fail", f"{figure_id}: no structured JSON source configured.")
            )
            continue
        json_path = resolve_project_path(root, json_rel)
        if not json_path.exists():
            messages.append(
                CheckMessage("fail", f"{figure_id}: JSON source missing: {json_rel}")
            )
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            messages.append(CheckMessage("fail", f"{figure_id}: invalid JSON ({exc})."))
            continue
        if not isinstance(data, dict):
            messages.append(CheckMessage("fail", f"{figure_id}: JSON root is not an object."))
            continue
        figure_messages, summary = evaluate_diagram_json(figure_id, data, config)
        messages.extend(figure_messages)
        figures.append(summary)

    if not messages:
        messages.append(CheckMessage("pass", "Diagram quality checks passed."))

    return DiagramQualityResult(messages=messages, figures=figures)


def render_diagram_quality_markdown(result: DiagramQualityResult) -> list[str]:
    lines = [f"- Status: {result.status}", "", "## Messages", ""]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "| Figure | Nodes | Bands | Content | Categories | Edges |",
            "| --- | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for fig in result.figures:
        lines.append(
            f"| {fig['figure_id']} | {fig['nodes']} | {fig['bands']} | "
            f"{fig['content_fraction']:.0%} | {fig['categories']} | {fig['edges']} |"
        )
    return lines


def write_diagram_quality_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> DiagramQualityResult:
    result = run_diagram_quality_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "diagram_quality_report.md",
        "Diagram Quality Report",
        render_diagram_quality_markdown(result),
    )
    return result
