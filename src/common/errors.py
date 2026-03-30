"""功能: 统一错误模型。作用: 提供稳定错误码与可诊断消息。边界: 不做异常恢复调度。"""

class AppError(Exception):
    """应用层基类异常。"""

    code = "E0000"

    def __init__(self, message: str, *, hint: str | None = None):
        self.message = message
        self.hint = hint
        super().__init__(self.__str__())

    def __str__(self) -> str:
        if self.hint:
            return f"[{self.code}] {self.message} | hint={self.hint}"
        return f"[{self.code}] {self.message}"


class IngestError(AppError):
    """输入/预处理阶段错误。"""

    code = "E1001"


class ASRError(AppError):
    """ASR 阶段错误。"""

    code = "E3001"


class SlideDetectError(AppError):
    """翻页检测阶段错误。"""

    code = "E4001"


class RenderError(AppError):
    """渲染导出阶段错误。"""

    code = "E5001"
