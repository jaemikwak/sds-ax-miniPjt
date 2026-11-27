"""Bedrock 없이 확인 가능한 부분: 가이드 로딩, RRF, BM25 ID 정확 일치."""
from src.retriever import GuideRetriever, load_guides, rrf_merge


def test_load_guides_has_21_with_confluence():
    docs = load_guides()
    assert [d.doc_id for d in docs] == [f"G{i:02d}" for i in range(1, 22)]
    assert all(d.confluence_path.startswith("https://confluence.example.com/") for d in docs)


def test_rrf_prefers_docs_ranked_high_in_both():
    assert rrf_merge(["G18", "G20", "G01"], ["G20", "G01", "G18"])[0] == "G20"
    assert rrf_merge(["A"], [])[0] == "A"


def test_bm25_exact_interface_id():
    r = GuideRetriever()
    r.build_bm25()
    assert r._bm25_search("IF-ONEQ-ERP-002 실패")[0] == "G18"
    assert "G19" in r._bm25_search("IF-ONEQ-HR-001")[:2]
