"""功能: common 聚合出口。作用: 暴露跨模块共享契约。边界: 不包含业务流程编排。"""

from .config import PipelineConfig, load_config
from .errors import (
    AppError,
    InputFileError,
    FfmpegError,
    ASRModelLoadError,
    SlideDetectionError,
    PdfRenderError,
)
from .schema import PageTextMap, SlideSpan, TranscriptSegment

__all__ = [
    "PipelineConfig",
    "load_config",
    "AppError",
    "IngestError",
    "ASRError",
    "SlideDetectError",
    "RenderError",
    "TranscriptSegment",
    "SlideSpan",
    "PageTextMap",
]
