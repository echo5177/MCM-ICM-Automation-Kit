"""Experiment integrity audit.

The Kit could prove a figure existed, a number was traceable, and a script ran. It
could not prove the *experiment behind the figure actually varied what the paper
says it varied*. This node closes that gap.

It exists because of a defect found in a real award-winning MCM paper
(2023 Problem B, team 2316192, published at GuangLun2000/COMAP-MCM-2026). Its
sensitivity-analysis script reads:

    a_j = 90
    for i in range(1, a_j):
        a = a_j * math.pi / 180      # <- a_j, not i
        ...

The loop variable `i` is never used, so `a` is 90 degrees on every iteration. The
script produces 89 points of a *fixed-parameter* stochastic run, and the paper
presents them as a sweep of alpha across (0, 90). No random seed is set either, so
the run is not reproducible. Both defects survived into an award-winning paper.

Three checks, all static and offline:

1. `audit_parameter_sweeps` - a loop whose variable is never read while a variable
   from its own `range()` bounds *is* read in the body. That is the exact
   signature above and is a `fail`: the sweep is not sweeping.
2. `audit_random_seeds` - stochastic code with no seed anywhere in the file.
3. `audit_figure_text` - template pollution in figure sources. The same paper's
   central workflow figure (Figure 3, "Overview of our works") still carried
   "Super-net w/o pretrained initialization", "Kernel-level", and "Depth-level"
   from a neural-architecture-search template, in a paper about wildlife
   conservation.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from .config import WorkflowConfig, resolve_project_path
from .reporting import CheckMessage, status_from_messages, write_markdown_report


# Calls that produce randomness.
RANDOM_USE_RE = re.compile(
    r"\b(?:np|numpy)\.random\.\w+|\brandom\.\w+|\btorch\.(?:rand|randn|randint)\w*"
)
# Anything that pins the stream. `default_rng()` only counts when given an argument.
SEED_RE = re.compile(
    r"\b(?:np|numpy)\.random\.seed\s*\(|\brandom\.seed\s*\(|\btorch\.manual_seed\s*\(|"
    r"\bdefault_rng\s*\(\s*[^)\s]|\bRandomState\s*\(\s*[^)\s]|\brandom_state\s*="
)

# Distinctive strings that betray a figure built on someone else's template.
# Kept deliberately narrow: bare "backbone"/"head" are excluded because they occur
# legitimately (road backbone, protein backbone, table head). Extend per project via
# `template_pollution_terms` rather than loosening these.
DEFAULT_POLLUTION_TERMS = [
    "super-net",
    "supernet",
    "pretrained initialization",
    "w/o pretrained",
    "kernel-level",
    "depth-level",
    "lorem ipsum",
    "click to edit",
    "double-click to edit",
    "your text here",
    "sample text",
    "insert text here",
    "edit master",
    "placeholder text",
]


@dataclass(frozen=True)
class ExperimentAuditResult:
    messages: list[CheckMessage]
    scanned_scripts: int = 0
    scanned_figures: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_messages(self.messages)


def _iter_files(root: Path, patterns: list[str]) -> list[Path]:
    seen: list[Path] = []
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and "__pycache__" not in path.parts and path not in seen:
                seen.append(path)
    return seen


def _loads_in(node: ast.AST) -> set[str]:
    """Names read (not merely assigned) anywhere under `node`."""
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_target_names(element))
        return names
    return []


def audit_parameter_sweeps(source: str, display_path: str) -> list[CheckMessage]:
    """Flag loops that iterate without using the loop variable.

    The `fail` case is the specific award-paper bug: the loop variable is never
    read, but a variable from the loop's own `range()` bounds *is* read in the
    body -- i.e. the body uses the sweep's upper bound where it meant to use the
    index, so every iteration computes the same thing.
    """
    messages: list[CheckMessage] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [
            CheckMessage("warn", f"{display_path}: could not parse for sweep audit ({exc.msg}).")
        ]

    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.AsyncFor)):
            continue
        names = [n for n in _target_names(node.target) if not n.startswith("_")]
        if not names:
            continue

        body_loads: set[str] = set()
        for statement in node.body:
            body_loads |= _loads_in(statement)

        unused = [n for n in names if n not in body_loads]
        if not unused:
            continue

        bound_names: set[str] = set()
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
            if node.iter.func.id == "range":
                for arg in node.iter.args:
                    bound_names |= _loads_in(arg)

        leaked = sorted(bound_names & body_loads)
        line = getattr(node, "lineno", 0)
        if leaked:
            messages.append(
                CheckMessage(
                    "fail",
                    f"{display_path}:{line}: loop variable "
                    f"{', '.join(unused)} is never used, but the range bound "
                    f"{', '.join(leaked)} IS used inside the loop. Every iteration "
                    f"computes the same value -- this loop is not sweeping the "
                    f"parameter it appears to sweep. Any figure or table built from "
                    f"it is mislabelled.",
                )
            )
        else:
            messages.append(
                CheckMessage(
                    "warn",
                    f"{display_path}:{line}: loop variable {', '.join(unused)} is "
                    f"never used in the body. If this is a repetition loop, rename it "
                    f"to `_` to say so; if it was meant to be a sweep, use it.",
                )
            )
    return messages


def audit_random_seeds(source: str, display_path: str) -> list[CheckMessage]:
    """Flag stochastic scripts that pin no seed, so results cannot be reproduced."""
    stripped = re.sub(r"#.*", "", source)
    if not RANDOM_USE_RE.search(stripped):
        return []
    if SEED_RE.search(stripped):
        return []
    return [
        CheckMessage(
            "warn",
            f"{display_path}: uses randomness but sets no seed. Fix the seed and "
            f"report a spread over repeated runs; an unseeded result cannot be "
            f"reproduced by a judge or by you.",
        )
    ]


def audit_figure_text(text: str, display_path: str, terms: list[str]) -> list[CheckMessage]:
    """Flag template text left inside a figure source."""
    lowered = text.lower()
    hits = sorted({term for term in terms if term.lower() in lowered})
    if not hits:
        return []
    return [
        CheckMessage(
            "fail",
            f"{display_path}: contains template text ({', '.join(hits)}) that does not "
            f"belong to this problem. A figure built on someone else's template with "
            f"its labels still attached reads as unserious -- this exact defect shipped "
            f"in an award-winning paper's main workflow figure.",
        )
    ]


def run_experiment_audit(
    project_root: str | Path,
    config: WorkflowConfig,
) -> ExperimentAuditResult:
    root = Path(project_root).resolve()
    messages: list[CheckMessage] = []
    findings: list[dict[str, Any]] = []

    scripts = _iter_files(root, config.code_globs)
    for path in scripts:
        display = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8", errors="replace")
        for message in audit_parameter_sweeps(source, display) + audit_random_seeds(
            source, display
        ):
            messages.append(message)
            findings.append({"file": display, "level": message.level, "message": message.message})

    terms = list(DEFAULT_POLLUTION_TERMS) + list(config.template_pollution_terms)
    figures = _iter_files(root, config.figure_source_globs)
    for path in figures:
        display = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for message in audit_figure_text(text, display, terms):
            messages.append(message)
            findings.append({"file": display, "level": message.level, "message": message.message})

    if not messages:
        messages.append(
            CheckMessage(
                "pass",
                f"Experiment audit passed over {len(scripts)} script(s) and "
                f"{len(figures)} figure source(s).",
            )
        )

    return ExperimentAuditResult(
        messages=messages,
        scanned_scripts=len(scripts),
        scanned_figures=len(figures),
        findings=findings,
    )


def render_experiment_audit_markdown(result: ExperimentAuditResult) -> list[str]:
    lines = [
        f"- Status: {result.status}",
        f"- Scripts scanned: {result.scanned_scripts}",
        f"- Figure sources scanned: {result.scanned_figures}",
        "- Checks: parameter sweeps actually sweep; stochastic runs are seeded; "
        "figure sources carry no foreign template text.",
        "",
        "## Messages",
        "",
    ]
    lines.extend(f"- {m.level.upper()}: {m.message}" for m in result.messages)
    return lines


def write_experiment_audit_report(
    project_root: str | Path,
    config: WorkflowConfig,
) -> ExperimentAuditResult:
    result = run_experiment_audit(project_root, config)
    reports_dir = resolve_project_path(project_root, config.workflow_reports_dir)
    write_markdown_report(
        reports_dir / "experiment_audit_report.md",
        "Experiment Integrity Audit",
        render_experiment_audit_markdown(result),
    )
    return result
