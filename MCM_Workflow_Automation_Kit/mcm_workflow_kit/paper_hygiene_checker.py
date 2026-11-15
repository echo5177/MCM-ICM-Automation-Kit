"""Paper hygiene: writing problems no other node catches and a judge notices within pages.

Carried over from the CUMCM Kit, where a user listed eleven such problems after the 2026
contest and every one of them had reached the submitted draft: notes to teammates printed
in the body ("in this version we fixed ..."), program-log phrases ("took 14 ms",
`method="highs"`), a dashed double title, paragraphs of defensive hedging, over-dense pages.

Nothing is ported on faith. Each rule below was measured on 147 local O papers (2018+,
`scripts/measure_award_corpus.py`, report in `reports/award_corpus_measurements.md`) and
kept only where O papers do not trip it. Several CUMCM rules were measured and dropped for
MCM because O papers routinely do the opposite: explanatory captions (13% run past 40
words), numbered strengths/weaknesses lists, strengths/weaknesses ratios (median 1:1), and
acronym counts in the summary (a quarter of O summaries have at most one).

Levels: notes to teammates and tool traces **fail** (no legitimate use; 0/147 O papers);
everything else **warns** for a human to judge.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import statistics
import subprocess

from .config import WorkflowConfig, resolve_project_path
from .paper_structure import TocEntry, toc_entries
from .pdf_text import page_texts
from .reporting import CheckMessage, status_from_messages, write_markdown_report
from .submission_checker import ai_report_start, references_start
from .tex_source import read_tex_expanded


WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")

# --- notes to teammates and tool traces: fail (0/147 O papers) ---------------------------
TEAM_FACING: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("version narrative", re.compile(
        r"\bin this version\b|\bprevious version of (?:the|this|our) (?:paper|draft|report)\b"
        r"|\b(?:our|the) previous draft\b|\bthis draft\b|\bearlier draft\b|\bv\d+ of the paper\b",
        re.I)),
    ("tool trace", re.compile(
        r"(?<![A-Za-z])Kit(?![A-Za-z])|mcm_workflow_kit|workflow_config|judge_review|run_workflow"
        r"|MCM-ICM-Automation")),
)

# --- program-log phrasing: warn -------------------------------------------------------------
MACHINE_PHRASES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("millisecond runtime", re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds?)\b")),           # 0/147
    ("solver parameter", re.compile(r"random_state|n_jobs|max_iter\s*=|method\s*=\s*['\"]")),  # 1/147
    ("script file name", re.compile(r"\b[\w-]{2,}\.(?:py|ipynb)\b")),                          # 1/147
)

# Defensive disclaimers only. "Note that" and "not necessarily" are left out: ordinary math
# English. O papers: 110/147 use none, max 6.1 per 10k words, 0/147 reach 5 hits AND > 3/10k.
HEDGES = re.compile(
    r"\bit should be noted\b|\bit is worth noting\b|\bit must be noted\b"
    r"|\bwe do not claim\b|\bdoes not imply\b|\bdo not imply\b"
    r"|\bstrictly speaking\b|\bshould not be interpreted\b|\bcannot be interpreted\b"
    r"|\bonly indicates?\b|\bis not equivalent to\b|\bwe acknowledge\b|\badmittedly\b"
    r"|\bit is important to note\b",
    re.I,
)
DASHES = re.compile(r"—|–|\s-\s|--")
APPENDIX_RE = re.compile(r"\\appendix\b|\\section\*?\s*\{\s*Appendi", re.I)

# --- the Summary promises an analysis the body does not show: fail ----------------------------
# The 2026 MCM A entry cut ten pages in its last half hour. Its Summary still promised a
# "global LHS-Monte Carlo sensitivity (Spearman indices)"; the body mentions Monte Carlo once.
# Each term below names an analysis a judge will look for once the Summary has promised it.
SUMMARY_CLAIMS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sensitivity analysis", re.compile(r"sensitiv", re.I)),
    ("Monte Carlo", re.compile(r"monte[\s-]*carlo", re.I)),
    ("Latin hypercube sampling", re.compile(r"(?i:latin\s+hypercube)|\bLHS\b")),
    ("bootstrap", re.compile(r"bootstrap", re.I)),
    ("cross-validation", re.compile(r"cross[\s-]*validat", re.I)),
    ("Spearman correlation", re.compile(r"spearman", re.I)),
    ("Sobol indices", re.compile(r"sobol", re.I)),
    ("uncertainty analysis", re.compile(r"uncertainty\s+(?:quantification|analys[ie]s)|\bUQ\b", re.I)),
    ("confidence or prediction interval", re.compile(r"(?:confidence|prediction)\s+intervals?", re.I)),
    ("robustness analysis", re.compile(r"robustness\s+(?:analys[ie]s|tests?|checks?)", re.I)),
    ("error analysis", re.compile(r"error\s+analys[ie]s", re.I)),
)
SUMMARY_CLAIM_MIN_BODY_MENTIONS = 2

# A numbered top-level heading as pdftotext prints it: "6 Time-to-Empty Prediction".
PDF_TOP_HEADING_RE = re.compile(r"^\s*(\d{1,2})\s+[A-Z][A-Za-z][A-Za-z ,:&/'()-]{2,80}$")
TEX_HEADING_RE = re.compile(r"\\(?P<level>(?:sub){0,2})section\*?\s*\{(?P<title>[^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
EMPTY_SECTION_MAX_CHARS = 10  # nothing at all; a thin section is mcm_format_checker's warning


@dataclass(frozen=True)
class PaperHygieneResult:
    messages: list[CheckMessage]
    title: str = ""
    median_words_per_page: float | None = None

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


DOT_LEADERS_RE = re.compile(r"(?:\.\s?){8,}")
HEADER_LINE_RE = re.compile(r"Summary Sheet|Team Control|Problem Chosen|\b\d{7}\b|^[A-F]$|MCM/ICM|^20\d\d$")


def title_of(first_page: str) -> str:
    """Title on the Summary Sheet.

    The official template puts it between the header block and the "Summary" heading; some
    papers (ProbA) put it above the header block instead, so fall back to the lines before
    the header.
    """
    lines = [ln.strip() for ln in first_page.splitlines() if ln.strip()]
    for index, line in enumerate(lines):
        if re.fullmatch(r"Summary|Abstract", line, re.I) and index > 0:
            candidates: list[str] = []
            for back in lines[max(0, index - 4):index][::-1]:
                if HEADER_LINE_RE.search(back):
                    break
                candidates.insert(0, back)
            if candidates:
                return " ".join(candidates)
            header = next((i for i, ln in enumerate(lines[:index]) if HEADER_LINE_RE.search(ln)), None)
            return " ".join(lines[:header][:4]) if header else ""
    return ""


def _snippet(text: str, match: re.Match[str], width: int = 30) -> str:
    return re.sub(r"\s+", " ", text[max(0, match.start() - width):match.end() + width]).strip()


def check_team_facing(tex: str) -> list[CheckMessage]:
    hits = []
    for label, regex in TEAM_FACING:
        for match in regex.finditer(tex):
            hits.append(f"[{label}] ...{_snippet(tex, match)}...")
    if not hits:
        return []
    return [CheckMessage(
        "fail",
        f"{len(hits)} note(s) to the team left in the paper: " + "; ".join(hits[:5])
        + ". Version history and tool names belong in the team's records; a judge reading them "
          "sees an unfinished draft. (0 of 147 O papers contain any.)",
    )]


def check_machine_phrases(tex_body: str) -> list[CheckMessage]:
    found = []
    for label, regex in MACHINE_PHRASES:
        match = regex.search(tex_body)
        if match:
            found.append(f"{label}: '{_snippet(tex_body, match, 20)}'")
    if not found:
        return []
    return [CheckMessage(
        "warn",
        "Program-log phrasing in the body: " + "; ".join(found)
        + ". Millisecond timings, solver arguments and script names read like a run log. Keep a "
          "runtime only when it is a result being compared, and say it the way an author would.",
    )]


def check_hedges(text: str, config: WorkflowConfig) -> list[CheckMessage]:
    found = HEDGES.findall(text)
    words = len(WORD_RE.findall(text))
    if not words or len(found) < config.hedge_min_count:
        return []
    rate = 1e4 * len(found) / words
    if rate <= config.hedge_warn_per_10k:
        return []
    common: dict[str, int] = {}
    for hedge in found:
        common[hedge.lower()] = common.get(hedge.lower(), 0) + 1
    top = sorted(common.items(), key=lambda kv: -kv[1])[:4]
    return [CheckMessage(
        "warn",
        f"{len(found)} defensive disclaimers, {rate:.1f} per 10k words (O papers: 110/147 use "
        f"none, max 6.1; none has 5+ at over 3). Most frequent: "
        + ", ".join(f"'{w}' x{n}" for w, n in top)
        + ". State each limitation once, in the evaluation section.",
    )]


def check_title(title: str, config: WorkflowConfig) -> list[CheckMessage]:
    if not title:
        return []
    messages = []
    words = len(WORD_RE.findall(title))
    if DASHES.search(title):
        messages.append(CheckMessage(
            "warn", f"The title uses a dash: '{title}'. No O paper title in the corpus does "
                    f"(37% use a colon, which is fine)."))
    if words > config.title_max_words:
        messages.append(CheckMessage(
            "warn", f"The title runs {words} words (O papers: median 8, P90 13): '{title}'. "
                    f"Name the method and the object; the result belongs in the summary."))
    return messages


def check_summary_numbers(first_page: str) -> list[CheckMessage]:
    keywords = re.search(r"Key\s*words?\s*[:：]", first_page, re.I)
    body = first_page[: keywords.start()] if keywords else first_page
    numbers = re.findall(r"\d+(?:\.\d+)?%?", body)
    numbers = [n for n in numbers if not re.fullmatch(r"20\d\d|\d{7}", n)]
    if len(numbers) >= 3:
        return []
    return [CheckMessage(
        "warn", f"The Summary Sheet carries {len(numbers)} number(s). O summaries carry a median of "
                f"14 (only 4 of 147 have fewer than 3): state the headline results, not just the methods."),
    ]


def unsupported_summary_claims(summary: str, body: str) -> list[tuple[str, int]]:
    """Analyses the Summary names that the body mentions fewer than twice: (label, body count)."""
    flat = re.sub(r"\s+", " ", re.sub(r"-\s*\n\s*", "", body))
    missing = []
    for label, regex in SUMMARY_CLAIMS:
        if not regex.search(summary):
            continue
        count = len(regex.findall(flat))
        if count < SUMMARY_CLAIM_MIN_BODY_MENTIONS:
            missing.append((label, count))
    return missing


def check_summary_claims(pages: list[str], prose_end: int) -> list[CheckMessage]:
    if len(pages) < 4:
        return []
    # The body starts after the Summary Sheet and the table of contents.
    start = 2 if DOT_LEADERS_RE.search(pages[1]) else 1
    missing = unsupported_summary_claims(pages[0], "\n".join(pages[start:prose_end]))
    if not missing:
        return []
    listed = ", ".join(f"{label} ({count} mention{'s' if count != 1 else ''} in the body)"
                       for label, count in missing)
    # 139 O papers: 8 trip on a single term (a word used once more in the Summary than in the
    # body), none on two. The 2026 MCM A entry trips on three.
    level = "fail" if len(missing) >= 2 else "warn"
    return [CheckMessage(
        level,
        f"The Summary Sheet promises an analysis the body barely mentions: {listed}. Either the "
        f"section was cut and the Summary was not re-read, or the analysis was never run. "
        f"Restore it with its figure or table, or take the claim out of the Summary. "
        f"(O papers: 8 of 139 have one such term, none has two.)",
    )]


def empty_sections_in_tex(tex: str) -> list[str]:
    """Titles of headings followed, almost at once, by a heading of the same or a higher level."""
    headings = [(m.start(), m.end(), len(m.group("level")) // 3, m.group("title").strip())
                for m in TEX_HEADING_RE.finditer(tex)]
    end_doc = tex.find(r"\end{document}")
    empty = []
    for index, (_start, end, level, title) in enumerate(headings):
        if index + 1 < len(headings):
            next_start, _e, next_level, _t = headings[index + 1]
        else:
            next_start, next_level = (end_doc if end_doc != -1 else len(tex)), level
        if next_level > level:
            continue  # a section that opens straight into its first subsection is normal
        between = re.sub(r"\\(?:label|newpage|clearpage|vspace\*?|noindent)\s*(?:\{[^{}]*\})?", "", tex[end:next_start])
        if len(re.sub(r"\s+", "", between)) < EMPTY_SECTION_MAX_CHARS:
            empty.append(title)
    return empty


def empty_sections_in_pdf(pages: list[str], toc: list[TocEntry]) -> list[str]:
    """A top-level heading directly followed by the next one (for a Word-built paper).

    Both lines must be top-level entries of the table of contents: "3 Europe" above
    "4 Asia" is otherwise a table row (two of 139 O papers have such rows).
    """
    known = {entry.number: re.sub(r"\W+", "", entry.title).lower()[:20]
             for entry in toc if entry.top_level}

    def is_heading(match: re.Match[str] | None, line: str) -> bool:
        if not match or match.group(1) not in known:
            return False
        title = re.sub(r"\W+", "", line.split(None, 1)[1]).lower()
        return bool(title) and title.startswith(known[match.group(1)][:len(title)])

    empty = []
    for page in pages[1:]:
        if DOT_LEADERS_RE.search(page):
            continue  # the table of contents is nothing but consecutive headings
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        for line, follow in zip(lines, lines[1:]):
            first, second = PDF_TOP_HEADING_RE.match(line), PDF_TOP_HEADING_RE.match(follow)
            if (is_heading(first, line) and is_heading(second, follow)
                    and int(second.group(1)) == int(first.group(1)) + 1):
                empty.append(line)
    return empty


def check_empty_sections(titles: list[str]) -> list[CheckMessage]:
    if not titles:
        return []
    return [CheckMessage(
        "fail",
        f"{len(titles)} heading(s) with nothing under them: " + "; ".join(f"'{t}'" for t in titles[:6])
        + ". A judge reads an empty section as an analysis that was planned and not done (the "
          "2026 MCM A entry left 'Time-to-Empty Prediction and Uncertainty Analysis' as a bare "
          "heading after a late page cut). Fill it, merge it into a neighbour, or delete the heading.",
    )]


def check_density(pages: list[str], counted: int, config: WorkflowConfig) -> tuple[list[CheckMessage], float | None]:
    body = pages[1:counted]
    per_page = [len(WORD_RE.findall(p)) for p in body]
    if len(per_page) < 4:
        return [], None
    median = statistics.median(per_page)
    if median <= config.max_words_per_page:
        return [], median
    return [CheckMessage(
        "warn",
        f"Median {median:.0f} words per page (O papers: median 298, max 484). Pages this dense read "
        f"as walls of text: cut repeated explanation and let equations, figures and tables carry "
        f"the argument. Do not shrink spacing or fonts to fit (COMAP: at least 12-point type).",
    )], median


def check_landscape(pdf: Path) -> list[CheckMessage]:
    try:
        info = subprocess.run(["pdfinfo", "-f", "1", "-l", "9999", str(pdf)],
                              capture_output=True, check=False).stdout.decode("utf-8", "replace")
    except FileNotFoundError:
        return []
    sizes = re.findall(r"Page\s+(\d+)\s+size:\s+([\d.]+)\s+x\s+([\d.]+)", info)
    rots = dict(re.findall(r"Page\s+(\d+)\s+rot:\s+(\d+)", info))
    landscape = [int(page) for page, w, h in sizes
                 if (float(w) > float(h)) != (int(rots.get(page, "0")) in (90, 270))]
    if not landscape:
        return []
    return [CheckMessage(
        "warn",
        f"Landscape page(s): {', '.join(map(str, landscape[:6]))}. No O paper in the corpus rotates "
        f"a page; judges read on screen or on paper and have to turn it. Shrink a wide flowchart "
        f"onto a portrait page (import_flowchart.py sizes it) or split a wide table.",
    )]


def run_paper_hygiene_checks(project_root: str | Path, config: WorkflowConfig) -> PaperHygieneResult:
    root = Path(project_root).resolve()
    tex_path = resolve_project_path(root, config.paper_tex)
    pdf = resolve_project_path(root, config.paper_pdf)
    messages: list[CheckMessage] = []
    pages = page_texts(pdf) if pdf.is_file() else []
    ai_start = ai_report_start(pages) if pages else None
    refs = references_start(pages) if pages else None
    counted = (ai_start - 1) if ai_start else len(pages)
    prose_end = (refs - 1) if refs else counted

    if tex_path.is_file():
        tex = read_tex_expanded(tex_path, root)
        body_end = APPENDIX_RE.search(tex)
        messages += check_team_facing(tex)
        messages += check_machine_phrases(tex[: body_end.start()] if body_end else tex)
        messages += check_empty_sections(empty_sections_in_tex(tex))
    elif pages:
        # A Word-built paper (the 2026 ProbA entry was one): read what the judges read.
        prose = "\n".join(pages[:prose_end])
        messages += check_team_facing(prose)
        messages += check_machine_phrases(prose)
        messages += check_empty_sections(empty_sections_in_pdf(pages[:prose_end], toc_entries(pdf)))
    else:
        messages.append(CheckMessage("warn", f"LaTeX source missing: {config.paper_tex}"))

    title, median = "", None
    if pages:
        title = title_of(pages[0])
        messages += check_title(title, config)
        messages += check_summary_numbers(pages[0])
        messages += check_summary_claims(pages, prose_end)
        messages += check_hedges("\n".join(pages[:prose_end]), config)
        density, median = check_density(pages, prose_end, config)
        messages += density
        messages += check_landscape(pdf)
    if not messages:
        messages.append(CheckMessage("pass", "Paper hygiene checks passed."))
    return PaperHygieneResult(messages=messages, title=title, median_words_per_page=median)


def render_paper_hygiene_markdown(result: PaperHygieneResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Title: {result.title or '(not found)'}",
        "- Median words per body page: "
        + (f"{result.median_words_per_page:.0f}" if result.median_words_per_page else "n/a"),
        "",
        "## Messages",
        "",
    ]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    return lines


def write_paper_hygiene_report(project_root: str | Path, config: WorkflowConfig) -> PaperHygieneResult:
    result = run_paper_hygiene_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "paper_hygiene_report.md",
        "Paper Hygiene Report",
        render_paper_hygiene_markdown(result),
    )
    return result
