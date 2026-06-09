from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import shutil

from .config import WorkflowConfig, resolve_project_path
from .orchestrator import timestamp_slug


@dataclass(frozen=True)
class ReleaseEntry:
    source: str
    destination: str
    artifact_type: str
    status: str
    size_bytes: int


@dataclass(frozen=True)
class ReleasePacket:
    release_dir: Path
    entries: list[ReleaseEntry]

    @property
    def missing_entries(self) -> list[ReleaseEntry]:
        return [entry for entry in self.entries if entry.status == "missing"]


def _directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def _copy_artifact(source: Path, destination: Path) -> tuple[str, str, int]:
    if not source.exists():
        return "missing", "missing", 0
    if source.is_dir():
        shutil.copytree(source, destination)
        return "directory", "copied", _directory_size(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return "file", "copied", destination.stat().st_size


def create_release_packet(
    project_root: str | Path,
    config: WorkflowConfig,
    timestamp: str | None = None,
) -> ReleasePacket:
    root = Path(project_root).resolve()
    release_dir = root / "release" / (timestamp or timestamp_slug())
    if release_dir.exists():
        raise FileExistsError(f"Release directory already exists: {release_dir}")
    release_dir.mkdir(parents=True)

    entries: list[ReleaseEntry] = []
    for artifact in config.release_artifacts:
        source = resolve_project_path(root, artifact)
        destination = release_dir / artifact
        artifact_type, status, size_bytes = _copy_artifact(source, destination)
        entries.append(
            ReleaseEntry(
                source=artifact,
                destination=str(destination.relative_to(release_dir)),
                artifact_type=artifact_type,
                status=status,
                size_bytes=size_bytes,
            )
        )

    write_release_manifest(release_dir, entries)
    write_final_checklist(release_dir, entries)
    return ReleasePacket(release_dir=release_dir, entries=entries)


def write_release_manifest(release_dir: Path, entries: list[ReleaseEntry]) -> Path:
    manifest_path = release_dir / "release_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source",
                "destination",
                "artifact_type",
                "status",
                "size_bytes",
            ],
        )
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "source": entry.source,
                    "destination": entry.destination,
                    "artifact_type": entry.artifact_type,
                    "status": entry.status,
                    "size_bytes": entry.size_bytes,
                }
            )
    return manifest_path


def write_final_checklist(release_dir: Path, entries: list[ReleaseEntry]) -> Path:
    missing = [entry.source for entry in entries if entry.status == "missing"]
    lines = [
        "# Final Release Checklist",
        "",
        "- [ ] Team control number checked",
        "- [ ] Summary and main report control numbers match",
        "- [ ] Page limit checked",
        "- [ ] Figure manifest checked",
        "- [ ] Key results checked",
        "- [ ] AI use log included",
        "- [ ] Source log included",
        "",
        "## Artifact Status",
        "",
    ]
    if missing:
        lines.append("Missing artifacts:")
        lines.extend(f"- {item}" for item in missing)
    else:
        lines.append("All configured artifacts were copied.")
    checklist_path = release_dir / "final_checklist.md"
    checklist_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return checklist_path
