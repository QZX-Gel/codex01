"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from pathlib import Path


def extract_audio(video_path: str, out_wav: str, sr: int = 16000) -> str:
    """Skeleton only: create a placeholder wav artifact path."""
    Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
    Path(out_wav).write_bytes(b"")
    return out_wav
