from __future__ import annotations

import os
import sys
from pathlib import Path

def configure_windows_cuda_paths() -> None:
    if sys.platform != "win32":
        return

    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    candidates = [
        base / "cublas" / "bin",
        base / "cuda_runtime" / "bin",
        base / "cuda_nvrtc" / "bin",
        base / "cudnn" / "bin",
    ]

    existing = [p for p in candidates if p.exists()]
    if hasattr(os, "add_dll_directory"):
        for p in existing:
            os.add_dll_directory(str(p))

    os.environ["PATH"] = os.pathsep.join([str(p) for p in existing] + [os.environ.get("PATH", "")])

def main() -> int:
    configure_windows_cuda_paths()

    audio_path = Path("output/audio.wav")
    if not audio_path.exists():
        print("SKIP: output/audio.wav not found")
        return 2

    from src.asr.transcribe import transcribe_audio

    model_name = os.getenv("GPU_TEST_MODEL", "tiny")
    segments = transcribe_audio(str(audio_path), model_name, "cuda")

    assert segments is not None
    assert len(segments) > 0

    first = segments[0]
    assert hasattr(first, "start_time")
    assert hasattr(first, "end_time")
    assert hasattr(first, "text")
    assert first.start_time < first.end_time

    print(f"OK: segment_count={len(segments)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())