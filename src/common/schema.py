"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""


from __future__ import annotations
from dataclasses import asdict, dataclass, field



"""功能: 定义 pipeline 的公共数据 Schema。作用: 统一模块输入输出契约。边界: 不包含模型推理实现。"""




@dataclass(frozen=True)
class TranscriptSegment:
    """ASR 段级结果。

    约束:
    - start_time/end_time 以秒为单位。
    - 要求 end_time >= start_time。
    - text 为该时间段内的可读文本（允许为空字符串，但建议上游过滤）。
    """

    start_time: float
    end_time: float
    text: str
    speaker: str | None = None
    confidence: float | None = None

    def validate(self) -> None:
        if self.start_time < 0:
            raise ValueError("TranscriptSegment.start_time must be >= 0")
        if self.end_time < self.start_time:
            raise ValueError("TranscriptSegment.end_time must be >= start_time")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError("TranscriptSegment.confidence must be in [0, 1]")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SlideSpan:
    """PPT 页面时间区间。

    约束:
    - page_id 从 1 开始递增（由检测模块保证）。
    - start_time/end_time 以秒为单位，且 end_time >= start_time。
    - keyframe_path 指向该页代表帧路径（可为相对路径）。
    """

    page_id: int
    start_time: float
    end_time: float
    keyframe_path: str
    ocr_text: str | None = None
    score: float | None = None

    def validate(self) -> None:
        if self.page_id <= 0:
            raise ValueError("SlideSpan.page_id must be > 0")
        if self.start_time < 0:
            raise ValueError("SlideSpan.start_time must be >= 0")
        if self.end_time < self.start_time:
            raise ValueError("SlideSpan.end_time must be >= start_time")
        if self.score is not None and not (0.0 <= self.score <= 1.0):
            raise ValueError("SlideSpan.score must be in [0, 1]")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PageTextMap:
    """页面到文本段的映射结果。"""

    page_id: int
    segments: list[TranscriptSegment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "page_id": self.page_id,
            "segments": [seg.to_dict() for seg in self.segments],
        }