from __future__ import annotations

from pathlib import Path

from mcm_workflow_kit import requirement_checker as rc
from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.paper_structure import TocEntry
from mcm_workflow_kit.requirement_checker import (
    find_section,
    number_on_page,
    run_requirement_checks,
    tex_sections,
)


HEADER = "req_id,requirement,kind,turns_on,expected,answer,section,evidence,status\n"
TEMPLATE_ROW = 'R1,"[the first task, in the problem\'s own words]",model,"[one plain sentence]","[what you expect]",,,,open\n'

TEX = "\n".join([
    r"\documentclass[12pt]{article}\begin{document}",
    r"\section{Introduction}", "We restate the problem. " * 20,
    r"\section{Assumptions and Justifications}", "Each assumption has a reason. " * 20,
    r"\section{Task 1: Time-to-Empty Model}", "The model. " * 40,
    r"\begin{figure}\caption{TTE by scenario}\label{fig:tte}\end{figure}",
    r"\subsection{Results}", "Idle lasts 15.52 h. " * 10,
    r"\section{Task 2: Power-Saving Strategies}", "Lower brightness gains 1.8 h. " * 20,
    r"\begin{table}\caption{Gain by strategy}\label{tab:gain}\end{table}",
    r"\section{A Unified Stochastic Framework}", "A framework nobody asked for. " * 30,
    r"\section{Sensitivity Analysis}", "We vary R0. " * 30,
    r"\section{Memo to the Product Team}", "Dimming the screen adds 1.8 hours; gaming drains it in 2.43 hours. " * 5,
    r"\section*{References}", r"\end{document}",
])
SUMMARY_PAGE = ("Summary\nTime-to-empty ranges from 15.52 h (idle) to 2.43 h (gaming). "
                "Lowering brightness gains 1.8 h.\nKeywords: battery\n")
TOC = [TocEntry("1", "Introduction", 3), TocEntry("2", "Assumptions and Justifications", 4),
       TocEntry("3", "Task 1: Time-to-Empty Model", 5), TocEntry("4", "Task 2: Power-Saving Strategies", 12),
       TocEntry("5", "A Unified Stochastic Framework", 17), TocEntry("6", "Sensitivity Analysis", 20),
       TocEntry("7", "Memo to the Product Team", 23)]

GOOD_ROWS = (
    'R1,"Develop a continuous-time model of battery drain and predict time-to-empty",model,'
    '"How fast the terminal voltage reaches the cutoff under a given power demand",'
    '"Gaming a few hours; idle most of a day","Time-to-empty ranges from 15.52 h (idle) to 2.43 h (gaming)",'
    '3,fig:tte,answered\n'
    'R2,"Recommend strategies to extend battery life",analysis,'
    '"Which component load buys the most hours per unit of inconvenience",'
    '"Screen brightness first","Lowering brightness gains 1.8 h, the largest single gain",'
    'Power-Saving Strategies,tab:gain,answered\n'
    'R3,"Write a one-page memo to the product team",deliverable,,,'
    '"The memo gives the two headline numbers",Memo to the Product Team,,answered\n'
)


def config(**overrides) -> WorkflowConfig:
    return WorkflowConfig.from_mapping({"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf", **overrides})


def setup(tmp_path: Path, monkeypatch, rows: str | None, tex: str = TEX, summary: str = SUMMARY_PAGE) -> None:
    (tmp_path / "paper").mkdir(exist_ok=True)
    (tmp_path / "reports").mkdir(exist_ok=True)
    (tmp_path / "paper" / "main.tex").write_text(tex, encoding="utf-8")
    (tmp_path / "paper" / "main.pdf").write_bytes(b"%PDF-1.4")
    if rows is not None:
        (tmp_path / "reports" / "requirements.csv").write_text(HEADER + rows, encoding="utf-8")
    monkeypatch.setattr(rc, "toc_entries", lambda _pdf: TOC)
    monkeypatch.setattr(rc, "page_texts", lambda _pdf: [summary, "Contents", "body"])


def texts(result, level: str | None = None) -> str:
    return " || ".join(m.message for m in result.messages if level is None or m.level == level)


