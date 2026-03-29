"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    start_time: float
    end_time: float
    text: str


@dataclass
class SlideSpan:
    page_id: int
    start_time: float
    end_time: float
    keyframe_path: str
