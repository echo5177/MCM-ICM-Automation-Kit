from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckMessage:
    level: str
    message: str


def ensure_parent(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def write_markdown_report(path: str | Path, title: str, lines: list[str]) -> Path:
    report_path = ensure_parent(path)
    content = [f"# {title}", "", *lines]
    report_path.write_text("\n".join(content).rstrip() + "\n", encoding="utf-8")
    return report_path


def status_from_messages(messages: list[CheckMessage]) -> str:
    levels = {message.level.lower() for message in messages}
    if "fail" in levels:
        return "fail"
    if "warn" in levels:
        return "warn"
    return "pass"
