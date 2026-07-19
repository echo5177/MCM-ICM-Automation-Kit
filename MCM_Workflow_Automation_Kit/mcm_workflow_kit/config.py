from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


KIT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = KIT_ROOT / "workflow_config.json"


@dataclass(frozen=True)
class WorkflowConfig:
    project_pipeline_command: list[str]
    raw_data_files: list[str]
    paper_tex: str
    paper_pdf: str
    latex_log: str
    key_results: str
    figure_manifest: str
    figures_dirs: list[str]
    tables_dir: str
    workflow_reports_dir: str
    page_target: int
    page_hard_limit: int
    placeholder_patterns: list[str]
    release_artifacts: list[str]
    team_control_number_placeholders: list[str] = field(default_factory=list)
    diagram_sources: list[dict[str, Any]] = field(default_factory=list)
    data_source_manifest: str = "reports/data_source_manifest.csv"
    external_data_needs: str = "reports/external_data_needs.md"
    external_data_dir: str = "data/raw/external"
    external_data_required: bool = False
    source_manifest_required: bool = False
    # --- v2 gate: contest-quality thresholds ---
    contest_page_limit: int = 25
    min_page_target: int = 20
    min_serious_pages: int = 15
    ai_report_pages: int = 0  # pages of AI Use Report, excluded from the contest page count
    judge_review_file: str = "reports/workflow/judge_review.md"
    judge_history_file: str = "reports/workflow/judge_review_history.jsonl"
    judge_min_score: int = 4
    judge_required_categories: int = 6
    diagram_min_nodes: int = 8
    diagram_min_bands: int = 3
    diagram_min_content_fraction: float = 0.6
    diagram_min_categories: int = 4
    visual_qa_dir: str = "reports/workflow/visual_qa"
    visual_qa_pages: int = 4
    # --- prose-structure checks (adapted from MathModelAgent writing_check) ---
    max_list_blocks: int = 12
    min_section_chars: int = 400
    stacked_float_gap_chars: int = 200

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "WorkflowConfig":
        return cls(
            project_pipeline_command=list(data.get("project_pipeline_command", [])),
            raw_data_files=list(data.get("raw_data_files", [])),
            paper_tex=str(data.get("paper_tex", "paper/main.tex")),
            paper_pdf=str(data.get("paper_pdf", "paper/main.pdf")),
            latex_log=str(data.get("latex_log", "paper/main.log")),
            key_results=str(data.get("key_results", "reports/key_results.csv")),
            figure_manifest=str(
                data.get("figure_manifest", "reports/figure_manifest.csv")
            ),
            figures_dirs=list(data.get("figures_dirs", ["figures"])),
            tables_dir=str(data.get("tables_dir", "tables")),
            workflow_reports_dir=str(
                data.get("workflow_reports_dir", "reports/workflow")
            ),
            page_target=int(data.get("page_target", 25)),
            page_hard_limit=int(data.get("page_hard_limit", 25)),
            placeholder_patterns=list(data.get("placeholder_patterns", [])),
            release_artifacts=list(data.get("release_artifacts", [])),
            team_control_number_placeholders=list(
                data.get("team_control_number_placeholders", [])
            ),
            diagram_sources=list(data.get("diagram_sources", [])),
            data_source_manifest=str(
                data.get("data_source_manifest", "reports/data_source_manifest.csv")
            ),
            external_data_needs=str(
                data.get("external_data_needs", "reports/external_data_needs.md")
            ),
            external_data_dir=str(data.get("external_data_dir", "data/raw/external")),
            external_data_required=bool(data.get("external_data_required", False)),
            source_manifest_required=bool(data.get("source_manifest_required", False)),
            contest_page_limit=int(data.get("contest_page_limit", 25)),
            min_page_target=int(data.get("min_page_target", 20)),
            min_serious_pages=int(data.get("min_serious_pages", 15)),
            ai_report_pages=int(data.get("ai_report_pages", 0)),
            judge_review_file=str(
                data.get("judge_review_file", "reports/workflow/judge_review.md")
            ),
            judge_history_file=str(
                data.get(
                    "judge_history_file",
                    "reports/workflow/judge_review_history.jsonl",
                )
            ),
            judge_min_score=int(data.get("judge_min_score", 4)),
            judge_required_categories=int(data.get("judge_required_categories", 6)),
            diagram_min_nodes=int(data.get("diagram_min_nodes", 8)),
            diagram_min_bands=int(data.get("diagram_min_bands", 3)),
            diagram_min_content_fraction=float(
                data.get("diagram_min_content_fraction", 0.6)
            ),
            diagram_min_categories=int(data.get("diagram_min_categories", 4)),
            visual_qa_dir=str(data.get("visual_qa_dir", "reports/workflow/visual_qa")),
            visual_qa_pages=int(data.get("visual_qa_pages", 4)),
            max_list_blocks=int(data.get("max_list_blocks", 12)),
            min_section_chars=int(data.get("min_section_chars", 400)),
            stacked_float_gap_chars=int(data.get("stacked_float_gap_chars", 200)),
        )


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> WorkflowConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return WorkflowConfig.from_mapping(data)


def resolve_project_path(project_root: str | Path, relative_path: str | Path) -> Path:
    return Path(project_root).resolve() / Path(relative_path)
