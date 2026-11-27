from pathlib import Path

from src.agent import mask_pii

S12 = (Path(__file__).resolve().parents[1] / "data" / "samples" / "S12_email_pii_approval.txt").read_text(encoding="utf-8")


def test_s12_pii_masked_but_dates_and_doc_numbers_kept():
    masked, hit = mask_pii(S12)
    assert hit
    for raw in ("010-2345-6789", "yujin.choi@example.com", "901015-2345678"):
        assert raw not in masked
    assert "AP-2026-11-0457" in masked and "2026-11-24" in masked
    assert "최유진" in masked  # 이름은 마스킹하지 않음


def test_account_and_card():
    assert mask_pii("계좌 110-123-456789로")[0] == "계좌 [계좌번호]로"
    assert mask_pii("카드 1234-5678-9012-3456")[0] == "카드 [카드번호]"
    assert mask_pii("기한 2026-11-25 18:00")[1] is False
