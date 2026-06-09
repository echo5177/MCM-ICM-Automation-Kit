#!/usr/bin/env python3
"""Sync the canonical MCM Workflow Automation Kit into a problem repo.

Updates the deterministic v2-gate Kit code in a target project to match this
template, WITHOUT clobbering that project's own ``workflow_config.json`` (the
per-problem paths/thresholds) or its ``runs/`` history.

Usage:
    python scripts/sync_kit.py --target ../Simulation_2026MCM-ICM_ProbA
    python scripts/sync_kit.py --target ../Simulation_2026MCM-ICM_ProbA --dry-run
    python scripts/sync_kit.py --target ../ProbX --force-config   # also overwrite config
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
KIT_NAME = "MCM_Workflow_Automation_Kit"
SOURCE_KIT = TEMPLATE_ROOT / KIT_NAME

# Kit subtrees that are pure, reusable code: replaced wholesale on sync.
CODE_DIRS = ("mcm_workflow_kit", "nodes", "docs", "scripts")
# Kit files that are pure code/docs: overwritten on sync.
CODE_FILES = ("run_workflow.py", "README.md")
# Project-owned, never overwritten unless explicitly forced.
CONFIG_FILE = "workflow_config.json"


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n == "__pycache__" or n == "runs" or n.endswith(".pyc")}


def sync(target_root: Path, dry_run: bool = False, force_config: bool = False) -> int:
    if not SOURCE_KIT.is_dir():
        raise SystemExit(f"Canonical kit not found: {SOURCE_KIT}")
    if not target_root.is_dir():
        raise SystemExit(f"Target project not found: {target_root}")

    target_kit = target_root / KIT_NAME
    actions: list[str] = []

    for name in CODE_DIRS:
        src = SOURCE_KIT / name
        if not src.is_dir():
            continue
        dst = target_kit / name
        actions.append(f"replace dir  {KIT_NAME}/{name}/")
        if not dry_run:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=_ignore)

    for name in CODE_FILES:
        src = SOURCE_KIT / name
        if not src.is_file():
            continue
        actions.append(f"copy file    {KIT_NAME}/{name}")
        if not dry_run:
            target_kit.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target_kit / name)

    dst_config = target_kit / CONFIG_FILE
    if force_config or not dst_config.exists():
        verb = "overwrite" if dst_config.exists() else "install "
        actions.append(f"{verb} config {KIT_NAME}/{CONFIG_FILE}")
        if not dry_run:
            target_kit.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_KIT / CONFIG_FILE, dst_config)
    else:
        actions.append(f"preserve     {KIT_NAME}/{CONFIG_FILE} (project-owned)")

    prefix = "[dry-run] would " if dry_run else "[done] "
    print(f"Sync kit  {SOURCE_KIT}  ->  {target_kit}")
    for a in actions:
        print(f"  {prefix}{a}")
    if not dry_run:
        print("\nNext: review workflow_config.json, then run")
        print(f"  python {KIT_NAME}/run_workflow.py --project-root . --mode check")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Path to the problem repo root.")
    parser.add_argument("--dry-run", action="store_true", help="Show actions only.")
    parser.add_argument(
        "--force-config",
        action="store_true",
        help="Also overwrite the project's workflow_config.json (rarely wanted).",
    )
    args = parser.parse_args()
    return sync(Path(args.target).resolve(), dry_run=args.dry_run, force_config=args.force_config)


if __name__ == "__main__":
    raise SystemExit(main())
