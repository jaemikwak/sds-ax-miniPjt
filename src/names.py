"""사람 이름 가명 처리: Bedrock·LangSmith로 가기 전에 '문채원' → '[사람1]', 화면·DB에 쓰기 직전에 되돌린다.

이름 사전이 없으니 이름이 드러나는 자리(메일 헤더, 메신저 화자, 직급·호칭 앞, 'EAI 홍길동입니다', 'GitHub 이름 (id)')에서
세 글자 한글 이름만 찾고, 찾은 이름은 본문 전체에서 바꾼다. '나'의 이름은 '나'를 찾는 데 필요해서 남긴다.
shortcut: 두·네 글자 이름과 이름만 단독으로 나오는 경우는 놓침, 놓친 사례가 나오면 사내 인사 목록 대조로 교체.
"""
from __future__ import annotations

import re

_NAME = r"(?<![가-힣])([가-힣]{3})"
_TITLES = r"(?:님|씨|선임|책임|수석|프로|매니저|사원|대리|과장|차장|부장|팀장|파트장|그룹장|상무|전무|위원)"
_HEADER = re.compile(r"^\s*(?:From|To|Cc|Sender|보낸\s*사람|받는\s*사람|참조)\s*:(.*)$", re.I | re.M)
_HEADER_NAME = re.compile(rf"{_NAME}\s*(?:<|\(|;|,|$)")
_SPOTS = [
    re.compile(rf"^\[[^\]]*\d{{2}}:\d{{2}}[^\]]*\]\s*{_NAME}\s*:", re.M),   # [2026-11-24 09:12] 이서준:
    re.compile(rf"{_NAME}\s?{_TITLES}"),                                  # 이서준 책임, 배수현님
    re.compile(rf"(?:[A-Za-z]+|[가-힣]+팀)\s+{_NAME}입니다"),              # EAI 배수현입니다
    re.compile(rf"{_NAME}\s*\([a-z][\w.-]*\)"),                            # 오태양 (taeyang-oh)
]
# 이름 자리에 오지만 이름이 아닌 세 글자: 담당자·관리자, 김부장(성+직급), 팀 이름
_NOT_NAMES = re.compile(r"(?:자|팀|부장|과장|차장|팀장|대리|사원|선임|책임|수석|프로)$|^(?:고객|여러분)")


def find_names(text: str, keep: set[str]) -> list[str]:
    found = [m.group(1) for line in _HEADER.findall(text) for m in _HEADER_NAME.finditer(line)]
    found += [m.group(1) for spot in _SPOTS for m in spot.finditer(text)]
    return [n for n in dict.fromkeys(found) if n not in keep and not _NOT_NAMES.search(n)]


def pseudonymize(text: str, keep: set[str]) -> tuple[str, dict[str, str]]:
    """(가명 텍스트, {'[사람1]': '문채원'}). '서준님'처럼 이름만 부른 호칭도 같은 가명으로 바꾼다."""
    mapping: dict[str, str] = {}
    for i, name in enumerate(find_names(text, keep), 1):
        token = f"[사람{i}]"
        mapping[token] = name
        text = text.replace(name, token)
        text = re.sub(rf"{name[1:]}(?=님|씨)", token, text)
    return text, mapping


def apply(obj, mapping: dict[str, str], restore: bool = True):
    """문자열·리스트·dict 안의 가명을 실명으로(restore=False면 실명을 가명으로) 바꾼다."""
    if not mapping:
        return obj
    if isinstance(obj, str):
        for token, name in mapping.items():
            obj = obj.replace(token, name) if restore else obj.replace(name, token)
        return obj
    if isinstance(obj, list):
        return [apply(v, mapping, restore) for v in obj]
    if isinstance(obj, dict):
        return {k: apply(v, mapping, restore) for k, v in obj.items()}
    return obj
