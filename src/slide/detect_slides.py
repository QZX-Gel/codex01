"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from src.common.schema import SlideSpan


def detect_slide_spans(frame_paths: list[str], ssim_threshold: float = 0.82) -> list[SlideSpan]:
    """Skeleton only: return 2 fake slide spans."""
    return [
        SlideSpan(page_id=1, start_time=0.0, end_time=6.0, keyframe_path=frame_paths[0] if frame_paths else ""),
        SlideSpan(page_id=2, start_time=6.0, end_time=12.0, keyframe_path=frame_paths[1] if len(frame_paths) > 1 else ""),
    ]
