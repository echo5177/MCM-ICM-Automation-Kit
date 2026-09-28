"""MCM/ICM format gate.

This node exists because the original Kit could report `paper_qa: pass` on a paper
that was a plain `article` lecture note, used hyperref with red link boxes, and had
its page target lowered to match a thin draft. It enforces objective, defensible
contest-format rules and, critically, detects *gate lowering* by inspecting the
workflow config itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .config import WorkflowConfig, resolve_project_path
from .paper_qa import run_pdfinfo
from .reporting import CheckMessage, status_from_messages, write_markdown_report
from .tex_source import read_tex_expanded


# Matches an actual \usepackage[...]{...hyperref...} load, not the word in prose.
HYPERREF_USE_RE = re.compile(
    r"\\usepackage\s*(\[[^\]]*\])?\s*\{[^}]*\bhyperref\b[^}]*\}"
)

# Tokens that prove hyperref link borders are suppressed.
HYPERREF_SAFE_TOKENS = [
    "hidelinks",
    "colorlinks=false",
    "colorlinks = false",
    "pdfborder={0 0 0}",
    "pdfborder = {0 0 0}",
    "pdfborder={0 0 0 [0 0]}",
]


@dataclass(frozen=True)
class MCMFormatResult:
    messages: list[CheckMessage]
    pages: int | None

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def check_gate_config(config: WorkflowConfig) -> list[CheckMessage]:
    """Detect attempts to weaken gates to make a thin paper pass."""
    messages: list[CheckMessage] = []
    limit = config.contest_page_limit
    if config.page_target < config.min_page_target:
        messages.append(
            CheckMessage(
                "fail",
                f"page_target={config.page_target} is below the minimum serious target "
                f"{config.min_page_target}. Do not lower the gate to match a thin draft; "
                f"deepen the paper instead.",
            )
        )
    if config.page_hard_limit > limit:
        messages.append(
            CheckMessage(
                "fail",
                f"page_hard_limit={config.page_hard_limit} exceeds the contest page limit "
                f"{limit}.",
            )
        )
    return messages


def check_hyperref(tex_text: str) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    match = HYPERREF_USE_RE.search(tex_text)
    if not match:
        return messages
    options = (match.group(1) or "").lower()
    lowered = tex_text.lower().replace(" ", "")
    safe = "hidelinks" in options or any(
        tok.replace(" ", "") in lowered for tok in HYPERREF_SAFE_TOKENS
    )
    if not safe:
        messages.append(
            CheckMessage(
                "fail",
                "hyperref is loaded without hidelinks/colorlinks=false; the PDF will likely "
                "show colored link boxes around the ToC and references.",
            )
        )
    return messages


def check_structure(tex_text: str) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    if "Summary" not in tex_text:
        messages.append(CheckMessage("fail", "No Summary / Summary Sheet heading found."))
    if r"\tableofcontents" not in tex_text:
        messages.append(CheckMessage("fail", "No table of contents (\\tableofcontents)."))
    has_refs = any(
        token in tex_text
        for token in ("References", r"\bibliography", "thebibliography", r"\printbibliography")
    )
    if not has_refs:
        messages.append(CheckMessage("fail", "No References / bibliography section."))
    has_ai = any(
        token.lower() in tex_text.lower()
        for token in ("AI Use", "AI-Use", "AI Use Report", "Use of AI", "AI tools")
    )
    if not has_ai:
        messages.append(
            CheckMessage(
                "warn",
                "No AI Use Report section found; the contest requires a separate AI report "
                "when AI is used (it does not count toward the page limit).",
            )
        )
    if r"\maketitle" in tex_text:
        messages.append(
            CheckMessage(
                "warn",
                "\\maketitle suggests a generic article title page rather than an MCM-style "
                "Summary Sheet.",
            )
        )
    return messages


H_FLOAT_RE = re.compile(r"\\begin\{(?:figure|table)\}\[H\]")


def check_layout(tex_text: str) -> list[CheckMessage]:
    """Catch layout choices that cause sparse pages or oversized captions."""
    messages: list[CheckMessage] = []
    n_h = len(H_FLOAT_RE.findall(tex_text))
    if n_h > 2:
        messages.append(
            CheckMessage(
                "warn",
                f"{n_h} floats use [H]; prefer [htbp] so text flows around figures/tables and "
                f"fills the page (avoids half-empty pages).",
            )
        )
    if "\\captionsetup" not in tex_text or "width=" not in tex_text:
        messages.append(
            CheckMessage(
                "warn",
                "Captions are not width-limited (\\captionsetup{...width=...}); they may span "
                "the full text width.",
            )
        )
    return messages


SECTION_TITLE_RE = re.compile(r"\\section\{([^}]*)\}")
SECTION_ANY_RE = re.compile(r"\\section\*?\{")
LIST_RE = re.compile(r"\\begin\{(?:itemize|enumerate)\}")
FLOAT_BEGIN_RE = re.compile(r"\\begin\{(?:figure|table)\}")
FLOAT_END_RE = re.compile(r"\\end\{(?:figure|table)\}")
SECTIONING_RE = re.compile(r"\\(?:sub)*section\b")


def _float_spans(tex_text: str) -> list[tuple[int, int]]:
    """(start, end) of each figure/table environment, in document order.

    Floats are not nested in practice, so the i-th begin pairs with the i-th end.
    """
    begins = [m.start() for m in FLOAT_BEGIN_RE.finditer(tex_text)]
    ends = [m.end() for m in FLOAT_END_RE.finditer(tex_text)]
    if len(begins) != len(ends):
        return []  # unbalanced; let the LaTeX compiler report it
    return list(zip(begins, ends))


def check_prose_structure(tex_text: str, config: WorkflowConfig) -> list[CheckMessage]:
    """Catch paper-as-slide-deck patterns: duplicate titles, list/figure dumps, thin sections.

    Adapted from MathModelAgent's writing_check for our single-file main.tex layout.
    """
    messages: list[CheckMessage] = []

    titles = [m.group(1).strip() for m in SECTION_TITLE_RE.finditer(tex_text)]
    seen: set[str] = set()
    dups: list[str] = []
    for title in titles:
        if title in seen and title not in dups:
            dups.append(title)
        seen.add(title)
    if dups:
        messages.append(
            CheckMessage("fail", "Duplicate \\section{} titles: " + ", ".join(dups))
        )

    n_lists = len(LIST_RE.findall(tex_text))
    if n_lists > config.max_list_blocks:
        messages.append(
            CheckMessage(
                "warn",
                f"{n_lists} itemize/enumerate blocks (> {config.max_list_blocks}); a paper that "
                f"leans this hard on lists reads like slides. Convert some to prose.",
            )
        )

    spans = _float_spans(tex_text)
    stacked = 0
    for (_, end_i), (start_j, _) in zip(spans, spans[1:]):
        between = tex_text[end_i:start_j]
        if SECTIONING_RE.search(between):
            continue  # a heading between floats is fine, not an image dump
        if len(re.sub(r"%.*", "", between).strip()) < config.stacked_float_gap_chars:
            stacked += 1
    if stacked:
        messages.append(
            CheckMessage(
                "warn",
                f"{stacked} place(s) stack figures/tables with little explanatory text between "
                f"them; lead into and interpret each float instead of dumping them in a row.",
            )
        )

    boundaries = [m.start() for m in SECTION_ANY_RE.finditer(tex_text)]
    end_doc = tex_text.find(r"\end{document}")
    if end_doc == -1:
        end_doc = len(tex_text)
    short_sections: list[str] = []
    for m in SECTION_TITLE_RE.finditer(tex_text):
        nexts = [b for b in boundaries if b > m.start()] + [end_doc]
        body = tex_text[m.end():min(nexts)]
        if len(re.sub(r"\s+", "", body)) < config.min_section_chars:
            short_sections.append(m.group(1).strip())
    if short_sections:
        messages.append(
            CheckMessage(
                "warn",
                f"Thin section(s) under {config.min_section_chars} chars: "
                + ", ".join(short_sections)
                + ". Develop them or merge into a neighbor.",
            )
        )

    return messages


ANY_SECTION_TITLE_RE = re.compile(r"\\(?:sub)*section\*?\{([^}]*)\}")
KEYWORDS_RE = re.compile(r"keywords?\s*[:\\]", re.IGNORECASE)

# The section skeleton shared by every O-award paper we sampled (see
# skill/references/award_patterns.md). `fail` items were present in 6/6 papers and
# are already mandatory in our doctrine; the rest were 5/6 and vary in wording.
AWARD_SECTIONS: list[tuple[str, str, str, str]] = [
    (
        "Assumptions",
        r"assumption",
        "fail",
        "Every sampled O paper has an 'Assumptions and Justification' section.",
    ),
    (
        "Sensitivity Analysis",
        r"sensitiv",
        "fail",
        "Every sampled O paper has a dedicated Sensitivity Analysis section; it is "
        "mandatory in a contest paper.",
    ),
    (
        "Strengths and Weaknesses",
        r"strength|weakness|limitation|model evaluation",
        "fail",
        "Every sampled O paper closes with a Strengths/Weaknesses (Model Evaluation) "
        "section; a paper that never states its own limits reads as overclaiming.",
    ),
    (
        "Notation",
        r"notation|symbol",
        "warn",
        "5 of 6 O papers give Notation its own section with a symbol table.",
    ),
    (
        "Restatement of the Problem",
        r"restat",
        "warn",
        "A named restatement is where problem-fit credit is won; 5 of 6 O papers have one.",
    ),
    (
        "Our Work / contributions",
        r"our work|our approach|contribution",
        "warn",
        "5 of 6 O papers summarise contributions up front, usually beside a global flowchart.",
    ),
]


def check_award_skeleton(tex_text: str) -> list[CheckMessage]:
    """Check the paper carries the O-award section skeleton."""
    messages: list[CheckMessage] = []
    titles = " | ".join(
        m.group(1) for m in ANY_SECTION_TITLE_RE.finditer(tex_text)
    ).lower()

    for label, pattern, level, rationale in AWARD_SECTIONS:
        if not re.search(pattern, titles):
            messages.append(
                CheckMessage(level, f"No '{label}' section found. {rationale}")
            )

    if not KEYWORDS_RE.search(tex_text):
        messages.append(
            CheckMessage(
                "warn",
                "No Keywords line found; O-paper Summary Sheets end with one.",
            )
        )
    return messages


def check_figure_density(
    tex_text: str,
    pages: int,
    config: WorkflowConfig,
) -> list[CheckMessage]:
    """Warn when the paper is visually thinner than O-award papers.

    Counts figure *environments* in the source, while the O-paper band was measured
    from rendered *images*. A float holding subfigures counts once here, so this
    slightly under-counts relative to the band; treat the floor as a lower bound.
    """
    counted = pages - config.ai_report_pages
    if counted <= 0:
        return []
    figures = len(re.findall(r"\\begin\{figure", tex_text))
    density = figures / counted
    if density < config.min_figures_per_page:
        return [
            CheckMessage(
                "warn",
                f"Figure density {density:.2f}/page ({figures} figures over {counted} "
                f"counted pages) is below the O-paper floor "
                f"{config.min_figures_per_page:.2f}. Every sampled O paper ran "
                f"0.60-1.27 images per page with 48-68% of pages visual; add "
                f"evidence-carrying figures (not decoration).",
            )
        ]
    return []


def run_mcm_format_checks(
    project_root: str | Path,
    config: WorkflowConfig,
) -> MCMFormatResult:
    root = Path(project_root).resolve()
    limit = config.contest_page_limit
    tex_path = resolve_project_path(root, config.paper_tex)
    pdf_path = resolve_project_path(root, config.paper_pdf)

    messages: list[CheckMessage] = []
    pages: int | None = None
    tex_text: str | None = None

    messages.extend(check_gate_config(config))

    if not tex_path.exists():
        messages.append(CheckMessage("fail", f"LaTeX source missing: {config.paper_tex}"))
    else:
        tex_text = read_tex_expanded(tex_path, root)
        messages.extend(check_hyperref(tex_text))
        messages.extend(check_structure(tex_text))
        messages.extend(check_layout(tex_text))
        messages.extend(check_prose_structure(tex_text, config))
        messages.extend(check_award_skeleton(tex_text))

    if not pdf_path.exists():
        messages.append(
            CheckMessage("warn", f"PDF not compiled yet: {config.paper_pdf}")
        )
    else:
        pages, _ = run_pdfinfo(pdf_path)
        if pages is None:
            messages.append(CheckMessage("warn", "Could not parse pdfinfo page count."))
        else:
            counted = pages - config.ai_report_pages   # AI Use Report does not count
            if counted > limit:
                messages.append(
                    CheckMessage(
                        "fail",
                        f"{counted} counted pages (of {pages} total, AI report excluded), above "
                        f"contest limit {limit}.",
                    )
                )
            elif counted < config.min_serious_pages:
                messages.append(
                    CheckMessage(
                        "fail",
                        f"{counted} counted pages, below the serious-depth floor "
                        f"{config.min_serious_pages}. A substantial problem warrants using the "
                        f"{limit}-page allowance; deepen the content (do not lower this floor).",
                    )
                )
            elif counted < config.page_target:
                messages.append(
                    CheckMessage(
                        "warn",
                        f"{counted} counted pages (AI report excluded), below target "
                        f"{config.page_target}; use more of the {limit}-page allowance.",
                    )
                )

    if tex_text is not None and pages is not None:
        messages.extend(check_figure_density(tex_text, pages, config))

    if not messages:
        messages.append(CheckMessage("pass", "MCM format checks passed."))

    return MCMFormatResult(messages=messages, pages=pages)


def render_mcm_format_markdown(result: MCMFormatResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Pages: {result.pages if result.pages is not None else 'unknown'}",
        "",
        "## Messages",
        "",
    ]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    return lines


def write_mcm_format_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> MCMFormatResult:
    result = run_mcm_format_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "mcm_format_report.md",
        "MCM Format Report",
        render_mcm_format_markdown(result),
    )
    return result
