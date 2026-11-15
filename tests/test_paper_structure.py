from __future__ import annotations

from pathlib import Path

from mcm_workflow_kit import mcm_format_checker, paper_structure
from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.paper_structure import TocEntry, first_model_entry, is_front_matter, toc_entries


TOC = """Team # 2612345                                   Page 2 of 25

                          Contents

1 Introduction                                                           3
1.1 Problem Background . . . . . . . . . . . . . . . . . . . . . . . . . . 3
1.2 Restatement of the Problem . . . . . . . . . . . . . . . . . . . . . . 3
2 Assumptions and Justifications                                          4
3 Notations                                                               5
4 Problem 1: Propagation Simulation Based on Yearly Time-Step Difference
Equation                                                                 6
4.1 Method Overview . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
5 Sensitivity Analysis                                                   21
6 Strengths and Weaknesses                                               23
"""
BODY = "Team # 2612345 Page 3 of 25\n1 Introduction\nWe study the spread of the species over ten years.\n"


def use_pages(monkeypatch, *pages: str) -> None:
    monkeypatch.setattr(paper_structure, "layout_pages", lambda _pdf, first=1, last=6: list(pages))


def test_toc_entries_reads_dot_leaders_and_spaced_page_numbers(monkeypatch):
    use_pages(monkeypatch, "Summary Sheet\n", TOC, BODY)
    entries = toc_entries("paper.pdf")
    assert TocEntry("1", "Introduction", 3) in entries
    assert TocEntry("1.2", "Restatement of the Problem", 3) in entries
    assert [e.number for e in entries if e.top_level] == ["1", "2", "3", "4", "5", "6"]


def test_wrapped_title_keeps_its_page_number(monkeypatch):
    # 2021 C 2101166: the title of section 3 wraps and the page number sits on the second line.
    use_pages(monkeypatch, "Summary Sheet\n", TOC, BODY)
    wrapped = next(e for e in toc_entries("paper.pdf") if e.number == "4")
    assert wrapped.page == 6 and wrapped.title.endswith("Equation")


def test_first_model_entry_skips_framing_sections(monkeypatch):
    use_pages(monkeypatch, "Summary Sheet\n", TOC, BODY)
    entry = first_model_entry(toc_entries("paper.pdf"))
    assert entry is not None and entry.number == "4" and entry.page == 6


def test_first_model_entry_is_none_when_an_earlier_section_was_not_parsed():
    # 2023 C 2311717: sections 5 and 6 had no readable page number, so the first parsed
    # model section was section 7 on page 17. A gap means "unknown", not "page 17".
    entries = [TocEntry("1", "Introduction", 3), TocEntry("4", "Data pre-processing", 6),
               TocEntry("7", "Task 3: Word Difficulty Classification Model", 17)]
    assert first_model_entry(entries) is None


def test_numbered_task_heading_is_never_front_matter():
    assert is_front_matter("Problem Restatement and Analysis")
    assert is_front_matter("Data Preprocessing")
    assert not is_front_matter("Problem 1: Propagation Simulation")
    assert not is_front_matter("Task 2: Data-Driven Prediction")


def test_no_contents_heading_gives_no_entries(monkeypatch):
    use_pages(monkeypatch, "Summary Sheet\n", BODY)
    assert toc_entries("paper.pdf") == []


def config(**overrides) -> WorkflowConfig:
    return WorkflowConfig.from_mapping({"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf", **overrides})


def test_late_first_model_page_warns(monkeypatch):
    late = TOC.replace("Equation                                                                 6",
                       "Equation                                                                 11")
    use_pages(monkeypatch, "Summary Sheet\n", late, BODY)
    messages = mcm_format_checker.check_first_model_page(Path("paper.pdf"), config())
    assert [m.level for m in messages] == ["warn"]
    assert "page 11" in messages[0].message and "triage" in messages[0].message


def test_first_model_by_page_seven_is_quiet(monkeypatch):
    use_pages(monkeypatch, "Summary Sheet\n", TOC, BODY)
    assert mcm_format_checker.check_first_model_page(Path("paper.pdf"), config()) == []
