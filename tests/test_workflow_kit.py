from __future__ import annotations

import pandas as pd

from mcm_workflow_kit.data_auditor import audit_csv_file, build_data_audit
from mcm_workflow_kit.result_checker import (
    check_key_results_in_text,
    check_table_numbers,
    missing_table_numbers,
    parse_latex_graphics,
    scan_placeholders,
)
from mcm_workflow_kit.paper_qa import (
    check_required_tex_sections,
    parse_pdfinfo_pages,
    scan_latex_log,
)
from mcm_workflow_kit.diagram_checker import read_png_dimensions, run_diagram_checks
from mcm_workflow_kit.orchestrator import NodeRun, WorkflowRun, render_workflow_summary
from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.release_packet import create_release_packet
from mcm_workflow_kit.source_checker import calculate_sha256, run_source_checks
from mcm_workflow_kit.v1_gate import run_v1_gate
from mcm_workflow_kit.mcm_format_checker import (
    check_award_skeleton,
    check_figure_density,
    check_gate_config,
    check_hyperref,
    check_prose_structure,
    check_structure,
)
from mcm_workflow_kit.source_role_checker import classify_artifact, evaluate_rows
from mcm_workflow_kit.diagram_quality_checker import evaluate_diagram_json
from mcm_workflow_kit.experiment_audit import (
    DEFAULT_POLLUTION_TERMS,
    audit_figure_text,
    audit_parameter_sweeps,
    audit_random_seeds,
    run_experiment_audit,
)
from mcm_workflow_kit.judge_review_gate import run_judge_review_gate
from mcm_workflow_kit.review_rounds import (
    analyze_trajectory,
    load_rounds,
    record_review_round,
    write_review_trajectory_report,
)
from mcm_workflow_kit.v2_gate import run_v2_gate


def make_config(**overrides):
    defaults = {
        "project_pipeline_command": [],
        "raw_data_files": [],
        "paper_tex": "paper/main.tex",
        "paper_pdf": "paper/main.pdf",
        "latex_log": "paper/main.log",
        "key_results": "reports/key_results.csv",
        "figure_manifest": "reports/figure_manifest.csv",
        "figures_dirs": [],
        "tables_dir": "tables",
        "workflow_reports_dir": "reports/workflow",
        "page_target": 25,
        "page_hard_limit": 26,
        "placeholder_patterns": [],
        "release_artifacts": [],
    }
    defaults.update(overrides)
    return WorkflowConfig(**defaults)


def test_data_auditor_summarizes_csv(tmp_path):
    csv_path = tmp_path / "sample.csv"
    pd.DataFrame(
        [
            {"season": 1, "week": 1, "score": 10.0, "name": "A"},
            {"season": 1, "week": 1, "score": None, "name": "B"},
            {"season": 1, "week": 2, "score": 40.0, "name": "A"},
            {"season": 1, "week": 2, "score": 40.0, "name": "A"},
        ]
    ).to_csv(csv_path, index=False)

    result = audit_csv_file(csv_path, display_path="sample.csv")

    assert result["path"] == "sample.csv"
    assert result["rows"] == 4
    assert result["columns"] == 4
    assert result["missing_values"] == 1
    assert result["missing_by_column"]["score"] == 1
    assert result["duplicate_rows"] == 1
    assert result["numeric_summary"]["score"]["count"] == 3
    assert result["group_counts"]["season"][0]["rows"] == 4
    assert len(result["group_counts"]["season/week"]) == 2


def test_build_data_audit_uses_project_relative_paths(tmp_path):
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    csv_path = data_dir / "data.csv"
    pd.DataFrame([{"value": 1}, {"value": 2}]).to_csv(csv_path, index=False)

    result = build_data_audit(tmp_path, ["data/raw/data.csv"])

    assert result.files[0]["path"] == "data/raw/data.csv"
    assert result.files[0]["rows"] == 2


