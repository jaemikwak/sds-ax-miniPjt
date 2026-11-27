from src.agent import KEEP_NAMES
from src.dates import find_anchor
from src.names import apply, pseudonymize

MAIL = """Sender : 김가람<[이메일]>
date:2026-11-23 13:13(GMT+9)
Title: 연계 사용 유무 확인 요청
안녕하세요? EAI 김가람입니다. 정하늘 선임님, 확인 부탁드립니다. 가람님께도 공유했어요.
담당자님 확인 후 박나래 책임에게 회신해 주세요."""

MESSENGER = """[사내 메신저] 이서준 책임(개발1팀) ↔ 정하늘 선임(시스템운영팀)
[2026-11-24 09:12] 이서준: 하늘님 안녕하세요~
오태양 (taeyang-oh) wants to merge"""


def test_mail_names_masked_and_restored():
    masked, mapping = pseudonymize(MAIL, KEEP_NAMES)
    assert "김가람" not in masked and "박나래" not in masked and "가람님" not in masked
    assert "정하늘" in masked and "담당자님" in masked  # 내 이름·일반 호칭은 유지
    assert set(mapping.values()) == {"김가람", "박나래"}
    assert apply(masked, mapping).replace("김가람님", "가람님") == MAIL


def test_messenger_and_github_names():
    masked, mapping = pseudonymize(MESSENGER, KEEP_NAMES)
    assert set(mapping.values()) == {"이서준", "오태양"}
    assert "[2026-11-24 09:12] [사람" in masked


def test_apply_both_directions_on_nested():
    mapping = {"[사람1]": "김가람"}
    todo = {"requester": "[사람1]", "evidence": ["[사람1]님 답장"], "n": 1}
    real = apply(todo, mapping)
    assert real == {"requester": "김가람", "evidence": ["김가람님 답장"], "n": 1}
    assert apply(real, mapping, restore=False) == todo


def test_no_names_no_mapping():
    assert pseudonymize("이번 주 마감인 미완료 할 일 보여줘", KEEP_NAMES) == ("이번 주 마감인 미완료 할 일 보여줘", {})


def test_find_anchor_header_variants():
    assert find_anchor(MAIL) == "2026-11-23"
    assert find_anchor("Date : 2026-11-24 00:06(GMT+9)") == "2026-11-24"
    assert find_anchor("보낸 날짜: 2026-11-20 오후 3:00") == "2026-11-20"
    assert find_anchor("[긴급] 점검 요청", "2026-11-26") == "2026-11-26"
