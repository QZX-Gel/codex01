"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from pathlib import Path


def extract_frames(video_path: str, out_dir: str, fps: float) -> list[str]:
    """Skeleton only: create placeholder frame files."""
    frame_dir = Path(out_dir)
    frame_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(3):
        p = frame_dir / f"frame_{i:04d}.jpg"
        p.write_bytes(b"")
        paths.append(str(p))
    return paths
