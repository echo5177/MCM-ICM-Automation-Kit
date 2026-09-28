from __future__ import annotations

import hashlib
from pathlib import Path

from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.judge_review_gate import run_judge_review_gate
from mcm_workflow_kit.v2_gate import run_v2_gate


GOOD = """# Judge-Style Review
PAPER_SHA256: {sha}
RELEASE: APPROVED
SCORE format_presentation: 4
SCORE problem_fit: 5
SCORE modeling_quality: 4
SCORE data_evidence: 4
SCORE results_interpretation: 5
SCORE originality_insight: 4
"""


def config(**overrides) -> WorkflowConfig:
    base = {"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf"}
    base.update(overrides)
    return WorkflowConfig.from_mapping(base)


def _pdf(tmp_path: Path, content: bytes = b"%PDF-1.4 v1") -> str:
    pdf = tmp_path / "paper" / "main.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _review(tmp_path: Path, body: str) -> None:
    path = tmp_path / "reports" / "workflow" / "judge_review.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_default_stage_is_final_and_unknown_values_count_as_final() -> None:
    assert config().is_final
    assert config(release_stage="Final").is_final
    assert config(release_stage="drafty").is_final
    assert not config(release_stage=" Draft ").is_final


def test_final_bound_review_passes(tmp_path: Path) -> None:
    sha = _pdf(tmp_path)
    _review(tmp_path, GOOD.format(sha=sha))
    result = run_judge_review_gate(tmp_path, config())
    assert result.status == "pass"
    assert result.pdf_sha256 == sha == result.review_sha256


def test_final_unbound_review_fails_and_names_the_current_hash(tmp_path: Path) -> None:
    sha = _pdf(tmp_path)
    _review(tmp_path, GOOD.replace("PAPER_SHA256: {sha}\n", ""))
    result = run_judge_review_gate(tmp_path, config())
    assert result.status == "fail"
    assert sha in " ".join(m.message for m in result.messages)


def test_final_stale_review_fails_after_a_rebuild(tmp_path: Path) -> None:
    old = _pdf(tmp_path, b"%PDF-1.4 v1")
    _review(tmp_path, GOOD.format(sha=old))
    _pdf(tmp_path, b"%PDF-1.4 v2")
    result = run_judge_review_gate(tmp_path, config())
    assert result.status == "fail"
    assert "different PDF" in " ".join(m.message for m in result.messages)


def test_draft_missing_stale_or_blocked_review_only_warns(tmp_path: Path) -> None:
    draft = config(release_stage="draft")
    assert run_judge_review_gate(tmp_path, draft).status == "warn"
    old = _pdf(tmp_path, b"%PDF-1.4 v1")
    _review(tmp_path, GOOD.format(sha=old).replace("APPROVED", "BLOCKED"))
    _pdf(tmp_path, b"%PDF-1.4 v2")
    result = run_judge_review_gate(tmp_path, draft)
    assert result.status == "warn"
    assert all(m.message.startswith("(draft; blocks at final)") for m in result.messages)


class _Node:
    def __init__(self, name: str, status: str) -> None:
        self.name, self.status, self.detail = name, status, ""


NODES = ["source_checker", "source_role_checker", "data_auditor", "result_checker",
         "experiment_audit", "diagram_checker", "diagram_quality_checker", "paper_qa",
         "mcm_format_checker", "paper_hygiene_checker", "submission_checker", "visual_qa_packet", "judge_review_gate",
         "v1_gate"]


def test_draft_v2_gate_lists_blockers_but_never_reports_ready(tmp_path: Path) -> None:
    nodes = [_Node(n, "fail" if n == "judge_review_gate" else "pass") for n in NODES]
    result = run_v2_gate(tmp_path, config(release_stage="draft"), nodes)
    assert result.contest_ready is False and result.stage == "draft"
    assert result.status == "warn"
    assert any("(blocks at final)" in m.message and "judge_review_gate" in m.message
               for m in result.messages)
    clean = run_v2_gate(tmp_path, config(release_stage="draft"), [_Node(n, "pass") for n in NODES])
    assert clean.contest_ready is False


def test_final_v2_gate_still_blocks(tmp_path: Path) -> None:
    nodes = [_Node(n, "fail" if n == "judge_review_gate" else "pass") for n in NODES]
    result = run_v2_gate(tmp_path, config(), nodes)
    assert result.status == "fail" and result.contest_ready is False
