"""마감일 계산 (강사 피드백 반영: LLM은 원문 표현만 뽑고, 날짜 계산은 여기서 한다).

하루로 특정되는 표현만 YYYY-MM-DD로 바꾸고, 기간·불명확 표현('다음 주 중', '조만간', '이번 달 안')은 빈 값.
기준 날짜는 시스템 시계가 아니라 원문의 Date 헤더·메신저 타임스탬프, 없으면 conversation_date.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

WEEKDAYS = "월화수목금토일"  # date.weekday(): 월=0


_DATE_MARKS = [
    # 메일 헤더(Date:, date:, Date :, Sent:, 보낸 날짜:)와 메신저 줄 타임스탬프 [2026-11-24 09:12]
    re.compile(r"^\s*(?:(?:Date|Sent|보낸\s*날짜)\s*:\s*|\[)(\d{4})-(\d{1,2})-(\d{1,2})", re.M | re.I),
    # 메신저 내보내기의 날짜 구분선 '----- 2026년 11월 25일 수요일 -----'
    re.compile(r"^[-=─\s]*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", re.M),
]


def _date_marks(text: str) -> list[tuple[int, str]]:
    """원문 속 날짜 표시를 (위치, YYYY-MM-DD) 목록으로, 앞에서부터."""
    marks = []
    for p in _DATE_MARKS:
        for m in p.finditer(text):
            try:
                marks.append((m.start(), date(*map(int, m.groups())).isoformat()))
            except ValueError:  # [2026-13-45] 같은 깨진 날짜는 건너뜀
                pass
    return sorted(marks)


def find_anchor(text: str, conversation_date: str | None = None) -> str:
    """원문의 첫 날짜 표시(메일 Date 헤더·메신저 타임스탬프·날짜 구분선)를 기준 날짜로.
    없으면 conversation_date, 그것도 없으면 ''."""
    marks = _date_marks(text)
    return marks[0][1] if marks else (conversation_date or "")


def anchor_for(excerpt: str, text: str, fallback: str = "") -> str:
    """할 일 하나의 기준 날짜. 여러 날에 걸친 대화에서는 그 요청이 나온 날이어야 한다.
    1) 발췌 줄에 날짜가 있으면 그것 2) 없으면 원문에서 발췌 위치를 찾아 그 앞의 마지막 날짜 표시 3) 그래도 없으면 fallback."""
    own = _date_marks(excerpt)
    if own:
        return own[0][1]
    for line in sorted((l.strip() for l in excerpt.splitlines()), key=len, reverse=True):
        pos = text.find(line) if line else -1
        if pos >= 0:
            before = [d for p, d in _date_marks(text) if p <= pos]
            return before[-1] if before else fallback
    return fallback


_EN_DAYS = {"monday": "월", "tuesday": "화", "wednesday": "수", "thursday": "목", "friday": "금", "saturday": "토", "sunday": "일"}
_EN = [(r"day after tomorrow", "모레"), (r"tomorrow", "내일"), (r"\b(?:today|tonight|eod|end of (?:the )?day)\b", "오늘"),
       (r"\blast\b", "지난"), (r"\bnext week\b", "다음주"), (r"\bthis week\b", "이번주"),
       (r"\b(?:this )?(" + "|".join(_EN_DAYS) + r")\b", lambda m: _EN_DAYS[m.group(1)] + "요일"),
       (r"\bnext (?=[월화수목금토일]요일)", "다음주")]  # 요일을 먼저 바꾼 뒤 'next 금요일' → '다음주 금요일'


def _from_english(expr: str) -> str:
    """'by next Friday' → 'by 다음주 금요일'. 영어 메일의 마감 표현을 한국어 규칙에 태운다."""
    expr = expr.lower()
    for pattern, repl in _EN:
        expr = re.sub(pattern, repl, expr)
    return expr


def resolve_due_date(expression: str, anchor: str) -> str:
    """'다음 주 수요일까지' + '2026-11-20' → '2026-11-25'. 특정할 수 없으면 ''."""
    expr = _from_english(expression or "").replace(" ", "")
    if not expr or re.search(r"지난|저번", expr):
        return ""

    m = re.search(r"(\d{4})[-./년](\d{1,2})[-./월](\d{1,2})", expr)
    if m:
        return date(*map(int, m.groups())).isoformat()
    if not anchor:
        return ""
    base = date.fromisoformat(anchor[:10])

    m = re.search(r"(?<!\d)(\d{1,2})(?:월|/|\.)(\d{1,2})(?!\d)", expr)  # 11월27일 · 11/27 · 11.27
    if m:
        try:
            d = date(base.year, int(m.group(1)), int(m.group(2)))
        except ValueError:  # '13/40' 같은 날짜 아닌 숫자
            return ""
        if d < base - timedelta(days=180):  # 12월에 받은 '1월 5일'은 내년
            d = date(base.year + 1, d.month, d.day)
        return d.isoformat()

    for word, days in (("모레", 2), ("내일", 1), ("명일", 1), ("오늘", 0), ("금일", 0)):
        if word in expr:
            return (base + timedelta(days=days)).isoformat()

    m = re.search(r"(\d+)일(?:후|뒤|내)", expr)
    if m:
        return (base + timedelta(days=int(m.group(1)))).isoformat()

    m = re.search(r"(다다음주|다음주|차주|이번주|금주)?([월화수목금토일])요일", expr)
    if m:
        target = WEEKDAYS.index(m.group(2))
        week = {"다다음주": 2, "다음주": 1, "차주": 1}.get(m.group(1), 0)
        if m.group(1) is None and target < base.weekday():
            week = 1  # 그냥 '금요일'인데 이번 주 금요일이 지났으면 다음 주
        monday = base - timedelta(days=base.weekday())
        return (monday + timedelta(weeks=week, days=target)).isoformat()

    return ""  # '다음 주 중', '조만간', '이번 달 말' 등 기간·불명확 표현
