from __future__ import annotations

from pathlib import Path

from mcm_workflow_kit import ai_use_checker as ai
from mcm_workflow_kit.ai_use_checker import build_report_tex, name_tokens, run_ai_use_checks
from mcm_workflow_kit.config import WorkflowConfig


HEADER = "tool,version,purpose,used_for,verified_by,query,output\n"
LOG = (
    "Anthropic Claude Code,Claude Fable 5.2,Code and experiments,src/ and scripts/run_all.py,"
    "key results re-derived by hand for two scenarios,,\n"
    "Anthropic Claude Code,Claude Fable 5.2,Drafting and revising text,sections 3 to 6,"
    "every paragraph read and edited by the team,,\n"
    "DeepL Translator,2027-01 web version,Translation,two paragraphs of section 1,compared with the source,,\n"
)
BODY = ["Summary Sheet\n", "Contents\n1 Introduction . . . . . . . . . . 3\n", "Team # 2612345 Page 3\nBody.\n"]
REFS = "Team # 2612345 Page 22\nReferences\n[1] A source.\n[9] Anthropic. Claude Code (Claude Fable 5.2). 2027.\n[10] DeepL SE. DeepL Translator. 2027.\n"
REPORT = ("Report on Use of AI\n1. Anthropic Claude Code (Claude Fable 5.2)\nCode and experiments.\n"
          "2. DeepL Translator\nTranslation of two paragraphs.\n")


def config(**overrides) -> WorkflowConfig:
    return WorkflowConfig.from_mapping({"paper_tex": "paper/main.tex", "paper_pdf": "paper/main.pdf", **overrides})


def setup(tmp_path: Path, monkeypatch, log: str | None, pages: list[str] | None = None) -> None:
    (tmp_path / "reports").mkdir(exist_ok=True)
    (tmp_path / "paper").mkdir(exist_ok=True)
    (tmp_path / "paper" / "main.pdf").write_bytes(b"%PDF-1.4")
    if log is not None:
        (tmp_path / "reports" / "ai_use_log.csv").write_text(HEADER + log, encoding="utf-8")
    monkeypatch.setattr(ai, "page_texts", lambda _pdf: BODY + [REFS, REPORT] if pages is None else pages)


def texts(result, level: str | None = None) -> str:
    return " || ".join(m.message for m in result.messages if level is None or m.level == level)


def test_every_logged_tool_disclosed_and_cited_passes(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, LOG)
    result = run_ai_use_checks(tmp_path, config())
    assert result.status == "pass"
    assert {t["tool"]: t["in_report"] for t in result.tools} == {
        "Anthropic Claude Code": "yes", "DeepL Translator": "yes"}


def test_tool_in_the_log_but_not_in_the_report_fails(tmp_path, monkeypatch):
    # The CUMCM 2026 declaration listed two tools; a third had been used.
    setup(tmp_path, monkeypatch, LOG + "OpenAI ChatGPT,GPT-5,Checklist for the submission,release checklist,read by the team,,\n")
    result = run_ai_use_checks(tmp_path, config())
    assert result.status == "fail" and "OpenAI ChatGPT is in the log and not in the Report" in texts(result, "fail")
    assert run_ai_use_checks(tmp_path, config(release_stage="draft")).status == "warn"


def test_logged_tools_with_no_report_in_the_paper_fail(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, LOG, pages=BODY + [REFS])
    assert "has no 'Report on Use of AI'" in texts(run_ai_use_checks(tmp_path, config()), "fail")


def test_tool_missing_from_the_reference_list_warns(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, LOG, pages=BODY + [REFS.replace("[10] DeepL SE. DeepL Translator. 2027.\n", ""), REPORT])
    result = run_ai_use_checks(tmp_path, config())
    assert result.status == "warn" and "DeepL Translator is not in the reference list" in texts(result, "warn")


def test_missing_or_empty_log_blocks_the_submission(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, None)
    assert "No AI use log" in texts(run_ai_use_checks(tmp_path, config()), "fail")
    setup(tmp_path, monkeypatch, "[product and vendor],[model],[purpose],[where],[how],,\n")
    assert "has no entry yet" in texts(run_ai_use_checks(tmp_path, config()), "fail")


def test_unverified_output_warns(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, LOG.replace("compared with the source", ""))
    assert "`verified_by` is empty" in texts(run_ai_use_checks(tmp_path, config()), "warn")


def test_no_ai_declared(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, None, pages=BODY + [REFS])
    assert run_ai_use_checks(tmp_path, config(ai_tools_used=False)).status == "pass"


def test_name_tokens_drop_vendor_words():
    assert name_tokens("Anthropic Claude Code") == ["claude"]
    assert name_tokens("OpenAI ChatGPT") == ["chatgpt"]
    assert name_tokens("GitHub Copilot") == ["copilot"]


def test_report_is_built_from_the_log_one_item_per_tool():
    rows = [dict(zip(HEADER.strip().split(","), line.split(","))) for line in LOG.strip().split("\n")]
    tex = build_report_tex(rows)
    assert tex.count(r"\item \textbf{") == 2
    assert r"Anthropic Claude Code (Claude Fable 5.2)" in tex
    assert r"scripts/run\_all.py" in tex and "Checked by the team" in tex
