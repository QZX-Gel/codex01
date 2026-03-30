"""功能: 日志工具。作用: 提供统一日志格式与结构化字段扩展。边界: 不负责日志采集后端。"""

import logging
from pathlib import Path
from typing import Any


def get_logger(name: str = "classnote") -> logging.Logger:
    """返回统一格式 logger，避免重复添加 handler。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        log_path = Path("output/logs/run.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def kv(msg: str, **fields: Any) -> str:
    """生成 key=value 风格日志消息，便于 grep 与后续接入结构化日志。"""
    if not fields:
        return msg
    payload = " ".join(f"{k}={v}" for k, v in fields.items())
    return f"{msg} {payload}"
