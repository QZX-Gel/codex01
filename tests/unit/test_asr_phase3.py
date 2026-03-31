from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from src.asr.transcribe import (
    _format_srt_timestamp,
    _normalize_segment,
    _write_transcript_jsonl,
    _write_transcript_srt,
    transcribe_audio,
)
from src.common.errors import InputFileError
from src.common.schema import TranscriptSegment


def test_transcribe_audio_missing_wav_should_raise() -> None:
    with pytest.raises(InputFileError):
        transcribe_audio("/path/does/not/exist.wav")


def test_normalize_backend_segment_to_transcript_segment() -> None:
    raw_segment = SimpleNamespace(start=1.2, end=3.4, text="  hello world  ")

    seg = _normalize_segment(raw_segment)

    assert isinstance(seg, TranscriptSegment)
    assert seg.start_time == 1.2
    assert seg.end_time == 3.4
    assert seg.text == "hello world"


def test_write_transcript_jsonl() -> None:
    out_path = Path("output/transcript.jsonl")
    if out_path.exists():
        out_path.unlink()

    segments = [
        TranscriptSegment(start_time=0.0, end_time=1.0, text="a"),
        TranscriptSegment(start_time=1.0, end_time=2.0, text="b"),
    ]

    _write_transcript_jsonl(segments, out_path)

    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    assert parsed[0] == {"start_time": 0.0, "end_time": 1.0, "text": "a"}
    assert parsed[1] == {"start_time": 1.0, "end_time": 2.0, "text": "b"}


def test_srt_formatting_and_write() -> None:
    out_path = Path("output/transcript.srt")
    if out_path.exists():
        out_path.unlink()

    assert _format_srt_timestamp(1.234) == "00:00:01,234"

    segments = [TranscriptSegment(start_time=1.234, end_time=2.5, text="line one")]
    _write_transcript_srt(segments, out_path)

    content = out_path.read_text(encoding="utf-8")
    assert "1" in content
    assert "00:00:01,234 --> 00:00:02,500" in content
    assert "line one" in content


def test_transcribe_audio_with_mocked_faster_whisper(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    wav_path = tmp_path / "audio.wav"
    wav_path.write_bytes(b"RIFF")

    fake_module = ModuleType("faster_whisper")

    class FakeModel:
        def __init__(self, model_name: str, device: str):
            assert model_name == "tiny"
            assert device == "cpu"

        def transcribe(self, input_wav: str, beam_size: int = 5):
            assert input_wav == str(wav_path)
            assert beam_size == 5
            segments = iter(
                [
                    SimpleNamespace(start=0.0, end=0.6, text=" hi "),
                    SimpleNamespace(start=0.6, end=1.2, text="there"),
                ]
            )
            info = SimpleNamespace(language="en")
            return segments, info

    fake_module.WhisperModel = FakeModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)

    monkeypatch.chdir(tmp_path)
    results = transcribe_audio(str(wav_path), model_name="tiny", device="cpu")

    assert [seg.text for seg in results] == ["hi", "there"]
    transcript_jsonl = tmp_path / "output" / "transcript.jsonl"
    assert transcript_jsonl.exists()
    assert (tmp_path / "output" / "transcript.srt").exists()

    lines = transcript_jsonl.read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in lines]
    assert parsed == [
        {"start_time": 0.0, "end_time": 0.6, "text": "hi"},
        {"start_time": 0.6, "end_time": 1.2, "text": "there"},
    ]
    assert all(item["text"] not in {"a", "b"} for item in parsed)
