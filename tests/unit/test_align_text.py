from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.align.align_text import (
    _overlap,
    align_segments_to_slides,
    export_page_text_map_from_files,
    export_page_text_map_json,
    generate_page_text_map,
)
from src.common.schema import SlideSpan, TranscriptSegment


def test_overlap_basic() -> None:
    assert _overlap(0, 5, 3, 7) == 2


def test_align_boundary_tolerance_assigns_near_boundary_segment() -> None:
    slides = [SlideSpan(page_id=1, start_time=5.0, end_time=10.0, keyframe_path="k1.jpg")]
    seg = TranscriptSegment(start_time=4.2, end_time=4.9, text="intro")

    mapping = align_segments_to_slides(
        [seg],
        slides,
        min_overlap_sec=0.3,
        boundary_tolerance_sec=1.0,
    )

    assert mapping[1] == [seg]


def test_align_selects_page_with_max_overlap() -> None:
    slides = [
        SlideSpan(page_id=1, start_time=0.0, end_time=5.0, keyframe_path="k1.jpg"),
        SlideSpan(page_id=2, start_time=4.0, end_time=8.0, keyframe_path="k2.jpg"),
    ]
    seg = TranscriptSegment(start_time=4.2, end_time=5.8, text="bridge")

    mapping = align_segments_to_slides([seg], slides, min_overlap_sec=0.1, boundary_tolerance_sec=0.0)

    assert mapping[1] == []
    assert mapping[2] == [seg]


def test_align_does_not_duplicate_assignment_across_pages() -> None:
    slides = [
        SlideSpan(page_id=1, start_time=0.0, end_time=4.0, keyframe_path="k1.jpg"),
        SlideSpan(page_id=2, start_time=4.0, end_time=8.0, keyframe_path="k2.jpg"),
    ]
    seg = TranscriptSegment(start_time=3.5, end_time=4.5, text="edge")

    mapping = align_segments_to_slides([seg], slides, min_overlap_sec=0.1, boundary_tolerance_sec=1.0)

    assigned_count = sum(seg in page_segments for page_segments in mapping.values())
    assert assigned_count == 1


def test_align_drops_segment_below_min_overlap() -> None:
    slides = [SlideSpan(page_id=1, start_time=10.0, end_time=20.0, keyframe_path="k1.jpg")]
    seg = TranscriptSegment(start_time=9.9, end_time=10.1, text="tiny")

    mapping = align_segments_to_slides([seg], slides, min_overlap_sec=0.3, boundary_tolerance_sec=0.0)

    assert mapping[1] == []


def test_align_preserves_empty_pages_and_order() -> None:
    slides = [
        SlideSpan(page_id=3, start_time=20.0, end_time=30.0, keyframe_path="k3.jpg"),
        SlideSpan(page_id=1, start_time=0.0, end_time=10.0, keyframe_path="k1.jpg"),
        SlideSpan(page_id=2, start_time=10.0, end_time=20.0, keyframe_path="k2.jpg"),
    ]
    seg1 = TranscriptSegment(start_time=1.0, end_time=2.0, text="a")
    seg2 = TranscriptSegment(start_time=11.0, end_time=12.0, text="b")

    mapping = align_segments_to_slides([seg1, seg2], slides)

    assert list(mapping.keys()) == [1, 2, 3]
    assert mapping[1] == [seg1]
    assert mapping[2] == [seg2]
    assert mapping[3] == []


def test_align_keeps_segments_chronological_with_unsorted_input() -> None:
    slides = [SlideSpan(page_id=1, start_time=0.0, end_time=10.0, keyframe_path="k1.jpg")]
    later = TranscriptSegment(start_time=3.0, end_time=4.0, text="later")
    earlier = TranscriptSegment(start_time=1.0, end_time=2.0, text="earlier")

    mapping = align_segments_to_slides([later, earlier], slides)

    assert [seg.text for seg in mapping[1]] == ["earlier", "later"]


def test_export_page_text_map_json(tmp_path) -> None:
    seg = TranscriptSegment(start_time=0.0, end_time=1.0, text="hello")
    out_path = tmp_path / "output" / "page_text_map.json"

    export_page_text_map_json({1: [seg], 2: []}, out_path)

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload == {
        "1": [{"start_time": 0.0, "end_time": 1.0, "text": "hello"}],
        "2": [],
    }


def test_export_page_text_map_from_files(tmp_path) -> None:
    transcript_path = tmp_path / "output" / "transcript.jsonl"
    manifest_path = tmp_path / "output" / "page_manifest.json"
    output_path = tmp_path / "output" / "page_text_map.json"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    transcript_path.write_text(
        "\n".join(
            [
                json.dumps({"start_time": 0.0, "end_time": 1.0, "text": "s1"}),
                json.dumps({"start_time": 5.0, "end_time": 6.0, "text": "s2"}),
            ]
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            [
                {"page_id": 1, "start_time": 0.0, "end_time": 2.0, "keyframe_path": "k1.jpg"},
                {"page_id": 2, "start_time": 4.0, "end_time": 7.0, "keyframe_path": "k2.jpg"},
                {"page_id": 3, "start_time": 8.0, "end_time": 10.0, "keyframe_path": "k3.jpg"},
            ]
        ),
        encoding="utf-8",
    )

    export_page_text_map_from_files(transcript_path, manifest_path, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert list(payload.keys()) == ["1", "2", "3"]
    assert payload["1"][0]["text"] == "s1"
    assert payload["2"][0]["text"] == "s2"
    assert payload["3"] == []


def test_generate_page_text_map_writes_default_output_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "transcript.jsonl").write_text(
        json.dumps({"start_time": 0.0, "end_time": 1.0, "text": "hello"}),
        encoding="utf-8",
    )
    (output_dir / "page_manifest.json").write_text(
        json.dumps([{"page_id": 1, "start_time": 0.0, "end_time": 2.0, "keyframe_path": "k1.jpg"}]),
        encoding="utf-8",
    )

    generated = generate_page_text_map()
    assert generated == Path("output/page_text_map.json")
    assert generated.exists()

    payload = json.loads(generated.read_text(encoding="utf-8"))
    assert payload["1"][0]["text"] == "hello"