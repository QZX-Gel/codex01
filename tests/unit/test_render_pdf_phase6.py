from __future__ import annotations

from pathlib import Path

import pytest

from src.common.errors import PdfRenderError
from src.common.schema import SlideSpan, TranscriptSegment
from src.render.render_pdf import _assemble_page_text, _sorted_slides, render_note_pdf


# Minimal 1x1 JPEG bytes for deterministic tests
_MIN_JPEG = bytes.fromhex(
    "FFD8"
    "FFE000104A46494600010100000100010000"
    "FFC00011080001000103012200021101031101"
    "FFDA000C03010002110311003F00"
    "00"
    "FFD9"
)


def _write_jpeg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_MIN_JPEG)


def test_render_note_pdf_empty_slides_should_fail(tmp_path: Path) -> None:
    out = tmp_path / "output" / "course_note.pdf"
    with pytest.raises(PdfRenderError):
        render_note_pdf([], {}, str(out))


def test_page_text_assembly_orders_by_time() -> None:
    seg2 = TranscriptSegment(start_time=3.0, end_time=4.0, text="second")
    seg1 = TranscriptSegment(start_time=1.0, end_time=2.0, text="first")

    assembled = _assemble_page_text([seg2, seg1])
    assert assembled == "first\nsecond"


def test_render_note_pdf_creates_non_empty_file(tmp_path: Path) -> None:
    img1 = tmp_path / "output" / "slides" / "keyframe_001.jpg"
    _write_jpeg(img1)

    slides = [SlideSpan(page_id=1, start_time=0.0, end_time=5.0, keyframe_path=str(img1))]
    page_text_map = {1: [TranscriptSegment(start_time=0.0, end_time=1.0, text="hello")]}  # noqa: E501

    out = tmp_path / "output" / "course_note.pdf"
    rendered = render_note_pdf(slides, page_text_map, str(out))

    assert rendered == str(out)
    assert out.exists()
    assert out.stat().st_size > 100
    assert out.read_bytes().startswith(b"%PDF")


def test_page_order_follows_page_id_order(tmp_path: Path) -> None:
    img1 = tmp_path / "output" / "slides" / "keyframe_001.jpg"
    img2 = tmp_path / "output" / "slides" / "keyframe_002.jpg"
    _write_jpeg(img1)
    _write_jpeg(img2)

    slides = [
        SlideSpan(page_id=2, start_time=5.0, end_time=10.0, keyframe_path=str(img2)),
        SlideSpan(page_id=1, start_time=0.0, end_time=5.0, keyframe_path=str(img1)),
    ]
    assert [s.page_id for s in _sorted_slides(slides)] == [1, 2]

    out = tmp_path / "output" / "course_note.pdf"
    render_note_pdf(slides, {1: [], 2: []}, str(out))

    pdf_text = out.read_bytes().decode("latin-1", errors="ignore")
    idx1 = pdf_text.find("Page 1")
    idx2 = pdf_text.find("Page 2")

    assert idx1 != -1 and idx2 != -1
    assert idx1 < idx2
