"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.common.config import load_config
from src.common.logger import get_logger
from src.ingest.extract_audio import extract_audio
from src.ingest.extract_frames import extract_frames
from src.asr.transcribe import transcribe_audio
from src.slide.detect_slides import run_slide_detection
from src.align.align_text import align_segments_to_slides
from src.render.render_pdf import render_note_pdf
from src.local_llm_hook.hook import run_local_llm_hook


def run_pipeline(config_path: str | None = None) -> int:
    logger = get_logger("pipeline")
    cfg = load_config(config_path)

    output_dir = Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    wav_path = str(output_dir / "audio.wav")
    frames_dir = str(output_dir / "frames")

    logger.info("stage=ingest.start")
    extract_audio(cfg.input_video, wav_path)
    frame_paths = extract_frames(cfg.input_video, frames_dir, cfg.frame_fps)
    logger.info("stage=ingest.done frames=%s", len(frame_paths))

    logger.info("stage=asr.start device=%s", cfg.asr_device)
    segments = transcribe_audio(wav_path, model_name=cfg.asr_model_name, device=cfg.asr_device)
    logger.info("stage=asr.done segments=%s", len(segments))

    logger.info("stage=slide.start")
    slides = run_slide_detection(
        frame_paths,
        output_dir=str(output_dir),
        ssim_threshold=cfg.ssim_threshold,
        fps=float(cfg.frame_fps),
        cooldown_sec=cfg.cooldown_sec,
        min_page_duration_sec=cfg.min_page_duration_sec,
    )
    logger.info("stage=slide.done pages=%s", len(slides))

    page_text_map = align_segments_to_slides(segments, slides)
    page_text_map_path = output_dir / "page_text_map.json"
    page_text_map_path.write_text(
        json.dumps(
            {
                str(k): [{"start_time": x.start_time, "end_time": x.end_time, "text": x.text} for x in v]
                for k, v in page_text_map.items()
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if cfg.enable_local_llm_hook:
        logger.info("stage=local_llm_hook.start")
        llm_result = run_local_llm_hook(page_text_map)
        (output_dir / "local_llm_hook.json").write_text(
            json.dumps(llm_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("stage=local_llm_hook.done")

    render_note_pdf(slides, page_text_map, str(output_dir / "course_note.pdf"))
    logger.info("stage=render.done")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Classnote local pipeline (skeleton)")
    parser.add_argument("--config", default=None, help="Path to JSON config file (skeleton stage)")
    args = parser.parse_args()
    return run_pipeline(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
