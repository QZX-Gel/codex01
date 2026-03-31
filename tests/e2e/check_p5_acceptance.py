from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL at {path}:{lineno}: {e}") from e
    return rows


def norm_page_key(k: Any) -> str:
    return str(k)


def seg_identity(seg: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (
        seg.get("start_time"),
        seg.get("end_time"),
        seg.get("text"),
    )


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def validate_transcript_segments(segments: list[dict[str, Any]]) -> None:
    for i, seg in enumerate(segments):
        assert_true("start_time" in seg, f"Transcript seg[{i}] missing start_time")
        assert_true("end_time" in seg, f"Transcript seg[{i}] missing end_time")
        assert_true("text" in seg, f"Transcript seg[{i}] missing text")

        s = seg["start_time"]
        e = seg["end_time"]
        t = seg["text"]

        assert_true(isinstance(s, (int, float)), f"Transcript seg[{i}] start_time not number")
        assert_true(isinstance(e, (int, float)), f"Transcript seg[{i}] end_time not number")
        assert_true(isinstance(t, str), f"Transcript seg[{i}] text not str")
        assert_true(s < e, f"Transcript seg[{i}] has invalid interval: {s} !< {e}")
        assert_true(t.strip() != "", f"Transcript seg[{i}] text is empty")


def validate_manifest(slides: list[dict[str, Any]]) -> list[str]:
    page_ids: list[str] = []
    seen: set[str] = set()

    for i, slide in enumerate(slides):
        for field in ("page_id", "start_time", "end_time", "keyframe_path"):
            assert_true(field in slide, f"Slide[{i}] missing {field}")

        pid = norm_page_key(slide["page_id"])
        s = slide["start_time"]
        e = slide["end_time"]
        kp = slide["keyframe_path"]

        assert_true(isinstance(s, (int, float)), f"Slide[{i}] start_time not number")
        assert_true(isinstance(e, (int, float)), f"Slide[{i}] end_time not number")
        assert_true(isinstance(kp, str), f"Slide[{i}] keyframe_path not str")
        assert_true(s < e, f"Slide[{i}] has invalid interval: {s} !< {e}")
        assert_true(pid not in seen, f"Duplicate page_id in manifest: {pid}")

        seen.add(pid)
        page_ids.append(pid)

    return page_ids


def validate_page_text_map(
    page_text_map: dict[str, Any],
    expected_page_ids: list[str],
    transcript_segments: list[dict[str, Any]],
) -> None:
    assert_true(isinstance(page_text_map, dict), "page_text_map.json must be a JSON object")

    actual_page_ids = [norm_page_key(k) for k in page_text_map.keys()]
    expected_set = set(expected_page_ids)
    actual_set = set(actual_page_ids)

    # 1. 所有 manifest 页必须保留，即使为空页
    missing_pages = expected_set - actual_set
    assert_true(not missing_pages, f"Missing pages in page_text_map: {sorted(missing_pages)}")

    # 2. 不应出现额外未知页
    extra_pages = actual_set - expected_set
    assert_true(not extra_pages, f"Unexpected extra pages in page_text_map: {sorted(extra_pages)}")

    # 3. 页顺序应与 manifest 顺序一致
    assert_true(
        actual_page_ids == expected_page_ids,
        f"Page order mismatch. expected={expected_page_ids}, actual={actual_page_ids}",
    )

    # 4. 每页 value 应为 list
    for pid in expected_page_ids:
        value = page_text_map[pid]
        assert_true(isinstance(value, list), f"page_text_map[{pid}] must be a list")

    # 5. 每个 segment 最多出现一次
    occurrence: dict[tuple[Any, Any, Any], list[str]] = {}
    for pid in expected_page_ids:
        segs = page_text_map[pid]
        prev_start: float | None = None

        for idx, seg in enumerate(segs):
            assert_true(isinstance(seg, dict), f"page_text_map[{pid}][{idx}] must be an object")
            for field in ("start_time", "end_time", "text"):
                assert_true(field in seg, f"page_text_map[{pid}][{idx}] missing {field}")

            s = seg["start_time"]
            e = seg["end_time"]
            t = seg["text"]

            assert_true(isinstance(s, (int, float)), f"{pid}[{idx}] start_time not number")
            assert_true(isinstance(e, (int, float)), f"{pid}[{idx}] end_time not number")
            assert_true(isinstance(t, str), f"{pid}[{idx}] text not str")
            assert_true(s < e, f"{pid}[{idx}] invalid interval: {s} !< {e}")

            # 6. 每页内部时间顺序应稳定
            if prev_start is not None:
                assert_true(
                    prev_start <= s,
                    f"Segments in page {pid} are not chronological at index {idx}"
                )
            prev_start = float(s)

            key = seg_identity(seg)
            occurrence.setdefault(key, []).append(pid)

    duplicates = {k: v for k, v in occurrence.items() if len(v) > 1}
    assert_true(
        not duplicates,
        f"Some segments are assigned to multiple pages: {duplicates}"
    )

    # 7. page_text_map 中的 segment 必须来自 transcript.jsonl
    transcript_identities = {seg_identity(seg) for seg in transcript_segments}
    for key in occurrence:
        assert_true(
            key in transcript_identities,
            f"Mapped segment not found in transcript.jsonl: {key}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Acceptance checker for Phase 5 aligner")
    parser.add_argument("--transcript", default="output/transcript.jsonl")
    parser.add_argument("--manifest", default="output/page_manifest.json")
    parser.add_argument("--page-map", default="output/page_text_map.json")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    manifest_path = Path(args.manifest)
    page_map_path = Path(args.page_map)

    assert_true(transcript_path.exists(), f"Missing transcript file: {transcript_path}")
    assert_true(manifest_path.exists(), f"Missing manifest file: {manifest_path}")
    assert_true(page_map_path.exists(), f"Missing page_text_map file: {page_map_path}")

    transcript_segments = load_jsonl(transcript_path)
    slides = load_json(manifest_path)
    page_text_map = load_json(page_map_path)

    assert_true(len(transcript_segments) > 0, "Transcript is empty")
    assert_true(isinstance(slides, list), "page_manifest.json must be a JSON array")
    assert_true(len(slides) > 0, "Page manifest is empty")

    validate_transcript_segments(transcript_segments)
    expected_page_ids = validate_manifest(slides)
    validate_page_text_map(page_text_map, expected_page_ids, transcript_segments)

    print("P5 acceptance PASSED")
    print(f"- transcript segments: {len(transcript_segments)}")
    print(f"- manifest pages: {len(expected_page_ids)}")
    print(f"- output file: {page_map_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"P5 acceptance FAILED: {e}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as e:
        print(f"P5 acceptance ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)