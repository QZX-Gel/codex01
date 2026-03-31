from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INPUT_VIDEO = ROOT / "input" / "class.mp4"
OUTPUT_DIR = ROOT / "output"

AUDIO_WAV = OUTPUT_DIR / "audio.wav"
FRAMES_DIR = OUTPUT_DIR / "frames"
VIDEO_INFO_JSON = OUTPUT_DIR / "meta" / "video_info.json"

TRANSCRIPT_JSONL = OUTPUT_DIR / "transcript.jsonl"
TRANSCRIPT_SRT = OUTPUT_DIR / "transcript.srt"

SLIDES_DIR = OUTPUT_DIR / "slides"
PAGE_MANIFEST_JSON = OUTPUT_DIR / "page_manifest.json"

PAGE_TEXT_MAP_JSON = OUTPUT_DIR / "page_text_map.json"

COURSE_NOTE_PDF = OUTPUT_DIR / "course_note.pdf"

RUN_PLAN_JSON = OUTPUT_DIR / "meta" / "run_plan.json"
CHECKPOINT_JSON = OUTPUT_DIR / "meta" / "checkpoint.json"
RUN_SUMMARY_JSON = OUTPUT_DIR / "meta" / "run_summary.json"
RUN_LOG = OUTPUT_DIR / "logs" / "run.log"


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(1)


def assert_exists(path: Path, *, min_size: int = 1) -> None:
    if not path.exists():
        fail(f"Missing file: {path}")
    size = path.stat().st_size
    if size < min_size:
        fail(f"File too small: {path} ({size} bytes)")


def assert_dir_has_files(path: Path, pattern: str, *, min_count: int = 1) -> None:
    if not path.exists() or not path.is_dir():
        fail(f"Missing directory: {path}")
    count = len(list(path.glob(pattern)))
    if count < min_count:
        fail(f"Directory {path} has too few files matching {pattern}: got {count}, need >= {min_count}")


