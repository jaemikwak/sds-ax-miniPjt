"""에이전트 수동 확인: python scripts/try_agent.py S01 PR03 "오늘 점심 메뉴 추천해줘" ...
샘플 ID면 data/samples/<ID>_*.txt를 읽는다. 임시 DB(data/try.sqlite)에 저장하고 모두 자동 승인한다."""
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["OPSMATE_DB"] = str(ROOT / "data" / "try.sqlite")
from src.agent import resume, run  # noqa: E402


def show(r: dict) -> None:
    print("  answer  :", r["answer"].replace("\n", "\n            "))
    print("  warnings:", r["warnings"], "| steps:", r.get("steps"))
    for c in r["tool_calls"]:
        print(f"  tool    : {c['name']} → {c.get('result_summary', '')}")
    for i, t in enumerate(r["extracted_todos"]):
        print(f"  todo[{i}] : {t['content']} | 요청자 {t['requester']} | 마감 {t['due_date'] or '-'} ({t['due_expression'] or '-'})"
              f" | 문의형 {t['is_inquiry']} | 근거 {t.get('evidence_doc_ids')} | 템플릿 {t.get('template_id')}")
        for k in ("guide_method", "answer_draft", "pr_comment_summary"):
            if t.get(k):
                print(f"            {k}: {t[k][:300]!r}")


for arg in sys.argv[1:]:
    files = list((ROOT / "data" / "samples").glob(f"{arg}_*.txt"))
    text = files[0].read_text(encoding="utf-8") if files else arg
    tid = f"try-{arg[:10]}-{uuid.uuid4().hex[:6]}"
    t0 = time.time()
    r = run(text, tid)
    print(f"\n=== {arg}  ({time.time() - t0:.0f}s)")
    show(r)
    if r.get("pending"):
        r2 = resume(tid, [{"todo_index": i, "action": "approve"} for i in range(len(r["extracted_todos"]))])
        print("  [승인 후]", r2["answer"], "| tools:", [c["name"] for c in r2["tool_calls"]])
