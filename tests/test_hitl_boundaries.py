"""저장 안전성 (AC6). Bedrock은 목으로 대체: 그래프 노드 중 LLM을 쓰는 summarize·guard·extract_todos·enrich를 바꿔 끼운다."""
import pytest

import src.agent as agent
import src.llm as llm
from src.tools import Todo, connect, save_todos

TODOS = [
    Todo(content="방화벽 신청 방법 안내", requester="이서준", source_excerpt="[2026-11-24 09:13] 이서준: 방화벽 신청 방법?", is_inquiry=True),
    Todo(content="개발서버 SSL 확인", requester="이서준", due_expression="내일까지", source_excerpt="[2026-11-24 09:16] 이서준: 내일까지 SSL 봐주세요"),
]


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "todos.sqlite"
    monkeypatch.setenv("OPSMATE_DB", str(db))
    monkeypatch.setattr(agent, "CHECKPOINT_DB", tmp_path / "ckpt.sqlite")
    monkeypatch.setattr(agent, "TRACE_DIR", tmp_path / "traces")
    monkeypatch.setattr(agent, "_GRAPH", None)
    monkeypatch.setattr(agent, "summarize", lambda s: {})
    monkeypatch.setattr(agent, "guard", lambda s: {"route": "extract"})
    monkeypatch.setattr(agent, "extract_todos", lambda text: [t.model_copy() for t in TODOS])
    monkeypatch.setattr(agent, "enrich", lambda s: {})
    yield db
    agent._GRAPH = None


def count(db) -> int:
    with connect(db) as c:
        return c.execute("SELECT COUNT(*) FROM todos").fetchone()[0]


def test_1_nothing_saved_before_approval(env):
    r = agent.run("[2026-11-24 09:13] 이서준: ...", "t1")
    assert r["pending"] and len(r["extracted_todos"]) == 2
    assert r["extracted_todos"][1]["due_date"] == "2026-11-25"  # '내일까지'는 파이썬이 계산
    assert count(env) == 0


def test_2_only_approved_saved(env):
    agent.run("입력", "t2")
    r = agent.resume("t2", [{"todo_index": 0, "action": "approve"}, {"todo_index": 1, "action": "reject"}])
    assert count(env) == 1 and "save_todos" in [c["name"] for c in r["tool_calls"]]


def test_2b_edit_applies_fields(env):
    agent.run("입력", "t2b")
    agent.resume("t2b", [{"todo_index": 1, "action": "edit", "edited_fields": {"due_date": "2026-11-30"}}])
    with connect(env) as c:
        assert c.execute("SELECT due_date FROM todos").fetchone()[0] == "2026-11-30"


@pytest.mark.parametrize("bad", [
    [{"todo_index": 0, "action": "delete"}],
    [{"todo_index": 5, "action": "approve"}],
    [{"todo_index": 0, "action": "edit", "edited_fields": {"pr_comment_summary": "x"}}],
    [{"todo_index": 0, "action": "edit", "edited_fields": {"due_date": "다음 주"}}],
])
def test_3_invalid_decision_saves_nothing(env, bad):
    agent.run("입력", "t3")
    r = agent.resume("t3", bad)
    assert r.get("error") and count(env) == 0
    assert agent.resume("t3", [{"todo_index": 0, "action": "approve"}])["tool_calls"]  # 승인 대기는 그대로 남음


def test_4_resume_twice_no_duplicate(env):
    agent.run("입력", "t4")
    agent.resume("t4", [{"todo_index": 0, "action": "approve"}])
    assert agent.resume("t4", [{"todo_index": 0, "action": "approve"}])["error"] == "no_pending"
    assert count(env) == 1


def test_5_save_is_idempotent(env):
    t = TODOS[0].model_copy(update={"source_id": "in-x"})
    assert save_todos([t]) == 1 and save_todos([t]) == 0 and count(env) == 1


def test_6_blank_input(env):
    r = agent.run("  \n\t ", "t6")
    assert r["tool_calls"] == [] and r["answer"] == agent.USAGE_TEXT


def test_7a_bedrock_down_saves_nothing(env, monkeypatch):
    sleeps, attempts = [], []
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)

    def down(state):
        def fail():
            attempts.append(1)
            raise TimeoutError("bedrock down")
        return llm.call_bedrock(fail)

    monkeypatch.setattr(agent, "guard", down)
    r = agent.run("입력", "t7a")
    assert "llm_unavailable" in r["warnings"] and count(env) == 0
    assert sleeps == [1, 2, 4] and len(attempts) == 4


def test_7b_time_budget_exceeded(env, monkeypatch):
    monkeypatch.setattr(agent, "start_budget", lambda: llm.start_budget(-1))  # 이미 150초가 지난 상태
    monkeypatch.setattr(agent, "guard", lambda s: llm.call_bedrock(lambda: {"route": "extract"}))
    r = agent.run("입력", "t7b")
    assert "llm_unavailable" in r["warnings"] and count(env) == 0
