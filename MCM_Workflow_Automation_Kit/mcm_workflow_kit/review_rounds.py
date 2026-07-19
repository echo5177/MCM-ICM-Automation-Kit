"""Judge-review round trajectory.

`judge_review_gate` is a single-snapshot floor: it checks whether the *current*
`judge_review.md` clears the minimum score and says APPROVED. It has no memory,
so it cannot tell whether a revision actually improved the paper or made it
worse across review rounds.

This module keeps an append-only ledger of judge-review rounds and reports the
score trajectory the way a real iterate-to-threshold loop does
(e.g. 3.8 -> 4.2 -> 4.7). It is *observability, not a gate*: it never emits
`fail`, so it can be appended after the gates without ever changing a
contest-readiness verdict. A regression -- a later round whose average score is
below the immediately preceding round -- is surfaced as a `warn`, so a revision
that quietly lowered quality does not pass unnoticed.

Ledger: ``reports/workflow/judge_review_history.jsonl`` (one JSON object per
round). A new round is appended only when the parsed scores/release differ from
the last recorded round, so repeated ``check`` runs on an unchanged review do
not inflate the history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path

from .config import WorkflowConfig, resolve_project_path
from .judge_review_gate import parse_review
from .reporting import CheckMessage, status_from_messages, write_markdown_report


# A later-round mean this far below the previous round counts as a regression.
# Means are averages of integer scores, so this only guards float noise.
REGRESSION_EPSILON = 1e-9


@dataclass(frozen=True)
class ReviewTrajectoryResult:
    messages: list[CheckMessage]
    rounds: list[dict] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round_stats(scores: dict[str, int]) -> tuple[float, int]:
    """Return (mean, min) over the parsed category scores."""
    values = list(scores.values())
    if not values:
        return 0.0, 0
    return sum(values) / len(values), min(values)


def _fingerprint(scores: dict[str, int], release: str) -> str:
    """Stable identity of a round so identical re-runs are not re-recorded."""
    ordered = ",".join(f"{name}={scores[name]}" for name in sorted(scores))
    return f"{release.upper()}|{ordered}"


def load_rounds(project_root: str | Path, config: WorkflowConfig) -> list[dict]:
    ledger = resolve_project_path(project_root, config.judge_history_file)
    if not ledger.exists():
        return []
    rounds: list[dict] = []
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rounds.append(json.loads(line))
        except json.JSONDecodeError:
            # A corrupt line should not crash the observability node.
            continue
    return rounds


def record_review_round(
    project_root: str | Path,
    config: WorkflowConfig,
) -> dict | None:
    """Append the current judge review as a new round if it changed.

    Returns the recorded round dict, or None when there is no parseable review
    or the review is identical to the last recorded round (deduplicated).
    """
    review_path = resolve_project_path(project_root, config.judge_review_file)
    if not review_path.exists():
        return None

    scores, release = parse_review(review_path.read_text(encoding="utf-8", errors="replace"))
    if not scores:
        return None

    existing = load_rounds(project_root, config)
    fingerprint = _fingerprint(scores, release)
    if existing and existing[-1].get("fingerprint") == fingerprint:
        return None

    mean, minimum = _round_stats(scores)
    record = {
        "round": len(existing) + 1,
        "recorded_at": _utc_now(),
        "release": release.upper(),
        "scores": scores,
        "mean": round(mean, 3),
        "min": minimum,
        "fingerprint": fingerprint,
    }

    ledger = resolve_project_path(project_root, config.judge_history_file)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def analyze_trajectory(
    rounds: list[dict],
    config: WorkflowConfig,
) -> ReviewTrajectoryResult:
    messages: list[CheckMessage] = []

    if not rounds:
        messages.append(
            CheckMessage(
                "pass",
                "No judge-review rounds recorded yet; the trajectory ledger is empty.",
            )
        )
        return ReviewTrajectoryResult(messages=messages, rounds=rounds)

    latest = rounds[-1]
    trail = " -> ".join(f"{r.get('mean', 0):.2f}" for r in rounds)

    if len(rounds) >= 2:
        prev = rounds[-2]
        prev_mean = float(prev.get("mean", 0.0))
        latest_mean = float(latest.get("mean", 0.0))
        if latest_mean < prev_mean - REGRESSION_EPSILON:
            messages.append(
                CheckMessage(
                    "warn",
                    f"Judge scores regressed: round {prev.get('round')} mean "
                    f"{prev_mean:.2f} -> round {latest.get('round')} mean "
                    f"{latest_mean:.2f}. A revision lowered average quality; "
                    f"confirm this was intentional.",
                )
            )

    messages.append(
        CheckMessage(
            "pass",
            f"{len(rounds)} judge-review round(s) recorded. Mean trajectory: "
            f"{trail}. Latest: mean {float(latest.get('mean', 0.0)):.2f}, "
            f"min {latest.get('min')}, release {latest.get('release')}.",
        )
    )
    return ReviewTrajectoryResult(messages=messages, rounds=rounds)


def render_trajectory_markdown(result: ReviewTrajectoryResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Rounds recorded: {len(result.rounds)}",
        "- Role: observability only; this node never blocks release "
        "(judge_review_gate is the floor).",
        "",
        "## Messages",
        "",
    ]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    lines.extend(["", "## Round history", "", "| Round | Mean | Min | Release | Recorded |", "| ---: | ---: | ---: | --- | --- |"])
    if result.rounds:
        for r in result.rounds:
            lines.append(
                f"| {r.get('round')} | {float(r.get('mean', 0.0)):.2f} | "
                f"{r.get('min')} | {r.get('release')} | {r.get('recorded_at', '')} |"
            )
    else:
        lines.append("| (none) | | | | |")
    return lines


def write_review_trajectory_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> ReviewTrajectoryResult:
    record_review_round(project_root, config)
    rounds = load_rounds(project_root, config)
    result = analyze_trajectory(rounds, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "review_trajectory_report.md",
        "Judge Review Trajectory",
        render_trajectory_markdown(result),
    )
    return result
