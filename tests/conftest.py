"""Make the Kit importable when pytest is run from the repo root without PYTHONPATH.

The tests used to import `mcm_workflow_kit` bare, so `pytest tests/` failed at collection
unless the caller had set PYTHONPATH (the README's own command did not).
"""

from __future__ import annotations

from pathlib import Path
import sys

KIT = Path(__file__).resolve().parents[1] / "MCM_Workflow_Automation_Kit"
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))
