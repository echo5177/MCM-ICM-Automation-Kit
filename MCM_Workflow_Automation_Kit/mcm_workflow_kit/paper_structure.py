"""Where the sections of a compiled paper sit: table-of-contents entries and the first model page.

Two things a judge on a 10 to 15 minute triage read needs are found from the table of
contents: where each answer is, and how many pages of preamble come before the first
model. The CUMCM 2026 post-mortem measured the second one: that paper's first question
began on page 11, while the latest among the award papers whose section starts could be
identified was page 7. `scripts/measure_award_corpus.py` measures the same quantity on the
MCM/ICM O-paper corpus, and the rule that reads it lives in `requirement_checker`.

Everything here reads the PDF text layer, so it works for a Word-built paper too.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


@dataclass(frozen=True)
class TocEntry:
    number: str  # "3" or "3.2"
    title: str
    page: int

    @property
    def top_level(self) -> bool:
        return "." not in self.number


_NUMBER = r"(?P<number>\d{1,2}(?:\.\d{1,2}){0,3})\.?"
_TITLE_START = r"[A-Za-z(\"'“‘]"
_LEADER = r"(?:(?:\.\s*){3,}|\s{2,})"

TOC_HEAD_RE = re.compile(r"(?m)^\s*(?:Table of )?Contents\s*$", re.I)
# "3 Model Overview . . . . . 5", "3.1 Rules ........ 7", or "3 Model Overview        5".
TOC_ENTRY_RE = re.compile(
    rf"^\s*{_NUMBER}\s+(?P<title>{_TITLE_START}.*?)\s*{_LEADER}(?P<page>\d{{1,2}})\s*$"
)
# A long title wraps: "3 Problem 1: Propagation Simulation Based on ..." / "Equation      5".
TOC_OPEN_RE = re.compile(rf"^\s*{_NUMBER}\s+(?P<title>{_TITLE_START}.*?)\s*$")
TOC_TAIL_RE = re.compile(rf"^\s*(?P<title>[^\d\s].*?)\s*{_LEADER}(?P<page>\d{{1,2}})\s*$")
TRAILING_DOTS_RE = re.compile(r"(?:\s*\.){2,}\s*$")

# Sections that come before the first model: framing, not an answer.
FRONT_MATTER_RE = re.compile(
    r"introduction|background|restatement|statement of the problem|problem (?:statement|analysis|"
    r"description|overview|background|review|understanding)|analysis of the problem|"
    r"assumption|notation|symbol|nomenclature|glossary|terminolog|abbreviation|definitions?\b|"
    r"literature|related work|our work|overview of|general (?:idea|framework)|preliminar|"
    r"preparation|data (?:pre-?\s?processing|cleaning|collection|description|sources?|"
    r"acquisition|preparation|and (?:pre)?processing)|^data$|^overview$|^preface$|"
    r"^general$|^contents$",
    re.I,
)
# A numbered task heading is a model section whatever else its title says.
TASK_HEADING_RE = re.compile(
    r"\b(?:task|problem|question|part|requirement)\s*(?:\d+|[IVX]+\b|one|two|three)", re.I
)
BACK_MATTER_RE = re.compile(
    r"^(?:references?|bibliography|appendi|conclusions?|report on (?:the )?use of ai|"
    r"strengths?|weakness|sensitivity|model evaluation|letter|memo|future work)",
    re.I,
)


def layout_pages(pdf_path: str | Path, first: int = 1, last: int = 6) -> list[str]:
    """Text of pages first..last with the line layout kept (a ToC line stays one line)."""
    try:
        completed = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", "-layout", "-f", str(first), "-l", str(last),
             str(pdf_path), "-"],
            capture_output=True, check=False, timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    pages = completed.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def _clean_title(title: str) -> str:
    return TRAILING_DOTS_RE.sub("", title).strip()


def _entries_on(page: str) -> list[TocEntry]:
    found = []
    lines = [line for line in page.splitlines() if line.strip()]
    index = 0
    while index < len(lines):
        match = TOC_ENTRY_RE.match(lines[index])
        if match:
            found.append(TocEntry(match.group("number"), _clean_title(match.group("title")),
                                  int(match.group("page"))))
        elif index + 1 < len(lines):
            opened = TOC_OPEN_RE.match(lines[index])
            follow = lines[index + 1]
            tail = TOC_TAIL_RE.match(follow) if opened else None
            if opened and tail and not TOC_OPEN_RE.match(follow):
                title = _clean_title(opened.group("title")) + " " + _clean_title(tail.group("title"))
                found.append(TocEntry(opened.group("number"), title, int(tail.group("page"))))
                index += 1
        index += 1
    return found


def toc_entries(pdf_path: str | Path) -> list[TocEntry]:
    """Numbered entries of the table of contents, in order. Empty when no ToC is found."""
    entries: list[TocEntry] = []
    started = False
    for page in layout_pages(pdf_path):
        found = _entries_on(page)
        if not started:
            if TOC_HEAD_RE.search(page) and len(found) >= 3:
                started = True
                entries.extend(found)
            continue
        # A continuation page is mostly ToC lines; the first body page is not.
        if len(found) >= 5 and len(found) >= 0.5 * len([ln for ln in page.splitlines() if ln.strip()]):
            entries.extend(found)
        else:
            break
    return entries


def is_front_matter(title: str) -> bool:
    if TASK_HEADING_RE.search(title):
        return False
    return bool(FRONT_MATTER_RE.search(title))


def first_model_entry(entries: list[TocEntry]) -> TocEntry | None:
    """The first top-level section that is neither framing nor back matter.

    Returns None when the table of contents could not be read reliably: a top-level number
    missing before the candidate means an earlier section was not parsed (a ToC whose page
    numbers have no text layer, an unusual layout), and that section may be the real answer.
    """
    previous: int | None = None
    for entry in entries:
        if not entry.top_level:
            continue
        number = int(entry.number)
        if is_front_matter(entry.title) or BACK_MATTER_RE.search(entry.title):
            previous = number
            continue
        if previous is not None and number != previous + 1:
            return None
        return entry
    return None
