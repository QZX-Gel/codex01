"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

import logging


def get_logger(name: str = "classnote") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
