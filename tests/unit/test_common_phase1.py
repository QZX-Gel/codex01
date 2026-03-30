from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

import pytest

from src.common.schema import TranscriptSegment, SlideSpan
from src.common.config import load_config
from src.common.logger import get_logger
from src.common.errors import (
    AppError,
    InputFileError,
    FfmpegError,
    ASRModelLoadError,
    SlideDetectionError,
    PdfRenderError,
)


def test_transcript_segment_can_be_created() -> None:
    seg = TranscriptSegment(
        start_time=0.0,
        end_time=2.5,
        text="今天我们开始讲第一章。"
    )
    assert seg.start_time == 0.0
    assert seg.end_time == 2.5
    assert seg.text == "今天我们开始讲第一章。"


def test_slide_span_can_be_created() -> None:
    slide = SlideSpan(
        page_id=1,
        start_time=0.0,
        end_time=30.0,
        keyframe_path="output/slides/keyframe_001.jpg",
    )
    assert slide.page_id == 1
    assert slide.start_time == 0.0
    assert slide.end_time == 30.0
    assert slide.keyframe_path.endswith(".jpg")


def test_schema_objects_are_serializable() -> None:
    seg = TranscriptSegment(1.0, 2.0, "hello")
    slide = SlideSpan(2, 10.0, 20.0, "output/slides/keyframe_002.jpg")

    seg_dict = asdict(seg)
    slide_dict = asdict(slide)

    assert seg_dict["start_time"] == 1.0
    assert seg_dict["end_time"] == 2.0
    assert seg_dict["text"] == "hello"

    assert slide_dict["page_id"] == 2
    assert slide_dict["start_time"] == 10.0
    assert slide_dict["end_time"] == 20.0
    assert slide_dict["keyframe_path"].endswith(".jpg")


def test_load_default_config() -> None:
    cfg = load_config("config/default.yaml")

    # 这些字段来自架构要求的最小配置集合
    assert hasattr(cfg, "asr")
    assert hasattr(cfg, "video")
    assert hasattr(cfg, "slide")
    assert hasattr(cfg, "align")

    assert hasattr(cfg.asr, "model_name")
    assert hasattr(cfg.asr, "device")
    assert hasattr(cfg.video, "frame_fps")
    assert hasattr(cfg.slide, "ssim_threshold")
    assert hasattr(cfg.align, "min_overlap_sec")


def test_load_config_missing_file_should_raise() -> None:
    with pytest.raises(Exception):
        load_config("config/this_file_should_not_exist.yaml")


def test_logger_writes_log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    这个测试假设 get_logger(name) 会把日志写到 output/logs/run.log。
    为了不污染真实 output/，这里把 cwd 临时切到 tmp_path。
    """
    monkeypatch.chdir(tmp_path)

    logger = get_logger("phase1-test")
    logger.info("phase1 logger test message")

    log_file = tmp_path / "output" / "logs" / "run.log"
    assert log_file.exists(), "run.log 应当被创建"

    content = log_file.read_text(encoding="utf-8")
    assert "phase1 logger test message" in content


def test_input_file_error_has_code_and_message() -> None:
    err = InputFileError("input missing")
    assert isinstance(err, AppError)
    assert hasattr(err, "code")
    assert hasattr(err, "message") or str(err)
    assert err.code == "E1001"


def test_ffmpeg_error_has_code() -> None:
    err = FfmpegError("ffmpeg failed")
    assert isinstance(err, AppError)
    assert err.code == "E2001"


def test_asr_model_load_error_has_code() -> None:
    err = ASRModelLoadError("model load failed")
    assert isinstance(err, AppError)
    assert err.code == "E3001"


def test_slide_detection_error_has_code() -> None:
    err = SlideDetectionError("slide detection failed")
    assert isinstance(err, AppError)
    assert err.code == "E4001"


def test_pdf_render_error_has_code() -> None:
    err = PdfRenderError("pdf render failed")
    assert isinstance(err, AppError)
    assert err.code == "E5001"