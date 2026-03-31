"""Align transcript segments to slide spans using max-overlap single-page assignment.

Behavior:
- Each transcript segment is assigned to at most one page.
- Slide boundaries are expanded by ``boundary_tolerance_sec`` before overlap calculation.
- If multiple pages overlap, the page with the largest overlap wins.
- If the best overlap is below ``min_overlap_sec``, the segment is left unassigned.
- Output preserves all pages (including empty ones) in slide order.
"""


from __future__ import annotations
import argparse
import json
from pathlib import Path

from src.common.schema import SlideSpan, TranscriptSegment


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    """Return overlap duration of two closed-open time intervals in seconds."""
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _expanded_slide_window(slide: SlideSpan, boundary_tolerance_sec: float) -> tuple[float, float]:
    start = max(0.0, slide.start_time - boundary_tolerance_sec)
    end = slide.end_time + boundary_tolerance_sec
    return start, end


def _segment_payload(seg: TranscriptSegment) -> dict[str, float | str]:
    return {
        "start_time": seg.start_time,
        "end_time": seg.end_time,
        "text": seg.text,
    }


def align_segments_to_slides(
    segments: list[TranscriptSegment],
    slides: list[SlideSpan],
    min_overlap_sec: float = 0.3,
    boundary_tolerance_sec: float = 1.0,
) -> dict[int, list[TranscriptSegment]]:
    tolerance = max(0.0, boundary_tolerance_sec)
    ordered_slides = sorted(slides, key=lambda s: (s.start_time, s.page_id))
    ordered_segments = sorted(enumerate(segments), key=lambda item: (item[1].start_time, item[1].end_time, item[0]))
    mapping: dict[int, list[TranscriptSegment]] = {slide.page_id: [] for slide in ordered_slides}

    for _, seg in ordered_segments:
        best_page_id: int | None = None
        best_overlap = 0.0

        for slide in ordered_slides:
            win_start, win_end = _expanded_slide_window(slide, boundary_tolerance_sec)
            overlap = _overlap(seg.start_time, seg.end_time, win_start, win_end)
            if overlap > best_overlap:
                best_overlap = overlap
                best_page_id = slide.page_id

        if best_page_id is not None and best_overlap >= min_overlap_sec:
            mapping[best_page_id].append(seg)

    return mapping


def export_page_text_map_json(
    page_text_map: dict[int, list[TranscriptSegment]],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {str(page_id): [_segment_payload(seg) for seg in segments] for page_id, segments in page_text_map.items()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_page_text_map_from_files(
    transcript_jsonl_path: str | Path,
    page_manifest_path: str | Path,
    output_path: str | Path,
    min_overlap_sec: float = 0.3,
    boundary_tolerance_sec: float = 1.0,
) -> Path:
    transcript_path = Path(transcript_jsonl_path)
    manifest_path = Path(page_manifest_path)

    segments = [TranscriptSegment(**json.loads(line)) for line in transcript_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    slides = [SlideSpan(**item) for item in json.loads(manifest_path.read_text(encoding="utf-8"))]

    page_text_map = align_segments_to_slides(
        segments,
        slides,
        min_overlap_sec=min_overlap_sec,
        boundary_tolerance_sec=boundary_tolerance_sec,
    )
    return export_page_text_map_json(page_text_map, output_path)


def generate_page_text_map(
    output_dir: str | Path = "output",
    min_overlap_sec: float = 0.3,
    boundary_tolerance_sec: float = 1.0,
) -> Path:
    output_path = Path(output_dir)
    return export_page_text_map_from_files(
        transcript_jsonl_path=output_path / "transcript.jsonl",
        page_manifest_path=output_path / "page_manifest.json",
        output_path=output_path / "page_text_map.json",
        min_overlap_sec=min_overlap_sec,
        boundary_tolerance_sec=boundary_tolerance_sec,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Align transcript segments to slide spans and export page_text_map.json")
    parser.add_argument("--output-dir", default="output", help="Directory containing transcript.jsonl and page_manifest.json")
    parser.add_argument("--min-overlap-sec", type=float, default=0.3)
    parser.add_argument("--boundary-tolerance-sec", type=float, default=1.0)
    args = parser.parse_args()

    generate_page_text_map(
        output_dir=args.output_dir,
        min_overlap_sec=args.min_overlap_sec,
        boundary_tolerance_sec=args.boundary_tolerance_sec,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())