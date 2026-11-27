"""PII 잔존 검사: python evaluation/check_pii.py → OK
S12의 전화번호·이메일·주민번호 원문이 트레이스·평가/시연 SQLite·Chroma·평가 원자료 어디에도 없어야 한다. 트레이스가 비면 실패."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PII = json.loads((ROOT / "evaluation" / "gold_labels.json").read_text(encoding="utf-8"))["samples"]["S12"]["_pii"]

traces = list((ROOT / "evaluation" / "traces").glob("*.json"))
if not traces:
    sys.exit(print("FAIL: evaluation/traces/ 가 비어 있습니다(평가를 먼저 실행)") or 1)
files = traces + list((ROOT / "evaluation" / "_eval_db").glob("*.sqlite")) + list((ROOT / "data").glob("*.sqlite")) \
    + [p for p in (ROOT / "chroma_db").rglob("*") if p.is_file()] + list((ROOT / "evaluation").glob("round*_results.json"))
leaks = [f"{p.relative_to(ROOT)}: {s}" for p in files for s in PII if s.encode() in p.read_bytes()]
print("OK" if not leaks else "FAIL:\n" + "\n".join(leaks))
sys.exit(1 if leaks else 0)
