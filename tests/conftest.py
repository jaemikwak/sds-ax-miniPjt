import pytest

import src.llm as llm


@pytest.fixture(autouse=True)
def reset_budget():
    """run() 150초 상한은 contextvar라 테스트끼리 새어 나가지 않게 매번 초기화."""
    llm._deadline.set(None)
