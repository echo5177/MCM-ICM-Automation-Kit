from __future__ import annotations

import argparse
from pathlib import Path
import sys


KIT_ROOT = Path(__file__).resolve().parents[2]
if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from mcm_workflow_kit.config import load_config
from mcm_workflow_kit.data_auditor import write_data_audit_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run reusable CSV data audit.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    parser.add_argument(
        "--config",
        default=str(KIT_ROOT / "workflow_config.json"),
        help="Workflow config JSON path.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    write_data_audit_outputs(args.project_root, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
