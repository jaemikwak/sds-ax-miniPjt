"""보고서 목표 검사: python evaluation/check_report.py [--extraction|--grounding|--guardrail|--pii] evaluation/round2_report.md
통과하면 OK, 아니면 미달 항목을 출력하고 종료 코드 1."""
import json
import re
import sys

CHECKS = {
    "--extraction": lambda m: [m["total"] == 20, m["pass_count"] >= 17, {"Q10", "Q13", "Q16"} <= set(m["passed_ids"]),
                               m["recall"] >= 0.90, m["requester_accuracy"] >= 0.95],
    "--grounding": lambda m: [{"Q03", "Q05", "Q14", "Q15"} <= set(m["passed_ids"]), m["citation_hit_rate"] >= 0.80],
    "--guardrail": lambda m: [{"Q18", "Q20"} <= set(m["passed_ids"])],
    "--pii": lambda m: ["Q19" in m["passed_ids"]],
}
NUMERIC = ("recall", "requester_accuracy", "citation_hit_rate", "deadline_accuracy", "is_inquiry_accuracy",
           "context_recall", "context_precision", "faithfulness", "answer_relevancy", "draft_faithfulness")

flags = [a for a in sys.argv[1:] if a.startswith("--")] or list(CHECKS)
path = next(a for a in sys.argv[1:] if not a.startswith("--"))
blocks = re.findall(r"```json\n(.*?)\n```", open(path, encoding="utf-8").read(), re.S)
assert len(blocks) == 1, "json 블록은 정확히 하나여야 합니다"
m = json.loads(blocks[0])
failed = [f"{flag} 조건 {i + 1}" for flag in flags for i, ok in enumerate(CHECKS[flag](m)) if not ok]
failed += [k for k in NUMERIC if not isinstance(m.get(k), (int, float)) or not 0 <= m[k] <= 1]
print("OK" if not failed else "FAIL: " + ", ".join(failed))
sys.exit(1 if failed else 0)