def test_missing_table_fails_at_final_and_warns_in_draft(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, rows=None)
    final = run_requirement_checks(tmp_path, config())
    assert final.status == "fail" and "addressing all problem requirements" in texts(final)
    assert run_requirement_checks(tmp_path, config(release_stage="draft")).status == "warn"


def test_template_row_alone_counts_as_no_requirement(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, rows=TEMPLATE_ROW)
    result = run_requirement_checks(tmp_path, config())
    assert result.status == "fail" and "only the template row" in texts(result)


def test_complete_table_reports_the_section_nobody_asked_for(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, rows=GOOD_ROWS)
    result = run_requirement_checks(tmp_path, config())
    assert texts(result, "fail") == ""
    # Three pages of framework that answer no requirement: the only message.
    assert "'A Unified Stochastic Framework' (3 pages)" in texts(result, "warn")
    assert "Sensitivity Analysis" not in texts(result, "warn")
    by_id = {row["req_id"]: row for row in result.rows}
    assert by_id["R1"]["page"] == 5 and by_id["R1"]["in_summary"] == "yes"
    assert by_id["R2"]["section"].startswith("4 Task 2")


def test_open_requirement_fails_at_final(tmp_path, monkeypatch):
    rows = GOOD_ROWS.replace("tab:gain,answered", "tab:gain,open")
    setup(tmp_path, monkeypatch, rows=rows)
    result = run_requirement_checks(tmp_path, config())
    assert result.status == "fail" and "R2 is open" in texts(result, "fail")
    draft = run_requirement_checks(tmp_path, config(release_stage="draft"))
    assert draft.status == "warn"


def test_answer_pointing_at_a_missing_section_fails(tmp_path, monkeypatch):
    rows = GOOD_ROWS.replace("Power-Saving Strategies,tab:gain", "Monte Carlo Uncertainty,tab:gain")
    setup(tmp_path, monkeypatch, rows=rows)
    result = run_requirement_checks(tmp_path, config())
    assert "R2: no section 'Monte Carlo Uncertainty'" in texts(result, "fail")


def test_cut_figure_takes_the_evidence_with_it(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, rows=GOOD_ROWS, tex=TEX.replace(r"\label{fig:tte}", ""))
    result = run_requirement_checks(tmp_path, config())
    assert "R1: evidence label(s) not in the paper: fig:tte" in texts(result, "fail")


def test_answer_absent_from_the_summary_warns(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, rows=GOOD_ROWS,
          summary="Summary\nWe build an electro-thermal model and solve it with Runge-Kutta.\n")
    result = run_requirement_checks(tmp_path, config())
    warned = texts(result, "warn")
    assert "R1: none of the answer's numbers (15.52, 2.43)" in warned and "R2: none of" in warned


def test_missing_turns_on_blocks_the_submission(tmp_path, monkeypatch):
    rows = GOOD_ROWS.replace('"How fast the terminal voltage reaches the cutoff under a given power demand"', "")
    setup(tmp_path, monkeypatch, rows=rows)
    result = run_requirement_checks(tmp_path, config())
    assert "R1: `turns_on` is empty" in texts(result, "fail")


def test_memo_with_equations_warns(tmp_path, monkeypatch):
    tex = TEX.replace(r"\section{Memo to the Product Team}",
                      r"\section{Memo to the Product Team}" "\n" r"\begin{equation}P=VI\end{equation}")
    setup(tmp_path, monkeypatch, rows=GOOD_ROWS, tex=tex)
    assert "contains displayed equations" in texts(run_requirement_checks(tmp_path, config()), "warn")


def test_sections_are_numbered_like_latex_and_found_by_number_or_title():
    sections = tex_sections(TEX)
    assert [s.number for s in sections if s.level == 0][:4] == ["1", "2", "3", "4"]
    assert find_section("3.1", sections).title == "Results"
    assert find_section("Section 4", sections).title.startswith("Task 2")
    assert find_section("time-to-empty model", sections).number == "3"
    assert find_section("9", sections) is None


def test_number_match_does_not_fire_inside_a_longer_number():
    assert number_on_page("15.52", "ranges from 15.52 h to 2.43 h")
    assert not number_on_page("5.52", "ranges from 15.52 h")
    assert not number_on_page("15.5", "ranges from 15.52 h")
    assert number_on_page("1378", "a cost of 1,378 thousand")
