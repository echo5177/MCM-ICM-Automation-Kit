from __future__ import annotations

import csv
from pathlib import Path
import shutil
import zipfile

import pytest

from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.diagram_checker import run_diagram_checks
from mcm_workflow_kit.diagram_quality_checker import run_diagram_quality_checks
from mcm_workflow_kit.flowchart_import import (
    ImportReceipt,
    import_flowchart,
    latex_snippet,
    pptx_font_sizes,
    receipt_path_for,
    sha256_file,
)


needs_poppler = pytest.mark.skipif(shutil.which("pdftocairo") is None, reason="needs pdftocairo")


def _pdf_with_box(path: Path, box=(0.3, 0.3, 0.4, 0.4), fontsize: int = 20) -> None:
    """One 13.33 x 7.5 in page (a PowerPoint 16:9 slide) with a labelled box in it."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(13.33, 7.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.add_patch(plt.Rectangle(box[:2], box[2], box[3], fill=False, linewidth=2))
    ax.text(box[0] + box[2] / 2, box[1] + box[3] / 2, "model", ha="center", va="center", fontsize=fontsize)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.savefig(path, metadata={"Author": "someone", "Title": "draft"})
    plt.close(fig)


@needs_poppler
def test_import_crops_and_clears_properties(tmp_path: Path) -> None:
    from pypdf import PdfReader

    src = tmp_path / "flow.pdf"
    _pdf_with_box(src)
    out = tmp_path / "figures" / "workflow.pdf"
    receipt = import_flowchart(src, out)
    assert 13.0 < receipt.width_cm < 15.0          # 40% of a 33.9 cm slide plus a margin
    meta = PdfReader(str(out)).metadata or {}
    assert not meta.get("/Author") and not meta.get("/Title")
    assert receipt.source_sha256 == sha256_file(src) and receipt.raster_images == 0


@needs_poppler
def test_small_text_after_scaling_is_flagged(tmp_path: Path) -> None:
    src = tmp_path / "flow.pdf"
    _pdf_with_box(src, box=(0.02, 0.3, 0.96, 0.4))
    receipt = import_flowchart(src, tmp_path / "workflow.pdf", target_width_cm=6.0)
    assert receipt.min_font_pt_final is not None and receipt.min_font_pt_final < 7
    assert any("below 7 pt" in w for w in receipt.warnings)


def test_pptx_font_sizes_apply_the_shrink_scale(tmp_path: Path) -> None:
    a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    p = "http://schemas.openxmlformats.org/presentationml/2006/main"
    r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    slide = (
        f'<p:sld xmlns:a="{a}" xmlns:p="{p}"><p:cSld><p:spTree>'
        f'<p:sp><p:txBody><a:bodyPr><a:normAutofit fontScale="50000"/></a:bodyPr>'
        f'<a:p><a:r><a:rPr sz="1600"/><a:t>Model</a:t></a:r></a:p></p:txBody></p:sp>'
        f'<p:sp><p:txBody><a:bodyPr/><a:p><a:r><a:rPr sz="1200"/><a:t>Data</a:t></a:r></a:p></p:txBody></p:sp>'
        f'<p:sp><p:txBody><a:bodyPr/><a:p><a:r><a:rPr sz="4000"/><a:t> </a:t></a:r></a:p></p:txBody></p:sp>'
        f'</p:spTree></p:cSld></p:sld>'
    )
    pptx = tmp_path / "flow.pptx"
    with zipfile.ZipFile(pptx, "w") as zf:
        zf.writestr("ppt/presentation.xml",
                    f'<p:presentation xmlns:p="{p}" xmlns:r="{r}"><p:sldIdLst>'
                    f'<p:sldId id="256" r:id="rId2"/></p:sldIdLst></p:presentation>')
        zf.writestr("ppt/_rels/presentation.xml.rels",
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId2" Target="slides/slide7.xml"/></Relationships>')
        zf.writestr("ppt/slides/slide7.xml", slide)
    assert sorted(pptx_font_sizes(pptx, 1)) == [8.0, 12.0]


def _receipt(**overrides) -> ImportReceipt:
    base = dict(source="flow.pptx", source_sha256="x", source_kind="pptx", page=1, output="workflow.pdf",
                width_cm=33.7, height_cm=17.7, target_width_cm=17.1, scale=0.51, final_height_cm=9.0,
                min_font_pt_source=6.1, min_font_pt_final=3.1, median_font_pt_final=4.0,
                font_basis="pptx", raster_images=0, warnings=[])
    base.update(overrides)
    return ImportReceipt(**base)


def test_snippet_is_a_portrait_figure_and_narrows_tall_charts() -> None:
    wide = latex_snippet(_receipt(), "workflow.pdf")
    assert r"\includegraphics[width=\textwidth]{workflow.pdf}" in wide
    assert "landscape" not in wide and r"\caption{Overview of our work}" in wide
    assert r"width=0.85\textwidth" in latex_snippet(_receipt(final_height_cm=23.0), "workflow.pdf")


def _user_project(tmp_path: Path, receipt: ImportReceipt | None) -> WorkflowConfig:
    (tmp_path / "flow.pptx").write_bytes(b"pptx v1")
    concept = tmp_path / "figures" / "concept"
    concept.mkdir(parents=True)
    (concept / "workflow.pdf").write_bytes(b"%PDF")
    (tmp_path / "reports").mkdir()
    with (tmp_path / "reports" / "figure_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["figure_id", "path", "source_script"])
        writer.writerow(["fig:workflow", "figures/concept/workflow.pdf", "flow.pptx"])
    if receipt is not None:
        receipt.source_sha256 = sha256_file(tmp_path / "flow.pptx")
        receipt.write(receipt_path_for(concept / "workflow.pdf"))
    return WorkflowConfig.from_mapping({"diagram_sources": [{
        "figure_id": "fig:workflow", "origin": "user", "source": "flow.pptx",
        "pdf": "figures/concept/workflow.pdf"}]})


def test_user_diagram_with_fresh_receipt_passes(tmp_path: Path) -> None:
    config = _user_project(tmp_path, _receipt(warnings=[]))
    assert run_diagram_checks(tmp_path, config).status == "pass"
    assert run_diagram_quality_checks(tmp_path, config).status == "pass"


def test_user_diagram_changed_after_import_fails(tmp_path: Path) -> None:
    config = _user_project(tmp_path, _receipt())
    (tmp_path / "flow.pptx").write_bytes(b"pptx v2")
    result = run_diagram_checks(tmp_path, config)
    assert result.status == "fail"
    assert "changed after it was imported" in " ".join(m.message for m in result.messages)


def test_user_diagram_without_receipt_warns(tmp_path: Path) -> None:
    result = run_diagram_checks(tmp_path, _user_project(tmp_path, None))
    assert result.status == "warn"


def test_receipt_warnings_surface_in_the_quality_report(tmp_path: Path) -> None:
    config = _user_project(tmp_path, _receipt(warnings=["At 17.1 cm wide the smallest text is 3.1 pt"]))
    result = run_diagram_quality_checks(tmp_path, config)
    assert result.status == "warn" and "3.1 pt" in result.messages[0].message


def test_powerpoint_export_retries_once_after_a_timeout(monkeypatch) -> None:
    # 2026-09-28: the first run of the day timed out with PowerPoint never starting; the
    # rerun exported in about 15 s.
    from mcm_workflow_kit import flowchart_import as module

    calls: list[int] = []

    def flaky(_src, _out, _timeout):
        calls.append(1)
        if len(calls) == 1:
            raise module._ExportTimeout()

    monkeypatch.setattr(module, "_export_with_powerpoint_once", flaky)
    module.export_with_powerpoint(Path("a.pptx"), Path("b.pdf"))
    assert len(calls) == 2

    def always(_src, _out, _timeout):
        raise module._ExportTimeout()

    monkeypatch.setattr(module, "_export_with_powerpoint_once", always)
    with pytest.raises(module.FlowchartImportError, match="2 tries"):
        module.export_with_powerpoint(Path("a.pptx"), Path("b.pdf"))
