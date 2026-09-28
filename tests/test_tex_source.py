from __future__ import annotations

from pathlib import Path

from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.mcm_format_checker import run_mcm_format_checks
from mcm_workflow_kit.tex_source import macro_values, read_tex_expanded


def test_input_resolves_against_the_main_document_directory(tmp_path: Path) -> None:
    # TeX resolves \input against its working directory (the main file's folder), not the
    # folder of the file that contains the \input.
    (tmp_path / "paper" / "parts").mkdir(parents=True)
    (tmp_path / "tables").mkdir()
    (tmp_path / "tables" / "table_1_results.tex").write_text(r"Mean error 3.27\%.", encoding="utf-8")
    (tmp_path / "paper" / "parts" / "results.tex").write_text(
        "\\section{Results}\n\\input{../tables/table_1_results.tex}\n", encoding="utf-8")
    main = tmp_path / "paper" / "main.tex"
    main.write_text("\\begin{document}\n\\input{parts/results}\n\\end{document}\n", encoding="utf-8")
    text = read_tex_expanded(main, tmp_path)
    assert "Mean error 3.27" in text and "\\section{Results}" in text


def test_comments_are_dropped_and_zero_arg_macros_expand(tmp_path: Path) -> None:
    main = tmp_path / "main.tex"
    main.write_text(
        "\\newcommand{\\Team}{2601234}\n% TODO remove\nTeam \\Team\\ Page 1\n", encoding="utf-8")
    text = read_tex_expanded(main, tmp_path)
    assert "Team 2601234" in text and "TODO" not in text
    assert macro_values(main, tmp_path) == {"Team": "2601234"}


def test_missing_file_reads_as_empty(tmp_path: Path) -> None:
    assert read_tex_expanded(tmp_path / "nope.tex", tmp_path) == ""


def test_include_cycle_is_cut(tmp_path: Path) -> None:
    (tmp_path / "a.tex").write_text("A \\input{b}", encoding="utf-8")
    (tmp_path / "b.tex").write_text("B \\input{a}", encoding="utf-8")
    assert read_tex_expanded(tmp_path / "a.tex", tmp_path).startswith("A B")


def test_format_checker_sees_sections_kept_in_input_files(tmp_path: Path) -> None:
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "evaluation.tex").write_text(
        "\\section{Sensitivity Analysis}\n\\section{Strengths and Weaknesses}\n", encoding="utf-8")
    (paper / "main.tex").write_text(
        "\\begin{document}Summary\n\\tableofcontents\n\\section{Assumptions}\n"
        "\\input{evaluation}\nReferences\n\\end{document}\n", encoding="utf-8")
    config = WorkflowConfig.from_mapping({"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf"})
    messages = " ".join(m.message for m in run_mcm_format_checks(tmp_path, config).messages)
    assert "No 'Sensitivity Analysis' section found" not in messages
    assert "No 'Strengths and Weaknesses' section found" not in messages
    assert "No table of contents" not in messages
