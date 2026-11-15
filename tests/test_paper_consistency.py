"""The Summary Sheet against the body, and headings with nothing under them.

Both come from the 2026 MCM A entry: a page cut in the last half hour left section 6 as a bare
heading while the Summary still promised an LHS-Monte Carlo sensitivity study.
"""

from __future__ import annotations

from mcm_workflow_kit.paper_hygiene_checker import (
    check_empty_sections,
    check_summary_claims,
    empty_sections_in_pdf,
    empty_sections_in_tex,
    unsupported_summary_claims,
)
from mcm_workflow_kit.paper_structure import TocEntry


SUMMARY = ("Summary\nWe predict time-to-empty for five scenarios. Local perturbations and a global "
           "LHS-Monte Carlo sensitivity study (Spearman indices) rank the parameters.\n")
TOC = "Contents\n1 Introduction . . . . . . . . . . 3\n2 Model . . . . . . . . . . 5\n"
BODY = "The battery model couples the state of charge to the terminal voltage. " * 30


def pages(body: str) -> list[str]:
    return [SUMMARY, TOC, body, body, "References\n[1] A source.\n"]


def test_summary_claim_backed_by_the_body_is_quiet():
    backed = BODY + ("We draw 2000 Latin hypercube samples and run a Monte Carlo study; the Monte "
                     "Carlo spread is 4%. Sensitivity is ranked by Spearman indices; the Spearman "
                     "index of R0 is 0.71. Sensitivity to capacity is next. LHS covers the ranges.")
    assert check_summary_claims(pages(backed), prose_end=4) == []


def test_two_unsupported_claims_fail():
    # The body never ran the study: what the 2026 entry looked like after the cut.
    messages = check_summary_claims(pages(BODY + " Sensitivity matters here."), prose_end=4)
    assert [m.level for m in messages] == ["fail"]
    assert "Monte Carlo (0 mentions" in messages[0].message
    assert "Spearman" in messages[0].message


def test_a_single_thin_term_only_warns():
    # 8 of 139 O papers name one term in the Summary that the body uses once; none names two.
    backed = BODY + ("Sensitivity is ranked by Spearman indices; the Spearman index is 0.71. "
                     "Sensitivity to capacity is next. We draw Latin hypercube (LHS) samples "
                     "in a Monte Carlo study.")
    messages = check_summary_claims([SUMMARY, TOC, backed, BODY, "References"], prose_end=4)
    assert [m.level for m in messages] == ["warn"]
    assert "Monte Carlo (1 mention in the body)" in messages[0].message


def test_hyphenated_line_break_still_counts_as_a_mention():
    missing = unsupported_summary_claims("We run a cross-validation.", "the cross-\nvalidation error; cross validation again")
    assert missing == []


def test_empty_tex_section_is_found_and_fails():
    tex = (r"\section{Model}" "\nWe build it.\n" + "x" * 200 +
           r"\section{Time-to-Empty Prediction and Uncertainty Analysis}" "\n"
           r"\section{Sensitivity and Assumptions}" "\n" + "y" * 200 + r"\end{document}")
    titles = empty_sections_in_tex(tex)
    assert titles == ["Time-to-Empty Prediction and Uncertainty Analysis"]
    messages = check_empty_sections(titles)
    assert messages[0].level == "fail" and "nothing under" in messages[0].message


def test_section_opening_into_a_subsection_is_not_empty():
    tex = (r"\section{Model}" "\n" r"\subsection{Overview}" "\n" + "x" * 200 +
           r"\subsection{Solver}" "\n" + "y" * 200 + r"\end{document}")
    assert empty_sections_in_tex(tex) == []


def test_empty_subsection_before_its_sibling_is_found():
    tex = (r"\section{Model}" "\n" r"\subsection{UQ}" "\n" r"\subsection{Solver}" "\n" + "y" * 200
           + r"\end{document}")
    assert empty_sections_in_tex(tex) == ["UQ"]


def test_pdf_fallback_needs_both_headings_in_the_table_of_contents():
    toc = [TocEntry("5", "Scenario Results", 14), TocEntry("6", "Time-to-Empty Prediction and Uncertainty Analysis", 17),
           TocEntry("7", "Sensitivity and Assumptions", 17)]
    body = ("Team # 2612345 Page 17\nTable 4: Results\n3 Europe\n4 Asia\n"
            "6 Time-to-Empty Prediction and Uncertainty Analysis\n7 Sensitivity and Assumptions\n"
            "We vary each parameter by ten percent.\n")
    found = empty_sections_in_pdf(["Summary Sheet\n", body], toc)
    assert found == ["6 Time-to-Empty Prediction and Uncertainty Analysis"]  # the table rows are not headings
