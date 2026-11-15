"""Parameter ledger: every number the model takes as given, its unit, and where it came from.

The 2026 MCM A entry listed seven data sources (CALCE, NASA, NREL, ...) and never said which
parameter, figure or table each one supported; its power table could not be told apart from
invented numbers, and some of it was. A head judge's commentary names the pattern from the
other side: papers with "generic 'factors', 'constants', or 'coefficients' without a detailed
explanation of how the variable was derived" were less successful, every variable should
carry a unit, and "the most successful teams focused their sensitivity analysis on the
assumptions that they made".

The CUMCM Kit has a ledger for constants copied from the problem statement. MCM/ICM problems
give few constants and expect the team to find the rest, so the question here is origin
rather than transcription. `reports/param_ledger.csv`, one row per parameter:

| column | meaning |
| --- | --- |
| `symbol` | as written in the paper |
| `meaning` | in words |
| `value` | one value per row |
| `unit` | the unit, or `-` when dimensionless (never blank) |
| `origin` | `statement`, `dataset`, `literature`, `calibrated`, or `assumed` |
| `source` | statement: page or quote. dataset / calibrated: a `source_id` of the source manifest. literature: the citation key used in the paper |
| `used_in` | the figure, table or section the parameter feeds |
| `sensitivity` | for an assumed parameter: the figure, table or section that varies it |
| `note` | anything a reader of the ledger needs |

What it cannot do: tell whether a value is right. It makes each value sit in one place,
with a unit and an origin a person can go and check.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report
from .tex_source import read_tex_expanded


REQUIRED_COLUMNS = ("symbol", "meaning", "value", "unit", "origin", "source", "used_in",
                    "sensitivity", "note")
ORIGINS = {"statement", "dataset", "literature", "calibrated", "assumed"}
CITE_KEY_RE = re.compile(r"\\bibitem(?:\[[^\]]*\])?\{([^{}]+)\}|@\w+\{\s*([^,\s]+)\s*,")
MAX_ASSUMED_SHARE = 0.5


@dataclass(frozen=True)
class ParamLedgerResult:
    messages: list[CheckMessage]
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def _stage(config: WorkflowConfig, message: str) -> CheckMessage:
    return CheckMessage("fail" if config.is_final else "warn", message)


def read_ledger(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = [name.strip() for name in (reader.fieldnames or [])]
        rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    rows = [row for row in rows if row.get("symbol") and not row["symbol"].startswith(("[", "#"))]
    return rows, missing


def manifest_source_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {(row.get("source_id") or "").strip() for row in csv.DictReader(handle)} - {""}


def citation_keys(root: Path, tex_path: Path) -> set[str]:
    """Keys of \\bibitem entries in the paper and of entries in any .bib file beside it."""
    text = read_tex_expanded(tex_path, root) if tex_path.is_file() else ""
    for bib in tex_path.parent.glob("*.bib") if tex_path.parent.is_dir() else []:
        text += "\n" + bib.read_text(encoding="utf-8", errors="replace")
    return {a or b for a, b in CITE_KEY_RE.findall(text)}


def run_param_ledger_checks(project_root: str | Path, config: WorkflowConfig) -> ParamLedgerResult:
    root = Path(project_root).resolve()
    path = resolve_project_path(root, config.param_ledger_file)
    if not config.param_ledger_required:
        if not path.is_file():
            return ParamLedgerResult([CheckMessage(
                "pass", "No parameter ledger; the config declares the model takes no given parameters.")])
    elif not path.is_file():
        return ParamLedgerResult([_stage(
            config,
            f"No parameter ledger ({config.param_ledger_file}). Enter every number the model takes "
            f"as given with its unit and origin. If the model has none, set "
            f"`param_ledger_required` to false.",
        )])

    rows, missing = read_ledger(path)
    if missing:
        return ParamLedgerResult([CheckMessage(
            "fail", f"{config.param_ledger_file} lacks column(s): {', '.join(missing)}.")])
    if not rows:
        return ParamLedgerResult([_stage(
            config, f"{config.param_ledger_file} has no parameter yet (only the template row).")])

    messages: list[CheckMessage] = []
    source_ids = manifest_source_ids(resolve_project_path(root, config.data_source_manifest))
    tex_path = resolve_project_path(root, config.paper_tex)
    keys = citation_keys(root, tex_path)

    values: dict[str, str] = {}
    for row in rows:
        symbol = row["symbol"]
        if symbol in values and values[symbol] != row["value"]:
            messages.append(CheckMessage(
                "fail", f"{symbol} is entered twice with different values ({values[symbol]} and "
                        f"{row['value']}). One of them is what the code uses; the paper must agree."))
        values.setdefault(symbol, row["value"])

        if not row["value"]:
            messages.append(_stage(config, f"{symbol}: no value."))
        if not row["unit"]:
            messages.append(_stage(
                config, f"{symbol}: no unit. Write `-` for a dimensionless quantity; a blank cannot "
                        f"be told apart from a forgotten unit."))
        origin = row["origin"].lower()
        if origin not in ORIGINS:
            messages.append(_stage(
                config, f"{symbol}: origin '{row['origin']}' is not one of {', '.join(sorted(ORIGINS))}."))
            continue
        source = row["source"]
        if origin in {"statement", "literature", "dataset", "calibrated"} and not source:
            messages.append(_stage(config, f"{symbol}: origin is '{origin}' but `source` is empty."))
        elif origin in {"dataset", "calibrated"} and source_ids and source not in source_ids:
            messages.append(_stage(
                config, f"{symbol}: source '{source}' is not a source_id in "
                        f"{config.data_source_manifest}."))
        elif origin == "literature" and keys and source not in keys:
            messages.append(_stage(
                config, f"{symbol}: citation key '{source}' is not in the paper's reference list."))
        if origin == "assumed" and not row["sensitivity"]:
            messages.append(CheckMessage(
                "warn", f"{symbol} is assumed and nothing varies it. Judges look for a sensitivity "
                        f"analysis aimed at the assumptions the team made."))
        if not row["used_in"]:
            messages.append(CheckMessage(
                "warn", f"{symbol}: `used_in` is empty. Name the figure, table or section it feeds, "
                        f"so a number in the paper can be traced back to it."))

    assumed = sum(1 for row in rows if row["origin"].lower() == "assumed")
    if len(rows) >= 4 and assumed / len(rows) > MAX_ASSUMED_SHARE:
        messages.append(CheckMessage(
            "warn", f"{assumed} of {len(rows)} parameters are assumed. A model resting mostly on "
                    f"assumed values needs either calibration against data or a sensitivity "
                    f"analysis that shows the conclusions survive."))

    if not any(m.level in {"fail", "warn"} for m in messages):
        messages.append(CheckMessage("pass", f"All {len(rows)} parameters carry a unit and an origin."))
    report_rows = [{k: row[k] for k in ("symbol", "value", "unit", "origin", "source", "used_in")} for row in rows]
    return ParamLedgerResult(messages=messages, rows=report_rows)


def render_param_ledger_markdown(result: ParamLedgerResult) -> list[str]:
    lines = [f"- Status: {result.status}", ""]
    if result.rows:
        lines += ["| Symbol | Value | Unit | Origin | Source | Used in |", "| --- | ---: | --- | --- | --- | --- |"]
        for row in result.rows:
            lines.append("| " + " | ".join(str(row[k]).replace("|", "/") for k in
                                           ("symbol", "value", "unit", "origin", "source", "used_in")) + " |")
        lines.append("")
    lines += ["## Messages", ""]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    return lines


def write_param_ledger_report(project_root: str | Path, config: WorkflowConfig) -> ParamLedgerResult:
    result = run_param_ledger_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "param_ledger_report.md",
        "Parameter Ledger Report",
        render_param_ledger_markdown(result),
    )
    return result
