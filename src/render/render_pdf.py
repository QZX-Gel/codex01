"""PDF 渲染：将关键帧与对齐文本导出为课程讲义 PDF。"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.common.errors import PdfRenderError
from src.common.logger import get_logger, kv
from src.common.schema import SlideSpan, TranscriptSegment


logger = get_logger(__name__)


_A4_WIDTH = 595.0
_A4_HEIGHT = 842.0
_MARGIN = 36.0
_GAP = 18.0


@dataclass(frozen=True)
class _PageLayout:
    img_x: float
    img_y: float
    img_w: float
    img_h: float
    text_x: float
    text_y_top: float
    text_w: float


def _sorted_slides(slides: list[SlideSpan]) -> list[SlideSpan]:
    return sorted(slides, key=lambda s: (s.page_id, s.start_time, s.end_time))


def _assemble_page_text(segments: list[TranscriptSegment]) -> str:
    if not segments:
        return ""
    ordered = sorted(segments, key=lambda s: (s.start_time, s.end_time))
    chunks = [seg.text.strip() for seg in ordered if seg.text and seg.text.strip()]
    return "\n".join(chunks)


def _read_jpeg_size(jpeg_path: Path) -> tuple[int, int]:
    data = jpeg_path.read_bytes()
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise PdfRenderError(f"invalid JPEG file: {jpeg_path}")

    idx = 2
    while idx + 1 < len(data):
        if data[idx] != 0xFF:
            idx += 1
            continue

        marker = data[idx + 1]
        idx += 2

        # standalone markers
        if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
            continue

        if idx + 2 > len(data):
            break
        seg_len = int.from_bytes(data[idx : idx + 2], "big")
        if seg_len < 2 or idx + seg_len > len(data):
            break

        # SOF0/SOF2 include dimensions
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if seg_len < 7:
                break
            height = int.from_bytes(data[idx + 3 : idx + 5], "big")
            width = int.from_bytes(data[idx + 5 : idx + 7], "big")
            if width <= 0 or height <= 0:
                break
            return width, height

        idx += seg_len

    raise PdfRenderError(f"failed to parse JPEG size: {jpeg_path}")


def _compute_layout(img_w: int, img_h: int) -> _PageLayout:
    content_w = _A4_WIDTH - 2 * _MARGIN
    content_h = _A4_HEIGHT - 2 * _MARGIN

    left_w = content_w * 0.56
    right_w = content_w - left_w - _GAP

    scale = min(left_w / img_w, content_h / img_h)
    draw_w = img_w * scale
    draw_h = img_h * scale

    img_x = _MARGIN
    img_y = _A4_HEIGHT - _MARGIN - draw_h

    text_x = _MARGIN + left_w + _GAP
    text_y_top = _A4_HEIGHT - _MARGIN - 18.0

    return _PageLayout(
        img_x=img_x,
        img_y=img_y,
        img_w=draw_w,
        img_h=draw_h,
        text_x=text_x,
        text_y_top=text_y_top,
        text_w=right_w,
    )


def _pdf_escape_text(text: str) -> str:
    # 最小实现：内置 Helvetica 对中文支持有限。
    # 如环境安装了 reportlab，可在后续阶段替换为 CJK 字体渲染。
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return "".join(ch if ord(ch) < 256 else "?" for ch in safe)


def _wrap_text(text: str, width: float, font_size: float = 10.0) -> list[str]:
    if not text:
        return []

    # Helvetica 近似宽度估算：0.52 * font_size * char_count
    max_chars = max(10, int(width / (font_size * 0.52)))
    out: list[str] = []
    for para in text.splitlines() or [""]:
        p = para.strip()
        if not p:
            out.append("")
            continue
        while len(p) > max_chars:
            out.append(p[:max_chars])
            p = p[max_chars:]
        out.append(p)
    return out


def _build_pdf_bytes(pages: Iterable[tuple[SlideSpan, str]]) -> bytes:
    objects: list[bytes] = []

    def add_obj(payload: str | bytes) -> int:
        if isinstance(payload, str):
            payload = payload.encode("latin-1", errors="ignore")
        objects.append(payload)
        return len(objects)

    font_obj = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_objs: list[int] = []

    for slide, page_text in pages:
        img_path = Path(slide.keyframe_path)
        image_raw = img_path.read_bytes()
        img_w, img_h = _read_jpeg_size(img_path)
        layout = _compute_layout(img_w, img_h)

        image_obj = add_obj(
            (
                f"<< /Type /XObject /Subtype /Image /Width {img_w} /Height {img_h} "
                "/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                f"/Length {len(image_raw)} >>\nstream\n"
            ).encode("latin-1")
            + image_raw
            + b"\nendstream"
        )

        lines = [f"Page {slide.page_id}"]
        lines.extend(_wrap_text(page_text, width=layout.text_w))

        text_cmd = [
            "BT",
            f"/F1 10 Tf",
            "12 TL",
            f"1 0 0 1 {layout.text_x:.2f} {layout.text_y_top:.2f} Tm",
        ]
        for line in lines:
            text_cmd.append(f"({_pdf_escape_text(line)}) Tj")
            text_cmd.append("T*")
        text_cmd.append("ET")

        stream = "\n".join(
            [
                "q",
                f"{layout.img_w:.2f} 0 0 {layout.img_h:.2f} {layout.img_x:.2f} {layout.img_y:.2f} cm",
                "/Im0 Do",
                "Q",
                *text_cmd,
            ]
        )

        content_bytes = stream.encode("latin-1", errors="ignore")
        content_obj = add_obj(
            f"<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1")
            + content_bytes
            + b"\nendstream"
        )

        page_obj = add_obj(
            (
                "<< /Type /Page /Parent PAGES_OBJ 0 R "
                f"/MediaBox [0 0 {_A4_WIDTH:.0f} {_A4_HEIGHT:.0f}] "
                f"/Resources << /Font << /F1 {font_obj} 0 R >> /XObject << /Im0 {image_obj} 0 R >> >> "
                f"/Contents {content_obj} 0 R >>"
            )
        )
        page_objs.append(page_obj)

    kids = " ".join(f"{pid} 0 R" for pid in page_objs)
    pages_obj = add_obj(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_objs)} >>")

    # patch Parent reference
    for idx in page_objs:
        objects[idx - 1] = objects[idx - 1].replace(b"PAGES_OBJ", str(pages_obj).encode("ascii"))

    catalog_obj = add_obj(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, payload in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("ascii"))
        out.extend(payload)
        out.extend(b"\nendobj\n")

    xref_start = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    out.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    return bytes(out)


def render_note_pdf(
    slides: list[SlideSpan],
    page_text_map: dict[int, list[TranscriptSegment]],
    out_pdf: str,
) -> str:
    """Render a minimal, real course note PDF and return output path."""
    if not slides:
        raise PdfRenderError("slides is empty, cannot render PDF")

    ordered_slides = _sorted_slides(slides)
    out = Path(out_pdf)

    logger.info(kv("pdf render start", output=str(out), slide_count=len(ordered_slides)))

    for slide in ordered_slides:
        p = Path(slide.keyframe_path)
        if not p.exists():
            logger.warning(kv("missing keyframe", page_id=slide.page_id, path=str(p)))
            raise PdfRenderError(f"missing keyframe image: {p}")

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.exception(kv("failed creating output directory", output=str(out.parent)))
        raise PdfRenderError(f"cannot create output directory: {out.parent}") from exc

    page_payload: list[tuple[SlideSpan, str]] = []
    for slide in ordered_slides:
        page_segments = page_text_map.get(slide.page_id, [])
        text = _assemble_page_text(page_segments)
        page_payload.append((slide, text))

    logger.info(kv("pdf render page count", pages=len(page_payload)))

    try:
        pdf_bytes = _build_pdf_bytes(page_payload)
        out.write_bytes(pdf_bytes)
    except OSError as exc:
        logger.exception(kv("failed writing pdf", output=str(out)))
        raise PdfRenderError(f"cannot write PDF output: {out}") from exc
    except Exception as exc:  # pragma: no cover - backend failure guard
        logger.exception(kv("pdf backend failure", output=str(out)))
        raise PdfRenderError(f"PDF backend failure: {exc}") from exc

    logger.info(kv("pdf render done", output=str(out)))
    return str(out)


def _load_slides(manifest_path: Path) -> list[SlideSpan]:
    if not manifest_path.exists():
        raise PdfRenderError(f"missing page manifest: {manifest_path}")

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PdfRenderError(f"invalid page manifest json: {manifest_path}") from exc

    if not isinstance(raw, list) or not raw:
        raise PdfRenderError("page manifest must be a non-empty list")

    slides: list[SlideSpan] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise PdfRenderError(f"page manifest item {idx} must be an object")
        try:
            slides.append(SlideSpan(**item))
        except Exception as exc:
            raise PdfRenderError(f"invalid page manifest item {idx}") from exc
    return slides


def _load_page_text_map(page_text_map_path: Path) -> dict[int, list[TranscriptSegment]]:
    if not page_text_map_path.exists():
        raise PdfRenderError(f"missing page_text_map: {page_text_map_path}")

    try:
        raw = json.loads(page_text_map_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PdfRenderError(f"invalid page_text_map json: {page_text_map_path}") from exc

    if not isinstance(raw, dict):
        raise PdfRenderError("page_text_map must be a JSON object")

    page_text_map: dict[int, list[TranscriptSegment]] = {}
    for page_id_raw, segments_raw in raw.items():
        try:
            page_id = int(page_id_raw)
        except Exception as exc:
            raise PdfRenderError(f"invalid page id in page_text_map: {page_id_raw}") from exc

        if not isinstance(segments_raw, list):
            raise PdfRenderError(f"page_text_map[{page_id_raw}] must be a list")

        segments: list[TranscriptSegment] = []
        for idx, seg_raw in enumerate(segments_raw):
            if not isinstance(seg_raw, dict):
                raise PdfRenderError(f"page_text_map[{page_id_raw}][{idx}] must be an object")
            try:
                segments.append(TranscriptSegment(**seg_raw))
            except Exception as exc:
                raise PdfRenderError(f"invalid segment at page_text_map[{page_id_raw}][{idx}]") from exc
        page_text_map[page_id] = segments
    return page_text_map


def build_course_note(output_dir: str = "output") -> str:
    out_dir = Path(output_dir)
    slides = _load_slides(out_dir / "page_manifest.json")
    page_text_map = _load_page_text_map(out_dir / "page_text_map.json")
    return render_note_pdf(slides, page_text_map, str(out_dir / "course_note.pdf"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Render course note PDF from output artifacts")
    parser.add_argument("--output-dir", default="output", help="Directory containing page_manifest.json and page_text_map.json")
    args = parser.parse_args()
    build_course_note(output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
