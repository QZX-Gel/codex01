"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from src.pipeline.run_pipeline import run_pipeline


def test_run_pipeline_callable():
    assert callable(run_pipeline)
