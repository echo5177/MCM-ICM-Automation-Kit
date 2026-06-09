#!/usr/bin/env python3
"""Project pipeline entry point (starter).

`run_workflow.py --mode full` runs this first, then the deterministic gate.
Replace the body with your real modeling pipeline. The contract the Kit expects:

  * write reports/key_results.csv      (columns: metric,value  -- numbers the paper cites)
  * write reports/figure_manifest.csv  (columns: figure_id,path,source_script,paper_location)
  * regenerate every figure in figures/generated/ and every table in tables/

Keeping every cited number in key_results.csv lets result_checker prove the paper's
headline numbers actually trace back to computed outputs.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
FIGS = ROOT / "figures" / "generated"
TABLES = ROOT / "tables"


def main() -> None:
    for d in (REPORTS, FIGS, TABLES):
        d.mkdir(parents=True, exist_ok=True)

    # TODO: replace with real computed results.
    key_results = [
        {"metric": "example_metric", "value": 0.0},
    ]
    with (REPORTS / "key_results.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(key_results)

    # TODO: one row per generated figure.
    figures = [
        # {"figure_id": "Fig. 2", "path": "figures/generated/fig_2.png",
        #  "source_script": "scripts/run_all.py", "paper_location": "Results"},
    ]
    with (REPORTS / "figure_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["figure_id", "path", "source_script", "paper_location"]
        )
        writer.writeheader()
        writer.writerows(figures)

    print("run_all (starter) wrote key_results.csv and figure_manifest.csv")


if __name__ == "__main__":
    main()