def test_source_checker_validates_manifest_and_hash(tmp_path):
    data_dir = tmp_path / "data" / "raw" / "external"
    reports_dir = tmp_path / "reports"
    data_dir.mkdir(parents=True)
    reports_dir.mkdir()
    data_path = data_dir / "source.csv"
    data_path.write_text("value\n1\n", encoding="utf-8")
    expected_hash = calculate_sha256(data_path)
    (reports_dir / "external_data_needs.md").write_text(
        "# External Data Needs\n\nOfficial test source declared.\n",
        encoding="utf-8",
    )
    (reports_dir / "data_source_manifest.csv").write_text(
        "source_id,dataset_name,source_type,publisher,url,access_date,"
        "license_or_terms,retrieval_method,local_path,sha256,why_needed,"
        "paper_usage,citation_key\n"
        "test_source,Test Source,external,Test Publisher,"
        "https://example.com/source.csv,2026-06-06,Public test terms,"
        "web_download,data/raw/external/source.csv,"
        f"{expected_hash},Validate source checker,Model input,test_source\n",
        encoding="utf-8",
    )
    config = make_config(
        data_source_manifest="reports/data_source_manifest.csv",
        external_data_needs="reports/external_data_needs.md",
        source_manifest_required=True,
        external_data_required=True,
    )

    result = run_source_checks(tmp_path, config)

    assert result.status == "pass"
    assert result.external_sources == 1
    assert result.source_rows[0]["hash_status"] == "match"


def test_source_checker_fails_on_hash_mismatch(tmp_path):
    data_dir = tmp_path / "data" / "raw" / "external"
    reports_dir = tmp_path / "reports"
    data_dir.mkdir(parents=True)
    reports_dir.mkdir()
    (data_dir / "source.csv").write_text("value\n1\n", encoding="utf-8")
    (reports_dir / "external_data_needs.md").write_text(
        "# External Data Needs\n\nOfficial test source declared.\n",
        encoding="utf-8",
    )
    (reports_dir / "data_source_manifest.csv").write_text(
        "source_id,dataset_name,source_type,publisher,url,access_date,"
        "license_or_terms,retrieval_method,local_path,sha256,why_needed,"
        "paper_usage,citation_key\n"
        "test_source,Test Source,external,Test Publisher,"
        "https://example.com/source.csv,2026-06-06,Public test terms,"
        "web_download,data/raw/external/source.csv,deadbeef,"
        "Validate source checker,Model input,test_source\n",
        encoding="utf-8",
    )
    config = make_config(
        data_source_manifest="reports/data_source_manifest.csv",
        external_data_needs="reports/external_data_needs.md",
        source_manifest_required=True,
    )

    result = run_source_checks(tmp_path, config)

    assert result.status == "fail"
    assert any("sha256 mismatch" in message.message for message in result.messages)


def test_parse_latex_graphics_handles_options():
    text = r"""
    \includegraphics[width=0.5\linewidth]{figures/generated/fig_1.png}
    \includegraphics{fig_2.png}
    """

    assert parse_latex_graphics(text) == [
        "figures/generated/fig_1.png",
        "fig_2.png",
    ]


def test_placeholder_scanner_is_case_insensitive():
    assert scan_placeholders("This still has a todo marker.", ["TODO"]) == ["TODO"]


def test_key_result_checker_matches_numeric_variants(tmp_path):
    path = tmp_path / "key_results.csv"
    pd.DataFrame(
        [
            {"metric": "rate", "value": 0.7356321839},
            {"metric": "rows", "value": 421.0},
        ]
    ).to_csv(path, index=False)

    result = check_key_results_in_text(
        path,
        "The exact-match rate is 73.56%. The data has 421 rows.",
    )

    assert [row["status"] for row in result] == ["found", "found"]


def test_table_number_checker_finds_gaps(tmp_path):
    (tmp_path / "table_1_data.tex").write_text("", encoding="utf-8")
    (tmp_path / "table_3_results.tex").write_text("", encoding="utf-8")

    numbers = check_table_numbers(tmp_path)

    assert numbers == [1, 3]
    assert missing_table_numbers(numbers) == [2]


def test_parse_pdfinfo_pages():
    assert parse_pdfinfo_pages("Title:\nPages:           26\n") == 26
    assert parse_pdfinfo_pages("Title:\n") is None


def test_latex_log_scanner_classifies_messages():
    messages = scan_latex_log(
        "LaTeX Warning: Reference `x' undefined.\n"
        "Overfull \\hbox in paragraph\n"
        "Package: rerunfilecheck 2022-07-10 v1.10 Rerun checks for auxiliary files\n"
        "! LaTeX Error: File `missing.sty' not found.\n"
    )

    assert [message.level for message in messages] == ["warn", "warn", "fail"]


