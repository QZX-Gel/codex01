"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

class AppError(Exception):
    """Base application error."""


class IngestError(AppError):
    code = "E1001"


class ASRError(AppError):
    code = "E3001"


class SlideDetectError(AppError):
    code = "E4001"


class RenderError(AppError):
    code = "E5001"
