"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from src.align.align_text import _overlap


def test_overlap_basic():
    assert _overlap(0, 5, 3, 7) == 2