def test_required_tex_sections():
    messages = check_required_tex_sections(
        r"\large \textbf{Summary}\tableofcontents References"
    )

    assert messages == []


def test_png_dimension_reader_uses_png_header(tmp_path):
    png_path = tmp_path / "sample.png"
    png_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + (200).to_bytes(4, "big")
        + (120).to_bytes(4, "big")
    )

    assert read_png_dimensions(png_path) == (200, 120)


def test_diagram_checker_requires_structured_sources(tmp_path):
    figure_dir = tmp_path / "figures" / "concept"
    source_dir = tmp_path / "figures" / "concept_src"
    report_dir = tmp_path / "reports"
    figure_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    report_dir.mkdir()
    (figure_dir / "fig.png").write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + (200).to_bytes(4, "big")
        + (120).to_bytes(4, "big")
    )
    (source_dir / "fig.svg").write_text("<svg></svg>", encoding="utf-8")
    (source_dir / "fig.json").write_text("{}", encoding="utf-8")
    (report_dir / "figure_manifest.csv").write_text(
        "figure_id,path,source_script,paper_location\n"
        "Fig. 1,figures/concept/fig.png,scripts/render_workflow_figure.py,Intro\n",
        encoding="utf-8",
    )

    config = WorkflowConfig(
        project_pipeline_command=[],
        raw_data_files=[],
        paper_tex="paper/main.tex",
        paper_pdf="paper/main.pdf",
        latex_log="paper/main.log",
        key_results="reports/key_results.csv",
        figure_manifest="reports/figure_manifest.csv",
        figures_dirs=[],
        tables_dir="tables",
        workflow_reports_dir="reports/workflow",
        page_target=25,
        page_hard_limit=26,
        placeholder_patterns=[],
        release_artifacts=[],
        diagram_sources=[
            {
                "figure_id": "Fig. 1",
                "png": "figures/concept/fig.png",
                "svg": "figures/concept_src/fig.svg",
                "json": "figures/concept_src/fig.json",
                "expected_source": "scripts/render_workflow_figure.py",
                "min_width": 100,
                "min_height": 100,
            }
        ],
    )

    result = run_diagram_checks(tmp_path, config)

    assert result.status == "pass"
    assert result.diagram_checks[0]["dimensions"] == "200x120"


def test_diagram_checker_warns_on_ai_generated_manifest_source(tmp_path):
    figure_dir = tmp_path / "figures" / "concept"
    source_dir = tmp_path / "figures" / "concept_src"
    report_dir = tmp_path / "reports"
    figure_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    report_dir.mkdir()
    (figure_dir / "fig.png").write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + (200).to_bytes(4, "big")
        + (120).to_bytes(4, "big")
    )
    (source_dir / "fig.svg").write_text("<svg></svg>", encoding="utf-8")
    (source_dir / "fig.json").write_text("{}", encoding="utf-8")
    (report_dir / "figure_manifest.csv").write_text(
        "figure_id,path,source_script,paper_location\n"
        "Fig. 1,figures/concept/fig.png,AI-generated concept figure,Intro\n",
        encoding="utf-8",
    )

    config = WorkflowConfig(
        project_pipeline_command=[],
        raw_data_files=[],
        paper_tex="paper/main.tex",
        paper_pdf="paper/main.pdf",
        latex_log="paper/main.log",
        key_results="reports/key_results.csv",
        figure_manifest="reports/figure_manifest.csv",
        figures_dirs=[],
        tables_dir="tables",
        workflow_reports_dir="reports/workflow",
        page_target=25,
        page_hard_limit=26,
        placeholder_patterns=[],
        release_artifacts=[],
        diagram_sources=[
            {
                "figure_id": "Fig. 1",
                "png": "figures/concept/fig.png",
                "svg": "figures/concept_src/fig.svg",
                "json": "figures/concept_src/fig.json",
                "min_width": 100,
                "min_height": 100,
            }
        ],
    )

    result = run_diagram_checks(tmp_path, config)

    assert result.status == "warn"
    assert "AI-generated" in result.messages[0].message


def test_workflow_summary_renders_node_statuses():
    run = WorkflowRun(
        mode="check",
        project_root=".",
        run_dir="runs/test",
        started_at="start",
        finished_at="finish",
        status="pass",
        nodes=[
            NodeRun(
                name="data_auditor",
                status="pass",
                started_at="start",
                finished_at="finish",
                duration_seconds=0.5,
                detail="ok",
            )
        ],
    )

    lines = render_workflow_summary(run)

    assert "| data_auditor | pass | 0.500s | ok |" in lines


