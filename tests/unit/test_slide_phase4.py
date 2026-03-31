from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.common.errors import SlideDetectionError
from src.slide import detect_slides as slide_mod


def _make_dummy_frames(tmp_path: Path, count: int) -> list[str]:
    frames_dir = tmp_path / "output" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    for idx in range(1, count + 1):
        p = frames_dir / f"frame_{idx:06d}.jpg"
        p.write_bytes(f"frame-{idx}".encode("utf-8"))
        out.append(str(p))
    return out


def test_detect_slide_spans_empty_input_should_raise() -> None:
    with pytest.raises(SlideDetectionError):
        slide_mod.detect_slide_spans([], ssim_threshold=0.82)


def test_boundary_filtering_with_cooldown_and_min_duration() -> None:
    candidates = [2, 3, 4, 10, 11]
    filtered = slide_mod._filter_boundaries(  # noqa: SLF001
        candidates,
        fps=2.0,
        cooldown_sec=1.0,
        min_page_duration_sec=1.0,
    )
    assert filtered == [2, 4, 10]


def test_detect_slide_spans_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    frames = _make_dummy_frames(tmp_path, 6)

    scores = {
        (frames[0], frames[1]): 0.95,
        (frames[1], frames[2]): 0.40,
        (frames[2], frames[3]): 0.96,
        (frames[3], frames[4]): 0.30,
        (frames[4], frames[5]): 0.97,
    }

    def fake_ssim(a: str, b: str) -> float:
        return scores[(a, b)]

    monkeypatch.setattr(slide_mod, "_compute_ssim", fake_ssim)

    spans = slide_mod.detect_slide_spans(frames, ssim_threshold=0.82, persist_artifacts=False)

    assert isinstance(spans, list)
    assert len(spans) >= 2
    assert spans[0].page_id == 1
    assert all(s.end_time >= s.start_time for s in spans)


def test_detect_slide_spans_single_page_still_writes_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    frames = _make_dummy_frames(tmp_path, 3)

    def fake_detect(_frame_paths: list[str], _threshold: float) -> list[int]:
        return []

    monkeypatch.setattr(slide_mod, "_detect_candidate_boundaries", fake_detect)

    spans = slide_mod.detect_slide_spans(
        frames,
        ssim_threshold=0.82,
        output_dir=str(tmp_path / "output"),
    )

    assert len(spans) == 1
    assert spans[0].page_id == 1

    manifest = tmp_path / "output" / "page_manifest.json"
    keyframe = tmp_path / "output" / "slides" / "keyframe_001.jpg"
    assert manifest.exists()
    assert keyframe.exists()

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["page_id"] == 1
    assert payload[0]["keyframe_path"].endswith("keyframe_001.jpg")



def test_page_manifest_serialization_and_keyframes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    frames = _make_dummy_frames(tmp_path, 5)

    def fake_detect(_frame_paths: list[str], _threshold: float) -> list[int]:
        return [2]

    monkeypatch.setattr(slide_mod, "_detect_candidate_boundaries", fake_detect)

    spans = slide_mod.run_slide_detection(
        frames,
        output_dir=str(tmp_path / "output"),
        ssim_threshold=0.82,
        fps=2.0,
        cooldown_sec=0.5,
        min_page_duration_sec=0.5,
    )

    manifest = tmp_path / "output" / "page_manifest.json"
    slides_dir = tmp_path / "output" / "slides"

    assert manifest.exists()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(payload) == len(spans)
    assert payload[0]["page_id"] == 1
    assert payload[0]["keyframe_path"].endswith("keyframe_001.jpg")

    assert (slides_dir / "keyframe_001.jpg").exists()


def test_run_slide_detection_empty_input_should_raise() -> None:
    with pytest.raises(SlideDetectionError):
        slide_mod.run_slide_detection([], output_dir="output")


def test_run_slide_detection_single_page_still_writes_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    frames = _make_dummy_frames(tmp_path, 3)

    def fake_detect(_frame_paths: list[str], _threshold: float) -> list[int]:
        return []

    monkeypatch.setattr(slide_mod, "_detect_candidate_boundaries", fake_detect)

    spans = slide_mod.run_slide_detection(
        frames,
        output_dir=str(tmp_path / "output"),
        ssim_threshold=0.82,
        fps=2.0,
        cooldown_sec=0.5,
        min_page_duration_sec=0.5,
    )

    assert len(spans) == 1
    assert spans[0].page_id == 1

    manifest = tmp_path / "output" / "page_manifest.json"
    keyframe = tmp_path / "output" / "slides" / "keyframe_001.jpg"
    assert manifest.exists()
    assert keyframe.exists()

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["page_id"] == 1
    assert payload[0]["keyframe_path"].endswith("keyframe_001.jpg")
