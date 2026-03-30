"""功能: 音频抽取。作用: 通过 ffprobe/ffmpeg 生成可用于 ASR 的 wav。边界: 不负责转写。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from src.common.errors import InputFileError, FfmpegError, FfprobeError
from src.common.logger import get_logger, kv

logger = get_logger(__name__)


def validate_video_path(video_path: str) -> Path:
    """Validate video path and return normalized absolute path."""
    path = Path(video_path)
    if not path.exists():
        raise InputFileError(
            f"Input video does not exist: {video_path}. "
            "Please provide a valid local video file path."
        )
    if not path.is_file():
        raise InputFileError(
            f"Input path is not a file: {video_path}. "
            "Please provide a file path instead of a directory."
        )
    return path.resolve()


def probe_video_metadata(video_path: str) -> dict[str, Any]:
    """Probe video metadata using ffprobe JSON output."""
    validated = validate_video_path(video_path)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(validated),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        logger.error(kv("ffprobe invocation failed", video_path=str(validated), error=str(exc)))
        raise FfprobeError(
            "Failed to execute ffprobe. Ensure ffprobe is installed and available in PATH."
        ) from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        logger.error(
            kv(
                "ffprobe returned non-zero exit code",
                video_path=str(validated),
                returncode=proc.returncode,
                stderr=stderr,
            )
        )
        raise FfprobeError(
            f"ffprobe failed for input: {validated}. stderr: {stderr or '<empty>'}"
        )

    try:
        metadata = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        logger.error(kv("ffprobe output is not valid JSON", video_path=str(validated), error=str(exc)))
        raise FfprobeError(
            f"ffprobe produced invalid JSON output for input: {validated}."
        ) from exc

    return metadata


def save_video_metadata(metadata: dict[str, Any], out_json: str = "output/meta/video_info.json") -> str:
    """Persist probed video metadata to a JSON file and return output path."""
    out_path = Path(out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_path)


def extract_audio(video_path: str, out_wav: str = "output/audio.wav", sr: int = 16000) -> str:
    """Extract mono wav audio from video using ffmpeg and return output path."""
    validated = validate_video_path(video_path)
    out_path = Path(out_wav)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(kv("audio extraction start", video_path=str(validated), out_wav=str(out_path), sr=sr))

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(validated),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sr),
        "-acodec",
        "pcm_s16le",
        str(out_path),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        logger.error(kv("ffmpeg invocation failed", video_path=str(validated), error=str(exc)))
        raise FfmpegError(
            "Failed to execute ffmpeg. Ensure ffmpeg is installed and available in PATH."
        ) from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        logger.error(
            kv(
                "audio extraction failed",
                video_path=str(validated),
                out_wav=str(out_path),
                returncode=proc.returncode,
                stderr=stderr,
            )
        )
        raise FfmpegError(
            f"ffmpeg audio extraction failed for input: {validated}. stderr: {stderr or '<empty>'}"
        )

    logger.info(kv("audio extraction end", out_wav=str(out_path)))
    return str(out_path)