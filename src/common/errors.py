class AppError(Exception):
    code = "E0000"
    suggestion = "请查看日志并检查配置。"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InputFileError(AppError):
    code = "E1001"
    suggestion = "请检查输入文件路径是否正确，文件是否存在或损坏。"


class FfmpegError(AppError):
    code = "E2001"
    suggestion = "请确认 ffmpeg 已安装，且命令可在终端中执行。"


class ASRModelLoadError(AppError):
    code = "E3001"
    suggestion = "请检查模型名称、CUDA/驱动是否匹配，必要时切换到 CPU。"


class SlideDetectionError(AppError):
    code = "E4001"
    suggestion = "请检查抽帧结果，并尝试调整 ssim_threshold 或 cooldown_sec。"


class PdfRenderError(AppError):
    code = "E5001"
    suggestion = "请检查字体、编码和输出目录权限。"

class FfprobeError(AppError):
    code = "E2002"
    suggestion = "请确认 ffprobe 已安装，且命令可在终端中执行。"


class ASRTranscriptionError(AppError):
    code = "E3002"
    suggestion = "请检查音频是否有效、模型推理依赖是否完整，并查看 ASR 日志。"
