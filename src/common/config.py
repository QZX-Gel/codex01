"""功能: 配置加载与归一化。作用: 把 JSON/YAML 配置映射为统一 PipelineConfig。边界: 不负责业务执行。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class ASRConfig:
    model_name: str
    device: str
    engine: str
    beam_size: int | None


@dataclass(frozen=True)
class VideoConfig:
    frame_fps: int


@dataclass(frozen=True)
class SlideConfig:
    ssim_threshold: float
    min_page_duration_sec: float
    cooldown_sec: float


@dataclass(frozen=True)
class AlignConfig:
    min_overlap_sec: float


@dataclass
class PipelineConfig:
    """Pipeline 扁平化运行配置。"""

    input_video: str = "input/class.mp4"
    output_dir: str = "output"
    frame_fps: int = 4
    asr_device: str = "cuda"
    enable_local_llm_hook: bool = False
    asr_model_name: str = "medium"
    asr_engine: str = "faster-whisper"
    asr_beam_size: int | None = None
    min_overlap_sec: float = 0.3
    ssim_threshold: float = 0.82
    min_page_duration_sec: float = 1.0
    cooldown_sec: float = 1.0

    @property
    def asr(self) -> ASRConfig:
        return ASRConfig(
            model_name=self.asr_model_name,
            device=self.asr_device,
            engine=self.asr_engine,
            beam_size=self.asr_beam_size,
        )

    @property
    def video(self) -> VideoConfig:
        return VideoConfig(frame_fps=self.frame_fps)

    @property
    def slide(self) -> SlideConfig:
        return SlideConfig(
            ssim_threshold=self.ssim_threshold,
            min_page_duration_sec=self.min_page_duration_sec,
            cooldown_sec=self.cooldown_sec,
        )

    @property
    def align(self) -> AlignConfig:
        return AlignConfig(min_overlap_sec=self.min_overlap_sec)

    @classmethod
    def from_mapping(cls, data: dict) -> "PipelineConfig":
        """兼容 JSON 扁平配置与 architecture.md 中的分层 YAML 配置。"""
        flat = dict(data or {})

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
            "asr_engine": flat.get("asr_engine", asr.get("engine", cls.asr_engine)),
            "asr_beam_size": flat.get("asr_beam_size", asr.get("beam_size", cls.asr_beam_size)),
            "min_overlap_sec": flat.get("min_overlap_sec", align.get("min_overlap_sec", cls.min_overlap_sec)),
            "ssim_threshold": flat.get("ssim_threshold", slide.get("ssim_threshold", cls.ssim_threshold)),
            "min_page_duration_sec": flat.get(
                "min_page_duration_sec",
                slide.get("min_page_duration_sec", cls.min_page_duration_sec),
            ),
            "cooldown_sec": flat.get("cooldown_sec", slide.get("cooldown_sec", cls.cooldown_sec)),
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
        raise FileNotFoundError(f"Config file not found: {path}")
    data = _load_raw_mapping(p)
    return PipelineConfig.from_mapping(data)