def test_v1_gate_classifies_warned_nodes_and_team_placeholder(tmp_path):
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text(
        r"\newcommand{\Team}{1111111}",
        encoding="utf-8",
    )

    config = WorkflowConfig(
        project_pipeline_command=[],
        raw_data_files=[],
        paper_tex="paper/main.tex",
        paper_pdf="paper/main.pdf",
        latex_log="paper/main.log",
        key_results="reports/key_results.csv",
        figure_manifest="reports/figure_manifest.csv",
        figures_dirs=[],
        tables_dir="tables",
        workflow_reports_dir="reports/workflow",
        page_target=25,
        page_hard_limit=26,
        placeholder_patterns=[],
        release_artifacts=[],
        team_control_number_placeholders=["1111111"],
    )
    nodes = [
        NodeRun(
            name="paper_qa",
            status="warn",
            started_at="start",
            finished_at="finish",
            duration_seconds=0.1,
            detail="page target warning",
        )
    ]

    result = run_v1_gate(tmp_path, config, nodes)

    assert result.status == "warn"
    assert "paper_qa" in result.messages[0].message
    assert result.known_warnings == [
        "Team control number placeholder remains pending: 1111111"
    ]


def test_release_packet_copies_configured_artifacts(tmp_path):
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "key_results.csv").write_text(
        "metric,value\nx,1\n",
        encoding="utf-8",
    )

    config = WorkflowConfig(
        project_pipeline_command=[],
        raw_data_files=[],
        paper_tex="paper/main.tex",
        paper_pdf="paper/main.pdf",
        latex_log="paper/main.log",
        key_results="reports/key_results.csv",
        figure_manifest="reports/figure_manifest.csv",
        figures_dirs=[],
        tables_dir="tables",
        workflow_reports_dir="reports/workflow",
        page_target=25,
        page_hard_limit=26,
        placeholder_patterns=[],
        release_artifacts=[
            "paper/main.pdf",
            "reports",
            "missing.txt",
        ],
    )

    packet = create_release_packet(tmp_path, config, timestamp="test-release")

    assert (packet.release_dir / "paper" / "main.pdf").exists()
    assert (packet.release_dir / "reports" / "key_results.csv").exists()
    assert (packet.release_dir / "release_manifest.csv").exists()
    assert (packet.release_dir / "final_checklist.md").exists()
    assert [entry.status for entry in packet.entries] == [
        "copied",
        "copied",
        "missing",
    ]


# ---------------------------------------------------------------------------
# v2 gate: contest-quality nodes (regression teeth for the ProbA failure)
# ---------------------------------------------------------------------------


def _levels(messages):
    return [m.level for m in messages]


# ---- mcm_format_checker ----


def test_format_gate_config_flags_lowering():
    config = make_config(
        page_target=14, page_hard_limit=26, contest_page_limit=25, min_page_target=20
    )
    messages = check_gate_config(config)
    assert "fail" in _levels(messages)
    text = " ".join(m.message for m in messages)
    assert "page_target" in text and "page_hard_limit" in text


def test_format_gate_config_passes_serious_target():
    config = make_config(
        page_target=22, page_hard_limit=25, contest_page_limit=25, min_page_target=20
    )
    assert check_gate_config(config) == []


def test_format_hyperref_requires_hidelinks():
    assert "fail" in _levels(check_hyperref(r"\usepackage{hyperref}"))
    assert check_hyperref(r"\usepackage[hidelinks]{hyperref}") == []
    assert check_hyperref("no hyperref here") == []


def test_format_structure_requires_summary_toc_refs():
    bad = check_structure("just some text")
    assert _levels(bad).count("fail") >= 3
    good = check_structure(r"Summary \tableofcontents References AI Use Report")
    assert "fail" not in _levels(good)


# ---- check_prose_structure (adapted from MathModelAgent writing_check) ----

_BODY = "x" * 600  # enough prose to clear the thin-section floor


def test_prose_structure_clean_paper_is_silent():
    tex = (
        r"\section{Intro}" + _BODY
        + r"\section{Model}" + _BODY
        + r"\end{document}"
    )
    assert check_prose_structure(tex, make_config()) == []


