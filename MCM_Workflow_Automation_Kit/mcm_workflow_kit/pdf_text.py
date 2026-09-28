"""Read a compiled PDF's text layer page by page, and its document properties.

Separate module so the submission, hygiene and format checks share one extraction.
Both helpers degrade to empty results when poppler/xpdf tools are missing; the callers
decide whether that is a failure.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess


def page_texts(pdf_path: str | Path) -> list[str]:
    """Text layer per page (index 0 is page 1). Empty list if pdftotext is unavailable."""
    try:
        completed = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", str(pdf_path), "-"],
            capture_output=True, check=False,
        )
    except FileNotFoundError:
        return []
    pages = completed.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def pdf_metadata(pdf_path: str | Path) -> dict[str, str]:
    """Document properties from pdfinfo (Title, Author, Creator, ...)."""
    try:
        completed = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, check=False)
    except FileNotFoundError:
        return {}
    meta: dict[str, str] = {}
    for line in completed.stdout.decode("utf-8", "replace").splitlines():
        match = re.match(r"^([A-Za-z ]+):[ \t]*(.*)$", line)
        if match:
            meta[match.group(1).strip()] = match.group(2).strip()
    return meta
