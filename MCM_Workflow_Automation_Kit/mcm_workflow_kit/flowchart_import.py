"""Import a flowchart a teammate drew (PowerPoint / PDF / SVG) as a vector PDF for the paper.

Ported from the CUMCM Kit, where the 2026 contest's overall flowchart came from a
teammate's PowerPoint and importing it went wrong three times:

1. calling PowerPoint to export hung with no visible dialog;
2. the wide flowchart was put on a landscape page, and the user rejected it on sight: a
   wide chart should be scaled onto an ordinary portrait page so it sits in the paper
   like any other figure;
3. the gate's diagram checks kept inspecting the Kit's own old diagram and never looked at
   the teammate's.

This module makes it one fixed route: export (PowerPoint, else LibreOffice) -> crop to the
drawn content -> clear document properties -> measure the font size, height and raster
images once scaled to the text width -> write an import receipt. The diagram gates read
that receipt for `diagram_sources[].origin = "user"` instead of asking for the Kit's JSON.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile


SUPPORTED_SUFFIXES = {".pptx", ".ppt", ".pdf", ".svg"}
# Kit template: US letter, 1in left, 0.75in right, 1in top/bottom -> 6.75in x 9in.
TEXT_WIDTH_CM = 17.1
TEXT_HEIGHT_CM = 22.9
MIN_FONT_PT = 7.0              # smallest font that stays legible in print
MAX_HEIGHT_FRACTION = 0.85     # leave room for the caption and some text on the page
PT_PER_CM = 72 / 2.54

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


class FlowchartImportError(RuntimeError):
    pass


@dataclass
class ImportReceipt:
    source: str
    source_sha256: str
    source_kind: str
    page: int
    output: str
    width_cm: float
    height_cm: float
    target_width_cm: float
    scale: float
    final_height_cm: float
    min_font_pt_source: float | None
    min_font_pt_final: float | None
    median_font_pt_final: float | None
    font_basis: str
    raster_images: int
    warnings: list[str] = field(default_factory=list)

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def receipt_path_for(pdf: Path) -> Path:
    return pdf.with_name(f"{pdf.stem}.import.json")


# ---------------------------------------------------------------------------
# Export to PDF
# ---------------------------------------------------------------------------

# The watchdog lives in Python, not in a PowerShell Start-Job. Two hangs were seen:
# 1. the COM call hangs with no visible dialog;
# 2. with the PowerShell output captured through a pipe, killing PowerShell on timeout is
#    not enough: the grandchild holding the COM call keeps the pipe open and communicate()
#    never returns. So output goes to a file, and on timeout the PowerShell tree and only
#    the PowerPoint processes started by this run are terminated. When PowerPoint was already
#    running (the user's own instance), it is neither quit nor killed.
_POWERPOINT_SCRIPT = r"""
param([string]$src, [string]$out, [string]$quit)
$ErrorActionPreference = "Stop"
$app = New-Object -ComObject PowerPoint.Application
try { $app.DisplayAlerts = 1 } catch {}
$pres = $app.Presentations.Open($src, -1, 0, 0)
$pres.SaveAs($out, 32)
$pres.Close()
[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($pres)
if ($quit -eq "1") { $app.Quit() }
[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
[GC]::Collect()
[GC]::WaitForPendingFinalizers()
"done"
"""


def _powerpoint_pids() -> set[int]:
    try:
        listing = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, errors="replace", timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    pids: set[int] = set()
    for line in listing.splitlines():
        cells = [cell.strip().strip('"') for cell in line.split('","')]
        if len(cells) >= 2 and cells[0].lower().startswith("powerpnt"):
            try:
                pids.add(int(cells[1]))
            except ValueError:
                pass
    return pids


def _kill(pid: int, tree: bool = False) -> None:
    args = ["taskkill", "/PID", str(pid), "/F"] + (["/T"] if tree else [])
    subprocess.run(args, capture_output=True, timeout=30)


def export_with_powerpoint(src: Path, out_pdf: Path, timeout: int = 150, attempts: int = 2) -> None:
    """Export through PowerPoint, retrying once after a timeout.

    Measured on 2026-09-28: the first run of the day timed out with PowerPoint never
    starting; a rerun a minute later exported in about 15 s.
    """
    for attempt in range(1, attempts + 1):
        try:
            _export_with_powerpoint_once(src, out_pdf, timeout)
            return
        except _ExportTimeout:
            if attempt == attempts:
                raise FlowchartImportError(
                    f"PowerPoint did not finish exporting within {timeout} s ({attempts} tries); the "
                    f"processes this run started were stopped. Save the slide as PDF in PowerPoint "
                    f"and import the PDF.") from None


class _ExportTimeout(Exception):
    pass


def _export_with_powerpoint_once(src: Path, out_pdf: Path, timeout: int) -> None:
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if shell is None or shutil.which("tasklist") is None:
        raise FlowchartImportError("Not a Windows machine with PowerPoint; cannot export through it.")
    before = _powerpoint_pids()
    was_running = bool(before)
    with tempfile.TemporaryDirectory(prefix="mcm-ppt-") as tmp:
        # ASCII-only paths for COM, and a copy so the user's open file is never locked.
        work = Path(tmp)
        copy = work / f"source{src.suffix.lower()}"
        shutil.copy2(src, copy)
        exported = work / "exported.pdf"
        script = work / "export.ps1"
        script.write_text(_POWERPOINT_SCRIPT, encoding="utf-8-sig")
        log_path = work / "export.log"
        with log_path.open("w", encoding="utf-8") as log:
            proc = subprocess.Popen(
                [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                 str(script), str(copy), str(exported), "0" if was_running else "1"],
                stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            )
            try:
                proc.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill(proc.pid, tree=True)
        if timed_out:
            for pid in _powerpoint_pids() - before:
                _kill(pid)
            raise _ExportTimeout()
        if not was_running:
            for _ in range(10):          # after Quit the COM server lingers for a moment
                if not (_powerpoint_pids() - before):
                    break
                time.sleep(1)
            for pid in _powerpoint_pids() - before:
                _kill(pid)
        if not exported.is_file():
            detail = log_path.read_text(encoding="utf-8", errors="replace").strip()[:300]
            raise FlowchartImportError(f"PowerPoint did not export a PDF. {detail}")
        shutil.copy2(exported, out_pdf)


def export_with_libreoffice(src: Path, out_pdf: Path, timeout: int = 150) -> None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        raise FlowchartImportError("LibreOffice not found.")
    with tempfile.TemporaryDirectory(prefix="mcm-lo-") as tmp:
        copy = Path(tmp) / f"source{src.suffix.lower()}"
        shutil.copy2(src, copy)
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(copy)],
                       capture_output=True, timeout=timeout)
        exported = Path(tmp) / "source.pdf"
        if not exported.is_file():
            raise FlowchartImportError("LibreOffice did not export a PDF.")
        shutil.copy2(exported, out_pdf)


def export_svg(src: Path, out_pdf: Path) -> None:
    for tool, args in (
        ("rsvg-convert", ["-f", "pdf", "-o", str(out_pdf), str(src)]),
        ("inkscape", [str(src), "--export-type=pdf", f"--export-filename={out_pdf}"]),
    ):
        exe = shutil.which(tool)
        if exe:
            subprocess.run([exe, *args], capture_output=True, timeout=120)
            if out_pdf.is_file():
                return
    try:
        import cairosvg  # type: ignore
    except ImportError:
        raise FlowchartImportError(
            "No SVG converter (rsvg-convert, Inkscape or cairosvg). Export a PDF from the drawing "
            "tool and import that.") from None
    cairosvg.svg2pdf(url=str(src), write_to=str(out_pdf))


def to_pdf(src: Path, work: Path) -> Path:
    suffix = src.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise FlowchartImportError(
            f"Unsupported format {suffix}. Supported: {sorted(SUPPORTED_SUFFIXES)}; export draw.io to PDF first.")
    out = work / "raw.pdf"
    if suffix == ".pdf":
        shutil.copy2(src, out)
    elif suffix == ".svg":
        export_svg(src, out)
    else:
        errors: list[str] = []
        for exporter in (export_with_powerpoint, export_with_libreoffice):
            try:
                exporter(src, out)
                break
            except (FlowchartImportError, OSError, subprocess.SubprocessError) as exc:
                errors.append(str(exc))
        else:
            raise FlowchartImportError(
                "Neither PowerPoint nor LibreOffice could export: " + "; ".join(errors)
                + ". Save the slide as PDF in PowerPoint and import the PDF.")
    return out


# ---------------------------------------------------------------------------
# Crop and clean
# ---------------------------------------------------------------------------

def content_bbox_pt(pdf: Path, page: int, dpi: int = 150) -> tuple[float, float, float, float]:
    """Inked area of the page in PDF points (origin bottom-left), found on a rendered bitmap."""
    from PIL import Image
    from pypdf import PdfReader

    exe = shutil.which("pdftocairo")
    if exe is None:
        raise FlowchartImportError("pdftocairo (poppler / TeX Live) not found; cannot find the crop box.")
    box = PdfReader(str(pdf)).pages[page - 1].mediabox
    width, height = float(box.width), float(box.height)
    with tempfile.TemporaryDirectory(prefix="mcm-bbox-") as tmp:
        stem = Path(tmp) / "page"
        subprocess.run([exe, "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
                        "-singlefile", str(pdf), str(stem)], capture_output=True, timeout=120)
        png = stem.with_suffix(".png")
        if not png.is_file():
            raise FlowchartImportError("pdftocairo did not render the page.")
        with Image.open(png) as image:
            gray = image.convert("L")
            bbox = gray.point(lambda value: 255 if value < 245 else 0).getbbox()
            px_w, px_h = gray.size
    if bbox is None:
        raise FlowchartImportError("The page is blank.")
    sx, sy = width / px_w, height / px_h
    left, top, right, bottom = bbox
    return (left * sx, height - bottom * sy, right * sx, height - top * sy)


def crop_and_clean(src_pdf: Path, page: int, bbox: tuple[float, float, float, float],
                   out_pdf: Path, margin_pt: float = 3.0) -> tuple[float, float]:
    """Keep one page, crop to the content plus a margin, clear document properties."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, RectangleObject

    reader = PdfReader(str(src_pdf))
    target = reader.pages[page - 1]
    box = target.mediabox
    x0, y0, x1, y1 = bbox
    left = max(float(box.left), float(box.left) + x0 - margin_pt)
    bottom = max(float(box.bottom), float(box.bottom) + y0 - margin_pt)
    right = min(float(box.right), float(box.left) + x1 + margin_pt)
    top = min(float(box.top), float(box.bottom) + y1 + margin_pt)
    rect = RectangleObject([left, bottom, right, top])
    for name in ("/MediaBox", "/CropBox", "/TrimBox", "/BleedBox", "/ArtBox"):
        target[NameObject(name)] = rect
    writer = PdfWriter()
    writer.add_page(target)
    # PowerPoint writes the account name into /Author; COMAP allows no identifying details.
    writer.add_metadata({"/Producer": "", "/Creator": "", "/Author": "", "/Title": ""})
    if "/Metadata" in writer._root_object:
        del writer._root_object["/Metadata"]
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with out_pdf.open("wb") as fh:
        writer.write(fh)
    return right - left, top - bottom


def raster_image_count(pdf: Path) -> int:
    exe = shutil.which("pdfimages")
    if exe is None:
        return 0
    completed = subprocess.run([exe, "-list", str(pdf)], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=60)
    return len([line for line in (completed.stdout or "").splitlines()[2:] if line.strip()])


# ---------------------------------------------------------------------------
# Font sizes
# ---------------------------------------------------------------------------

def _ordered_slide_parts(archive: zipfile.ZipFile) -> list[str]:
    presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
    rels = ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
    targets = {rel.get("Id"): rel.get("Target") for rel in rels.findall("rel:Relationship", NS)}
    parts = []
    for sld in presentation.findall("p:sldIdLst/p:sldId", NS):
        target = targets.get(sld.get(f"{{{NS['r']}}}id"), "")
        if target:
            parts.append("ppt/" + target.lstrip("/").removeprefix("ppt/"))
    return parts


def pptx_font_sizes(pptx: Path, slide: int = 1) -> list[float]:
    """Explicit font sizes on the slide (pt), times any shrink-text-on-overflow scale."""
    with zipfile.ZipFile(pptx) as archive:
        parts = _ordered_slide_parts(archive)
        if not 1 <= slide <= len(parts):
            raise FlowchartImportError(f"There is no slide {slide} ({len(parts)} slides).")
        root = ET.fromstring(archive.read(parts[slide - 1]))
    sizes: list[float] = []
    for body in root.iter(f"{{{NS['p']}}}txBody"):
        scale = 1.0
        autofit = body.find("a:bodyPr/a:normAutofit", NS)
        if autofit is not None and autofit.get("fontScale"):
            scale = int(autofit.get("fontScale")) / 100000
        if not any((node.text or "").strip() for node in body.iter(f"{{{NS['a']}}}t")):
            continue
        for tag in ("rPr", "endParaRPr", "defRPr"):
            for node in body.iter(f"{{{NS['a']}}}{tag}"):
                if node.get("sz"):
                    sizes.append(int(node.get("sz")) / 100 * scale)
    return sizes


def pdf_font_sizes(pdf: Path, page: int = 1) -> list[float]:
    """Font size of each text run: font size times the vertical scale of Tm and CTM.

    pypdf rather than `pdftotext -bbox`: the pdftotext on PATH differs by shell on Windows
    (Git Bash finds Git's Xpdf 4.00, which has no -bbox).
    """
    from pypdf import PdfReader

    sizes: list[float] = []

    def visit(text, cm, tm, _font, font_size) -> None:
        if not text or not text.strip() or not font_size:
            return
        scale = math.hypot(tm[2], tm[3]) * math.hypot(cm[2], cm[3])
        sizes.append(float(font_size) * (scale or 1.0))

    try:
        PdfReader(str(pdf)).pages[page - 1].extract_text(visitor_text=visit)
    except Exception:  # noqa: BLE001 - font sizes are advisory; unknown is acceptable
        return []
    return [size for size in sizes if size > 0.5]


# ---------------------------------------------------------------------------
# Main route
# ---------------------------------------------------------------------------

def import_flowchart(src: Path, out_pdf: Path, *, page: int = 1,
                     target_width_cm: float = TEXT_WIDTH_CM) -> ImportReceipt:
    src = src.resolve()
    if not src.is_file():
        raise FlowchartImportError(f"Source not found: {src}")
    with tempfile.TemporaryDirectory(prefix="mcm-flow-") as tmp:
        raw = to_pdf(src, Path(tmp))
        bbox = content_bbox_pt(raw, page)
        width_pt, height_pt = crop_and_clean(raw, page, bbox, out_pdf)

    scale = target_width_cm * PT_PER_CM / width_pt
    final_height_cm = height_pt * scale / PT_PER_CM
    if src.suffix.lower() == ".pptx":
        sizes, basis = pptx_font_sizes(src, page), "pptx"
    else:
        sizes, basis = pdf_font_sizes(out_pdf), "pdf"
    min_source = min(sizes) if sizes else None
    min_final = round(min_source * scale, 2) if min_source is not None else None
    median_final = round(sorted(sizes)[len(sizes) // 2] * scale, 2) if sizes else None
    rasters = raster_image_count(out_pdf)

    warnings: list[str] = []
    if min_final is not None and min_final < MIN_FONT_PT:
        warnings.append(
            f"At {target_width_cm:g} cm wide the smallest text is {min_final:.1f} pt and most text about "
            f"{median_final:.1f} pt (source {min_source:.1f} pt), below {MIN_FONT_PT:g} pt. Redraw on a "
            f"canvas about 17 cm wide with text of at least 8 pt so scaling stops eating the font; do "
            f"not rotate the page to landscape.")
    if final_height_cm > TEXT_HEIGHT_CM * MAX_HEIGHT_FRACTION:
        warnings.append(
            f"At text width it is {final_height_cm:.1f} cm tall, over {MAX_HEIGHT_FRACTION:.0%} of the text "
            f"height: the caption and surrounding text will not fit on the page. Use a smaller width or "
            f"tighten the vertical spacing in the source.")
    if width_pt / height_pt > 2.4:
        warnings.append(
            f"Aspect ratio {width_pt / height_pt:.1f}: very wide, so text becomes tiny at text width. "
            f"Fold the flow into two rows instead of rotating the page.")
    if rasters:
        warnings.append(f"The PDF holds {rasters} raster image(s) that will blur when scaled; draw the "
                        f"elements as shapes and text boxes.")

    return ImportReceipt(
        source=src.name,
        source_sha256=sha256_file(src),
        source_kind=src.suffix.lower().lstrip("."),
        page=page,
        output=out_pdf.name,
        width_cm=round(width_pt / PT_PER_CM, 2),
        height_cm=round(height_pt / PT_PER_CM, 2),
        target_width_cm=target_width_cm,
        scale=round(scale, 4),
        final_height_cm=round(final_height_cm, 2),
        min_font_pt_source=round(min_source, 2) if min_source is not None else None,
        min_font_pt_final=min_final,
        median_font_pt_final=median_final,
        font_basis=basis if sizes else "unknown",
        raster_images=rasters,
        warnings=warnings,
    )


def latex_snippet(receipt: ImportReceipt, graphics_path: str, label: str = "fig:workflow",
                  caption: str = "Overview of our work") -> str:
    """An ordinary figure on a portrait page; a tall chart gets a narrower width, never a landscape page."""
    limit = TEXT_HEIGHT_CM * MAX_HEIGHT_FRACTION
    fraction = 1.0 if receipt.final_height_cm <= limit else round(limit / receipt.final_height_cm, 2)
    width = r"\textwidth" if fraction >= 1.0 else rf"{fraction:.2f}\textwidth"
    return "\n".join([
        r"\begin{figure}[htbp]",
        r"  \centering",
        rf"  \includegraphics[width={width}]{{{graphics_path}}}",
        rf"  \caption{{{caption}}}",
        rf"  \label{{{label}}}",
        r"\end{figure}",
    ])
