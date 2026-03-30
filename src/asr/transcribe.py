"""ASR transcription with faster-whisper backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.common.errors import ASRModelLoadError, ASRTranscriptionError, InputFileError
from src.common.logger import get_logger, kv
from src.common.schema import TranscriptSegment


def _normalize_segment(raw_segment: Any) -> TranscriptSegment:
    """Convert a faster-whisper segment object into TranscriptSegment."""
    segment = TranscriptSegment(
        start_time=float(raw_segment.start),
        end_time=float(raw_segment.end),
        text=str(raw_segment.text).strip(),
    )
    segment.validate()
    return segment


def _write_transcript_jsonl(segments: list[TranscriptSegment], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(
        json.dumps(
            {"start_time": seg.start_time, "end_time": seg.end_time, "text": seg.text},
            ensure_ascii=False,
        )
        for seg in segments
    )
    output_path.write_text(payload, encoding="utf-8")


def _format_srt_timestamp(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def _write_transcript_srt(segments: list[TranscriptSegment], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for index, seg in enumerate(segments, start=1):
        lines.extend(
            [
                str(index),
                f"{_format_srt_timestamp(seg.start_time)} --> {_format_srt_timestamp(seg.end_time)}",
                seg.text,
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def transcribe_audio(wav_path: str, model_name: str = "medium", device: str = "cuda") -> list[TranscriptSegment]:
    """Transcribe a WAV file and persist transcript artifacts under output/."""
    logger = get_logger("asr")
    wav = Path(wav_path)
    if not wav.exists() or not wav.is_file():
        raise InputFileError(f"Audio file not found: {wav}")

    logger.info(kv("asr.transcribe.start", wav_path=str(wav), model_name=model_name, device=device))

    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel(model_name, device=device)
    except Exception as exc:  # pragma: no cover - exercised via unit tests with monkeypatch
        logger.exception(kv("asr.model_load.failed", model_name=model_name, device=device, error=str(exc)))
        raise ASRModelLoadError(
            f"Failed to load ASR model '{model_name}' on device '{device}': {exc}"
        ) from exc

    try:
        raw_segments, info = model.transcribe(str(wav), beam_size=5)
        segments = [_normalize_segment(seg) for seg in raw_segments]
    except Exception as exc:
        logger.exception(kv("asr.transcribe.failed", wav_path=str(wav), error=str(exc)))
        raise ASRTranscriptionError(f"Failed to transcribe audio '{wav}': {exc}") from exc

    language = getattr(info, "language", None)
    logger.info(
        kv(
            "asr.transcribe.done",
            language=language if language is not None else "unknown",
            segment_count=len(segments),
        )
    )

    jsonl_path = Path("output") / "transcript.jsonl"
    _write_transcript_jsonl(segments, jsonl_path)
    logger.info(kv("asr.artifact.written", path=str(jsonl_path)))

    srt_path = Path("output") / "transcript.srt"
    _write_transcript_srt(segments, srt_path)
    logger.info(kv("asr.artifact.written", path=str(srt_path)))

    return segments


__all__ = [
    "transcribe_audio",
    "_normalize_segment",
    "_write_transcript_jsonl",
    "_format_srt_timestamp",
    "_write_transcript_srt",
]