def test_prose_structure_flags_duplicate_section_titles():
    tex = (
        r"\section{Results}" + _BODY
        + r"\section{Results}" + _BODY
        + r"\end{document}"
    )
    messages = check_prose_structure(tex, make_config())
    assert "fail" in _levels(messages)
    assert "Results" in " ".join(m.message for m in messages)


def test_prose_structure_warns_on_list_overuse():
    tex = r"\section{Intro}" + _BODY + (r"\begin{itemize}\item a\end{itemize}" * 13)
    messages = check_prose_structure(tex, make_config(max_list_blocks=12))
    assert "warn" in _levels(messages)


def test_prose_structure_warns_on_stacked_floats():
    tex = (
        r"\section{Results}" + _BODY
        + r"\begin{figure}\includegraphics{a}\caption{A}\end{figure}"
        + r"\begin{figure}\includegraphics{b}\caption{B}\end{figure}"
        + _BODY
        + r"\end{document}"
    )
    messages = check_prose_structure(tex, make_config())
    assert any("stack" in m.message for m in messages if m.level == "warn")


def test_prose_structure_warns_on_thin_section():
    tex = r"\section{Intro}" + _BODY + r"\section{Stub}tiny\section{Big}" + _BODY + r"\end{document}"
    messages = check_prose_structure(tex, make_config())
    assert any("Stub" in m.message for m in messages if m.level == "warn")


# ---- award skeleton + figure density (from award_patterns.md evidence) ----

_AWARD_TEX = (
    r"\section{Introduction}"
    r"\subsection{Restatement of the Problem}"
    r"\subsection{Our Work}"
    r"\section{Assumptions and Justification}"
    r"\section{Notation}"
    r"\section{Sensitivity Analysis}"
    r"\section{Strengths and Weaknesses}"
    " Keywords: battery; sensitivity."
)


def test_award_skeleton_complete_paper_is_silent():
    assert check_award_skeleton(_AWARD_TEX) == []


def test_award_skeleton_missing_sensitivity_fails():
    tex = _AWARD_TEX.replace(r"\section{Sensitivity Analysis}", "")
    messages = check_award_skeleton(tex)
    assert "fail" in _levels(messages)
    assert any("Sensitivity" in m.message for m in messages)


def test_award_skeleton_missing_assumptions_fails():
    tex = _AWARD_TEX.replace(r"\section{Assumptions and Justification}", "")
    assert "fail" in _levels(check_award_skeleton(tex))


def test_award_skeleton_missing_notation_only_warns():
    tex = _AWARD_TEX.replace(r"\section{Notation}", "")
    messages = check_award_skeleton(tex)
    assert "warn" in _levels(messages)
    assert "fail" not in _levels(messages)


def test_award_skeleton_missing_keywords_warns():
    tex = _AWARD_TEX.replace(" Keywords: battery; sensitivity.", "")
    messages = check_award_skeleton(tex)
    assert any("Keywords" in m.message for m in messages if m.level == "warn")


def test_award_skeleton_missing_strengths_fails():
    tex = _AWARD_TEX.replace(r"\section{Strengths and Weaknesses}", "")
    messages = check_award_skeleton(tex)
    assert "fail" in _levels(messages)
    assert any("Strengths" in m.message for m in messages)


def test_figure_density_ok_at_o_paper_level():
    # 16 figures over 25 counted pages = 0.64/page, inside the O band.
    tex = r"\begin{figure}x\end{figure}" * 16
    assert check_figure_density(tex, 26, make_config(ai_report_pages=1)) == []


def test_figure_density_warns_just_below_o_floor():
    # 14 figures over 25 counted pages = 0.56/page: passable, but thinner than
    # every O paper measured. The floor is deliberately set to catch this.
    tex = r"\begin{figure}x\end{figure}" * 14
    messages = check_figure_density(tex, 26, make_config(ai_report_pages=1))
    assert "warn" in _levels(messages)
    assert "0.56/page" in messages[0].message


def test_figure_density_warns_when_visually_thin():
    tex = r"\begin{figure}x\end{figure}" * 5  # 5/25 = 0.20/page
    messages = check_figure_density(tex, 26, make_config(ai_report_pages=1))
    assert "warn" in _levels(messages)
    assert "0.20/page" in messages[0].message


