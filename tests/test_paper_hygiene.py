from __future__ import annotations

from pathlib import Path

from mcm_workflow_kit import paper_hygiene_checker as hygiene
from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.paper_hygiene_checker import run_paper_hygiene_checks, title_of
from mcm_workflow_kit.submission_checker import references_start


FILLER = ("The model links the demand of each component to the battery current and the state of "
          "charge through a small set of equations that we calibrate on public data. ")


def config(**overrides) -> WorkflowConfig:
    base = {"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf"}
    base.update(overrides)
    return WorkflowConfig.from_mapping(base)


def summary_page(title: str = "A Continuous-Time Model of Battery Drain",
                 numbers: str = "15.52 h, 2.43 h and 6.53%") -> str:
    return (f"Problem Chosen\nA\n2026 MCM/ICM Summary Sheet\nTeam Control Number\n2612345\n{title}\n"
            f"Summary\nWe predict time-to-empty; the five scenarios give {numbers}.\n"
            f"Keywords: battery; time-to-empty\n")


def pages(body_words: int = 250, extra: str = "", title: str | None = None,
          numbers: str | None = None) -> list[str]:
    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if numbers is not None:
        kwargs["numbers"] = numbers
    out = [summary_page(**kwargs), "Team # 2612345 Page 1\nContents\n1 Introduction . . . . . . 3\nReferences\n"]
    words_per_filler = len(FILLER.split())
    for index in range(2, 22):
        out.append(f"Team # 2612345 Page {index}\n" + FILLER * max(1, body_words // words_per_filler) + extra)
    out.append("Team # 2612345 Page 22\nReferences\n[1] A source.\n")
    out.append("Report on Use of AI\nOpenAI ChatGPT was used to polish wording.\n")
    return out


CLEAN_TEX = ("\\documentclass[12pt]{article}\\begin{document}\n\\section{Introduction}\n"
             "We build the model.\n\\end{document}\n")


def setup(tmp_path: Path, monkeypatch, page_list: list[str], tex: str | None = CLEAN_TEX) -> None:
    paper = tmp_path / "paper"
    paper.mkdir(exist_ok=True)
    (paper / "main.pdf").write_bytes(b"%PDF-1.4")
    if tex is not None:
        (paper / "main.tex").write_text(tex, encoding="utf-8")
    monkeypatch.setattr(hygiene, "page_texts", lambda _pdf: page_list)
    monkeypatch.setattr(hygiene, "check_landscape", lambda _pdf: [])


def texts(result, level: str | None = None) -> str:
    return " ".join(m.message for m in result.messages if level is None or m.level == level)


def test_clean_paper_passes(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages())
    result = run_paper_hygiene_checks(tmp_path, config())
    assert result.status == "pass", texts(result)
    assert result.title == "A Continuous-Time Model of Battery Drain"


def test_notes_to_the_team_fail(tmp_path: Path, monkeypatch) -> None:
    tex = CLEAN_TEX.replace("We build the model.",
                            "In this version we fixed the units. The figures come from the Kit renderer.")
    setup(tmp_path, monkeypatch, pages(), tex=tex)
    result = run_paper_hygiene_checks(tmp_path, config())
    failed = texts(result, "fail")
    assert "[version narrative]" in failed and "[tool trace]" in failed


def test_word_built_paper_is_read_from_the_pdf(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages(extra="Compared with our previous draft, "), tex=None)
    assert "[version narrative]" in texts(run_paper_hygiene_checks(tmp_path, config()), "fail")


def test_program_log_phrases_warn_but_not_in_the_appendix(tmp_path: Path, monkeypatch) -> None:
    body = CLEAN_TEX.replace("We build the model.", "The solver took 14 ms with method='highs'.")
    setup(tmp_path, monkeypatch, pages(), tex=body)
    warned = texts(run_paper_hygiene_checks(tmp_path, config()), "warn")
    assert "millisecond runtime" in warned and "solver parameter" in warned
    appendix = CLEAN_TEX.replace("We build the model.", "We build the model.\n\\appendix\nSee run_all.py.")
    setup(tmp_path, monkeypatch, pages(), tex=appendix)
    assert "script file name" not in texts(run_paper_hygiene_checks(tmp_path, config()))


def test_hedges_need_both_count_and_rate(tmp_path: Path, monkeypatch) -> None:
    hedge = "It should be noted that this does not imply causation. "
    setup(tmp_path, monkeypatch, pages(extra=hedge * 1))        # 40 hits over ~10k words
    assert "defensive disclaimers" in texts(run_paper_hygiene_checks(tmp_path, config()), "warn")
    few = pages()
    few[5] += hedge * 2                                           # 4 hits: below the count floor
    setup(tmp_path, monkeypatch, few)
    assert "defensive disclaimers" not in texts(run_paper_hygiene_checks(tmp_path, config()))


def test_title_dash_or_length_warns_but_a_colon_does_not(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages(title="Riding the Wave: A Model of Tidal Drift"))
    assert run_paper_hygiene_checks(tmp_path, config()).status == "pass"
    setup(tmp_path, monkeypatch, pages(title="Riding the Wave — A Model of Tidal Drift"))
    assert "dash" in texts(run_paper_hygiene_checks(tmp_path, config()), "warn")
    long_title = " ".join(["Model"] * 24)
    setup(tmp_path, monkeypatch, pages(title=long_title))
    assert "24 words" in texts(run_paper_hygiene_checks(tmp_path, config()), "warn")


def test_summary_without_numbers_warns(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages(numbers="a clear ranking of the scenarios"))
    assert "carries 0 number" in texts(run_paper_hygiene_checks(tmp_path, config()), "warn")


def test_dense_pages_warn(tmp_path: Path, monkeypatch) -> None:
    setup(tmp_path, monkeypatch, pages(body_words=650))
    assert "words per page" in texts(run_paper_hygiene_checks(tmp_path, config()), "warn")


def test_landscape_pages_warn(tmp_path: Path, monkeypatch) -> None:
    class Done:
        stdout = ("Page    1 size: 612 x 792 pts (letter)\nPage    1 rot:  0\n"
                  "Page    2 size: 792 x 612 pts\nPage    2 rot:  0\n").encode()

    monkeypatch.setattr(hygiene.subprocess, "run", lambda *a, **k: Done())
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")
    messages = hygiene.check_landscape(pdf)
    assert messages and "Landscape page(s): 2" in messages[0].message


def test_toc_line_is_not_the_references_heading() -> None:
    # ProbA's contents ran onto page 3 with a bare "References" line.
    page_list = ["summary", "Contents\n1 Introduction . . . . . . . . 1",
                 "12 Recommendations . . . . . . . . . 15\n13 Limits . . . . . . . 16\n14 Charging . . . . . 18\nReferences\n",
                 "body", "body", "References\n[1] x"]
    assert references_start(page_list) == 6


def test_title_placed_above_the_official_header() -> None:
    first = ("A Continuous-Time Equivalent-Circuit Model of\nSmartphone Battery Drain\n"
             "Problem Chosen: A\nTeam Control Number: 1111111\n2026 MCM/ICM Summary Sheet\nSummary\nText")
    assert title_of(first) == "A Continuous-Time Equivalent-Circuit Model of Smartphone Battery Drain"
