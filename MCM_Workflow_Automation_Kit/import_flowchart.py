#!/usr/bin/env python3
"""Import a teammate's flowchart as a vector PDF for the paper and write an import receipt.

    python MCM_Workflow_Automation_Kit/import_flowchart.py flowchart.pptx --out figures/concept/workflow.pdf
    python MCM_Workflow_Automation_Kit/import_flowchart.py flowchart.pdf --page 2 --out figures/concept/workflow.pdf

Accepts .pptx/.ppt (PowerPoint, else LibreOffice), .pdf and .svg. Crops to the drawn content,
clears document properties (PowerPoint writes the account name into /Author), measures the
font size, height and raster images once scaled to the text width (17.1 cm on the Kit's
letter template), writes `<output>.import.json`, and prints two things: the figure block for
the paper (an ordinary figure on a portrait page) and the `diagram_sources` entry for
workflow_config.json.

Re-run it whenever the source changes: the gate compares the receipt's hash with the source.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcm_workflow_kit.flowchart_import import (  # noqa: E402
    TEXT_WIDTH_CM,
    FlowchartImportError,
    import_flowchart,
    latex_snippet,
    receipt_path_for,
)


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="flowchart source: .pptx / .ppt / .pdf / .svg")
    parser.add_argument("--out", default="figures/concept/workflow.pdf", help="output PDF, relative to the project root")
    parser.add_argument("--page", type=int, default=1, help="page or slide number")
    parser.add_argument("--width-cm", type=float, default=TEXT_WIDTH_CM, help="width in the paper")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--figure-id", default="fig:workflow")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    source = Path(args.source)
    source = source if source.is_absolute() else root / source
    out = Path(args.out)
    out = out if out.is_absolute() else root / out
    try:
        receipt = import_flowchart(source, out, page=args.page, target_width_cm=args.width_cm)
    except FlowchartImportError as exc:
        print(f"Import failed: {exc}")
        return 1
    receipt_path = receipt_path_for(out)
    receipt.write(receipt_path)

    print(f"Imported {_rel(out, root)} ({receipt.width_cm} x {receipt.height_cm} cm; "
          f"{receipt.final_height_cm} cm tall at {receipt.target_width_cm:g} cm wide)")
    if receipt.min_font_pt_final is not None:
        print(f"Smallest text: {receipt.min_font_pt_source} pt in the source -> "
              f"{receipt.min_font_pt_final} pt in the paper ({receipt.font_basis})")
    print(f"Raster images: {receipt.raster_images}; receipt: {_rel(receipt_path, root)}")
    for warning in receipt.warnings:
        print(f"  note: {warning}")
    print("\nIn the paper (an ordinary figure on a portrait page; the caption names the figure):\n")
    print(latex_snippet(receipt, out.name, label=args.figure_id))
    entry = {
        "figure_id": args.figure_id,
        "origin": "user",
        "source": _rel(source, root),
        "pdf": _rel(out, root),
        "receipt": _rel(receipt_path, root),
    }
    print("\nAdd to diagram_sources in workflow_config.json:\n")
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