# ---- source_role_checker ----


def test_classify_artifact():
    assert classify_artifact("a/b.csv") == "data"
    assert classify_artifact("a/b.md") == "card"
    assert classify_artifact("a/b.pdf") == "document"


def test_source_role_flags_card_as_data():
    rows = [
        {
            "source_id": "calce",
            "source_type": "external",
            "local_path": "data/raw/external/calce.md",
            "why_needed": "impedance and temperature evidence",
            "paper_usage": "validation",
            "license_or_terms": "open access",
            "dataset_name": "CALCE",
        }
    ]
    messages, _ = evaluate_rows(rows, make_config(external_data_required=True))
    assert "fail" in _levels(messages)


def test_source_role_passes_real_open_dataset():
    rows = [
        {
            "source_id": "calce",
            "source_type": "external",
            "role": "true_dataset",
            "local_path": "data/raw/external/calce_capacity.csv",
            "why_needed": "capacity fade evidence",
            "paper_usage": "validation",
            "license_or_terms": "open access",
            "dataset_name": "CALCE",
        }
    ]
    messages, _ = evaluate_rows(rows, make_config(external_data_required=True))
    assert "fail" not in _levels(messages)


# ---- diagram_quality_checker ----

SPARSE_DIAGRAM = {
    "nodes": [{"label": f"n{i}", "x": 0, "y": 0} for i in range(7)],
    "edges": [{"from": "n0", "to": "n1"}],
}

DENSE_DIAGRAM = {
    "title": "Workflow",
    "stages": [{"id": s} for s in ["inputs", "params", "model", "solve", "validate"]],
    "nodes": [
        {"stage": "inputs", "title": "Raw data", "body": "observations", "artifact": "data.csv"},
        {"stage": "inputs", "title": "Usage logs", "body": "measurement input", "artifact": "logs.csv"},
        {"stage": "params", "title": "Parameter estimation", "body": "calibrate from data", "artifact": "params.csv"},
        {"stage": "model", "title": "Continuous-time ODE", "body": "state equation dSOC/dt", "artifact": "model.py"},
        {"stage": "model", "title": "Power constraint", "body": "governing equation", "artifact": "model.py"},
        {"stage": "solve", "title": "Numerical solver", "body": "integrate the ODE", "artifact": "solve.py"},
        {"stage": "validate", "title": "Validation", "body": "uncertainty and sensitivity", "artifact": "val.csv"},
        {"stage": "validate", "title": "Diagnostics", "body": "baseline check", "artifact": "diag.csv"},
        {"stage": "outputs", "title": "TTE predictions", "body": "result output", "artifact": "tte.csv"},
        {"stage": "outputs", "title": "Recommendations", "body": "policy decision", "artifact": "rec.md"},
    ],
    "edges": [
        {"from": "a", "to": "b", "label": "x"},
        {"from": "b", "to": "a", "label": "loop", "kind": "feedback"},
    ],
}


def test_diagram_quality_flags_sparse():
    messages, summary = evaluate_diagram_json("Fig. 1", SPARSE_DIAGRAM, make_config())
    assert "fail" in _levels(messages)
    assert summary["bands"] == 0
    assert summary["nodes"] == 7


def test_diagram_quality_passes_dense():
    messages, summary = evaluate_diagram_json("Fig. 1", DENSE_DIAGRAM, make_config())
    assert "fail" not in _levels(messages)
    assert summary["bands"] >= 3
    assert summary["content_fraction"] >= 0.6


# ---- experiment_audit ----

# The real defect from the award paper this check exists for (2023 MCM Problem B,
# team 2316192): `i` is never used and the body uses the range bound `a_j`, so the
# "sweep of alpha over (0, 90)" is 89 runs at a fixed 90 degrees.
_REAL_SWEEP_BUG = """
import math
a_j = 90
res_lst = []
for i in range(1, a_j):
    a = a_j * math.pi / 180
    res_lst.append(math.sin(a))
"""

_FIXED_SWEEP = """
import math
a_j = 90
res_lst = []
for i in range(1, a_j):
    a = i * math.pi / 180
    res_lst.append(math.sin(a))
"""


def test_sweep_audit_catches_the_real_award_paper_bug():
    messages = audit_parameter_sweeps(_REAL_SWEEP_BUG, "test-data.py")
    assert "fail" in _levels(messages)
    text = " ".join(m.message for m in messages)
    assert "a_j" in text and "not sweeping" in text


