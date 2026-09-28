"""Judge-style review gate.

ProbA reached "full workflow pass" without anyone reviewing it as a judge would.
This gate refuses to pass unless a real judge-style review exists and approves release.

The review file is written by the agent (or a human) after applying
`references/judge_rubric.md`. It cannot be auto-generated to pass; that is the point.

Expected machine-readable lines in the review file (case-insensitive category names):

    PAPER_SHA256: <sha256 of the reviewed paper PDF>
    RELEASE: APPROVED            # or BLOCKED
    SCORE format_presentation: 4
    SCORE problem_fit: 5
    SCORE modeling_quality: 4
    SCORE data_evidence: 4
    SCORE results_interpretation: 4
    SCORE originality_insight: 4
The review is bound to the PDF it judged. Without the binding, an APPROVED written for
an early draft kept passing after every later rebuild, which is the opposite of a gate.
At `release_stage: final` a missing, unbound or stale binding fails; in `draft` it only
warns, because drafts are rebuilt constantly and most of them never ship.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


SCORE_RE = re.compile(r"^\s*SCORE\s+([A-Za-z0-9_./ -]+?)\s*[:=]\s*([0-5])\b", re.MULTILINE)
RELEASE_RE = re.compile(r"^\s*RELEASE\s*[:=]\s*([A-Za-z]+)", re.MULTILINE | re.IGNORECASE)
PAPER_SHA_RE = re.compile(r"^\s*PAPER_SHA256\s*[:=]\s*([0-9a-fA-F]{64})\b", re.MULTILINE)

TEMPLATE = """# Judge-Style Review

PAPER_SHA256: <sha256 of the reviewed paper PDF>
RELEASE: BLOCKED

SCORE format_presentation: 0
SCORE problem_fit: 0
SCORE modeling_quality: 0
SCORE data_evidence: 0
SCORE results_interpretation: 0
SCORE originality_insight: 0

## Notes
Apply references/judge_rubric.md. Score each 0-5, justify, then set RELEASE to
APPROVED only when every score is >= the configured minimum.
"""


@dataclass(frozen=True)
class JudgeReviewResult:
    messages: list[CheckMessage]
    scores: dict[str, int] = field(default_factory=dict)
    release: str = "MISSING"
    pdf_sha256: str = ""
    review_sha256: str = ""
    stage: str = "final"

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def parse_review(text: str) -> tuple[dict[str, int], str]:
    scores = {name.strip().lower().replace(" ", "_"): int(value) for name, value in SCORE_RE.findall(text)}
    release_match = RELEASE_RE.search(text)
    release = release_match.group(1).upper() if release_match else "MISSING"
    return scores, release


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_paper_sha(text: str) -> str:
    match = PAPER_SHA_RE.search(text)
    return match.group(1).lower() if match else ""


def _draft_softened(messages: list[CheckMessage], config: WorkflowConfig) -> list[CheckMessage]:
    """In draft, report what would block at final without blocking now."""
    if config.is_final:
        return messages
    return [
        CheckMessage("warn", f"(draft; blocks at final) {m.message}") if m.level == "fail" else m
        for m in messages
    ]


def run_judge_review_gate(
    project_root: str | Path,
    config: WorkflowConfig,
) -> JudgeReviewResult:
    root = Path(project_root).resolve()
    review_path = resolve_project_path(root, config.judge_review_file)
    pdf_path = resolve_project_path(root, config.paper_pdf)
    pdf_sha = sha256_file(pdf_path) if pdf_path.is_file() else ""
    stage = "final" if config.is_final else "draft"

    if not review_path.exists():
        return JudgeReviewResult(
            messages=_draft_softened([
                CheckMessage(
                    "fail",
                    f"No judge-style review found at {config.judge_review_file}. Apply "
                    f"the rubric and write the review before release.",
                )
            ], config),
            scores={},
            release="MISSING",
            pdf_sha256=pdf_sha,
            stage=stage,
        )

    text = review_path.read_text(encoding="utf-8", errors="replace")
    scores, release = parse_review(text)
    review_sha = parse_paper_sha(text)
    messages: list[CheckMessage] = []

    if not pdf_sha:
        messages.append(CheckMessage(
            "fail", f"PDF not compiled ({config.paper_pdf}); the review cannot be bound to it."))
    elif not review_sha:
        messages.append(CheckMessage(
            "fail",
            f"The review is not bound to a PDF. Add `PAPER_SHA256: {pdf_sha}` after re-reading "
            f"the current {config.paper_pdf}; an unbound APPROVED would keep passing after every "
            f"later rebuild.",
        ))
    elif review_sha != pdf_sha:
        messages.append(CheckMessage(
            "fail",
            f"The review judged a different PDF (PAPER_SHA256 {review_sha[:12]}..., current "
            f"{pdf_sha[:12]}...). The paper changed after the review; review the current PDF "
            f"and update the binding.",
        ))

    if len(scores) < config.judge_required_categories:
        messages.append(
            CheckMessage(
                "fail",
                f"Judge review scores only {len(scores)} categories; expected at least "
                f"{config.judge_required_categories}.",
            )
        )

    low = {name: value for name, value in scores.items() if value < config.judge_min_score}
    if low:
        rendered = ", ".join(f"{name}={value}" for name, value in sorted(low.items()))
        messages.append(
            CheckMessage(
                "fail",
                f"Judge scores below the minimum {config.judge_min_score}: {rendered}. "
                f"Revise the paper, do not lower the bar.",
            )
        )

    if release != "APPROVED":
        messages.append(
            CheckMessage("fail", f"Judge release decision is '{release}', not APPROVED.")
        )

    if not messages:
        messages.append(
            CheckMessage("pass", f"Judge review approved with {len(scores)} categories >= {config.judge_min_score}.")
        )

    return JudgeReviewResult(
        messages=_draft_softened(messages, config),
        scores=scores,
        release=release,
        pdf_sha256=pdf_sha,
        review_sha256=review_sha,
        stage=stage,
    )


def render_judge_review_markdown(result: JudgeReviewResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Release stage: {result.stage}",
        f"- Release decision: {result.release}",
        f"- Current PDF SHA-256: {result.pdf_sha256 or '(no PDF)'}",
        f"- Review bound to: {result.review_sha256 or '(not bound)'}",
        "",
        "## Messages",
        "",
    ]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    lines.extend(["", "## Parsed scores", ""])
    if result.scores:
        lines.extend(f"- {name}: {value}" for name, value in sorted(result.scores.items()))
    else:
        lines.append("- (none parsed)")
    if result.release == "MISSING" and not result.scores:
        lines.extend(["", "## Suggested review template", "", "```", TEMPLATE.strip(), "```"])
    return lines


def write_judge_review_gate_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> JudgeReviewResult:
    result = run_judge_review_gate(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "judge_review_gate_report.md",
        "Judge Review Gate",
        render_judge_review_markdown(result),
    )
    return result
