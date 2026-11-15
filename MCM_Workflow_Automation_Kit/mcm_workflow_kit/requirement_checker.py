"""Requirement table: every requirement of the problem, where it is answered, and the answer.

COMAP defines the award levels by this. Successful Participant: "incomplete responses to all
or some requirements". Honorable Mention: "addressing all problem requirements" with sound,
supported processes. Meritorious: all requirements addressed "in a clear, well-supported,
well-organized, and well-presented manner". The judges' advice says the same from the other
side: "Answer all the required parts and make it clear that you have done so", "Make it
clear where in the paper the answers are", and "papers missing several elements are
eliminated quickly".

Nothing in the Kit checked it. The format gate looked for sections every paper has
(Assumptions, Sensitivity Analysis); the judge review scored categories. The 2026 MCM A
entry promised an analysis in its Summary that its body no longer contained, and the CUMCM
2026 entry scattered the evidence for its most heavily weighted question across four
chapters and never said what that question turned on.

The table is `reports/requirements.csv`, one row per requirement of the problem statement:

| column | what goes in it |
| --- | --- |
| `req_id` | R1, R2, ... in the problem's order |
| `requirement` | the requirement in the problem's own words |
| `kind` | `model`, `analysis`, or `deliverable` (a letter, memo or one-page article) |
| `turns_on` | one plain sentence: the trade-off or quantity that decides the answer. Written by a person, before any model exists |
| `expected` | what you expect the answer to look like, written before modeling |
| `answer` | the answer in one sentence, with its number and unit |
| `section` | the section that answers it: a number ("4.2") or part of its title |
| `evidence` | labels of the figures and tables that carry it, separated by `;` |
| `status` | `answered`, `partial`, or `open` |

It also reports body sections that no requirement points to, with their page count: pages
spent on something the problem did not ask for (CUMCM 2026: three such analyses in the body
while the key question got three pages).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .paper_structure import BACK_MATTER_RE, TocEntry, is_front_matter, toc_entries
from .pdf_text import page_texts
from .reporting import CheckMessage, status_from_messages, write_markdown_report
from .tex_source import read_tex_expanded


REQUIRED_COLUMNS = ("req_id", "requirement", "kind", "turns_on", "expected", "answer",
                    "section", "evidence", "status")
KINDS = {"model", "analysis", "deliverable"}
STATUSES = {"answered", "partial", "open"}
TEMPLATE_VALUE_RE = re.compile(r"^\s*(?:\[.*\]|<.*>|TODO\b.*|TBD\b.*)?\s*$", re.I | re.S)
NUMBER_RE = re.compile(r"(?<![A-Za-z\d.])\d+(?:,\d{3})*(?:\.\d+)?")
HEADING_RE = re.compile(
    r"\\(?P<level>(?:sub){0,2})section(?P<star>\*?)\s*\{(?P<title>[^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
)
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
DISPLAY_MATH_RE = re.compile(r"\\begin\{(?:equation|align|gather|multline)\*?\}|\\\[|\$\$")
SECTION_REF_RE = re.compile(r"^(?:section|sec\.?|§)?\s*(\d{1,2}(?:\.\d{1,2}){0,2})\s*$", re.I)


def _blank(value: str) -> bool:
    return bool(TEMPLATE_VALUE_RE.match(value or ""))


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


@dataclass(frozen=True)
class Requirement:
    req_id: str
    requirement: str
    kind: str
    turns_on: str
    expected: str
    answer: str
    section: str
    evidence: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class Section:
    number: str
    title: str
    level: int
    body: str
    page: int | None = None


@dataclass(frozen=True)
class RequirementResult:
    messages: list[CheckMessage]
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def read_requirements(path: Path) -> tuple[list[Requirement], list[str]]:
    """Rows of the table (template rows dropped) and the columns it lacks."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = [name.strip() for name in (reader.fieldnames or [])]
        raw = [{(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader]
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    rows = []
    for row in raw:
        if _blank(row.get("requirement", "")) and _blank(row.get("answer", "")):
            continue  # the template's example row, or an empty line
        rows.append(Requirement(
            req_id=row.get("req_id", ""),
            requirement=row.get("requirement", ""),
            kind=row.get("kind", "").lower(),
            turns_on=row.get("turns_on", ""),
            expected=row.get("expected", ""),
            answer=row.get("answer", ""),
            section=row.get("section", ""),
            evidence=tuple(part.strip() for part in re.split(r"[;,]", row.get("evidence", "")) if part.strip()),
            status=row.get("status", "").lower(),
        ))
    return rows, missing


def tex_sections(tex: str) -> list[Section]:
    """Numbered sections of the LaTeX source, numbered the way LaTeX numbers them."""
    stop = re.search(r"\\appendix\b", tex)
    end_doc = tex.find(r"\end{document}")
    limit = min(x for x in (stop.start() if stop else len(tex), end_doc if end_doc != -1 else len(tex)))
    headings = [m for m in HEADING_RE.finditer(tex) if m.start() < limit]
    counters = [0, 0, 0]
    sections = []
    for index, match in enumerate(headings):
        level = len(match.group("level")) // 3
        body_end = headings[index + 1].start() if index + 1 < len(headings) else limit
        if match.group("star"):
            number = ""
        else:
            counters[level] += 1
            for deeper in range(level + 1, 3):
                counters[deeper] = 0
            number = ".".join(str(c) for c in counters[: level + 1])
        sections.append(Section(number, match.group("title").strip(), level, tex[match.end():body_end]))
    return sections


def toc_sections(entries: list[TocEntry]) -> list[Section]:
    return [Section(e.number, e.title, e.number.count("."), "", e.page) for e in entries]


def with_pages(sections: list[Section], entries: list[TocEntry]) -> list[Section]:
    pages = {entry.number: entry.page for entry in entries}
    return [Section(s.number, s.title, s.level, s.body, pages.get(s.number)) for s in sections]


def find_section(reference: str, sections: list[Section]) -> Section | None:
    """A section by its number ("4.2", "Section 4") or by part of its title."""
    by_number = SECTION_REF_RE.match(reference)
    if by_number:
        return next((s for s in sections if s.number == by_number.group(1)), None)
    wanted = _norm(reference)
    if len(wanted) < 3:
        return None
    return next((s for s in sections if wanted in _norm(s.title)), None)


def section_body(target: Section, sections: list[Section]) -> str:
    """The section's own text plus that of its subsections."""
    start = sections.index(target)
    body = target.body
    for later in sections[start + 1:]:
        if later.level <= target.level:
            break
        body += later.body
    return body


def answer_numbers(answer: str) -> list[str]:
    """Numbers in an answer worth looking for elsewhere: decimals and multi-digit values first."""
    found = [n.replace(",", "") for n in NUMBER_RE.findall(answer)]
    strong = [n for n in found if "." in n or len(n) >= 2]
    return strong or found


def number_on_page(number: str, page: str) -> bool:
    flat = page.replace(",", "")
    return bool(re.search(rf"(?<![\d.]){re.escape(number)}(?![\d]|\.\d)", flat))


def _stage(config: WorkflowConfig, message: str) -> CheckMessage:
    """A defect that blocks the submission build but is expected while drafting."""
    return CheckMessage("fail" if config.is_final else "warn", message)


def unreferenced_sections(sections: list[Section], targets: list[Section]) -> list[tuple[Section, int | None]]:
    """Top-level body sections no requirement points to (or into), with their page span."""
    top = [s for s in sections if s.level == 0 and s.number]
    used = {t.number.split(".")[0] for t in targets if t.number}
    out = []
    for index, section in enumerate(top):
        if section.number in used or is_front_matter(section.title) or BACK_MATTER_RE.search(section.title):
            continue
        following = top[index + 1] if index + 1 < len(top) else None
        span = None
        if section.page is not None and following is not None and following.page is not None:
            span = max(1, following.page - section.page)
        out.append((section, span))
    return out


def run_requirement_checks(project_root: str | Path, config: WorkflowConfig) -> RequirementResult:
    root = Path(project_root).resolve()
    table = resolve_project_path(root, config.requirements_file)
    messages: list[CheckMessage] = []

    if not table.is_file():
        return RequirementResult([_stage(
            config,
            f"No requirement table ({config.requirements_file}). List every requirement of the "
            f"problem statement, where the paper answers it and what the answer is. COMAP defines "
            f"Honorable Mention by 'addressing all problem requirements' and Successful "
            f"Participant by 'incomplete responses to all or some requirements'.",
        )])

    rows, missing_columns = read_requirements(table)
    if missing_columns:
        return RequirementResult([CheckMessage(
            "fail", f"{config.requirements_file} lacks column(s): {', '.join(missing_columns)}.")])
    if not rows:
        return RequirementResult([_stage(
            config,
            f"{config.requirements_file} has no requirement yet (only the template row). Read "
            f"the problem statement and enter each task, including any letter or memo it asks for.",
        )])

    tex_path = resolve_project_path(root, config.paper_tex)
    pdf_path = resolve_project_path(root, config.paper_pdf)
    entries = toc_entries(pdf_path) if pdf_path.is_file() else []
    tex = read_tex_expanded(tex_path, root) if tex_path.is_file() else ""
    sections = with_pages(tex_sections(tex), entries) if tex else toc_sections(entries)
    labels = set(LABEL_RE.findall(tex))
    pages = page_texts(pdf_path) if pdf_path.is_file() else []
    summary = pages[0] if pages else ""

    seen: set[str] = set()
    targets: list[Section] = []
    report_rows: list[dict[str, Any]] = []
    for row in rows:
        rid = row.req_id or "(no id)"
        if not row.req_id or row.req_id in seen:
            messages.append(CheckMessage("fail", f"{rid}: req_id is missing or used twice."))
        seen.add(row.req_id)
        if row.kind not in KINDS:
            messages.append(CheckMessage(
                "warn", f"{rid}: kind '{row.kind}' is not one of {', '.join(sorted(KINDS))}."))
        if row.status not in STATUSES:
            messages.append(CheckMessage(
                "fail", f"{rid}: status '{row.status}' is not one of {', '.join(sorted(STATUSES))}."))

        if row.kind != "deliverable" and _blank(row.turns_on):
            messages.append(_stage(
                config,
                f"{rid}: `turns_on` is empty. Say in one plain sentence what this requirement "
                f"turns on (the trade-off, the deciding quantity, the ratio the statement gives). "
                f"A person writes it, before the model.",
            ))
        if row.kind != "deliverable" and _blank(row.expected):
            messages.append(CheckMessage(
                "warn",
                f"{rid}: `expected` is empty. Write what you expect before modeling; a result "
                f"that differs from it is either a finding or a bug, and both need a sentence.",
            ))

        target = None
        in_summary: bool | None = None
        if row.status == "open":
            messages.append(_stage(
                config, f"{rid} is open: '{row.requirement[:80]}'. Every requirement needs an answer; "
                        f"a partial one is accepted by COMAP and costs the award level."))
        else:
            if row.status == "partial":
                messages.append(CheckMessage(
                    "warn", f"{rid} is only partly answered: '{row.requirement[:80]}'."))
            if _blank(row.answer):
                messages.append(_stage(
                    config, f"{rid}: `answer` is empty. State the answer in one sentence with its number."))
            elif row.kind != "deliverable" and not NUMBER_RE.search(row.answer):
                messages.append(CheckMessage(
                    "warn", f"{rid}: the answer carries no number: '{row.answer[:80]}'. Judges ask "
                            f"for results stated clearly and a precise recommendation."))

            if _blank(row.section):
                messages.append(_stage(config, f"{rid}: `section` is empty. Name the section that answers it."))
            elif sections:
                target = find_section(row.section, sections)
                if target is None:
                    messages.append(_stage(
                        config, f"{rid}: no section '{row.section}' in the paper. Judges ask that it "
                                f"be clear where each answer is."))
                else:
                    targets.append(target)

            if tex:
                gone = [label for label in row.evidence if label not in labels]
                if gone:
                    messages.append(_stage(
                        config, f"{rid}: evidence label(s) not in the paper: {', '.join(gone)}. A "
                                f"figure or table that was cut takes the requirement's support with it."))
            if not row.evidence and row.kind != "deliverable":
                messages.append(CheckMessage(
                    "warn", f"{rid}: no figure or table is listed as evidence."))

            numbers = answer_numbers(row.answer)
            if summary and numbers and row.kind != "deliverable":
                in_summary = any(number_on_page(n, summary) for n in numbers)
                if not in_summary:
                    messages.append(CheckMessage(
                        "warn",
                        f"{rid}: none of the answer's numbers ({', '.join(numbers[:4])}) is on the "
                        f"Summary Sheet. The Summary should carry the result of every requirement.",
                    ))

            if row.kind == "deliverable" and target is not None and tex:
                body = section_body(target, sections)
                if DISPLAY_MATH_RE.search(body):
                    messages.append(CheckMessage(
                        "warn", f"{rid}: the {target.title} contains displayed equations. Judges ask "
                                f"that a letter or memo give bottom-line results, not methods or equations."))
                if len(NUMBER_RE.findall(body)) < 2:
                    messages.append(CheckMessage(
                        "warn", f"{rid}: the {target.title} carries fewer than two numbers; it should "
                                f"state the model's results for its reader."))

        report_rows.append({
            "req_id": rid, "status": row.status, "kind": row.kind,
            "section": (f"{target.number} {target.title}".strip() if target else row.section or "-"),
            "page": target.page if target and target.page else "",
            "in_summary": {True: "yes", False: "no", None: ""}[in_summary],
            "answer": row.answer,
        })

    stray = unreferenced_sections(sections, targets) if targets else []
    if stray:
        listed = "; ".join(
            f"'{section.title}'" + (f" ({span} page{'s' if span != 1 else ''})" if span else "")
            for section, span in stray
        )
        messages.append(CheckMessage(
            "warn",
            f"Body section(s) no requirement points to: {listed}. Either a requirement is "
            f"answered there and the table should say so, or these pages answer nothing the "
            f"problem asked.",
        ))

    if not any(m.level in {"fail", "warn"} for m in messages):
        messages.append(CheckMessage(
            "pass", f"All {len(rows)} requirements are answered, located and on the Summary Sheet."))
    return RequirementResult(messages=messages, rows=report_rows)


def render_requirement_markdown(result: RequirementResult) -> list[str]:
    lines = [f"- Status: {result.status}", ""]
    if result.rows:
        lines += ["| Requirement | Status | Kind | Answered in | Page | On Summary Sheet | Answer |",
                  "| --- | --- | --- | --- | ---: | --- | --- |"]
        for row in result.rows:
            answer = str(row["answer"]).replace("|", "/")
            lines.append(f"| {row['req_id']} | {row['status']} | {row['kind']} | {row['section']} | "
                         f"{row['page']} | {row['in_summary']} | {answer[:110]} |")
        lines.append("")
    lines += ["## Messages", ""]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    return lines


def write_requirement_report(project_root: str | Path, config: WorkflowConfig) -> RequirementResult:
    result = run_requirement_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "requirement_report.md",
        "Requirement Report",
        render_requirement_markdown(result),
    )
    return result
