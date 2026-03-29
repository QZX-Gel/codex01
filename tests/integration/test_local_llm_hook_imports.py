"""功能: 模块骨架/测试代码。作用: 提供最小可运行能力。边界: 当前为 stub，不含真实业务推理。"""

from src.local_llm_hook.hook import run_local_llm_hook


def test_local_llm_hook_callable():
    assert callable(run_local_llm_hook)
