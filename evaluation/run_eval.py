"""20문항 자체 평가 (패턴 12): python evaluation/run_eval.py --round 1 [--only 1,5,18]

문항마다 픽스처 SQLite를 새로 만들고 run() → (승인 대기면) 전부 자동 승인 resume() 후 채점한다.
- 기계 채점: 호출 도구 집합 == expected_tools, expected_traits의 'warnings에 X', PII 원문 미노출, 검색 문항 결과 ID
- Claude 판정(judge_prompt.txt, temperature 0): expected_traits 항목별 pass/fail, forbidden 항목별 위반 여부
- 문항 통과 = 기계 채점 + 판정 모두 통과
- 정답 라벨 지표(gold_labels.json): 재현율·요청자·마감일·문의형·인용 적중률 (정답 기준 1:1 매칭은 Claude)
- RAGAS 근사(라이브러리 미사용): context_recall·context_precision(샘플 단위 검색 상위 5),
  faithfulness·draft_faithfulness(주장 단위, Claude 판정), answer_relevancy(질문 3개 ↔ 할 일 Titan 코사인)
결과: evaluation/roundN_report.md (--only면 roundN_partial.md), 원자료 evaluation/roundN_results.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel  # noqa: E402

from src.agent import TRACE_DIR, resume, run  # noqa: E402
from src.llm import call_bedrock, chat, embeddings, start_budget  # noqa: E402
from src.retriever import get_retriever  # noqa: E402
from src.tools import load_fixture  # noqa: E402

EVAL = ROOT / "evaluation"
DBS = EVAL / "_eval_db"
GOLD = json.loads((EVAL / "gold_labels.json").read_text(encoding="utf-8"))
JUDGE_PROMPT = (EVAL / "judge_prompt.txt").read_text(encoding="utf-8")
PII = GOLD["samples"]["S12"]["_pii"]


def split(cell: str) -> list[str]:
    return [x.strip() for x in cell.split(";") if x.strip()]


# ---------- 실행 ----------
def execute(row: dict, rnd: int) -> dict:
    qid = int(row["id"])
    db = DBS / f"Q{qid:02d}.sqlite"
    load_fixture(db)
    os.environ["OPSMATE_DB"] = str(db)
    tid = f"eval-r{rnd}-Q{qid:02d}-{time.time_ns()}"
    t0 = time.time()
    r1 = run(row["input"], tid)
    out = r1
    if r1.get("pending"):
        r2 = resume(tid, [{"todo_index": i, "action": "approve"} for i in range(len(r1["extracted_todos"]))])
        out = r2 | {"extracted_todos": r1["extracted_todos"], "answer": f"{r1['answer']}\n{r2['answer']}",
                    "warnings": list(dict.fromkeys(r1["warnings"] + r2["warnings"])), "steps": r1["steps"],
                    "approved_by_evaluator": True}
    start_budget(10**9)  # 채점용 호출은 run() 150초 상한과 무관
    return out | {"seconds": round(time.time() - t0, 1)}


# ---------- 기계 채점 ----------
def searched_ids(out: dict) -> set[str]:
    for c in out["tool_calls"]:
        if c["name"] == "search_todos" and ": " in c.get("result_summary", ""):
            return set(c["result_summary"].split(": ", 1)[1].split(","))
    return set()


def mechanical(row: dict, out: dict) -> list[str]:
    fails = []
    called = {c["name"] for c in out["tool_calls"]}
    expected = set(split(row["expected_tools"]))
    if called != expected:
        fails.append(f"도구 {sorted(called)} ≠ 기대 {sorted(expected)}")
    for w in re.findall(r"warnings에 (\w+)", row["expected_traits"]):
        if w not in out["warnings"]:
            fails.append(f"warnings에 {w} 없음")
    if any(p in json.dumps(out, ensure_ascii=False) for p in PII):
        fails.append("PII 원문 노출")
    search_gold = GOLD["search"].get(f"Q{int(row['id']):02d}")
    if search_gold is not None and searched_ids(out) != set(search_gold["expected_todo_ids"]):
        fails.append(f"검색 결과 {sorted(searched_ids(out))} ≠ 기대 {search_gold['expected_todo_ids']}")
    return fails


# ---------- Claude 판정 ----------
class TraitVerdict(BaseModel):
    trait: str
    passed: bool
    reason: str


class ForbiddenVerdict(BaseModel):
    item: str
    violated: bool
    reason: str


class Judgement(BaseModel):
    traits: list[TraitVerdict]
    forbidden: list[ForbiddenVerdict]


def judge(row: dict, out: dict) -> Judgement:
    view = {k: out.get(k) for k in ("answer", "extracted_todos", "tool_calls", "warnings", "steps")}
    if out.get("approved_by_evaluator"):
        view["hitl"] = ("run()은 할 일을 추출한 뒤 승인 대기(interrupt)에서 멈췄고 이 시점 저장 0건이었다. "
                        "평가자가 모든 항목을 approve로 resume()한 뒤에 save_todos가 실행됐다.")
    msg = (f"<output>\n{json.dumps(view, ensure_ascii=False, indent=1)}\n</output>\n"
           f"<traits>{json.dumps(split(row['expected_traits']), ensure_ascii=False)}</traits>\n"
           # PII 원문 금지 항목은 기계 채점(mechanical)만: 판정 기록에 원문이 다시 적히지 않게
           f"<forbidden>{json.dumps([f for f in split(row['forbidden']) if f not in PII], ensure_ascii=False)}</forbidden>")
    return call_bedrock(chat().with_structured_output(Judgement).invoke, [("system", JUDGE_PROMPT), ("human", msg)])


# ---------- 정답 라벨 지표 ----------
class Pair(BaseModel):
    gid: str
    todo_index: Optional[int]  # 매칭되는 추출 항목이 없으면 null


class Matching(BaseModel):
    pairs: list[Pair]


def match(gold: list[dict], ext: list[dict]) -> dict[str, int | None]:
    if not ext:
        return {g["gid"]: None for g in gold}
    prompt = ("정답 할 일마다 같은 일을 가리키는 추출 항목을 하나씩 짝지어라(1:1, 한 추출 항목은 한 번만). 없으면 null.\n"
              f"<gold>{json.dumps([{k: g[k] for k in ('gid', 'content', 'requester')} for g in gold], ensure_ascii=False)}</gold>\n"
              f"<extracted>{json.dumps([{'todo_index': i, 'content': t['content'], 'requester': t['requester']} for i, t in enumerate(ext)], ensure_ascii=False)}</extracted>")
    pairs, used = {}, set()
    for p in call_bedrock(chat().with_structured_output(Matching).invoke, prompt).pairs:
        ok = p.todo_index is not None and 0 <= p.todo_index < len(ext) and p.todo_index not in used
        pairs[p.gid] = p.todo_index if ok else None
        used.add(p.todo_index)
    return {g["gid"]: pairs.get(g["gid"]) for g in gold}


def gold_metrics(sample: str, out: dict) -> dict:
    gold, ext = GOLD["samples"][sample]["todos"], out["extracted_todos"]
    m = {"gold": len(gold), "matched": 0, "requester_ok": 0, "deadline_ok": 0, "inquiry_ok": 0, "cite_total": 0, "cite_hit": 0}
    pairs = match(gold, ext) if gold else {}
    for g in gold:
        t = ext[pairs[g["gid"]]] if pairs[g["gid"]] is not None else None
        m["matched"] += t is not None
        m["requester_ok"] += bool(t and g["requester"] in t["requester"])
        m["deadline_ok"] += bool(t and t["due_date"] == g["deadline"])
        m["inquiry_ok"] += bool(t and t["is_inquiry"] == g["is_inquiry"])
        if g["gold_docs"]:
            m["cite_total"] += 1
            m["cite_hit"] += bool(t and set(t.get("evidence_doc_ids") or []) & set(g["gold_docs"]))
    return m


# ---------- RAGAS 근사 ----------
class Claim(BaseModel):
    text: str
    in_draft: bool
    supported: bool


class Grounding(BaseModel):
    claims: list[Claim]
    questions: list[str]


def retrieved_top5(out: dict) -> list[str]:
    ids: list[str] = []
    for c in out["tool_calls"]:
        if c["name"] == "search_guides":
            ids += [d for d in re.findall(r"\b(G\d{2})\(", c.get("result_summary", "")) if d not in ids]
    return ids[:5]


def context_scores(sample: str, out: dict) -> dict | None:
    gt = set(GOLD["samples"][sample]["ground_truth_contexts"])
    if not gt:
        return None
    top = retrieved_top5(out)
    rel = [d in gt for d in top]
    precisions = [sum(rel[:k + 1]) / (k + 1) for k, r in enumerate(rel) if r]
    return {"context_recall": len(gt & set(top)) / len(gt),
            "context_precision": sum(precisions) / len(precisions) if precisions else 0.0}


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def answer_scores(todo: dict) -> dict | None:
    docs = get_retriever().docs
    if not todo.get("evidence_doc_ids") or not docs:
        return None
    context = "\n".join(f'<document id="{d}">{docs[d].text}</document>' for d in todo["evidence_doc_ids"] if d in docs)
    answer = f"[처리 방법]\n{todo.get('guide_method') or ''}\n[답변 초안]\n{todo.get('answer_draft') or ''}"
    prompt = ("<answer>를 사실 주장 문장 단위로 나누고, 각 주장이 <context> 문서로 뒷받침되면 supported=true. "
              "[답변 초안]에서 나온 주장은 in_draft=true. 인사말·맺음말은 주장이 아니다. "
              "그리고 이 답변이 답하고 있는 질문을 한국어로 3개 만들어라.\n"
              f"<context>{context}</context>\n<answer>{answer}</answer>")
    g = call_bedrock(chat().with_structured_output(Grounding).invoke, prompt)
    draft = [c for c in g.claims if c.in_draft]
    vecs = call_bedrock(embeddings().embed_documents, [todo["content"], *g.questions[:3]])
    return {"faithfulness": sum(c.supported for c in g.claims) / len(g.claims) if g.claims else None,
            "draft_faithfulness": sum(c.supported for c in draft) / len(draft) if draft else None,
            "answer_relevancy": sum(cosine(vecs[0], v) for v in vecs[1:]) / max(len(vecs) - 1, 1)}


def mean(xs: list) -> float:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else 0.0


# ---------- 보고서 ----------
def write_report(path: Path, rnd: int, rows: list[dict], results: dict, elapsed: float) -> dict:
    g = {k: sum(r["gold"].get(k, 0) for r in results.values() if r.get("gold")) for k in
         ("gold", "matched", "requester_ok", "deadline_ok", "inquiry_ok", "cite_total", "cite_hit")}
    passed = [f"Q{int(r['id']):02d}" for r in rows if results[r["id"]]["passed"]]
    ctx = [r["context"] for r in results.values() if r.get("context")]
    ans = [a for r in results.values() for a in r.get("answer_scores", []) if a]
    metrics = {
        "round": rnd, "pass_count": len(passed), "total": len(rows), "passed_ids": passed,
        "failed_ids": [f"Q{int(r['id']):02d}" for r in rows if not results[r["id"]]["passed"]],
        "guardrail_pass": sum(results[r["id"]]["passed"] for r in rows if r["category"] == "guardrail"),
        "recall": round(g["matched"] / g["gold"], 3) if g["gold"] else 0.0,
        "requester_accuracy": round(g["requester_ok"] / g["gold"], 3) if g["gold"] else 0.0,
        "citation_hit_rate": round(g["cite_hit"] / g["cite_total"], 3) if g["cite_total"] else 0.0,
        "deadline_accuracy": round(g["deadline_ok"] / g["gold"], 3) if g["gold"] else 0.0,
        "is_inquiry_accuracy": round(g["inquiry_ok"] / g["gold"], 3) if g["gold"] else 0.0,
        "context_recall": mean([c["context_recall"] for c in ctx]),
        "context_precision": mean([c["context_precision"] for c in ctx]),
        "faithfulness": mean([a["faithfulness"] for a in ans]),
        "answer_relevancy": mean([a["answer_relevancy"] for a in ans]),
        "draft_faithfulness": mean([a["draft_faithfulness"] for a in ans]),
        "judge_reasons": {f"Q{int(k):02d}": [f"{'O' if t['passed'] else 'X'} {t['trait']} — {t['reason']}" for t in v["judge"]["traits"]]
                          + [f"{'금지위반' if f['violated'] else '금지준수'} {f['item']} — {f['reason']}" for f in v["judge"]["forbidden"]]
                          for k, v in results.items() if v.get("judge")},
    }
    lines = [f"# Round {rnd} 자체 평가 보고서", "",
             f"- 실행: {datetime.now():%Y-%m-%d %H:%M} · 소요 {elapsed / 60:.1f}분 · 모델 us.anthropic.claude-sonnet-4-6 / amazon.titan-embed-text-v2:0",
             f"- **통과 {metrics['pass_count']}/{metrics['total']}** · guardrail {metrics['guardrail_pass']}/3",
             "- 문항 통과 = 기계 채점(도구·경고·PII·검색 결과) + Claude 판정(expected_traits 전부 통과, forbidden 위반 없음)", "",
             "| 문항 | 분류 | 결과 | 시간(초) | 실패 원인 |", "|---|---|---|---|---|"]
    for r in rows:
        v = results[r["id"]]
        why = v["mechanical"] + [f"판정 X: {t['trait']}" for t in v.get("judge", {}).get("traits", []) if not t["passed"]] \
            + [f"금지 위반: {f['item']}" for f in v.get("judge", {}).get("forbidden", []) if f["violated"]]
        lines.append(f"| Q{int(r['id']):02d} | {r['category']} | {'✅' if v['passed'] else '❌'} | {v['out'].get('seconds', '')} | "
                     f"{'<br>'.join(w.replace('|', '/') for w in why) or '-'} |")
    lines += ["", "## 지표", "", "| 지표 | 값 | 목표 |", "|---|---|---|",
              f"| 할 일 재현율 | {metrics['recall']} | ≥ 0.90 |", f"| 요청자 정확도 | {metrics['requester_accuracy']} | ≥ 0.95 |",
              f"| 인용 적중률 | {metrics['citation_hit_rate']} | ≥ 0.80 |", f"| 마감일 정확도 | {metrics['deadline_accuracy']} | 측정 |",
              f"| 문의형 판정 정확도 | {metrics['is_inquiry_accuracy']} | 측정 |",
              f"| context_recall (근사) | {metrics['context_recall']} | 측정 |", f"| context_precision (근사) | {metrics['context_precision']} | 측정 |",
              f"| faithfulness (근사) | {metrics['faithfulness']} | 측정 |", f"| answer_relevancy (근사) | {metrics['answer_relevancy']} | 측정 |",
              f"| draft_faithfulness (근사) | {metrics['draft_faithfulness']} | 측정 |", "",
              "> RAGAS 지표는 ragas 라이브러리 없이 같은 정의로 직접 계산한 근사치(판정 LLM: Claude Sonnet 4.6, 임베딩: Titan v2). "
              "context_*는 샘플 단위 검색 상위 5개 기준.", "",
              "## 기계 판독용", "", "```json", json.dumps(metrics, ensure_ascii=False, indent=1), "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--only", help="문항 id 목록(예: 1,5,18). 지정하면 roundN_partial.md에 쓴다")
    args = ap.parse_args()
    rows = list(csv.DictReader(open(EVAL / "test_queries.csv", encoding="utf-8-sig")))
    if args.only:
        rows = [r for r in rows if r["id"] in args.only.split(",")]
    shutil.rmtree(TRACE_DIR, ignore_errors=True)
    shutil.rmtree(DBS, ignore_errors=True)
    DBS.mkdir(parents=True)
    get_retriever().build()
    t0, results = time.time(), {}
    for row in rows:
        out = execute(row, args.round)
        res = {"out": out, "mechanical": mechanical(row, out)}
        res["judge"] = judge(row, out).model_dump()
        sample = (re.search(r"sample=(\w+)", row["note"]) or [None, None])[1]
        if sample:
            res["gold"] = gold_metrics(sample, out)
            res["context"] = context_scores(sample, out)
            res["answer_scores"] = [answer_scores(t) for t in out["extracted_todos"]]
        res["passed"] = (not res["mechanical"] and all(t["passed"] for t in res["judge"]["traits"])
                         and not any(f["violated"] for f in res["judge"]["forbidden"]))
        results[row["id"]] = res
        print(f"Q{int(row['id']):02d} {'PASS' if res['passed'] else 'FAIL'} ({out['seconds']}s) {res['mechanical']}", flush=True)
    name = f"round{args.round}_partial.md" if args.only else f"round{args.round}_report.md"
    metrics = write_report(EVAL / name, args.round, rows, results, time.time() - t0)
    (EVAL / f"round{args.round}_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{metrics['pass_count']}/{metrics['total']} 통과 · guardrail {metrics['guardrail_pass']} → evaluation/{name}")


if __name__ == "__main__":
    main()
