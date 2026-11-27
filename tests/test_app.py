"""운영자 화면 (AC7). agent는 목: 추출 결과 표시 → 1건 승인 저장 → 완료 체크 → 앱을 다시 열어도 완료 유지."""
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import src.agent as agent
from src.tools import Todo, save_todos

APP = str(Path(__file__).resolve().parents[1] / "src" / "app.py")
S01 = (Path(__file__).resolve().parents[1] / "data" / "samples" / "S01_messenger_firewall_devssl.txt").read_text(encoding="utf-8")
TODOS = [
    {"content": "원큐 개발서버 방화벽 신청 방법 안내", "requester": "이서준", "due_date": "", "due_expression": "",
     "source_excerpt": "[2026-11-24 09:13] 이서준: 방화벽 신청하려면?", "is_inquiry": True, "kind": "general", "source_id": "in-1",
     "guide_method": "ITSM 포털에서 방화벽 오픈 신청 (G01)", "evidence_doc_ids": ["G01"], "answer_draft": "이서준 책임님, ITSM에서 신청해 주세요.",
     "template_id": None, "pr_comment_summary": None, "dims_interface_id": None, "status": "미완료"},
    {"content": "개발서버 SSL 인증서 만료 확인", "requester": "이서준", "due_date": "2026-11-25", "due_expression": "내일까지",
     "source_excerpt": "[2026-11-24 09:16] 이서준: 내일까지", "is_inquiry": False, "kind": "general", "source_id": "in-1",
     "guide_method": "PKI 포털 재발급 후 IIS 바인딩 교체 (G04)", "evidence_doc_ids": ["G04"], "answer_draft": None,
     "template_id": None, "pr_comment_summary": None, "dims_interface_id": None, "status": "미완료"},
]


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "todos.sqlite"
    monkeypatch.setenv("OPSMATE_DB", str(path))
    monkeypatch.setattr(agent, "run", lambda text, tid, d=None: {
        "answer": "할 일 2건", "extracted_todos": TODOS, "tool_calls": [], "warnings": [], "pending": True})

    def fake_resume(tid, decisions):
        approved = [Todo(**TODOS[d["todo_index"]]) for d in decisions if d["action"] != "reject"]
        save_todos(approved)
        return {"answer": f"{len(approved)}건을 새로 저장했습니다.", "extracted_todos": [], "tool_calls": [], "warnings": []}

    monkeypatch.setattr(agent, "resume", fake_resume)
    return path


def test_rerun_does_not_keep_previous_review_values(db, monkeypatch):
    """승인 대기 화면이 떠 있는 채로 다른 글을 다시 실행하면, 새 결과 칸에 이전 결과 값이 남지 않아야 한다."""
    monkeypatch.setattr(agent, "run", lambda text, tid, d=None: {
        "answer": "", "extracted_todos": [TODOS[1] | {"content": f"할일-{text}", "requester": f"요청자-{text}"}],
        "tool_calls": [], "warnings": [], "pending": True})
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_area(key="input").input("A")
    at.button(key="run").click().run()
    at.text_area(key="input").input("B")
    at.button(key="run").click().run()
    assert at.text_input(key="content-0").value == "할일-B" and at.text_input(key="req-0").value == "요청자-B"
    assert not at.button(key="run").disabled  # 끝나면 실행 버튼이 다시 풀린다


def test_operator_flow(db):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_area(key="input").input(S01)
    at.button(key="run").click().run()
    page = " ".join(m.value for m in at.markdown)
    assert at.text_input(key="req-0").value == "이서준" and at.date_input(key="due-1").value == date(2026, 11, 25)
    assert at.date_input(key="due-0").value == date.today()  # 마감 없는 할 일은 오늘 날짜로 채움
    assert "ITSM 포털" in page and "confluence.example.com" in page
    assert "ITSM에서 신청" in at.text_area(key="draft-0").value

    at.radio(key="act-1").set_value("거절")
    at.button(key="decide").click().run()
    boxes = at.checkbox
    assert len(boxes) == 1 and "방화벽 신청 방법 안내" in boxes[0].label
    assert "거절 1건" in at.success[0].value and at.text_area(key="input").value == ""  # 결과 안내 + 입력칸 비움
    # 저장 뒤에도 상세 보기에서 답변 초안(복사용 코드 블록)과 처리 방법을 다시 볼 수 있다
    assert any("ITSM에서 신청" in c.value for c in at.code)
    assert "ITSM 포털" in " ".join(m.value for m in at.markdown)

    boxes[0].check().run()
    reopened = AppTest.from_file(APP, default_timeout=30).run()  # 같은 SQLite로 앱을 새로 연다
    assert len(reopened.checkbox) == 0                            # 완료한 할 일은 할 일 보기에서 숨김
    reopened.segmented_control(key="view").set_value("done").run()  # '완료'를 고르면 완료한 것만
    assert len(reopened.checkbox) == 1 and reopened.checkbox[0].value is True
