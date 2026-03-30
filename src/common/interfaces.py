"""功能: 定义模块级协议接口。作用: 用 Protocol 约束可替换实现。边界: 不包含具体算法逻辑。"""

from typing import Protocol
from .schema import TranscriptSegment, SlideSpan


class ASREngine(Protocol):
    """音频转写引擎协议。"""

    def transcribe(self, wav_path: str) -> list[TranscriptSegment]: ...


class SlideDetector(Protocol):
    """翻页检测器协议。"""

    def detect(self, frame_paths: list[str]) -> list[SlideSpan]: ...


class IngestEngine(Protocol):
    """输入预处理协议。"""

    def extract_audio(self, video_path: str, out_wav: str, sr: int = 16000) -> str: ...
    def extract_frames(self, video_path: str, out_dir: str, fps: float) -> list[str]: ...


class Aligner(Protocol):
    """页文对齐协议。"""

    def align(
        self,
        segments: list[TranscriptSegment],
        slides: list[SlideSpan],
        min_overlap_sec: float = 0.3,
    ) -> dict[int, list[TranscriptSegment]]: ...


class PDFRenderer(Protocol):
    """PDF 渲染器协议。"""

    def render(
        self,
        slides: list[SlideSpan],
        page_text_map: dict[int, list[TranscriptSegment]],
        out_pdf: str,
    ) -> str: ...