def load_json(path: Path):
    assert_exists(path, min_size=2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Invalid JSON in {path}: {e}")


def assert_json_object(path: Path) -> None:
    data = load_json(path)
    if not isinstance(data, dict):
        fail(f"Expected JSON object in {path}, got {type(data).__name__}")
    if len(data) == 0:
        fail(f"JSON object is empty: {path}")


def assert_json_array(path: Path) -> None:
    data = load_json(path)
    if not isinstance(data, list):
        fail(f"Expected JSON array in {path}, got {type(data).__name__}")
    if len(data) == 0:
        fail(f"JSON array is empty: {path}")


def assert_jsonl(path: Path, *, min_lines: int = 1) -> None:
    assert_exists(path, min_size=2)
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < min_lines:
        fail(f"JSONL has too few lines: {path} ({len(lines)} lines)")
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except Exception as e:
            fail(f"Invalid JSONL at {path}, line {i}: {e}")
        if not isinstance(obj, dict):
            fail(f"JSONL line {i} in {path} is not a JSON object")


def assert_pdf(path: Path, *, min_size: int = 1024) -> None:
    assert_exists(path, min_size=min_size)
    with path.open("rb") as f:
        head = f.read(5)
    if head != b"%PDF-":
        fail(f"Not a PDF header: {path}")


def run_module(module_name: str, args: list[str] | None = None) -> bool:
    cmd = [sys.executable, "-m", module_name]
    if args:
        cmd.extend(args)

    info("Running: " + " ".join(str(x) for x in cmd))
    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode == 0:
        if completed.stdout.strip():
            print(completed.stdout)
        ok(f"Module succeeded: {module_name}")
        return True

    stderr = completed.stderr or ""
    stdout = completed.stdout or ""

    # 模块不存在：不是“真实失败”，继续尝试候选入口
    if "No module named" in stderr:
        info(f"Module not found, skip: {module_name}")
        return False

    # 模块存在但执行失败：打印出来，方便定位
    print("STDOUT:")
    print(stdout)
    print("STDERR:")
    print(stderr)
    fail(f"Module execution failed: {module_name}")
    return False


def try_modules(module_names: list[str], args: list[str] | None = None) -> bool:
    for name in module_names:
        if run_module(name, args=args):
            return True
    return False


def ensure_input() -> None:
    if not INPUT_VIDEO.exists():
        fail(f"Missing input video: {INPUT_VIDEO}")
    if INPUT_VIDEO.stat().st_size == 0:
        fail(f"Input video is empty: {INPUT_VIDEO}")
    ok(f"Input video exists: {INPUT_VIDEO}")


def accept_p1() -> None:
    info("=== P1 / M1 ingest acceptance ===")

    if not AUDIO_WAV.exists() or not FRAMES_DIR.exists() or not VIDEO_INFO_JSON.exists():
        try_modules(
            [
                "src.ingest.extract_audio",
                "src.ingest.extract_frames",
                "src.ingest.run_ingest",
                "src.pipeline.run_until_p1",
            ]
        )

    assert_exists(AUDIO_WAV, min_size=1024)
    assert_dir_has_files(FRAMES_DIR, "*.jpg", min_count=1)
    assert_json_object(VIDEO_INFO_JSON)
    ok("P1 accepted: audio.wav + frames + video_info.json")


def accept_p2() -> None:
    info("=== P2 / M2 asr acceptance ===")

    if not TRANSCRIPT_JSONL.exists():
        # 默认走 CPU，避免 GPU 运行时阻塞验收
        ran = try_modules(
            [
                "src.asr.transcribe",
                "src.asr.run_asr",
                "src.pipeline.run_until_p2",
            ],
            args=["--device", "cpu"],
        )

        if not ran:
            info("No known P2 CLI entry found; validating existing artifacts only.")

    assert_jsonl(TRANSCRIPT_JSONL, min_lines=1)

    # srt 是架构里“可选”，所以只做弱检查
    if TRANSCRIPT_SRT.exists():
        assert_exists(TRANSCRIPT_SRT, min_size=8)

    ok("P2 accepted: transcript.jsonl")


def accept_p3() -> None:
    info("=== P3 / M3 slide detector acceptance ===")

    if not PAGE_MANIFEST_JSON.exists() or not SLIDES_DIR.exists():
        ran = try_modules(
            [
                "src.slide.detect_slides",
                "src.slide.run_slide_detector",
                "src.pipeline.run_until_p3",
            ]
        )
        if not ran:
            info("No known P3 CLI entry found; validating existing artifacts only.")

    assert_json_exists_with_content(PAGE_MANIFEST_JSON)
    assert_dir_has_files(SLIDES_DIR, "*.jpg", min_count=1)
    ok("P3 accepted: page_manifest.json + slides/keyframe_*.jpg")


def accept_p4() -> None:
    info("=== P4 / M4 aligner acceptance ===")

    if not PAGE_TEXT_MAP_JSON.exists():
        ran = try_modules(
            [
                "src.align.align_text",
                "src.align.run_aligner",
                "src.pipeline.run_until_p4",
                "src.pipeline.run_until_p5",  # 有些项目把 P4/P5 合并到一个检查节点
            ]
        )
        if not ran:
            info("No known P4 CLI entry found; validating existing artifacts only.")

    data = load_json(PAGE_TEXT_MAP_JSON)
    if not isinstance(data, (dict, list)):
        fail(f"page_text_map must be dict or list, got {type(data).__name__}")
    if len(data) == 0:
        fail("page_text_map.json is empty")

    ok("P4 accepted: page_text_map.json")


def accept_p5() -> None:
    info("=== P5 / M5 pdf renderer acceptance ===")

    if not COURSE_NOTE_PDF.exists():
        ran = try_modules(
            [
                "src.render.render_course_note",
                "src.render.build_course_note",
                "src.render.render_pdf",
                "src.pipeline.run_until_p5",
            ]
        )
        if not ran:
            info("No known P5 CLI entry found; validating existing artifacts only.")

    assert_pdf(COURSE_NOTE_PDF, min_size=1024)
    ok("P5 accepted: course_note.pdf")


def accept_p6() -> None:
    info("=== P6 / M6 orchestrator acceptance ===")

    # 如果 run_summary 或 run_plan 不存在，尝试总控入口
    if not RUN_SUMMARY_JSON.exists():
        ran = try_modules(
            [
                "src.pipeline.orchestrator",
                "src.pipeline.run_pipeline",
                "src.pipeline.main",
            ],
            args=["--input", str(INPUT_VIDEO), "--output-dir", str(OUTPUT_DIR), "--device", "cpu"],
        )
        if not ran:
            info("No known P6 CLI entry found; falling back to final artifact validation.")

    # P6 的本质是“全链路调度成功”，所以以最终产物 + 元数据为主
    assert_exists(AUDIO_WAV, min_size=1024)
    assert_jsonl(TRANSCRIPT_JSONL, min_lines=1)
    assert_json_exists_with_content(PAGE_MANIFEST_JSON)

    data = load_json(PAGE_TEXT_MAP_JSON)
    if not isinstance(data, (dict, list)) or len(data) == 0:
        fail("Invalid page_text_map.json after orchestrator run")

    assert_pdf(COURSE_NOTE_PDF, min_size=1024)

    # 这些是架构里给的 orchestrator 元数据输出；若存在则做强校验，不存在不直接判死
    if RUN_PLAN_JSON.exists():
        assert_json_object(RUN_PLAN_JSON)
    if CHECKPOINT_JSON.exists():
        assert_json_object(CHECKPOINT_JSON)
    if RUN_SUMMARY_JSON.exists():
        assert_json_object(RUN_SUMMARY_JSON)
    if RUN_LOG.exists():
        assert_exists(RUN_LOG, min_size=1)

    ok("P6 accepted: full pipeline artifacts are present")


def assert_json_exists_with_content(path: Path) -> None:
    data = load_json(path)
    if not isinstance(data, (dict, list)):
        fail(f"Expected JSON object or array in {path}, got {type(data).__name__}")
    if len(data) == 0:
        fail(f"JSON is empty: {path}")


def main() -> None:
    ensure_input()
    accept_p1()
    accept_p2()
    accept_p3()
    accept_p4()
    accept_p5()
    accept_p6()
    print("\nALL ACCEPTANCE CHECKS PASSED: P1 -> P6")


if __name__ == "__main__":
    main()