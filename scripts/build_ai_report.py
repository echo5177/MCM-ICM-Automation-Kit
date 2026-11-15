#!/usr/bin/env python3
"""Build the paper's "Report on Use of AI" from the log kept while working.

    python scripts/build_ai_report.py --project-root ../Simulation_2027MCM-ICM_ProbB

Reads `reports/ai_use_log.csv` and writes `paper/ai_report.tex`, which the paper template
includes after the references. The report is built from the log so that it says what was
done rather than what is remembered; `ai_use_checker` then checks the compiled PDF against
the same log. Edit the log, never the generated file.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
for candidate in (REPO / "MCM_Workflow_Automation_Kit", Path.cwd() / "MCM_Workflow_Automation_Kit"):
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from mcm_workflow_kit.ai_use_checker import build_report_tex, read_log  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--log", default="reports/ai_use_log.csv")
    parser.add_argument("--out", default="paper/ai_report.tex")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    log = root / args.log
    if not log.is_file():
        print(f"No log at {log}. Start it from templates/ai_use_log.template.csv.")
        return 1
    rows, missing = read_log(log)
    if missing:
        print(f"{log} lacks column(s): {', '.join(missing)}")
        return 1
    if not rows:
        print(f"{log} has no entry yet.")
        return 1
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_report_tex(rows), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} log entries, {len({r['tool'] for r in rows})} tool(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
