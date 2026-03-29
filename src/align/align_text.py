"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from collections import defaultdict
from src.common.schema import TranscriptSegment, SlideSpan


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def align_segments_to_slides(
    segments: list[TranscriptSegment],
    slides: list[SlideSpan],
    min_overlap_sec: float = 0.3,
) -> dict[int, list[TranscriptSegment]]:
    mapping: dict[int, list[TranscriptSegment]] = defaultdict(list)
    for seg in segments:
        for slide in slides:
            if _overlap(seg.start_time, seg.end_time, slide.start_time, slide.end_time) >= min_overlap_sec:
                mapping[slide.page_id].append(seg)
    return dict(mapping)
