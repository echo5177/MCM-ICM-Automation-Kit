#!/usr/bin/env python3
"""Scaffold a new MCM/ICM problem repo from this template.

Creates the standard project layout, drops in the canonical v2-gate Kit, a starter
paper built on the official COMAP template, a starter pipeline, and the new-problem
checklist + judge-review stub. The new repo's gate is intentionally RED until you do
the real work (no paper / no judge review yet) -- that is the point.

Usage:
    python scripts/new_problem.py --name ProbB
    python scripts/new_problem.py --name ProbB --problem-letter B
    python scripts/new_problem.py --name ProbB --year 2027 --dir "D:/documents/MCM&ICM/2027/MCM_Automation"

The repo is named Simulation_<year>MCM-ICM_<name>; <year> defaults to the next contest.
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
KIT_NAME = "MCM_Workflow_Automation_Kit"

# Standard project directories (each gets a .gitkeep so it is tracked while empty).
DIRS = [
    "data/raw/external",
    "data/processed",
    "src",
    "scripts",
    "paper",
    "figures/concept",
    "figures/concept_src",
    "figures/generated",
    "tables",
    "reports/workflow",
    "tests",
]


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n == "__pycache__" or n == "runs" or n.endswith(".pyc")}


def next_contest_year(today: dt.date | None = None) -> int:
    """MCM/ICM runs in late January or early February; from March on, the next one is next year's."""
    today = today or dt.date.today()
    return today.year + 1 if today.month >= 3 else today.year


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scaffold(target: Path, problem_letter: str | None, force: bool, year: int | None = None) -> int:
    year = year or next_contest_year()
    if target.exists():
        if not force or not target.is_dir():
            raise SystemExit(f"Target already exists: {target} (use --force to add into it)")

    name = target.name
    target.mkdir(parents=True, exist_ok=True)

    # 1) Standard directory tree.
    for rel in DIRS:
        d = target / rel
        d.mkdir(parents=True, exist_ok=True)
        gk = d / ".gitkeep"
        if not gk.exists():
            gk.write_text("", encoding="utf-8")

    # 2) Canonical Kit (with the generic workflow_config.json).
    dst_kit = target / KIT_NAME
    if dst_kit.exists():
        shutil.rmtree(dst_kit)
    shutil.copytree(TEMPLATE_ROOT / KIT_NAME, dst_kit, ignore=_ignore)

    # 3) Official summary template at the repo root (so the paper can build on it).
    shutil.copy2(TEMPLATE_ROOT / "templates" / "MCM-ICM_Summary.tex", target / "MCM-ICM_Summary.tex")

    # 4) Starter paper (official template + layout lessons baked in).
    paper_tex = (TEMPLATE_ROOT / "templates" / "paper_main.template.tex").read_text(encoding="utf-8")
    if problem_letter:
        paper_tex = paper_tex.replace(
            r"\newcommand{\Problem}{ABCDEF}",
            rf"\newcommand{{\Problem}}{{{problem_letter.upper()}}}",
        )
    _write(target / "paper" / "main.tex", paper_tex)

    # 5) Starter pipeline.
    shutil.copy2(TEMPLATE_ROOT / "templates" / "run_all.template.py", target / "scripts" / "run_all.py")

    # 6) Judge-review stub (the gate requires this file; it starts BLOCKED on purpose).
    shutil.copy2(
        TEMPLATE_ROOT / "templates" / "judge_review.template.md",
        target / "reports" / "workflow" / "judge_review.md",
    )

    # 7) Standard .gitignore + environment.yml + checklist.
    shutil.copy2(TEMPLATE_ROOT / "templates" / "gitignore.template", target / ".gitignore")
    if (TEMPLATE_ROOT / "environment.yml").exists():
        shutil.copy2(TEMPLATE_ROOT / "environment.yml", target / "environment.yml")
    shutil.copy2(
        TEMPLATE_ROOT / "checklists" / "NEW_PROBLEM_CHECKLIST.md",
        target / "NEW_PROBLEM_CHECKLIST.md",
    )

    # 8) Project README.
    letter = (problem_letter or "X").upper()
    _write(
        target / "README.md",
        f"""# {name} — {year} MCM/ICM Problem {letter}

Scaffolded from the MCM-ICM Automation Kit. The deterministic v2-gate Kit lives in
`{KIT_NAME}/`. Follow `NEW_PROBLEM_CHECKLIST.md`.

## Run the gate

```bash
python {KIT_NAME}/run_workflow.py --project-root . --mode check
```

Use `--mode full` to run `scripts/run_all.py` first, then the gate. The gate is RED
until the paper, results, figures, and an honest judge review all exist.
""",
    )

    print(f"Scaffolded new problem repo: {target}")
    print("\nNext steps:")
    print(f"  cd {target}")
    print("  conda env create -f environment.yml   # or reuse the shared 'mcm' env")
    print("  # read NEW_PROBLEM_CHECKLIST.md and fill the human-input docs")
    print(f"  python {KIT_NAME}/run_workflow.py --project-root . --mode check")
    print("  git init && git add -A && git commit -m \"scaffold\"")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Repo name, e.g. ProbB or Simulation_2027MCM-ICM_ProbB.")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Contest year for the repo prefix and README (default: the next contest).",
    )
    parser.add_argument(
        "--dir",
        default=str(TEMPLATE_ROOT.parent),
        help="Parent directory for the new repo (default: sibling of this template).",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Prefix applied to --name unless --name already starts with it "
             "(default: Simulation_<year>MCM-ICM_; pass '' for none).",
    )
    parser.add_argument("--problem-letter", default=None, help="Contest problem letter, e.g. A..F.")
    parser.add_argument("--force", action="store_true", help="Scaffold into an existing directory.")
    args = parser.parse_args()

    year = args.year or next_contest_year()
    prefix = f"Simulation_{year}MCM-ICM_" if args.prefix is None else args.prefix
    name = args.name
    if prefix and not name.startswith(prefix):
        name = prefix + name
    target = (Path(args.dir).resolve()) / name
    return scaffold(target, args.problem_letter, args.force, year)


if __name__ == "__main__":
    raise SystemExit(main())
