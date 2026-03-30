"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from pathlib import Path
from src.common.schema import SlideSpan, TranscriptSegment


def render_note_pdf(
    slides: list[SlideSpan],
    page_text_map: dict[int, list[TranscriptSegment]],
    out_pdf: str,
) -> str:
    """Skeleton only: write a text placeholder with .pdf extension."""
    out = Path(out_pdf)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["CLASSNOTE STUB PDF", f"slides={len(slides)}", f"pages_with_text={len(page_text_map)}"]
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)
