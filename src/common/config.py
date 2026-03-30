"""功能: 配置加载与归一化。作用: 把 JSON/YAML 配置映射为统一 PipelineConfig。边界: 不负责业务执行。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class PipelineConfig:
    """Pipeline 扁平化运行配置。

    说明:
    - 字段命名与运行时直接消费保持一致，便于模块调用。
    - 允许从 YAML 分层配置映射到当前扁平结构（见 `from_mapping`）。
    """

    input_video: str = "input/class.mp4"
    output_dir: str = "output"
    frame_fps: int = 4
    asr_device: str = "cuda"
    enable_local_llm_hook: bool = False
    asr_model_name: str = "medium"
    min_overlap_sec: float = 0.3
    ssim_threshold: float = 0.82

    @classmethod
    def from_mapping(cls, data: dict) -> "PipelineConfig":
        """兼容 JSON 扁平配置与 architecture.md 中的分层 YAML 配置。"""
        flat = dict(data or {})

        # 分层 YAML -> 扁平字段映射
        video = flat.get("video", {})
        asr = flat.get("asr", {})
        align = flat.get("align", {})
        slide = flat.get("slide", {})
        llm = flat.get("local_llm_hook", {})

        mapped = {
            "input_video": flat.get("input_video", cls.input_video),
            "output_dir": flat.get("output_dir", cls.output_dir),
            "frame_fps": flat.get("frame_fps", video.get("frame_fps", cls.frame_fps)),
            "asr_device": flat.get("asr_device", asr.get("device", cls.asr_device)),
            "asr_model_name": flat.get("asr_model_name", asr.get("model_name", cls.asr_model_name)),
            "min_overlap_sec": flat.get("min_overlap_sec", align.get("min_overlap_sec", cls.min_overlap_sec)),
            "ssim_threshold": flat.get("ssim_threshold", slide.get("ssim_threshold", cls.ssim_threshold)),
            "enable_local_llm_hook": flat.get(
                "enable_local_llm_hook",
                llm.get("enabled", cls.enable_local_llm_hook),
            ),
        }
        return cls(**mapped)


def _load_raw_mapping(path: Path) -> dict:
    if path.suffix.lower() in {".json"}:
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception:
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def load_config(path: str | None = None) -> PipelineConfig:
    """加载配置文件并返回归一化后的 PipelineConfig。"""
    if not path:
        return PipelineConfig()
    p = Path(path)
    if not p.exists():
        return PipelineConfig()
    data = _load_raw_mapping(p)
    return PipelineConfig.from_mapping(data)
