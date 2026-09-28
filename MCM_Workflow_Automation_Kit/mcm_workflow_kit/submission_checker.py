"""Submission integrity: what COMAP checks before a judge reads a word.

The 2026 Problem A entry this Kit grew out of was submitted with one control number on the
Summary Sheet and a different one in every page header. Its retrospective ranks that first
among the reasons for the result, ahead of every modelling issue: a judge who sees two team
numbers stops trusting the document. Nothing in the Kit checked it; the release checklist
only asked a human to tick "Summary and main report control numbers match".

COMAP's instructions (en: contest.comap.com, checked 2026-09-28 against the posted 2027
rules) that can be checked mechanically:

- "Each page of the solution must contain the team control number and the page number at
  the top of the page."
- "The solution must not contain any identifying information other than the team Control
  Number." (no student, advisor or institution names)
- "Papers must be typed in English, with a readable font of at least 12-point type."
- The Report on Use of AI goes "following the end of your report" and does not count toward
  the 25 pages.
- The PDF is named after the control number ("0000000.pdf") and "must be less than 25MB".

Calibrated on 112 O papers (2020+, `scripts/measure_award_corpus.py`): the Summary Sheet's
number appears on a median 100% of body pages (P10 94%); exactly one paper's summary number
differs from its headers (a one-digit typo); none shows a school name or an e-mail on page 1.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import re

from .config import WorkflowConfig, resolve_project_path
from .pdf_text import page_texts, pdf_metadata
from .reporting import CheckMessage, status_from_messages, write_markdown_report
from .tex_source import read_tex_expanded


CONTROL_RE = re.compile(r"(?<!\d)(\d{7})(?!\d)")
# The official template ships 1111111; COMAP's file-name example is 0000000.pdf.
OFFICIAL_PLACEHOLDERS = {"1111111", "0000000"}
CONTROL_LABEL_RE = re.compile(r"Control\s*Number[^\d]{0,40}(\d{7})", re.I | re.S)
AI_REPORT_RE = re.compile(r"Report\s+on\s+(?:the\s+)?Use\s+of\s+AI", re.I)
REFERENCES_RE = re.compile(r"(?m)^\s*(?:\d+\s*\.?\s*)?(?:References|Bibliography|Reference List)\s*$", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z][\w.]*")
SCHOOL_RE = re.compile(r"\b(?:University|College|Institute of Technology|Polytechnic)\b")
DOCCLASS_RE = re.compile(r"\\documentclass\s*\[([^\]]*)\]")
FONTSIZE_RE = re.compile(r"\\fontsize\s*\{\s*(\d+(?:\.\d+)?)\s*(?:pt)?\s*\}")


@dataclass(frozen=True)
class SubmissionResult:
    messages: list[CheckMessage]
    summary_number: str = ""
    header_number: str = ""
    counted_pages: int | None = None
    ai_report_start: int | None = None
    pages_missing_number: list[int] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def summary_control_number(first_page: str) -> str:
    labelled = CONTROL_LABEL_RE.search(first_page[:3000])
    if labelled:
        return labelled.group(1)
    found = CONTROL_RE.findall(first_page[:3000])
    return found[0] if found else ""


def header_control_number(pages: list[str]) -> str:
    """The number the page headers carry: the most common 7-digit number in the top lines."""
    top = Counter()
    for page in pages:
        head = "\n".join(line for line in page.splitlines()[:5])
        top.update(set(CONTROL_RE.findall(head)))
    return top.most_common(1)[0][0] if top else ""


TOC_HEAD_RE = re.compile(r"(?m)^\s*(?:Table of )?Contents\s*$")
DOT_LEADER_RE = re.compile(r"(?:\.\s){5,}")


def is_toc_page(page: str) -> bool:
    """A table-of-contents page: a Contents heading or a column of dot leaders.

    The ToC lists "References" and "Report on Use of AI" on lines of their own. ProbA's ToC
    runs onto page 3, and taking that line as the References heading cut the body off after
    page 2.
    """
    return bool(TOC_HEAD_RE.search(page)) or len(DOT_LEADER_RE.findall(page)) >= 3


def ai_report_start(pages: list[str]) -> int | None:
    """1-based page where the Report on Use of AI begins (never the summary or the ToC)."""
    for index, page in enumerate(pages):
        if index == 0 or is_toc_page(page):
            continue
        head = "\n".join(page.splitlines()[:12])
        if AI_REPORT_RE.search(head):
            return index + 1
    return None


def references_start(pages: list[str]) -> int | None:
    for index, page in enumerate(pages):
        if index == 0 or is_toc_page(page):
            continue
        if REFERENCES_RE.search(page):
            return index + 1
    return None


def check_control_numbers(pages: list[str], tex: str, config: WorkflowConfig,
                          counted: int) -> tuple[list[CheckMessage], str, str, list[int]]:
    messages: list[CheckMessage] = []
    summary = summary_control_number(pages[0]) if pages else ""
    body = pages[1:counted]
    header = header_control_number(body)
    if not summary:
        messages.append(CheckMessage(
            "fail", "No 7-digit team control number on the Summary Sheet (page 1)."))
        return messages, summary, header, []
    # The template's own placeholders are always checked: ProbA's config had emptied the list,
    # which silenced the warning instead of fixing the number.
    placeholders = set(config.team_control_number_placeholders) | OFFICIAL_PLACEHOLDERS
    if summary in placeholders:
        messages.append(CheckMessage(
            "fail" if config.is_final else "warn",
            f"The control number is still the template placeholder {summary}. Put the team's "
            f"real control number in \\Team (and team_control_number in the config).",
        ))
    if config.team_control_number and summary != config.team_control_number:
        messages.append(CheckMessage(
            "fail",
            f"Summary Sheet shows control number {summary}, the config says "
            f"{config.team_control_number}.",
        ))
    if header and header != summary:
        messages.append(CheckMessage(
            "fail",
            f"The Summary Sheet says {summary} but the page headers say {header}. Two team "
            f"numbers in one PDF read as a spliced or borrowed document; the 2026 ProbA "
            f"entry was submitted this way.",
        ))
    missing = [index + 2 for index, page in enumerate(body) if summary not in page]
    if header and header != summary:
        missing = []          # already reported as the mismatch; the pages carry the other number
    if body and missing:
        share = 1 - len(missing) / len(body)
        if share < 0.5:
            messages.append(CheckMessage(
                "fail",
                f"The control number is missing from {len(missing)} of {len(body)} counted pages. "
                f"COMAP: every page must carry the team control number and the page number at the "
                f"top (O papers: median 100% of pages).",
            ))
        elif missing:
            messages.append(CheckMessage(
                "warn",
                f"The control number is missing on page(s) {', '.join(map(str, missing[:10]))}"
                + (" ..." if len(missing) > 10 else "") + "; check their headers.",
            ))
    numbers_in_tex = sorted(set(CONTROL_RE.findall(tex)))
    stray = [n for n in numbers_in_tex if n != summary and n not in placeholders]
    if stray and any(n in page for n in stray for page in pages):
        messages.append(CheckMessage(
            "warn",
            f"Other 7-digit numbers also appear in the paper ({', '.join(stray[:4])}). If any is a "
            f"team number hard-coded somewhere (the AI report, a footer), use \\Team instead.",
        ))
    return messages, summary, header, missing


def check_page_roles(pages: list[str], config: WorkflowConfig) -> tuple[list[CheckMessage], int, int | None]:
    messages: list[CheckMessage] = []
    ai_start = ai_report_start(pages)
    refs = references_start(pages)
    counted = (ai_start - 1) if ai_start else len(pages)
    if ai_start and refs and ai_start < refs:
        messages.append(CheckMessage(
            "fail",
            f"The Report on Use of AI starts on page {ai_start}, before the References (page "
            f"{refs}). COMAP: add it following the end of your report.",
        ))
    if ai_start:
        measured_ai = len(pages) - ai_start + 1
        if measured_ai != config.ai_report_pages:
            messages.append(CheckMessage(
                "warn",
                f"The AI report runs {measured_ai} page(s) (pages {ai_start}-{len(pages)}) but "
                f"ai_report_pages is {config.ai_report_pages}; the page checks subtract the "
                f"configured value. Set it to {measured_ai}.",
            ))
    if counted > config.contest_page_limit:
        messages.append(CheckMessage(
            "fail",
            f"{counted} pages before the AI report, above the {config.contest_page_limit}-page "
            f"limit (it covers the Summary Sheet, contents, references, appendices and code).",
        ))
    return messages, counted, ai_start


def check_anonymity(pages: list[str], meta: dict[str, str], config: WorkflowConfig) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    text = "\n".join(pages)
    for term in (t.strip() for t in config.anonymity_terms):
        if term and term.lower() in text.lower():
            messages.append(CheckMessage(
                "fail", f"Identifying term '{term}' appears in the paper. Only the control number "
                        f"may identify the team."))
    for key in ("Author", "Title", "Subject", "Keywords"):
        value = meta.get(key, "")
        if value and any(t.strip() and t.strip().lower() in value.lower() for t in config.anonymity_terms):
            messages.append(CheckMessage("fail", f"PDF property {key}='{value}' identifies the team."))
    if meta.get("Author"):
        messages.append(CheckMessage(
            "warn", f"PDF Author is set ('{meta['Author']}'). Clear it (\\hypersetup{{pdfauthor={{}}}}); "
                    f"Word and some LaTeX setups write the account name there."))
    # Built-in patterns only where a legitimate paper never has them: the Summary Sheet and the
    # top two lines of each page (the running header). 0 of 113 O papers (2020+) hit there.
    # Footers are left out: pdftotext can put body text or reference entries in a page's last
    # lines, and 8 of those 113 papers cite a university there.
    exposed = []
    for index, page in enumerate(pages):
        lines = [ln for ln in page.splitlines() if ln.strip()]
        region = page if index == 0 else "\n".join(lines[:2])
        for pattern, label in ((EMAIL_RE, "e-mail"), (SCHOOL_RE, "school name")):
            match = pattern.search(region)
            if match:
                exposed.append(f"page {index + 1}: {label} '{match.group(0)}'")
    if exposed:
        messages.append(CheckMessage(
            "fail", "Identifying details on the Summary Sheet or in a page header: "
                    + "; ".join(exposed[:4]) + ". (0 of 113 O papers show any.)"))
    return messages


def check_font_size(tex: str) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    match = DOCCLASS_RE.search(tex)
    if match:
        sizes = [int(s) for s in re.findall(r"(\d+)\s*pt", match.group(1))]
        if sizes and min(sizes) < 12:
            messages.append(CheckMessage(
                "fail", f"\\documentclass uses {min(sizes)}pt. COMAP requires a font of at least "
                        f"12-point type."))
    preamble = tex.split("\\begin{document}")[0]
    small = [float(s) for s in FONTSIZE_RE.findall(preamble) if float(s) < 12]
    if small:
        messages.append(CheckMessage(
            "warn", f"The preamble sets \\fontsize{{{small[0]:g}}}; body text must stay at 12pt or larger."))
    return messages


def check_file(pdf: Path, summary: str, config: WorkflowConfig, root: Path) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    size_mb = pdf.stat().st_size / (1024 * 1024)
    if size_mb >= config.max_pdf_mb:
        messages.append(CheckMessage(
            "fail", f"The PDF is {size_mb:.1f} MB; COMAP requires less than {config.max_pdf_mb:g} MB."))
    if config.submission_pdf:
        upload = resolve_project_path(root, config.submission_pdf)
        if not upload.is_file():
            messages.append(CheckMessage(
                "fail" if config.is_final else "warn", f"submission_pdf {config.submission_pdf} does not exist."))
        elif summary and upload.name != f"{summary}.pdf":
            messages.append(CheckMessage(
                "fail", f"The upload is named {upload.name}; COMAP asks for the control number as the "
                        f"file name ({summary}.pdf)."))
        elif upload.read_bytes() != pdf.read_bytes():
            messages.append(CheckMessage(
                "fail", f"{config.submission_pdf} is not the current {config.paper_pdf}; rebuild the upload."))
    elif config.is_final and summary:
        messages.append(CheckMessage(
            "warn", f"Set submission_pdf to the file you will upload; COMAP wants it named {summary}.pdf."))
    return messages


def run_submission_checks(project_root: str | Path, config: WorkflowConfig) -> SubmissionResult:
    root = Path(project_root).resolve()
    pdf = resolve_project_path(root, config.paper_pdf)
    tex_path = resolve_project_path(root, config.paper_tex)
    tex = read_tex_expanded(tex_path, root) if tex_path.is_file() else ""
    messages = check_font_size(tex) if tex else []
    if not pdf.is_file():
        messages.append(CheckMessage("warn", f"PDF not compiled yet: {config.paper_pdf}"))
        return SubmissionResult(messages=messages)
    pages = page_texts(pdf)
    if not pages:
        messages.append(CheckMessage(
            "fail", "The PDF has no extractable text layer; COMAP judges read it and this gate cannot."))
        return SubmissionResult(messages=messages)
    role_messages, counted, ai_start = check_page_roles(pages, config)
    number_messages, summary, header, missing = check_control_numbers(pages, tex, config, counted)
    messages += number_messages + role_messages
    messages += check_anonymity(pages, pdf_metadata(pdf), config)
    messages += check_file(pdf, summary, config, root)
    if not messages:
        messages.append(CheckMessage(
            "pass", f"Submission integrity checks passed (control number {summary} on every page, "
                    f"{counted} counted pages)."))
    return SubmissionResult(messages=messages, summary_number=summary, header_number=header,
                            counted_pages=counted, ai_report_start=ai_start,
                            pages_missing_number=missing)


def render_submission_markdown(result: SubmissionResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Summary Sheet control number: {result.summary_number or '(none)'}",
        f"- Page-header control number: {result.header_number or '(none)'}",
        f"- Pages before the AI report: {result.counted_pages if result.counted_pages is not None else 'unknown'}",
        f"- AI report starts on page: {result.ai_report_start or '(not found)'}",
        "",
        "## Messages",
        "",
    ]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    lines.extend([
        "",
        "## Before uploading (COMAP)",
        "",
        "- One PDF, named `<control number>.pdf`, under 25 MB; no code or data files attached.",
        "- Control number and page number at the top of every page; no names, advisor or school.",
        "- Report on Use of AI after the references; it does not count toward the 25 pages.",
    ])
    return lines


def write_submission_report(project_root: str | Path, config: WorkflowConfig) -> SubmissionResult:
    result = run_submission_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "submission_report.md",
        "Submission Integrity Report",
        render_submission_markdown(result),
    )
    return result
