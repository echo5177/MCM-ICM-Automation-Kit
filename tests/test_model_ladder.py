"""The model ladder, on the numbers that motivated it.

CUMCM 2026, question 2, annual cost in units of 10,000 yuan (lower is better), from the
post-mortem's control experiment: the submitted paper kept the model-predictive controller.
"""

from __future__ import annotations

from pathlib import Path

from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.model_ladder_checker import run_model_ladder_checks


HEADER = "req_id,rung,model,metric,value,higher_is_better,kept,note\n"
REQUIREMENTS = (
    "req_id,requirement,kind,turns_on,expected,answer,section,evidence,status\n"
    'R2,"Plan day-ahead purchases",model,"How much to over-buy",,"Annual cost 1371.60",3,,answered\n'
    'R5,"Write a memo",deliverable,,,"Memo",7,,answered\n'
)
SUBMITTED = (
    "R2,0,quantile plan + charge-when-over discharge-when-short,annual cost,1371.60,no,no,\n"
    "R2,1,stochastic program + simple rule,annual cost,1390.62,no,no,\n"
    "R2,2,stochastic program + 6-sigma margin + hourly MPC,annual cost,1467.57,no,yes,\n"
)


def config(**overrides) -> WorkflowConfig:
    return WorkflowConfig.from_mapping({"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf", **overrides})


def setup(tmp_path: Path, ladder: str | None, requirements: str | None = REQUIREMENTS,
          tex: str = "The baseline costs 1371.60 and the controller 1467.57.") -> None:
    (tmp_path / "reports").mkdir(exist_ok=True)
    (tmp_path / "paper").mkdir(exist_ok=True)
    (tmp_path / "paper" / "main.tex").write_text(tex, encoding="utf-8")
    if ladder is not None:
        (tmp_path / "reports" / "model_ladder.csv").write_text(HEADER + ladder, encoding="utf-8")
    if requirements is not None:
        (tmp_path / "reports" / "requirements.csv").write_text(requirements, encoding="utf-8")


def texts(result, level: str | None = None) -> str:
    return " || ".join(m.message for m in result.messages if level is None or m.level == level)


def test_kept_model_that_loses_to_a_simpler_rung_fails(tmp_path):
    setup(tmp_path, SUBMITTED)
    result = run_model_ladder_checks(tmp_path, config())
    assert result.status == "fail"
    assert "loses to a simpler rung (rung 0" in texts(result, "fail")
    by_rung = {row["rung"]: row for row in result.rows}
    assert by_rung[2]["vs_baseline"] == "+7.0%" and by_rung[2]["kept"] == "yes"


def test_a_recorded_reason_turns_the_failure_into_a_warning(tmp_path):
    setup(tmp_path, SUBMITTED.replace("no,yes,\n", "no,yes,required by the statement to replan hourly\n"))
    result = run_model_ladder_checks(tmp_path, config())
    assert result.status == "warn" and "the note gives a reason" in texts(result, "warn")


def test_keeping_the_winner_passes(tmp_path):
    ladder = SUBMITTED.replace("1371.60,no,no,", "1371.60,no,yes,").replace("1467.57,no,yes,", "1467.57,no,no,")
    setup(tmp_path, ladder)
    assert run_model_ladder_checks(tmp_path, config()).status == "pass"


def test_higher_is_better_is_respected(tmp_path):
    ladder = ("R2,0,grouped mean,R2 score,0.61,yes,no,\n"
              "R2,1,gradient boosting,R2 score,0.83,yes,yes,\n")
    setup(tmp_path, ladder, tex="The grouped mean reaches 0.61; boosting reaches 0.83.")
    assert run_model_ladder_checks(tmp_path, config()).status == "pass"


def test_missing_ladder_blocks_the_submission_and_names_the_requirement(tmp_path):
    setup(tmp_path, ladder=None)
    final = run_model_ladder_checks(tmp_path, config())
    assert final.status == "fail" and "for R2" in texts(final) and "R5" not in texts(final)
    assert run_model_ladder_checks(tmp_path, config(release_stage="draft")).status == "warn"


def test_modeling_requirement_without_a_rung_fails(tmp_path):
    setup(tmp_path, "R9,0,mean,rmse,1.0,no,yes,\nR9,1,fit,rmse,2.0,no,no,\n")
    assert "R2 is a modeling requirement with no rung" in texts(run_model_ladder_checks(tmp_path, config()), "fail")


def test_no_rung_zero_fails(tmp_path):
    setup(tmp_path, "R2,1,stochastic program,annual cost,1390.62,no,yes,\n")
    assert "R2: no rung 0" in texts(run_model_ladder_checks(tmp_path, config()), "fail")


def test_baseline_declared_not_applicable_needs_a_reason(tmp_path):
    setup(tmp_path, "R2,0,n/a,,,no,no,\n")
    assert "marked n/a with no reason" in texts(run_model_ladder_checks(tmp_path, config()), "fail")
    setup(tmp_path, "R2,0,n/a,,,no,no,a design task with no quantity to predict\n")
    assert run_model_ladder_checks(tmp_path, config()).status == "pass"


def test_baseline_absent_from_the_paper_warns(tmp_path):
    ladder = SUBMITTED.replace("1371.60,no,no,", "1371.60,no,yes,").replace("1467.57,no,yes,", "1467.57,no,no,")
    setup(tmp_path, ladder, tex="Our framework achieves an excellent annual cost.")
    result = run_model_ladder_checks(tmp_path, config())
    assert result.status == "warn" and "is not in the paper" in texts(result, "warn")


def test_two_kept_rungs_are_rejected(tmp_path):
    setup(tmp_path, SUBMITTED.replace("1390.62,no,no,", "1390.62,no,yes,"))
    assert "2 rung(s) marked kept" in texts(run_model_ladder_checks(tmp_path, config()), "fail")
