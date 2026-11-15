"""Model ladder: the naive baseline, each added component, and whether the component won.

Two post-mortems reached the same conclusion from opposite ends. The 2026 MCM A entry built
a differential-algebraic battery model with no baseline, could not feed it, and invented
its inputs. The CUMCM 2026 entry had an agent that could build anything, and it built a
model-predictive controller for a question where "charge when over-bought, discharge when
short" was 5% cheaper: 367,920 back-substituted periods proved the arithmetic and 20
ablations compared information sets, but no experiment removed the controller. COMAP's
judges ask for the same thing in their own words: "Start with a simple model and then
refine it", and "Against what baseline can you compare/validate it?".

The ladder is `reports/model_ladder.csv`, written by the pipeline:

| column | meaning |
| --- | --- |
| `req_id` | the requirement (as in `reports/requirements.csv`) |
| `rung` | 0 for the naive baseline, then 1, 2, ... as components are added |
| `model` | what this rung is, in a few words |
| `metric` | the one metric the rungs are compared on |
| `value` | its value, out of sample where that applies |
| `higher_is_better` | `yes` or `no` |
| `kept` | `yes` on the rung the paper uses, `no` elsewhere |
| `note` | why a rung is kept although a simpler one scores better; or why no baseline applies |

The rule is the post-mortem's: a component stays only if it wins. The check fails when the
rung the paper keeps is beaten by another rung and no note says why, and when a `model`
requirement has no baseline at all. A requirement for which no baseline makes sense gets a
single rung-0 row whose `model` is `n/a` and whose `note` gives the reason.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .pdf_text import page_texts
from .reporting import CheckMessage, status_from_messages, write_markdown_report
from .requirement_checker import read_requirements
from .result_checker import _normal_text, _value_variants
from .tex_source import read_tex_expanded


REQUIRED_COLUMNS = ("req_id", "rung", "model", "metric", "value", "higher_is_better", "kept", "note")
TRUE = {"yes", "y", "true", "1"}


@dataclass(frozen=True)
class Rung:
    req_id: str
    rung: int
    model: str
    metric: str
    value: float | None
    raw_value: str
    higher_is_better: bool
    kept: bool
    note: str

    @property
    def not_applicable(self) -> bool:
        return self.model.strip().lower() in {"n/a", "na", "none", "not applicable"}


@dataclass(frozen=True)
class ModelLadderResult:
    messages: list[CheckMessage]
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def read_ladder(path: Path) -> tuple[list[Rung], list[str], list[str]]:
    """Rungs, missing columns, and rows that could not be read."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = [name.strip() for name in (reader.fieldnames or [])]
        raw = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    rungs, bad = [], []
    if missing:
        return rungs, missing, bad
    for line, row in enumerate(raw, start=2):
        if not row["req_id"] or row["req_id"].startswith("["):
            continue
        try:
            rung = int(row["rung"])
        except ValueError:
            bad.append(f"line {line}: rung '{row['rung']}' is not an integer")
            continue
        try:
            value: float | None = float(row["value"].replace(",", ""))
        except ValueError:
            value = None
        rungs.append(Rung(row["req_id"], rung, row["model"], row["metric"], value, row["value"],
                          row["higher_is_better"].lower() in TRUE, row["kept"].lower() in TRUE,
                          row["note"]))
    return rungs, missing, bad


def _stage(config: WorkflowConfig, message: str) -> CheckMessage:
    return CheckMessage("fail" if config.is_final else "warn", message)


def _better(a: float, b: float, higher: bool) -> bool:
    """a strictly better than b, beyond rounding."""
    tolerance = 1e-9 * max(abs(a), abs(b), 1.0)
    return (a - b) > tolerance if higher else (b - a) > tolerance


def check_group(req_id: str, rungs: list[Rung], config: WorkflowConfig) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    rungs = sorted(rungs, key=lambda r: r.rung)
    baseline = next((r for r in rungs if r.rung == 0), None)
    if baseline is None:
        return [_stage(config, f"{req_id}: no rung 0. Enter the naive baseline (a grouped mean, a "
                               f"linear fit, the rule a person would use) and its score.")]
    if baseline.not_applicable:
        if not baseline.note:
            messages.append(_stage(config, f"{req_id}: the baseline is marked n/a with no reason in `note`."))
        return messages
    if len(rungs) < 2:
        return [CheckMessage(
            "warn", f"{req_id}: only the baseline is on the ladder. If the baseline is the model "
                    f"the paper uses, say so in the paper; otherwise add the rungs above it.")]
    unreadable = [r for r in rungs if r.value is None]
    if unreadable:
        return [_stage(config, f"{req_id}: value(s) not numeric: "
                               + ", ".join(f"rung {r.rung} '{r.raw_value}'" for r in unreadable) + ".")]
    if len({r.metric for r in rungs}) > 1:
        messages.append(CheckMessage(
            "warn", f"{req_id}: rungs use different metrics ({', '.join(sorted({r.metric for r in rungs}))}); "
                    f"a ladder compares one metric."))
    kept = [r for r in rungs if r.kept]
    if len(kept) != 1:
        return messages + [_stage(config, f"{req_id}: {len(kept)} rung(s) marked kept; mark exactly "
                                          f"the one the paper uses.")]
    chosen = kept[0]
    higher = chosen.higher_is_better
    beaten_by = [r for r in rungs if r is not chosen and _better(r.value, chosen.value, higher)]
    simpler = [r for r in beaten_by if r.rung < chosen.rung]
    if simpler:
        best = max(simpler, key=lambda r: r.value) if higher else min(simpler, key=lambda r: r.value)
        text = (f"{req_id}: the kept model (rung {chosen.rung}, '{chosen.model}', {chosen.metric} "
                f"{chosen.raw_value}) loses to a simpler rung (rung {best.rung}, '{best.model}', "
                f"{best.raw_value}). A component that does not win does not stay")
        if chosen.note:
            messages.append(CheckMessage("warn", text + f"; the note gives a reason: '{chosen.note}'. "
                                                        f"Make sure the paper gives it too."))
        else:
            messages.append(CheckMessage("fail", text + ". Use the simpler model, or record in `note` "
                                                        "why the paper keeps this one."))
    elif beaten_by:
        best = beaten_by[0]
        messages.append(CheckMessage(
            "warn", f"{req_id}: rung {best.rung} ('{best.model}', {best.raw_value}) scores better than "
                    f"the kept rung {chosen.rung} ({chosen.raw_value}). Say in the paper why it is not used."))
    return messages


