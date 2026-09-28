from __future__ import annotations

from pathlib import Path

from mcm_workflow_kit import submission_checker
from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.submission_checker import run_submission_checks


NUM = "2612345"
OTHER = "2698765"


def config(**overrides) -> WorkflowConfig:
    base = {"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf", "ai_report_pages": 1}
    base.update(overrides)
    return WorkflowConfig.from_mapping(base)


def pages(summary: str = NUM, header: str = NUM, body: int = 22, ai_pages: int = 1,
          ai_before_refs: bool = False) -> list[str]:
    out = [f"Problem Chosen\nA\n2026 MCM/ICM Summary Sheet\nTeam Control Number\n{summary}\nTitle\nSummary\n..."]
    out.append(f"Team # {header} Page 1 of {body}\nContents\n1 Introduction\nReport on Use of AI\n")
    for index in range(2, body):
        out.append(f"Team # {header} Page {index} of {body}\nSome text of the model on this page.\n")
    refs = f"Team # {header} Page {body} of {body}\nReferences\n[1] A source.\n"
    ai = [f"Report on Use of AI\n1. OpenAI ChatGPT\n"] + ["more of the AI report\n"] * (ai_pages - 1)
    return out + (ai + [refs] if ai_before_refs else [refs] + ai)


def setup(tmp_path: Path, monkeypatch, page_list: list[str], meta: dict | None = None,
          tex: str = "\\documentclass[12pt]{article}\n\\begin{document}x\\end{document}") -> None:
    paper = tmp_path / "paper"
    paper.mkdir(exist_ok=True)
    (paper / "main.pdf").write_bytes(b"%PDF-1.4 paper")
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    monkeypatch.setattr(submission_checker, "page_texts", lambda _pdf: page_list)
    monkeypatch.setattr(submission_checker, "pdf_metadata", lambda _pdf: meta or {})


def texts(result, level: str | None = None) -> str:
    return " ".join(m.message for m in result.messages if level is None or m.level == level)


def test_clean_paper_passes(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages())
    (tmp_path / "upload").mkdir()
    (tmp_path / "upload" / f"{NUM}.pdf").write_bytes(b"%PDF-1.4 paper")
    result = run_submission_checks(tmp_path, config(submission_pdf=f"upload/{NUM}.pdf"))
    assert result.status == "pass", texts(result)
    assert result.summary_number == result.header_number == NUM
    # summary + contents + 20 body pages + references = 23 counted; the AI report is page 24.
    assert result.ai_report_start == 24 and result.counted_pages == 23


def test_summary_and_header_numbers_disagree(tmp_path: Path, monkeypatch) -> None:
    # The 2026 ProbA entry: one number on the Summary Sheet, another in every page header.
    setup(tmp_path, monkeypatch, pages(summary=NUM, header=OTHER))
    result = run_submission_checks(tmp_path, config())
    assert result.status == "fail"
    failed = texts(result, "fail")
    assert NUM in failed and OTHER in failed
    assert "missing from" not in failed        # reported once, as the mismatch


def test_placeholder_number_warns_in_draft_and_fails_at_final(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages(summary="1111111", header="1111111"))
    assert run_submission_checks(tmp_path, config(release_stage="draft")).status == "warn"
    assert run_submission_checks(tmp_path, config()).status == "fail"


def test_configured_number_must_match(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages())
    result = run_submission_checks(tmp_path, config(team_control_number=OTHER))
    assert result.status == "fail" and "the config says" in texts(result, "fail")


def test_pages_without_the_number(tmp_path: Path, monkeypatch) -> None:
    page_list = pages()
    page_list[5] = "A page whose header was lost.\n"
    setup(tmp_path, monkeypatch, page_list)
    result = run_submission_checks(tmp_path, config())
    assert result.status == "warn" and result.pages_missing_number == [6]


def test_ai_report_before_references_fails_and_page_count_is_measured(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages(ai_before_refs=True))
    assert "before the References" in texts(run_submission_checks(tmp_path, config()), "fail")
    setup(tmp_path, monkeypatch, pages(ai_pages=3))
    warned = texts(run_submission_checks(tmp_path, config()), "warn")
    assert "runs 3 page(s)" in warned and "Set it to 3" in warned


def test_over_the_page_limit(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages(body=26))
    assert "above the 25-page limit" in texts(run_submission_checks(tmp_path, config()), "fail")


def test_identity_in_text_metadata_or_headers(tmp_path: Path, monkeypatch) -> None:
    page_list = pages()
    page_list[8] += "Thanks to Alice Zhang for the data.\n"
    setup(tmp_path, monkeypatch, page_list, meta={"Author": "Alice Zhang"})
    result = run_submission_checks(tmp_path, config(anonymity_terms=["Alice Zhang"]))
    failed = texts(result, "fail")
    assert "'Alice Zhang' appears" in failed and "Author" in failed
    page_list = pages()
    page_list[3] = "Tsinghua University Team\n" + page_list[3]      # in the running header
    setup(tmp_path, monkeypatch, page_list, meta={"Author": "me"})
    result = run_submission_checks(tmp_path, config())
    assert "school name" in texts(result, "fail")
    assert "PDF Author is set" in texts(result, "warn")


def test_a_university_cited_at_the_bottom_of_a_page_is_not_identity(tmp_path: Path, monkeypatch) -> None:
    # 8 of 113 O papers have a university in a page's last lines (a reference, a data source).
    page_list = pages()
    page_list[-2] += "[2] Data from Johns Hopkins University.\n"
    page_list[7] += "Data were provided by the University of Michigan.\n"
    setup(tmp_path, monkeypatch, page_list)
    result = run_submission_checks(tmp_path, config(release_stage="draft"))
    assert "school name" not in texts(result)


def test_font_below_twelve_points(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages(), tex="\\documentclass[11pt,a4paper]{article}\n\\begin{document}x\\end{document}")
    assert "11pt" in texts(run_submission_checks(tmp_path, config()), "fail")


def test_upload_file_name_size_and_freshness(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages())
    (tmp_path / "upload").mkdir()
    (tmp_path / "upload" / "paper.pdf").write_bytes(b"%PDF-1.4 paper")
    assert "named paper.pdf" in texts(run_submission_checks(
        tmp_path, config(submission_pdf="upload/paper.pdf")), "fail")
    (tmp_path / "upload" / f"{NUM}.pdf").write_bytes(b"%PDF-1.4 older build")
    assert "not the current" in texts(run_submission_checks(
        tmp_path, config(submission_pdf=f"upload/{NUM}.pdf")), "fail")
    assert "less than" in texts(run_submission_checks(tmp_path, config(max_pdf_mb=0.000001)), "fail")


def test_emptying_the_placeholder_list_does_not_silence_the_check(tmp_path: Path, monkeypatch) -> None:
    # ProbA's config had team_control_number_placeholders: [] and 1111111 went unflagged.
    setup(tmp_path, monkeypatch, pages(summary="1111111", header="1111111"))
    result = run_submission_checks(tmp_path, config(team_control_number_placeholders=[]))
    assert result.status == "fail" and "placeholder" in texts(result, "fail")


def test_upload_name_hint_never_suggests_the_placeholder(tmp_path: Path, monkeypatch) -> None:
    # A fresh scaffold at release_stage final was told to name its upload 1111111.pdf.
    setup(tmp_path, monkeypatch, pages(summary="1111111", header="1111111"))
    assert "named <control number>.pdf" in texts(run_submission_checks(tmp_path, config()), "warn")
    setup(tmp_path, monkeypatch, pages())
    assert f"named {NUM}.pdf" in texts(run_submission_checks(tmp_path, config()), "warn")
