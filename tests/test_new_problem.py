from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "new_problem.py"


def _load():
    spec = importlib.util.spec_from_file_location("new_problem", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_next_contest_year_rolls_over_after_the_contest() -> None:
    # The prefix used to be hard-coded to 2026; a scaffold made in autumn 2026 is for 2027.
    module = _load()
    assert module.next_contest_year(dt.date(2026, 9, 28)) == 2027
    assert module.next_contest_year(dt.date(2027, 1, 20)) == 2027


def test_scaffold_names_the_repo_after_the_year(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    monkeypatch.setattr("sys.argv", ["new_problem.py", "--name", "ProbB", "--problem-letter", "B",
                                     "--year", "2027", "--dir", str(tmp_path)])
    assert module.main() == 0
    repo = tmp_path / "Simulation_2027MCM-ICM_ProbB"
    assert "2027 MCM/ICM Problem B" in (repo / "README.md").read_text(encoding="utf-8")
    assert r"\newcommand{\Problem}{B}" in (repo / "paper" / "main.tex").read_text(encoding="utf-8")
