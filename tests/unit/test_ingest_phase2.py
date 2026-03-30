from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.common.errors import InputFileError
from src.ingest import extract_audio as audio_mod
from src.ingest import extract_frames as frame_mod


def test_validate_video_path_missing_should_raise() -> None:
    with pytest.raises(InputFileError):
        audio_mod.validate_video_path("this/file/does/not/exist.mp4")


def test_probe_video_metadata_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"not-a-real-video-but-path-exists")

    fake_payload = {"format": {"filename": str(video), "duration": "12.34"}, "streams": []}

    class DummyProc:
        returncode = 0
        stdout = json.dumps(fake_payload)
        stderr = ""

    def fake_run(cmd, capture_output, text, check):  # noqa: ANN001
        assert cmd[0] == "ffprobe"
        return DummyProc()

    monkeypatch.setattr(audio_mod.subprocess, "run", fake_run)

    metadata = audio_mod.probe_video_metadata(str(video))
    assert metadata["format"]["duration"] == "12.34"

    out_json = tmp_path / "output" / "meta" / "video_info.json"
    saved = audio_mod.save_video_metadata(metadata, str(out_json))
    assert Path(saved).exists()
    reloaded = json.loads(Path(saved).read_text(encoding="utf-8"))
    assert reloaded["format"]["filename"] == str(video)


def test_extract_frames_collects_sorted_frame_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"dummy")
    out_dir = tmp_path / "output" / "frames"

    class DummyProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, capture_output, text, check):  # noqa: ANN001
        assert cmd[0] == "ffmpeg"
        pattern = Path(cmd[-1])
        pattern.parent.mkdir(parents=True, exist_ok=True)
        # create out-of-order names to verify sorting behavior
        (pattern.parent / "frame_000003.jpg").write_bytes(b"3")
        (pattern.parent / "frame_000001.jpg").write_bytes(b"1")
        (pattern.parent / "frame_000002.jpg").write_bytes(b"2")
        return DummyProc()

    monkeypatch.setattr(frame_mod.subprocess, "run", fake_run)

    frames = frame_mod.extract_frames(str(video), str(out_dir), fps=2.0)
    assert len(frames) == 3
    assert frames == [
        str(out_dir / "frame_000001.jpg"),
        str(out_dir / "frame_000002.jpg"),
        str(out_dir / "frame_000003.jpg"),
    ]
