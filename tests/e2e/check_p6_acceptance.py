from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
PAGE_TEXT_MAP = OUTPUT_DIR / "page_text_map.json"
COURSE_NOTE_PDF = OUTPUT_DIR / "course_note.pdf"


def fail(msg: str) -> None:
    print(f"P6 acceptance FAILED: {msg}")
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"P6 acceptance OK: {msg}")


def ensure_prereq() -> None:
    if not PAGE_TEXT_MAP.exists():
        fail(f"Missing prerequisite file: {PAGE_TEXT_MAP}")

    try:
        data = json.loads(PAGE_TEXT_MAP.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"page_text_map is not valid JSON: {e}")

    if not data:
        fail("page_text_map.json is empty")

    if not isinstance(data, (dict, list)):
        fail(f"page_text_map must be dict or list, got {type(data).__name__}")

    ok("P5 artifact exists and is structurally readable")


def try_module_entry() -> bool:
    """
    优先尝试约定式模块入口：
    - src.render.render_course_note
    - main()
    这样更适合项目内模块化调用。
    """
    candidates = [
        ("src.render.render_course_note", "main"),
        ("src.render.build_course_note", "main"),
        ("src.render.render_pdf", "main"),
    ]

    for module_name, func_name in candidates:
        try:
            mod = importlib.import_module(module_name)
            fn = getattr(mod, func_name, None)
            if callable(fn):
                print(f"[P6] trying module entry: {module_name}.{func_name}()")
                fn()
                return True
        except ModuleNotFoundError:
            continue
        except Exception as e:
            fail(f"Module entry {module_name}.{func_name} failed: {e}")

    return False


def try_cli_entry() -> bool:
    """
    如果模块入口不存在，则尝试常见 CLI 入口。
    """
    commands = [
        [sys.executable, "-m", "src.render.render_course_note"],
        [sys.executable, "-m", "src.render.build_course_note"],
        [sys.executable, "-m", "src.render.render_pdf"],
    ]

    for cmd in commands:
        try:
            print(f"[P6] trying CLI entry: {' '.join(cmd)}")
            completed = subprocess.run(
                cmd,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode == 0:
                return True

            # 模块存在但执行失败，说明不是“不存在”，而是真失败
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            if "No module named" not in stderr:
                fail(
                    "CLI entry failed.\n"
                    f"CMD: {' '.join(cmd)}\n"
                    f"STDOUT:\n{stdout}\n"
                    f"STDERR:\n{stderr}"
                )
        except Exception as e:
            fail(f"CLI invocation failed for {' '.join(cmd)}: {e}")

    return False


def validate_pdf() -> None:
    if not COURSE_NOTE_PDF.exists():
        fail(f"Expected output PDF not found: {COURSE_NOTE_PDF}")

    size = COURSE_NOTE_PDF.stat().st_size
    if size < 1024:
        fail(f"Output PDF looks too small: {size} bytes")

    with COURSE_NOTE_PDF.open("rb") as f:
        header = f.read(5)

    if header != b"%PDF-":
        fail("Output file is not a valid PDF header")

    ok(f"PDF exists and header is valid; size={size} bytes")


def main() -> None:
    os.chdir(ROOT)
    ensure_prereq()

    ran = try_module_entry()
    if not ran:
        ran = try_cli_entry()

    if not ran:
        fail(
            "No known P6 entrypoint found. "
            "Please update check_p6_acceptance.py with the actual module path."
        )

    validate_pdf()
    ok("P6 acceptance PASSED")


if __name__ == "__main__":
    main()