"""가이드 검색 수동 확인: python scripts/try_search.py "질의" ..."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.retriever import get_retriever  # noqa: E402

QUERIES = sys.argv[1:] or [
    "DIMS IF-ONEQ-ERP-002 인터페이스 실패 ORA-00001 확인",   # Q05 → G18, G20
    "재택근무용 VPN 계정 신청 방법",                          # Q14 → 근거 없음
    "원큐 시스템 접속하려면 방화벽 신청 어떻게 해요",          # Q01 → G01
    "퇴사자 명의 방화벽 정책 해제 대리 신청",                  # Q13 → G02 (G01 아님)
    "CORP 계정으로 로그인하면 승인대기중 화면이 나와요",        # Q03 → G21
]

r = get_retriever()
for q in QUERIES:
    t = time.time()
    res = r.search(q)
    top = ", ".join(f"{h.doc_id}({h.score:.2f})" for h in res.hits)
    flag = "근거 없음" if res.no_evidence else "OK"
    print(f"\n[{flag}] {q}  ({time.time() - t:.1f}s{', 재검색' if res.researched else ''})")
    print(f"  질의: {' → '.join(res.queries)}")
    print(f"  상위: {top}")
