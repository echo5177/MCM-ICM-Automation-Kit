"""Read the LaTeX source the way LaTeX compiles it: local ``\\input`` files and simple macros.

The checkers used to read ``main.tex`` alone. A paper that keeps its result tables in
``tables/*.tex`` (the 2026 ProbA project pulls in ten of them with ``\\input``) was then
checked without its tables: numbers in those tables never counted as "cited", and a
section kept in its own file would be reported missing.

Only the safe, deterministic subset is implemented:

- local ``\\input{...}`` / ``\\include{...}``, resolved the way TeX resolves them — against
  the directory of the **main** document (TeX's working directory), falling back to the
  including file's directory;
- zero-argument ``\\newcommand`` / ``\\renewcommand`` / ``\\providecommand`` definitions,
  so ``\\Team`` in the header reads as the control number it stands for.

Comments are stripped first. Missing or out-of-project inputs are left as commands, and
include cycles are cut instead of recursing forever.
"""

from __future__ import annotations

from pathlib import Path
import re


COMMENT_RE = re.compile(r"(?<!\\)%.*")
INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")
COMMAND_START_RE = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand)\*?\s*"
    r"(?:\{\\([A-Za-z@]+)\}|\\([A-Za-z@]+))\s*"
    r"(?:\[\s*0\s*\])?\s*\{"
)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _matching_brace(text: str, opening: int) -> int | None:
    depth = 0
    index = opening
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2          # an escaped brace does not change the grouping depth
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _candidates(name: str, main_dir: Path, including_dir: Path) -> list[Path]:
    out = []
    for base in (main_dir, including_dir):
        candidate = (base / name).resolve()
        if not candidate.suffix:
            candidate = candidate.with_suffix(".tex")
        if candidate not in out:
            out.append(candidate)
    return out


def _expand_inputs(path: Path, main_dir: Path, root: Path, stack: tuple[Path, ...]) -> str:
    resolved = path.resolve()
    if resolved in stack or not resolved.is_file() or not _inside(resolved, root):
        return ""
    text = COMMENT_RE.sub("", resolved.read_text(encoding="utf-8", errors="replace"))

    def replace(match: re.Match[str]) -> str:
        for candidate in _candidates(match.group(1).strip(), main_dir, resolved.parent):
            if _inside(candidate, root) and candidate.is_file():
                return _expand_inputs(candidate, main_dir, root, (*stack, resolved))
        return match.group(0)

    return INPUT_RE.sub(replace, text)


def _remove_definitions(text: str) -> tuple[str, dict[str, str]]:
    macros: dict[str, str] = {}
    pieces: list[str] = []
    cursor = 0
    while True:
        match = COMMAND_START_RE.search(text, cursor)
        if match is None:
            pieces.append(text[cursor:])
            break
        opening = match.end() - 1
        closing = _matching_brace(text, opening)
        if closing is None:
            pieces.append(text[cursor:])
            break
        pieces.append(text[cursor:match.start()])
        name = match.group(1) or match.group(2)
        macros[name] = text[opening + 1:closing]
        cursor = closing + 1
    return "".join(pieces), macros


def _expand_zero_arg_macros(text: str, macros: dict[str, str]) -> str:
    for _ in range(8):
        changed = False
        for name in sorted(macros, key=len, reverse=True):
            pattern = re.compile(rf"\\{re.escape(name)}(?![A-Za-z@])")
            text, count = pattern.subn(lambda _m, value=macros[name]: value, text)
            changed = changed or bool(count)
        if not changed:
            break
    return text


def read_tex_expanded(path: str | Path, project_root: str | Path | None = None) -> str:
    """Active source with local inputs and zero-argument macros expanded.

    Returns an empty string when ``path`` does not exist. Command definitions are removed
    after their values are collected, so a number that only sits in a definition cannot
    count as cited in the paper.
    """
    tex_path = Path(path).resolve()
    root = Path(project_root).resolve() if project_root is not None else tex_path.parent
    source = _expand_inputs(tex_path, tex_path.parent, root, ())
    body, macros = _remove_definitions(source)
    return _expand_zero_arg_macros(body, macros)


def macro_values(path: str | Path, project_root: str | Path | None = None) -> dict[str, str]:
    """The zero-argument macros the document defines (e.g. ``{"Team": "2601234"}``)."""
    tex_path = Path(path).resolve()
    root = Path(project_root).resolve() if project_root is not None else tex_path.parent
    _body, macros = _remove_definitions(_expand_inputs(tex_path, tex_path.parent, root, ()))
    return macros
