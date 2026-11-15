from __future__ import annotations

from pathlib import Path

from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.param_ledger import run_param_ledger_checks


HEADER = "symbol,meaning,value,unit,origin,source,used_in,sensitivity,note\n"
MANIFEST = "source_id,dataset_name\ncalce_ocv_25c,CALCE OCV test at 25C\n"
TEX = (r"\begin{document}Body." "\n" r"\begin{thebibliography}{9}\bibitem{carroll2010} Carroll and Heiser."
       r"\end{thebibliography}\end{document}")
GOOD = (
    "Q_max,cell capacity,2.0,Ah,dataset,calce_ocv_25c,tab:params,,\n"
    "P_scr,screen power at full brightness,1.2,W,literature,carroll2010,fig:breakdown,,\n"
    "V_cut,cutoff voltage,3.0,V,statement,page 2: 'shuts down at the cutoff',sec:tte,,\n"
    "eta,converter efficiency,0.9,-,assumed,,fig:tte,fig:tornado,\n"
)


def config(**overrides) -> WorkflowConfig:
    return WorkflowConfig.from_mapping({"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf", **overrides})


def setup(tmp_path: Path, ledger: str | None) -> None:
    (tmp_path / "reports").mkdir(exist_ok=True)
    (tmp_path / "paper").mkdir(exist_ok=True)
    (tmp_path / "paper" / "main.tex").write_text(TEX, encoding="utf-8")
    (tmp_path / "reports" / "data_source_manifest.csv").write_text(MANIFEST, encoding="utf-8")
    if ledger is not None:
        (tmp_path / "reports" / "param_ledger.csv").write_text(HEADER + ledger, encoding="utf-8")


def texts(result, level: str | None = None) -> str:
    return " || ".join(m.message for m in result.messages if level is None or m.level == level)


def test_complete_ledger_passes(tmp_path):
    setup(tmp_path, GOOD)
    result = run_param_ledger_checks(tmp_path, config())
    assert result.status == "pass" and len(result.rows) == 4


def test_missing_ledger_blocks_the_submission_unless_declared_unneeded(tmp_path):
    setup(tmp_path, None)
    assert run_param_ledger_checks(tmp_path, config()).status == "fail"
    assert run_param_ledger_checks(tmp_path, config(release_stage="draft")).status == "warn"
    assert run_param_ledger_checks(tmp_path, config(param_ledger_required=False)).status == "pass"


def test_template_row_alone_is_not_a_ledger(tmp_path):
    setup(tmp_path, "[R_0],[what the symbol means],,[unit],[statement],[page],[figure],,\n")
    assert "only the template row" in texts(run_param_ledger_checks(tmp_path, config()), "fail")


def test_blank_unit_is_rejected_and_a_dash_is_accepted(tmp_path):
    setup(tmp_path, GOOD.replace("0.9,-,assumed", "0.9,,assumed"))
    assert "eta: no unit" in texts(run_param_ledger_checks(tmp_path, config()), "fail")


def test_source_must_exist_where_it_claims_to(tmp_path):
    setup(tmp_path, GOOD.replace("calce_ocv_25c,tab", "nasa_aging,tab").replace("carroll2010,fig", "powertutor,fig"))
    failed = texts(run_param_ledger_checks(tmp_path, config()), "fail")
    assert "Q_max: source 'nasa_aging' is not a source_id" in failed
    assert "P_scr: citation key 'powertutor' is not in the paper's reference list" in failed


def test_same_symbol_with_two_values_fails(tmp_path):
    setup(tmp_path, GOOD + "Q_max,cell capacity,2.2,Ah,dataset,calce_ocv_25c,tab:params,,\n")
    assert "Q_max is entered twice with different values (2.0 and 2.2)" in texts(
        run_param_ledger_checks(tmp_path, config()), "fail")


def test_assumed_value_nobody_varies_warns(tmp_path):
    setup(tmp_path, GOOD.replace("fig:tte,fig:tornado,", "fig:tte,,"))
    result = run_param_ledger_checks(tmp_path, config())
    assert result.status == "warn" and "eta is assumed and nothing varies it" in texts(result, "warn")


def test_mostly_assumed_parameters_warn(tmp_path):
    rows = "".join(f"p{i},a parameter,1.0,-,assumed,,fig:x,fig:tornado,\n" for i in range(3))
    setup(tmp_path, rows + "Q_max,cell capacity,2.0,Ah,dataset,calce_ocv_25c,tab:params,,\n")
    assert "3 of 4 parameters are assumed" in texts(run_param_ledger_checks(tmp_path, config()), "warn")
