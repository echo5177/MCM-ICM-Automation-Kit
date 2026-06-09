from __future__ import annotations

import argparse
from pathlib import Path
import sys


KIT_ROOT = Path(__file__).resolve().parents[1]
if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from mcm_workflow_kit.config import load_config
from mcm_workflow_kit.release_packet import create_release_packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an MCM release packet.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    parser.add_argument(
        "--config",
        default=str(KIT_ROOT / "workflow_config.json"),
        help="Workflow config JSON path.",
    )
    parser.add_argument("--timestamp", default=None, help="Optional release timestamp.")
    args = parser.parse_args()

    config = load_config(args.config)
    packet = create_release_packet(args.project_root, config, timestamp=args.timestamp)
    print(packet.release_dir)
    return 1 if packet.missing_entries else 0


if __name__ == "__main__":
    raise SystemExit(main())
