from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _has_command(name: str) -> bool:
    return shutil.which(name) is not None


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.mark.integration
def test_nvidia_smi_visible():
    """
    测试 1：
    系统层是否能看到 NVIDIA 驱动。
    这一步不保证项目一定能跑 GPU，只说明驱动/显卡基本可见。
    """
    if not _has_command("nvidia-smi"):
        pytest.skip("nvidia-smi not found in PATH")

    result = _run(["nvidia-smi"])
    assert result.returncode == 0, (
        "nvidia-smi failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    output = (result.stdout + "\n" + result.stderr).lower()
    assert "nvidia" in output or "cuda" in output, (
        "nvidia-smi ran but output does not look like an NVIDIA environment.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


@pytest.mark.integration
def test_ctranslate2_cuda_runtime_available():
    """
    测试 2：
    CTranslate2 是否能看到 CUDA 设备。
    这是 faster-whisper 真正依赖的运行时层。
    """
    ctranslate2 = pytest.importorskip("ctranslate2")

    # 某些版本提供 get_cuda_device_count
    if not hasattr(ctranslate2, "get_cuda_device_count"):
        pytest.skip("ctranslate2.get_cuda_device_count is not available in this version")

    try:
        count = ctranslate2.get_cuda_device_count()
    except Exception as e:
        pytest.fail(f"CTranslate2 CUDA runtime probe failed: {e}")

    assert isinstance(count, int), f"Unexpected device count type: {type(count)}"
    assert count >= 1, f"No CUDA devices visible to CTranslate2, count={count}"


@pytest.mark.integration
def test_faster_whisper_gpu_model_load_smoke():
    """
    测试 3：
    faster-whisper 能否以 device='cuda' 成功创建模型。
    这一步主要发现类似 cublas64_12.dll / cudnn 缺失问题。

    注意：
    - 这一步可能需要模型已缓存
    - 默认用 tiny，避免太重
    - 可通过环境变量覆盖模型名：
      GPU_TEST_MODEL=tiny
    """
    pytest.importorskip("faster_whisper")

    from faster_whisper import WhisperModel

    model_name = os.getenv("GPU_TEST_MODEL", "tiny")

    try:
        model = WhisperModel(model_name, device="cuda", compute_type="float16")
    except Exception as e:
        pytest.fail(
            "Failed to initialize faster-whisper with CUDA.\n"
            "This usually means CUDA runtime / cuBLAS / cuDNN is not correctly installed.\n"
            f"error: {e}"
        )

    assert model is not None


@pytest.mark.integration
def test_project_transcribe_audio_gpu_smoke():
    """
    测试 4：
    项目自己的 GPU 路径能否跑通最小冒烟测试。

    前提：
    - output/audio.wav 已存在
    - transcribe_audio 支持 device='cuda'
    - 模型可加载

    为了避免太重，只要求返回至少 1 个 segment。
    """
    audio_path = Path("output/audio.wav")
    if not audio_path.exists():
        pytest.skip("output/audio.wav not found; run ingest first")

    from src.asr.transcribe import transcribe_audio

    model_name = os.getenv("GPU_TEST_MODEL", "tiny")

    try:
        segments = transcribe_audio(str(audio_path), model_name, "cuda")
    except Exception as e:
        pytest.fail(
            "Project GPU ASR smoke test failed.\n"
            f"audio={audio_path}\n"
            f"error={e}"
        )

    assert segments is not None
    assert len(segments) > 0, "GPU ASR returned no segments"

    first = segments[0]
    assert hasattr(first, "start_time")
    assert hasattr(first, "end_time")
    assert hasattr(first, "text")
    assert first.start_time < first.end_time