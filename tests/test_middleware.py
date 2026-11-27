"""미들웨어 테스트 (Bedrock은 목). ① 긴 입력 요약 ② 짧은 입력은 요약 안 함 ③ 재시도 1·2·4초 ④ 마감일 규칙."""
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.agent as agent
import src.llm as llm
from src.dates import anchor_for, find_anchor, resolve_due_date

S08 = (Path(__file__).resolve().parents[1] / "data" / "samples" / "S08_email_long_thread_fw_removal.txt").read_text(encoding="utf-8")


class FakeChat:
    def __init__(self, text):
        self.text, self.calls = text, 0

    def invoke(self, messages):
        self.calls += 1
        return SimpleNamespace(content=self.text)


def test_1_long_thread_summarized_keeping_date_requester_request(monkeypatch):
    fake = FakeChat("서하린 책임 요청: 퇴사자 박지훈 명의 방화벽 정책 해제 대리 신청을 이번 주 금요일까지 올려 주세요. " * 3)
    monkeypatch.setattr(agent, "chat", lambda: fake)
    masked, _ = agent.mask_pii(S08)
    assert agent.count_tokens(masked) > agent.SUMMARY_TRIGGER_TOKENS
    out = agent.summarize({"input": masked})["input"]
    assert fake.calls == 1 and agent.count_tokens(out) <= agent.SUMMARY_MAX_TOKENS
    for must in ("2026-11-24", "서하린", "이번 주 금요일", "해제"):  # Date 헤더는 코드가 그대로 보존
        assert must in out


def test_1b_summary_truncated_to_limit(monkeypatch):
    monkeypatch.setattr(agent, "chat", lambda: FakeChat("가나다라 " * 3000))
    out = agent.summarize({"input": agent.mask_pii(S08)[0]})["input"]
    assert agent.count_tokens(out) <= agent.SUMMARY_MAX_TOKENS + 5  # 디코드 경계 오차


def test_2_short_input_not_summarized(monkeypatch):
    fake = FakeChat("x")
    monkeypatch.setattr(agent, "chat", lambda: fake)
    assert agent.summarize({"input": "짧은 메신저 대화"}) == {} and fake.calls == 0


def test_3_retry_then_success(monkeypatch):
    sleeps, calls = [], []
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)
    llm.start_budget(1000)

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError
        return "ok"

    assert llm.call_bedrock(flaky) == "ok" and sleeps == [1, 2]


@pytest.mark.parametrize("expr, anchor, expected", [
    # seed 고정 케이스
    ("내일까지", "2026-11-24", "2026-11-25"),
    ("다음 주 중", "2026-11-25", ""),
    # 샘플 실제 표현 ↔ gold_labels.json
    ("다음 주 수요일까지", "2026-11-20", "2026-11-25"),   # S02 (금요일 메일)
    ("이번 주 금요일까지", "2026-11-24", "2026-11-27"),   # S08
    ("다음 주 화요일", "2026-11-24", "2026-12-01"),       # S10 (화요일에 받은 '다음 주 화요일')
    ("이번 주 목요일 밤", "2026-11-24", "2026-11-26"),    # S05
    ("오늘 오전 중", "2026-11-25", "2026-11-25"),         # S15
    ("오늘 밤", "2026-11-25", "2026-11-25"),              # S11
    ("2026-11-25 18:00", "2026-11-25", "2026-11-25"),     # S13 재처리 기한
    # 기타 규칙
    ("금요일까지", "2026-11-28", "2026-12-04"),           # 토요일에 받은 '금요일' → 다음 주
    ("12월 1일까지", "2026-11-24", "2026-12-01"),
    ("1월 5일", "2026-12-20", "2027-01-05"),
    ("회신 : 11/27(금) 11:00", "2026-11-26", "2026-11-27"),  # 메일 제목 슬래시 표기
    ("12.3까지", "2026-11-26", "2026-12-03"),
    ("13/40", "2026-11-26", ""),                         # 날짜 아닌 숫자
    # 영어 메일
    ("by tomorrow", "2026-11-24", "2026-11-25"),
    ("by EOD", "2026-11-24", "2026-11-24"),
    ("by the day after tomorrow", "2026-11-24", "2026-11-26"),
    ("by Friday", "2026-11-24", "2026-11-27"),
    ("by next Wednesday", "2026-11-20", "2026-11-25"),
    ("by 11/30", "2026-11-24", "2026-11-30"),
    ("sometime next week", "2026-11-24", ""),
    ("last Friday", "2026-11-24", ""),
    ("모레", "2026-11-30", "2026-12-02"),                 # 월말 넘김
    ("3일 내", "2026-11-24", "2026-11-27"),
    ("조만간", "2026-11-24", ""),
    ("이번 달 말까지", "2026-11-24", ""),
    ("시간 될 때", "2026-11-24", ""),
    ("지난주 금요일", "2026-11-23", ""),
    ("내일", "", ""),                                     # 기준 날짜 없으면 비움
    ("", "2026-11-24", ""),
])
def test_resolve_due_date(expr, anchor, expected):
    assert resolve_due_date(expr, anchor) == expected


def test_find_anchor():
    assert find_anchor("From: a\nDate: 2026-11-20 (금) 16:40\n본문") == "2026-11-20"
    assert find_anchor("[메신저]\n[2026-11-24 09:12] 이서준: 안녕하세요") == "2026-11-24"
    assert find_anchor("날짜 없는 붙여넣기", "2026-11-26") == "2026-11-26"
    assert find_anchor("날짜 없는 붙여넣기") == ""
    assert find_anchor("--- 2026년 11월 23일 월요일 ---\n[유하준] [오전 10:12] 안녕하세요") == "2026-11-23"
    assert find_anchor("[2026-13-45 09:00] 깨진 날짜", "2026-11-26") == "2026-11-26"


MULTI_DAY = """[2026-11-23 10:00] 유하준: 하늘님 계정 잠금 해제 내일까지 부탁드려요.
[2026-11-25 15:00] 유하준: 하늘님 SSL 교체 일정 모레까지 알려주세요.
--------------- 2026년 11월 26일 목요일 ---------------
[유하준] [오후 2:00] 작업계획서 내일까지 등록 부탁드려요."""


@pytest.mark.parametrize("excerpt, expected", [
    ("[2026-11-25 15:00] 유하준: 하늘님 SSL 교체 일정 모레까지 알려주세요.", "2026-11-25"),  # 발췌에 날짜 있음
    ("유하준: 하늘님 SSL 교체 일정 모레까지 알려주세요.", "2026-11-25"),     # 타임스탬프 없이 옮겨도 그 줄의 날짜
    ("[유하준] [오후 2:00] 작업계획서 내일까지 등록 부탁드려요.", "2026-11-26"),  # 날짜 구분선 아래 줄
    ("원문에 없는 요약 문장", "2026-11-30"),                                 # 못 찾으면 fallback
])
def test_anchor_for_multi_day(excerpt, expected):
    assert anchor_for(excerpt, MULTI_DAY, "2026-11-30") == expected
