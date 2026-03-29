"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class PipelineConfig:
    input_video: str = "input/class.mp4"
    output_dir: str = "output"
    frame_fps: int = 4
    asr_device: str = "cuda"
    enable_local_llm_hook: bool = False


def load_config(path: str | None = None) -> PipelineConfig:
    if not path:
        return PipelineConfig()
    p = Path(path)
    if not p.exists():
        return PipelineConfig()
    # Skeleton stage: support JSON-shaped config for minimal runability.
    # Real YAML loader can be plugged in later.
    data = json.loads(p.read_text(encoding="utf-8"))
    return PipelineConfig(**{**PipelineConfig().__dict__, **data})
