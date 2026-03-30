from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

from src.common.schema import TranscriptSegment, SlideSpan
from src.common.config import load_config
from src.common.logger import get_logger
from src.common.errors import InputFileError


def main() -> int:
    # 1. load config
    cfg = load_config("config/default.yaml")

    # 2. create shared schema objects
    seg = TranscriptSegment(
        start_time=0.0,
        end_time=1.5,
        text="Phase 1 acceptance test segment",
    )
    slide = SlideSpan(
        page_id=1,
        start_time=0.0,
        end_time=10.0,
        keyframe_path="output/slides/keyframe_001.jpg",
    )

    # 3. logger
    logger = get_logger("phase1-acceptance")
    logger.info("phase1 acceptance started")

    # 4. verify config fields
    assert hasattr(cfg, "asr")
    assert hasattr(cfg, "video")
    assert hasattr(cfg, "slide")
    assert hasattr(cfg, "align")

    # 5. verify schema serialization
    seg_dict = asdict(seg)
    slide_dict = asdict(slide)

    assert seg_dict["text"] == "Phase 1 acceptance test segment"
    assert slide_dict["page_id"] == 1

    # 6. verify error system
    try:
        raise InputFileError("demo input error")
    except InputFileError as e:
        logger.info(f"caught demo error code={e.code}")
        assert e.code == "E1001"

    # 7. verify log file exists
    log_path = Path("output/logs/run.log")
    assert log_path.exists(), "run.log should exist after logger writes"

    print("[PASS] Phase 1 acceptance passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())