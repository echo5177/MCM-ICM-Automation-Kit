"""Visual-QA packet.

ProbA passed every deterministic check while looking bad on the page. No node ever
forced the PDF to be *seen*. This node renders the first pages of the PDF (and lists
critical figures) into a folder and writes a checklist, so the agent or a human must
actually look before claiming the paper is done.

It is a producer, not an aesthetic judge: rendering success = pass, missing PDF = fail,
missing renderer = warn. The aesthetic verdict is recorded by the judge_review_gate.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


VISUAL_CHECKLIST = [
    "Does page 1 look like a credible MCM Summary Sheet (not a generic title page)?",
    "Are there colored/red link boxes around the ToC or references?",
    "Are figures legible, with readable labels, axes, and units?",
    "Are tables full and aligned, without large empty regions?",
    "Is page density similar to a strong contest paper (no lecture-note whitespace)?",
    "Is the first workflow/model figure information-dense, not boxes-and-arrows?",
]


@dataclass(frozen=True)
class VisualQAResult:
    messages: list[CheckMessage]
    rendered_pages: list[str] = field(default_factory=list)
    critical_figures: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def render_pdf_pages(pdf_path: Path, out_dir: Path, pages: int) -> list[Path]:
    """Render the first `pages` pages to PNG using poppler's pdftoppm."""
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "page"
    subprocess.run(
        [
            "pdftoppm", "-png", "-r", "110",
            "-f", "1", "-l", str(pages),
            str(pdf_path), str(prefix),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return sorted(out_dir.glob("page*.png"))


def run_visual_qa(
    project_root: str | Path,
    config: WorkflowConfig,
) -> VisualQAResult:
    root = Path(project_root).resolve()
    pdf_path = resolve_project_path(root, config.paper_pdf)
    out_dir = resolve_project_path(root, config.visual_qa_dir)

    messages: list[CheckMessage] = []
    rendered: list[str] = []
    critical: list[str] = []

    # Critical figures: the configured diagram sources.
    for source in config.diagram_sources:
        png_rel = str(source.get("png", ""))
        if png_rel and resolve_project_path(root, png_rel).exists():
            critical.append(png_rel)

    if not pdf_path.exists():
        messages.append(CheckMessage("fail", f"PDF missing; cannot render for visual QA: {config.paper_pdf}"))
        return VisualQAResult(messages=messages, rendered_pages=rendered, critical_figures=critical)

    if shutil.which("pdftoppm") is None:
        messages.append(
            CheckMessage(
                "warn",
                "pdftoppm not found; render the PDF manually and inspect the first pages.",
            )
        )
        return VisualQAResult(messages=messages, rendered_pages=rendered, critical_figures=critical)

    pages = render_pdf_pages(pdf_path, out_dir, config.visual_qa_pages)
    if not pages:
        messages.append(CheckMessage("warn", "Renderer produced no page images."))
    else:
        rendered = [str(p.relative_to(root)) if p.is_absolute() else str(p) for p in pages]
        messages.append(
            CheckMessage(
                "pass",
                f"Rendered {len(pages)} PDF page(s) and {len(critical)} critical figure(s) for inspection.",
            )
        )
    return VisualQAResult(messages=messages, rendered_pages=rendered, critical_figures=critical)


def render_visual_qa_markdown(result: VisualQAResult) -> list[str]:
    lines = [f"- Status: {result.status}", "", "## Messages", ""]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    lines.extend(["", "## Rendered PDF pages", ""])
    if result.rendered_pages:
        lines.extend(f"- {p}" for p in result.rendered_pages)
    else:
        lines.append("- (none)")
    lines.extend(["", "## Critical figures", ""])
    if result.critical_figures:
        lines.extend(f"- {p}" for p in result.critical_figures)
    else:
        lines.append("- (none)")
    lines.extend(["", "## Inspection checklist", ""])
    lines.extend(f"- [ ] {item}" for item in VISUAL_CHECKLIST)
    return lines


def write_visual_qa_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> VisualQAResult:
    result = run_visual_qa(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "visual_qa_report.md",
        "Visual QA Packet",
        render_visual_qa_markdown(result),
    )
    return result