def run_model_ladder_checks(project_root: str | Path, config: WorkflowConfig) -> ModelLadderResult:
    root = Path(project_root).resolve()
    ladder_path = resolve_project_path(root, config.model_ladder_file)
    table = resolve_project_path(root, config.requirements_file)
    model_reqs: list[str] = []
    if table.is_file():
        rows, missing_columns = read_requirements(table)
        if not missing_columns:
            model_reqs = [r.req_id for r in rows if r.kind == "model" and r.req_id]

    if not ladder_path.is_file():
        which = (f"for {', '.join(model_reqs)}" if model_reqs else "for each modeling requirement")
        return ModelLadderResult([_stage(
            config,
            f"No model ladder ({config.model_ladder_file}). Record the naive baseline and each "
            f"added component {which}, on one metric. Judges ask: 'Against what baseline can "
            f"you compare/validate it?'",
        )])

    rungs, missing, bad = read_ladder(ladder_path)
    if missing:
        return ModelLadderResult([CheckMessage(
            "fail", f"{config.model_ladder_file} lacks column(s): {', '.join(missing)}.")])
    messages = [CheckMessage("fail", f"{config.model_ladder_file} {text}.") for text in bad]

    groups: dict[str, list[Rung]] = {}
    for rung in rungs:
        groups.setdefault(rung.req_id, []).append(rung)
    for req_id in model_reqs:
        if req_id not in groups:
            messages.append(_stage(config, f"{req_id} is a modeling requirement with no rung on the ladder."))
    for req_id, members in groups.items():
        messages.extend(check_group(req_id, members, config))

    # The paper has to show the comparison: judges do not see the code.
    tex_path = resolve_project_path(root, config.paper_tex)
    pdf_path = resolve_project_path(root, config.paper_pdf)
    paper_text = ""
    if tex_path.is_file():
        paper_text = read_tex_expanded(tex_path, root)
    elif pdf_path.is_file():
        paper_text = "\n".join(page_texts(pdf_path))
    normal = _normal_text(paper_text)
    report_rows: list[dict[str, Any]] = []
    for req_id, members in groups.items():
        members = sorted(members, key=lambda r: r.rung)
        baseline = next((r for r in members if r.rung == 0), None)
        for rung in members:
            gain = ""
            if baseline and baseline.value not in (None, 0) and rung.value is not None and rung.rung > 0:
                change = 100 * (rung.value - baseline.value) / abs(baseline.value)
                gain = f"{change:+.1f}%"
            report_rows.append({"req_id": req_id, "rung": rung.rung, "model": rung.model,
                                "metric": rung.metric, "value": rung.raw_value,
                                "kept": "yes" if rung.kept else "", "vs_baseline": gain})
        if (paper_text and baseline and not baseline.not_applicable and len(members) > 1
                and not any(v.lower().replace(",", "") in normal for v in _value_variants(baseline.raw_value))):
            messages.append(CheckMessage(
                "warn",
                f"{req_id}: the baseline's score ({baseline.raw_value}) is not in the paper. A judge "
                f"cannot see the code; print the comparison that shows the model earns its complexity.",
            ))

    if not any(m.level in {"fail", "warn"} for m in messages):
        messages.append(CheckMessage("pass", f"Model ladder holds for {len(groups)} requirement(s)."))
    return ModelLadderResult(messages=messages, rows=report_rows)


def render_model_ladder_markdown(result: ModelLadderResult) -> list[str]:
    lines = [f"- Status: {result.status}", ""]
    if result.rows:
        lines += ["| Requirement | Rung | Model | Metric | Value | vs baseline | Kept |",
                  "| --- | ---: | --- | --- | ---: | ---: | --- |"]
        for row in result.rows:
            lines.append(f"| {row['req_id']} | {row['rung']} | {row['model']} | {row['metric']} | "
                         f"{row['value']} | {row['vs_baseline']} | {row['kept']} |")
        lines.append("")
    lines += ["## Messages", ""]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    return lines


def write_model_ladder_report(project_root: str | Path, config: WorkflowConfig) -> ModelLadderResult:
    result = run_model_ladder_checks(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "model_ladder_report.md",
        "Model Ladder Report",
        render_model_ladder_markdown(result),
    )
    return result
