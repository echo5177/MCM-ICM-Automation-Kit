"""AI use: the log kept while working against the report the paper prints.

COMAP's policy (v102025) asks teams to "be open and honest about all their uses of AI
tools, including embedded AI" (translation software, code copilots, auto-complete), to name
each tool with its version and purpose in a "Report on Use of AI Tools" after the report, to
cite the tools inline and in the reference list, and to verify what the tools produced. It
adds: "COMAP will take appropriate action when we identify submissions likely prepared with
undisclosed use of such tools."

A report written from memory in the last hour is where disclosure goes wrong. The CUMCM 2026
post-mortem found three mismatches between the declaration and the record: a tool that had
been used and was not listed, "drafting" softened to "polishing", and a claim about who led
the modeling that the files did not support. So the log is kept as the work happens
(`reports/ai_use_log.csv`), `scripts/build_ai_report.py` turns it into the report, and this
node checks the printed report against it.

| column | meaning |
| --- | --- |
| `tool` | product and vendor, e.g. "Anthropic Claude Code" |
| `version` | model name or the date of use |
| `purpose` | what it was used for, in the words the report will print |
| `used_for` | where: which code, sections, figures |
| `verified_by` | how a team member checked the output |
| `query`, `output` | optional: the wording sent and what came back, when the report quotes them |

What it cannot do: know about a tool nobody logged. The log is only as honest as its keeper.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .pdf_text import page_texts
from .reporting import CheckMessage, status_from_messages, write_markdown_report
from .submission_checker import ai_report_start, references_start


REQUIRED_COLUMNS = ("tool", "version", "purpose", "used_for", "verified_by")
VENDOR_WORDS = {"openai", "anthropic", "google", "microsoft", "github", "baidu", "alibaba",
                "tencent", "version", "model", "tool", "tools", "code", "chat", "desktop", "with"}


@dataclass(frozen=True)
class AIUseResult:
    messages: list[CheckMessage]
    tools: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def _stage(config: WorkflowConfig, message: str) -> CheckMessage:
    return CheckMessage("fail" if config.is_final else "warn", message)


def read_log(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = [name.strip() for name in (reader.fieldnames or [])]
        rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    rows = [row for row in rows if row.get("tool") and not row["tool"].startswith(("[", "#"))]
    return rows, missing


def name_tokens(tool: str) -> list[str]:
    """The words that identify a tool: 'Anthropic Claude Code' -> ['claude']."""
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", tool)]
    distinctive = [w for w in words if w not in VENDOR_WORDS]
    return distinctive or words


def named_in(tool: str, text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in name_tokens(tool))


def run_ai_use_checks(project_root: str | Path, config: WorkflowConfig) -> AIUseResult:
    root = Path(project_root).resolve()
    log_path = resolve_project_path(root, config.ai_use_log_file)
    pdf_path = resolve_project_path(root, config.paper_pdf)
    pages = page_texts(pdf_path) if pdf_path.is_file() else []
    ai_start = ai_report_start(pages) if pages else None

    if not config.ai_tools_used:
        if ai_start:
            return AIUseResult([CheckMessage(
                "warn", "The config says no AI tool was used, but the paper has a Report on Use of AI.")])
        return AIUseResult([CheckMessage("pass", "The config declares that no AI tool was used.")])

    if not log_path.is_file():
        return AIUseResult([_stage(
            config,
            f"No AI use log ({config.ai_use_log_file}). Log each tool as it is used, embedded "
            f"ones included (translation, copilots), then build the report from the log. COMAP "
            f"acts on submissions 'likely prepared with undisclosed use of such tools'.",
        )])
    rows, missing = read_log(log_path)
    if missing:
        return AIUseResult([CheckMessage(
            "fail", f"{config.ai_use_log_file} lacks column(s): {', '.join(missing)}.")])
    if not rows:
        return AIUseResult([_stage(
            config, f"{config.ai_use_log_file} has no entry yet. This Kit is run with an AI agent; "
                    f"its first entry is that agent.")])

    messages: list[CheckMessage] = []
    tools: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = tools.setdefault(row["tool"], {"tool": row["tool"], "version": row["version"],
                                               "purposes": [], "in_report": "", "in_references": ""})
        if row["purpose"]:
            entry["purposes"].append(row["purpose"])
        else:
            messages.append(_stage(config, f"{row['tool']}: an entry has no purpose."))
        if not row["version"]:
            messages.append(CheckMessage(
                "warn", f"{row['tool']}: no version. The policy asks which model was used."))
        if not row["verified_by"]:
            messages.append(CheckMessage(
                "warn", f"{row['tool']} ({row['purpose'] or 'no purpose'}): `verified_by` is empty. "
                        f"Teams are required to verify the accuracy of what a tool generates."))

    if pages:
        if ai_start is None:
            messages.append(_stage(
                config, f"The log lists {len(tools)} AI tool(s) and the paper has no 'Report on Use "
                        f"of AI' after its references."))
        else:
            report_text = "\n".join(pages[ai_start - 1:])
            refs = references_start(pages)
            reference_text = "\n".join(pages[refs - 1:ai_start - 1]) if refs and refs < ai_start else ""
            for name, entry in tools.items():
                entry["in_report"] = "yes" if named_in(name, report_text) else "no"
                if entry["in_report"] == "no":
                    messages.append(_stage(
                        config, f"{name} is in the log and not in the Report on Use of AI. Rebuild "
                                f"the report from the log (scripts/build_ai_report.py)."))
                if reference_text:
                    entry["in_references"] = "yes" if named_in(name, reference_text) else "no"
                    if entry["in_references"] == "no":
                        messages.append(CheckMessage(
                            "warn", f"{name} is not in the reference list. The policy: 'Use inline "
                                    f"citations and list all AI tools used in the reference section'."))

    if not any(m.level in {"fail", "warn"} for m in messages):
        messages.append(CheckMessage("pass", f"All {len(tools)} logged AI tool(s) are disclosed."))
    return AIUseResult(messages=messages, tools=list(tools.values()))


def render_ai_use_markdown(result: AIUseResult) -> list[str]:
    lines = [f"- Status: {result.status}", ""]
    if result.tools:
        lines += ["| Tool | Version | Purposes | In the report | In the references |",
                  "| --- | --- | --- | --- | --- |"]
        for tool in result.tools:
            purposes = "; ".join(dict.fromkeys(tool["purposes"]))
            lines.append(f"| {tool['tool']} | {tool['version']} | {purposes[:120]} | "
                         f"{tool['in_report']} | {tool['in_references']} |")
        lines.append("")
    lines += ["## Messages", ""]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    return lines


def write_ai_use_report(project_root: str | Path, config: WorkflowConfig) -> AIUseResult:
    result = run_ai_use_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(reports_dir / "ai_use_report.md", "AI Use Report Check",
                          render_ai_use_markdown(result))
    return result


LATEX_SPECIAL = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                 "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}"}


def latex_escape(text: str) -> str:
    return "".join(LATEX_SPECIAL.get(ch, ch) for ch in text)


def build_report_tex(rows: list[dict[str, str]]) -> str:
    """The Report on Use of AI Tools in COMAP's example layout, one item per tool."""
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault((row["tool"], row["version"]), []).append(row)
    lines = ["% Built from reports/ai_use_log.csv by scripts/build_ai_report.py. Edit the log, not this file.",
             r"\begin{enumerate}"]
    for (tool, version), entries in grouped.items():
        head = latex_escape(tool) + (f" ({latex_escape(version)})" if version else "")
        lines.append(rf"  \item \textbf{{{head}}}")
        lines.append(r"  \begin{itemize}")
        for entry in entries:
            text = latex_escape(entry["purpose"])
            if entry.get("used_for"):
                text += ": " + latex_escape(entry["used_for"])
            if entry.get("verified_by"):
                text += ". Checked by the team: " + latex_escape(entry["verified_by"])
            lines.append(rf"    \item {text}.")
            if entry.get("query"):
                lines.append(rf"    \item Query: {latex_escape(entry['query'])}")
            if entry.get("output"):
                lines.append(rf"    \item Output: {latex_escape(entry['output'])}")
        lines.append(r"  \end{itemize}")
    lines.append(r"\end{enumerate}")
    return "\n".join(lines) + "\n"
