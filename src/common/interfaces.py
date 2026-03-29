"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from typing import Protocol
from .schema import TranscriptSegment, SlideSpan


class ASREngine(Protocol):
    def transcribe(self, wav_path: str) -> list[TranscriptSegment]: ...


class SlideDetector(Protocol):
    def detect(self, frame_paths: list[str]) -> list[SlideSpan]: ...
