"""功能: 视频抽帧。作用: 通过 ffmpeg 以固定 fps 导出顺序 jpg 帧。边界: 不做翻页检测。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.common.errors import InputFileError, FfmpegError
from src.common.logger import get_logger, kv
from src.ingest.extract_audio import validate_video_path

logger = get_logger(__name__)


def _collect_frame_paths(out_dir: Path) -> list[str]:
    """Collect extracted frame paths in stable sorted order."""
    return [str(p) for p in sorted(out_dir.glob("frame_*.jpg"))]


def extract_frames(video_path: str, out_dir: str = "output/frames", fps: float = 2.0) -> list[str]:
    """Extract jpg frames at requested fps and return sorted frame paths."""
    if fps <= 0:
        raise InputFileError(f"fps must be > 0, got {fps}. Please set a positive frame rate.")

    validated = validate_video_path(video_path)
    frame_dir = Path(out_dir)
    frame_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = frame_dir / "frame_%06d.jpg"

    logger.info(
        kv("frame extraction start", video_path=str(validated), out_dir=str(frame_dir), fps=fps)
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(validated),
        "-vf",
        f"fps={fps}",
        str(output_pattern),
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
                "frame extraction failed",
                video_path=str(validated),
                out_dir=str(frame_dir),
                returncode=proc.returncode,
                stderr=stderr,
            )
        )
        raise FfmpegError(
            f"ffmpeg frame extraction failed for input: {validated}. stderr: {stderr or '<empty>'}"
        )

    frame_paths = _collect_frame_paths(frame_dir)
    logger.info(kv("frame extraction end", out_dir=str(frame_dir), frame_count=len(frame_paths)))
    return frame_paths