def test_sweep_audit_silent_when_loop_variable_is_used():
    assert audit_parameter_sweeps(_FIXED_SWEEP, "test-data.py") == []


def test_sweep_audit_allows_underscore_repetition_loop():
    src = "total = 0\nfor _ in range(100):\n    total += 1\n"
    assert audit_parameter_sweeps(src, "mc.py") == []


def test_sweep_audit_warns_but_does_not_fail_on_plain_unused_index():
    # A Monte Carlo repetition loop written with `i`: worth a nudge, not a failure.
    src = "total = 0\nfor i in range(100):\n    total += 1\n"
    messages = audit_parameter_sweeps(src, "mc.py")
    assert _levels(messages) == ["warn"]


def test_sweep_audit_survives_unparseable_file():
    messages = audit_parameter_sweeps("def broken(:\n", "bad.py")
    assert _levels(messages) == ["warn"]


def test_seed_audit_flags_unseeded_randomness():
    src = "import numpy as np\nx = np.random.normal(0, 1, 100)\n"
    assert "warn" in _levels(audit_random_seeds(src, "sim.py"))


def test_seed_audit_accepts_seeded_variants():
    for src in (
        "import numpy as np\nnp.random.seed(7)\nx = np.random.normal(0, 1)\n",
        "import numpy as np\nrng = np.random.default_rng(20260204)\nx = rng.normal()\n",
        "import random\nrandom.seed(1)\ny = random.random()\n",
    ):
        assert audit_random_seeds(src, "sim.py") == []


def test_seed_audit_ignores_deterministic_code():
    assert audit_random_seeds("x = 1 + 1\n", "calc.py") == []


def test_figure_text_audit_catches_template_pollution():
    # The real case: a wildlife-conservation workflow figure still carrying
    # neural-architecture-search labels.
    svg = "<svg><text>Super-net w/o pretrained initialization</text>" \
          "<text>Kernel-level</text></svg>"
    messages = audit_figure_text(svg, "figures/concept_src/flow.svg", DEFAULT_POLLUTION_TERMS)
    assert "fail" in _levels(messages)
    assert "super-net" in messages[0].message


def test_figure_text_audit_silent_on_clean_figure():
    svg = "<svg><text>State of charge</text><text>Validation</text></svg>"
    assert audit_figure_text(svg, "figures/f.svg", DEFAULT_POLLUTION_TERMS) == []


def test_experiment_audit_end_to_end(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "sweep.py").write_text(_REAL_SWEEP_BUG, encoding="utf-8")
    (tmp_path / "figures").mkdir()
    (tmp_path / "figures" / "flow.svg").write_text(
        "<svg><text>Backbone Kernel-level</text></svg>", encoding="utf-8"
    )

    result = run_experiment_audit(tmp_path, make_config())

    assert result.status == "fail"
    assert result.scanned_scripts == 1
    assert result.scanned_figures == 1
    assert len(result.findings) == 2


def test_experiment_audit_passes_on_clean_project(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "model.py").write_text(_FIXED_SWEEP, encoding="utf-8")

    result = run_experiment_audit(tmp_path, make_config())

    assert result.status == "pass"


# ---- judge_review_gate ----

GOOD_REVIEW = """# Judge-Style Review
RELEASE: APPROVED
SCORE format_presentation: 4
SCORE problem_fit: 5
SCORE modeling_quality: 4
SCORE data_evidence: 4
SCORE results_interpretation: 5
SCORE originality_insight: 4
"""


def _write_review(tmp_path, body):
    path = tmp_path / "reports" / "workflow" / "judge_review.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_judge_review_missing_fails(tmp_path):
    result = run_judge_review_gate(tmp_path, make_config())
    assert result.status == "fail"
    assert result.release == "MISSING"


def test_judge_review_pass(tmp_path):
    # An approval only counts for the PDF it judged: bind it by SHA-256.
    import hashlib

    pdf = tmp_path / "paper" / "main.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4 reviewed")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    _write_review(tmp_path, GOOD_REVIEW.replace("RELEASE:", f"PAPER_SHA256: {digest}\nRELEASE:", 1))
    result = run_judge_review_gate(tmp_path, make_config())
    assert result.status == "pass"
    assert result.release == "APPROVED"


