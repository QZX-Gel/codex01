"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from src.common.schema import TranscriptSegment


def transcribe_audio(wav_path: str, model_name: str = "medium", device: str = "cuda") -> list[TranscriptSegment]:
    """Skeleton only: return deterministic fake transcript segments."""
    return [
        TranscriptSegment(start_time=0.0, end_time=5.0, text="[stub] segment 1"),
        TranscriptSegment(start_time=5.0, end_time=10.0, text="[stub] segment 2"),
    ]
