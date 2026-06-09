from __future__ import annotations

import argparse
from pathlib import Path
import sys


KIT_ROOT = Path(__file__).resolve().parents[2]
if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from mcm_workflow_kit.config import load_config
from mcm_workflow_kit.result_checker import write_result_check_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run result consistency checks.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    parser.add_argument(
        "--config",
        default=str(KIT_ROOT / "workflow_config.json"),
        help="Workflow config JSON path.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    result = write_result_check_report(args.project_root, config)
    return 1 if result.status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