def test_judge_review_low_score_fails(tmp_path):
    _write_review(tmp_path, GOOD_REVIEW.replace("SCORE data_evidence: 4", "SCORE data_evidence: 2"))
    assert run_judge_review_gate(tmp_path, make_config()).status == "fail"


def test_judge_review_blocked_fails(tmp_path):
    _write_review(tmp_path, GOOD_REVIEW.replace("RELEASE: APPROVED", "RELEASE: BLOCKED"))
    assert run_judge_review_gate(tmp_path, make_config()).status == "fail"


# ---- review_rounds (trajectory ledger) ----

_JUDGE_CATS = [
    "format_presentation",
    "problem_fit",
    "modeling_quality",
    "data_evidence",
    "results_interpretation",
    "originality_insight",
]


def _review_body(score: int, release: str = "APPROVED") -> str:
    lines = ["# Judge-Style Review", f"RELEASE: {release}"]
    lines += [f"SCORE {cat}: {score}" for cat in _JUDGE_CATS]
    return "\n".join(lines) + "\n"


def test_review_round_records_and_dedups(tmp_path):
    config = make_config()
    _write_review(tmp_path, _review_body(4))
    first = record_review_round(tmp_path, config)
    assert first is not None and first["round"] == 1 and first["mean"] == 4.0
    # Re-running on the unchanged review must not inflate the ledger.
    assert record_review_round(tmp_path, config) is None
    assert len(load_rounds(tmp_path, config)) == 1


def test_review_round_appends_on_change(tmp_path):
    config = make_config()
    _write_review(tmp_path, _review_body(3))
    record_review_round(tmp_path, config)
    _write_review(tmp_path, _review_body(4))
    second = record_review_round(tmp_path, config)
    assert second["round"] == 2
    rounds = load_rounds(tmp_path, config)
    assert [r["round"] for r in rounds] == [1, 2]
    assert [r["mean"] for r in rounds] == [3.0, 4.0]


def test_trajectory_flags_regression_as_warn(tmp_path):
    config = make_config()
    _write_review(tmp_path, _review_body(4))
    record_review_round(tmp_path, config)
    _write_review(tmp_path, _review_body(3))  # a revision that lowered scores
    record_review_round(tmp_path, config)
    result = analyze_trajectory(load_rounds(tmp_path, config), config)
    assert result.status == "warn"
    assert any("regress" in m.message.lower() for m in result.messages)


def test_trajectory_no_warn_on_improvement(tmp_path):
    config = make_config()
    _write_review(tmp_path, _review_body(3))
    record_review_round(tmp_path, config)
    _write_review(tmp_path, _review_body(5))
    record_review_round(tmp_path, config)
    result = analyze_trajectory(load_rounds(tmp_path, config), config)
    assert result.status == "pass"
    assert not any(m.level == "warn" for m in result.messages)


def test_trajectory_missing_review_is_graceful(tmp_path):
    config = make_config()
    assert record_review_round(tmp_path, config) is None
    result = write_review_trajectory_report(tmp_path, config)
    assert result.status == "pass"
    assert result.rounds == []
    assert (tmp_path / "reports" / "workflow" / "review_trajectory_report.md").exists()


# ---- v2_gate ----


class _FakeNode:
    def __init__(self, name, status):
        self.name = name
        self.status = status
        self.detail = f"{name} {status}"


def _all_nodes(status_map):
    names = [
        "source_checker",
        "source_role_checker",
        "data_auditor",
        "result_checker",
        "experiment_audit",
        "diagram_checker",
        "diagram_quality_checker",
        "paper_qa",
        "mcm_format_checker",
        "paper_hygiene_checker",
        "submission_checker",
        "visual_qa_packet",
        "judge_review_gate",
        "v1_gate",
    ]
    return [_FakeNode(n, status_map.get(n, "pass")) for n in names]


def test_v2_gate_blocks_on_quality_fail(tmp_path):
    result = run_v2_gate(tmp_path, make_config(), _all_nodes({"diagram_quality_checker": "fail"}))
    assert result.status == "fail"
    assert result.contest_ready is False


def test_v2_gate_passes_when_all_pass(tmp_path):
    result = run_v2_gate(tmp_path, make_config(), _all_nodes({}))
    assert result.status == "pass"
    assert result.contest_ready is True
