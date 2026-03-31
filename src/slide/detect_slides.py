"""Basic slide detection based on adjacent-frame SSIM."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
import shutil

from src.common.errors import SlideDetectionError
from src.common.logger import get_logger, kv
from src.common.schema import SlideSpan


def _extract_frame_index(frame_path: str) -> int:
    """Extract numeric frame index from filename for deterministic ordering."""
    stem = Path(frame_path).stem
    matches = re.findall(r"(\d+)", stem)
    if not matches:
        return -1
    return int(matches[-1])


def _frame_time_sec(frame_index: int, fps: float) -> float:
    if fps <= 0:
        raise SlideDetectionError("video.frame_fps must be > 0")
    return frame_index / fps


def _compute_ssim(frame_a: str, frame_b: str) -> float:
    """Compute SSIM between two images using scikit-image when available."""
    try:
        import numpy as np
        from skimage import io
        from skimage.color import rgb2gray
        from skimage.metrics import structural_similarity
    except Exception as exc:  # pragma: no cover - dependency gate
        raise SlideDetectionError(
            "SSIM dependencies are missing. Install scikit-image and numpy."
        ) from exc

    try:
        img_a = io.imread(frame_a)
        img_b = io.imread(frame_b)
    except Exception as exc:
        raise SlideDetectionError(f"Failed to read image file: {exc}") from exc

    if img_a.ndim == 3:
        img_a = rgb2gray(img_a)
    if img_b.ndim == 3:
        img_b = rgb2gray(img_b)

    if img_a.shape != img_b.shape:
        h = min(img_a.shape[0], img_b.shape[0])
        w = min(img_a.shape[1], img_b.shape[1])
        img_a = img_a[:h, :w]
        img_b = img_b[:h, :w]

    return float(structural_similarity(np.asarray(img_a), np.asarray(img_b), data_range=1.0))


def _detect_candidate_boundaries(frame_paths: list[str], ssim_threshold: float) -> list[int]:
    """Return frame indexes that should start a new page."""
    candidates: list[int] = []
    for idx in range(1, len(frame_paths)):
        score = _compute_ssim(frame_paths[idx - 1], frame_paths[idx])
        if score < ssim_threshold:
            candidates.append(idx)
    return candidates


def _filter_boundaries(
    candidates: list[int],
    *,
    fps: float,
    cooldown_sec: float,
    min_page_duration_sec: float,
) -> list[int]:
    """Filter near-duplicate boundary candidates by cooldown and min duration."""
    if not candidates:
        return []

    min_gap_frames = int(max(cooldown_sec, min_page_duration_sec) * fps)
    filtered: list[int] = []
    for candidate in sorted(candidates):
        if not filtered:
            filtered.append(candidate)
            continue
        if candidate - filtered[-1] >= min_gap_frames:
            filtered.append(candidate)
    return filtered


def _build_slide_spans(
    frame_paths: list[str],
    boundary_starts: list[int],
    *,
    fps: float,
) -> list[SlideSpan]:
    """Construct ordered SlideSpan objects from boundary starts."""
    page_starts = [0, *boundary_starts]
    page_ends = [*boundary_starts, len(frame_paths)]

    spans: list[SlideSpan] = []
    for page_no, (start_idx, end_idx) in enumerate(zip(page_starts, page_ends), start=1):
        if end_idx <= start_idx:
            continue
        start_time = _frame_time_sec(start_idx, fps)
        end_time = _frame_time_sec(end_idx, fps)
        spans.append(
            SlideSpan(
                page_id=page_no,
                start_time=start_time,
                end_time=end_time,
                keyframe_path="",
            )
        )
    return spans


def _persist_slide_artifacts(
    ordered: list[str],
    spans: list[SlideSpan],
    *,
    fps: float,
    output_dir: str,
    logger,
) -> list[SlideSpan]:
    output_root = Path(output_dir)
    slides_dir = output_root / "slides"
    manifest_path = output_root / "page_manifest.json"

    spans_with_keyframes = _write_keyframes(ordered, spans, slides_dir, fps=fps)
    written_manifest = _write_manifest(spans_with_keyframes, manifest_path)

    logger.info(kv("slide.detect.output", manifest_output_path=written_manifest, keyframe_output_dir=str(slides_dir), keyframe_count=len(spans_with_keyframes)))
    return spans_with_keyframes


def detect_slide_spans(
    frame_paths: list[str],
    ssim_threshold: float = 0.82,
    *,
    output_dir: str = "output",
    persist_artifacts: bool = True,
) -> list[SlideSpan]:
    """Detect slide spans from ordered frame paths and persist M3 artifacts by default."""
    from src.common.config import load_config

    logger = get_logger("slide_detector")

    if not frame_paths:
        raise SlideDetectionError("Empty frame list: no frames found for slide detection.")

    ordered = sorted(frame_paths, key=lambda p: (_extract_frame_index(p), Path(p).name))
    for frame in ordered:
        if not Path(frame).exists():
            raise SlideDetectionError(f"Unreadable image file: {frame}")

    cfg = load_config(None)
    fps = float(cfg.video.frame_fps)
    cooldown_sec = float(getattr(cfg.slide, "cooldown_sec", 1.0))
    min_page_duration_sec = float(getattr(cfg.slide, "min_page_duration_sec", 1.0))

    logger.info(kv("slide.detect.start", frame_count=len(ordered), ssim_threshold=ssim_threshold))
    candidates = _detect_candidate_boundaries(ordered, ssim_threshold)
    logger.info(
        kv(
            "slide.detect.candidates",
            candidate_boundary_count=len(candidates),
            candidates=candidates,
            note="no boundaries detected" if not candidates else "",
        )
    )

    filtered = _filter_boundaries(
        candidates,
        fps=fps,
        cooldown_sec=cooldown_sec,
        min_page_duration_sec=min_page_duration_sec,
    )
    logger.info(kv("slide.detect.filtered", filtered_boundary_count=len(filtered), filtered=filtered))
    spans = _build_slide_spans(ordered, filtered, fps=fps)

    if not persist_artifacts:
        logger.info(kv("slide.detect.done", page_count=len(spans), keyframe_count=0, artifacts_written=False))
        return spans

    spans_with_keyframes = _persist_slide_artifacts(ordered, spans, fps=fps, output_dir=output_dir, logger=logger)
    logger.info(kv("slide.detect.done", page_count=len(spans_with_keyframes), keyframe_count=len(spans_with_keyframes), artifacts_written=True))
    return spans_with_keyframes


def _write_keyframes(
    frame_paths: list[str],
    spans: list[SlideSpan],
    slides_dir: Path,
    *,
    fps: float,
) -> list[SlideSpan]:
    slides_dir.mkdir(parents=True, exist_ok=True)

    new_spans: list[SlideSpan] = []
    for span in spans:
        frame_idx = int(round(span.start_time * fps))
        frame_idx = min(max(frame_idx, 0), len(frame_paths) - 1)

        src = Path(frame_paths[frame_idx])
        dst = slides_dir / f"keyframe_{span.page_id:03d}.jpg"
        try:
            shutil.copy2(src, dst)
        except Exception as exc:
            raise SlideDetectionError(f"Failed to write/copy keyframe: {src} -> {dst}") from exc

        new_spans.append(
            SlideSpan(
                page_id=span.page_id,
                start_time=span.start_time,
                end_time=span.end_time,
                keyframe_path=str(dst).replace("\\\\", "/"),
            )
        )
    return new_spans


def _write_manifest(spans: list[SlideSpan], manifest_path: Path) -> str:
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(span) for span in spans]
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        raise SlideDetectionError(f"Failed to write page manifest: {manifest_path}") from exc
    return str(manifest_path)


def run_slide_detection(
    frame_paths: list[str],
    *,
    output_dir: str = "output",
    ssim_threshold: float = 0.82,
    fps: float = 4.0,
    cooldown_sec: float = 1.0,
    min_page_duration_sec: float = 1.0,
) -> list[SlideSpan]:
    """Run slide detection and persist keyframes + manifest for M3 outputs."""
    logger = get_logger("slide_detector")

    if not frame_paths:
        raise SlideDetectionError("Empty frame list: no frames found for slide detection.")

    ordered = sorted(frame_paths, key=lambda p: (_extract_frame_index(p), Path(p).name))
    for frame in ordered:
        if not Path(frame).exists():
            raise SlideDetectionError(f"Unreadable image file: {frame}")

    logger.info(kv("slide.detect.start", frame_count=len(ordered), ssim_threshold=ssim_threshold))

    candidates = _detect_candidate_boundaries(ordered, ssim_threshold)
    logger.info(
        kv(
            "slide.detect.candidates",
            candidate_boundary_count=len(candidates),
            candidates=candidates,
            note="no boundaries detected" if not candidates else "",
        )
    )

    filtered = _filter_boundaries(
        candidates,
        fps=fps,
        cooldown_sec=cooldown_sec,
        min_page_duration_sec=min_page_duration_sec,
    )
    logger.info(kv("slide.detect.filtered", filtered_boundary_count=len(filtered), filtered=filtered))
    spans = _build_slide_spans(ordered, filtered, fps=fps)

    spans_with_keyframes = _persist_slide_artifacts(ordered, spans, fps=fps, output_dir=output_dir, logger=logger)
    logger.info(kv("slide.detect.done", page_count=len(spans_with_keyframes), keyframe_count=len(spans_with_keyframes), artifacts_written=True))