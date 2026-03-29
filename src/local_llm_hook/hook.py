"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from src.common.schema import TranscriptSegment


def run_local_llm_hook(
    page_text_map: dict[int, list[TranscriptSegment]],
) -> dict[str, object]:
    """M7 skeleton: reserved local <20B API hook, no real model call yet."""
    return {
        "enabled": True,
        "summary": "[stub] local llm hook reserved",
        "pages": len(page_text_map),
    }
