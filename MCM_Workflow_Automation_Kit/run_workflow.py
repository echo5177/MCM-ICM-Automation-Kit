from __future__ import annotations

import argparse

from mcm_workflow_kit.config import DEFAULT_CONFIG_PATH
from mcm_workflow_kit.orchestrator import run_workflow


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MCM workflow automation checks.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Workflow config JSON path.",
    )
    parser.add_argument(
        "--mode",
        choices=["check", "full"],
        default="check",
        help="check existing artifacts or run the full project pipeline first.",
    )
    args = parser.parse_args()
    result = run_workflow(args.project_root, mode=args.mode, config_path=args.config)
    return 1 if result.status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
