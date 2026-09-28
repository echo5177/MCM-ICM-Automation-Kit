from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report
from .tex_source import read_tex_expanded


PAGES_RE = re.compile(r"^Pages:\s+(?P<pages>\d+)\s*$", re.MULTILINE)
LATEX_FAILURE_PATTERNS = [
    "Undefined control sequence",
    "Emergency stop",
    "Fatal error",
    "! LaTeX Error",
]
LATEX_WARNING_PATTERNS = [
    "LaTeX Warning",
    "Overfull",
    "Undefined references",
    "Label(s) may have changed",
    "Rerun to get",
    "Rerun LaTeX",
]


@dataclass(frozen=True)
class PaperQAResult:
    messages: list[CheckMessage]
    pages: int | None

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def parse_pdfinfo_pages(output: str) -> int | None:
    match = PAGES_RE.search(output)
    if not match:
        return None
    return int(match.group("pages"))


def run_pdfinfo(pdf_path: str | Path) -> tuple[int | None, str]:
    completed = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        return None, output
    return parse_pdfinfo_pages(output), output


def scan_latex_log(log_text: str) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    for line in log_text.splitlines():
        if line.startswith("Package: rerunfilecheck"):
            continue
        if any(pattern in line for pattern in LATEX_FAILURE_PATTERNS):
            messages.append(CheckMessage("fail", line.strip()))
        elif any(pattern in line for pattern in LATEX_WARNING_PATTERNS):
            messages.append(CheckMessage("warn", line.strip()))
    return messages


def check_required_tex_sections(tex_text: str) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    if "Summary" not in tex_text:
        messages.append(CheckMessage("fail", "Summary heading not found."))
    if r"\tableofcontents" not in tex_text:
        messages.append(CheckMessage("fail", "Table of contents command not found."))
    if "References" not in tex_text:
        messages.append(CheckMessage("fail", "References section not found."))
    return messages


def run_paper_qa(
    project_root: str | Path,
    config: WorkflowConfig,
) -> PaperQAResult:
    root = Path(project_root).resolve()
    pdf_path = resolve_project_path(root, config.paper_pdf)
    tex_path = resolve_project_path(root, config.paper_tex)
    log_path = resolve_project_path(root, config.latex_log)

    messages: list[CheckMessage] = []
    pages: int | None = None

    if not pdf_path.exists():
        messages.append(CheckMessage("fail", f"PDF missing: {config.paper_pdf}"))
    else:
        pages, pdfinfo_output = run_pdfinfo(pdf_path)
        if pages is None:
            messages.append(
                CheckMessage("fail", f"Could not parse pdfinfo output: {pdfinfo_output}")
            )
        else:
            counted = pages - config.ai_report_pages   # AI Use Report is not counted
            if counted > config.page_hard_limit:
                messages.append(
                    CheckMessage(
                        "fail",
                        f"{counted} counted pages (of {pages} total), above hard limit "
                        f"{config.page_hard_limit}.",
                    )
                )
            elif counted > config.page_target:
                messages.append(
                    CheckMessage(
                        "warn",
                        f"{counted} counted pages, above target {config.page_target}.",
                    )
                )
            elif counted < config.page_target:
                messages.append(
                    CheckMessage(
                        "warn",
                        f"{counted} counted pages, below target {config.page_target}.",
                    )
                )

    if not tex_path.exists():
        messages.append(CheckMessage("fail", f"LaTeX source missing: {config.paper_tex}"))
    else:
        tex_text = read_tex_expanded(tex_path, root)
        messages.extend(check_required_tex_sections(tex_text))

    if not log_path.exists():
        messages.append(CheckMessage("warn", f"LaTeX log missing: {config.latex_log}"))
    else:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        messages.extend(scan_latex_log(log_text))

    if not messages:
        messages.append(CheckMessage("pass", "Paper QA checks passed."))

    return PaperQAResult(messages=messages, pages=pages)


def write_paper_qa_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> PaperQAResult:
    result = run_paper_qa(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "paper_qa_report.md",
        "Paper QA Report",
        render_paper_qa_markdown(result),
    )
    return result


def render_paper_qa_markdown(result: PaperQAResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Pages: {result.pages if result.pages is not None else 'unknown'}",
        "",
        "## Messages",
        "",
    ]
    lines.extend(
        f"- {message.level.upper()}: {message.message}" for message in result.messages
    )
    return lines
