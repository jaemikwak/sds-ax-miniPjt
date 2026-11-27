"""OpsMate Streamlit 화면: streamlit run src/app.py
화면은 표시만 하고 판단은 src/agent.run()/resume()이 한다. 완료 체크만 화면에서 직접 DB를 바꾼다."""
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from src import agent  # noqa: E402
from src.retriever import load_guides  # noqa: E402
from src.tools import list_todos, set_status  # noqa: E402

WARN = {
    "injection": "붙여넣은 내용 속 지시문(예: '이전 지시 무시', '승인 처리')은 따르지 않고 무시했어요.",
    "pii_masked": "전화번호·이메일·주민번호 등 개인정보를 가린 뒤 처리했어요.",
    "names_masked": "사람 이름은 [사람1]처럼 가명으로 바꿔 AI에 보냈고, 화면과 저장에는 실명으로 되돌렸어요.",
    "out_of_scope": "OpsMate가 도와드릴 수 있는 범위 밖의 요청이에요.",
    "llm_unavailable": "Bedrock 응답이 없어 처리하지 못했어요. 저장된 내용은 없어요.",
}
KIND = {"general": "📝 일반", "pr_review": "🔀 PR 리뷰", "dims": "🔌 DIMS 장애"}
TOOL_LABEL = {"extract_todos": "할 일 추출", "search_guides": "가이드 검색", "save_todos": "저장", "search_todos": "할 일 검색"}
CONFLUENCE = {g.doc_id: (g.title, g.confluence_path) for g in load_guides()}
SAMPLES = {p.stem: p for p in sorted((ROOT / "data" / "samples").glob("*.txt"))}

st.set_page_config(page_title="OpsMate", page_icon="🗂️", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 1.2rem; padding-left: 2rem; padding-right: 2rem; max-width: 100%;}
[data-testid="stHeader"] {height: 0; background: transparent;}
.badge {display:inline-block; padding:2px 10px; margin-right:6px; border-radius:999px; font-size:0.8rem;
        background:rgba(37,99,235,.12); color:#2563eb; font-weight:600;}
.badge.red {background:rgba(220,38,38,.12); color:#dc2626;}
.badge.amber {background:rgba(217,119,6,.14); color:#b45309;}
.badge.gray {background:rgba(100,116,139,.14); color:#475569;}
</style>""", unsafe_allow_html=True)
ss = st.session_state


def dday(due: str, today: date) -> tuple[str, str]:
    """('D-1', 'amber') 형태. 마감 없으면 ('마감 없음', 'gray')."""
    if not due:
        return "마감 없음", "gray"
    n = (date.fromisoformat(due) - today).days
    if n < 0:
        return f"D+{-n} 지남", "red"
    return ("D-DAY", "red") if n == 0 else (f"D-{n}", "amber" if n <= 2 else "")


def badges(*items: tuple[str, str]) -> str:
    return "".join(f'<span class="badge {c}">{t}</span>' for t, c in items)


def load_sample():
    if ss.sample != "(선택 안 함)":
        ss.input = SAMPLES[ss.sample].read_text(encoding="utf-8")


def start_run():
    ss.running = True
    # 이전 결과의 승인 칸 값이 같은 key로 새 결과에 남지 않게 지운다(남으면 새 할 일이 이전 내용으로 저장됨)
    for k in [k for k in ss if str(k).startswith(("act-", "content-", "req-", "due-", "draft-"))]:
        del ss[k]


if ss.pop("clear_input", False):  # 위젯이 그려지기 전에만 값을 바꿀 수 있어 저장 직후 다음 실행에서 비운다
    ss.input, ss.sample = "", "(선택 안 함)"

with st.sidebar:
    st.header("🗂️ OpsMate")
    st.caption("원큐 운영 담당자(정하늘 선임)의 할 일 비서")
    ref_date = st.date_input("기준 날짜", value=date.today(),
                             help="원문에 날짜(메일 Date·메신저 시각)가 없을 때만 마감일 계산 기준으로 씁니다.")
    st.selectbox("샘플 불러오기 (가상 데이터)", ["(선택 안 함)", *SAMPLES], key="sample", on_change=load_sample)
    st.markdown("**처리 흐름**\n\n1. 개인정보·이름 가리기\n2. 범위·지시문 점검\n3. 할 일 추출 · 마감일 계산\n"
                "4. 운영 가이드 검색(근거 인용)\n5. **내가 승인한 것만 저장**")
    st.info("🔒 이 화면은 이 PC에서만 열립니다. 실제 사내 메일·대화는 넣지 마세요.")

left, right = st.columns([3, 2], gap="large")

with left:  # 제목을 왼쪽 열에 넣어 오른쪽 할 일 영역이 제목 높이부터 시작하게 한다
    st.title("원큐 운영자 할 일 비서")
    st.caption("메신저·메일·PR·DIMS 알림을 붙여넣으면 나에게 온 요청만 골라 처리 방법과 근거를 붙여 드려요.")
    # 분석 중에는 실행 버튼만 잠근다(입력칸까지 잠그면 Streamlit이 다른 위젯으로 보고 입력값을 비운다)
    running = ss.get("running", False)
    text = st.text_area("메신저·메일·PR·DIMS 알림을 붙여넣거나, 저장된 할 일을 검색하세요",
                        height=220, placeholder="예) 대화 붙여넣기  /  이번 주 마감인 미완료 할 일 보여줘", key="input")
    st.button("분석 중..." if running else "실행", type="primary", key="run", use_container_width=True,
              on_click=start_run, disabled=running)
    if running:  # 잠긴 버튼은 클릭 값이 False라서, 클릭 콜백이 세운 running 표시로 실행한다
        ss.tid = f"ui-{uuid.uuid4().hex[:8]}"
        try:
            with st.spinner("분석 중이에요... (할 일마다 가이드를 찾느라 30~60초 걸릴 수 있어요)"):
                ss.result = agent.run(text, ss.tid, ref_date.isoformat())
            ss.done_msg = None
        finally:
            ss.running = False  # 오류가 나도 버튼이 잠긴 채 남지 않게
        st.rerun()

    r = ss.get("result")
    if r:
        for w in r["warnings"]:
            (st.error if w == "llm_unavailable" else st.warning)(WARN.get(w, w), icon="⚠️")
        if r.get("pending"):
            st.subheader(f"찾은 할 일 {len(r['extracted_todos'])}건 · 항목별로 확인해 주세요")
            decisions = []
            for i, t in enumerate(r["extracted_todos"]):
                with st.container(border=True):
                    tags = [(KIND.get(t.get("kind"), "📝 일반"), ""), dday(t["due_date"], ref_date)]
                    if t.get("is_inquiry"):
                        tags.append(("💬 답장 필요", "amber"))
                    st.markdown(badges(*tags), unsafe_allow_html=True)
                    act = st.radio("결정", ["승인", "거절"], horizontal=True, key=f"act-{i}")
                    content = st.text_input("할 일", t["content"], key=f"content-{i}")
                    c1, c2 = st.columns(2)
                    requester = c1.text_input("요청자", t["requester"], key=f"req-{i}")
                    # 원문에 마감이 없으면 오늘 날짜로 채워 두고, 달력에서 바꿀 수 있게 한다
                    due = c2.date_input("마감일", date.fromisoformat(t["due_date"]) if t["due_date"] else date.today(),
                                        key=f"due-{i}", help=f"원문 표현: {t.get('due_expression') or '없음'}").isoformat()
                    if not t["due_date"]:
                        c2.caption("원문에 마감이 없어 오늘 날짜로 채웠어요. 바꿀 수 있어요.")
                    if t.get("guide_method"):
                        with st.expander("🧭 처리 방법", expanded=True):
                            st.markdown(t["guide_method"])
                            for d in t.get("evidence_doc_ids") or []:
                                title, url = CONFLUENCE.get(d, (d, ""))
                                st.markdown(f"📎 근거 {d} · [{title}]({url})")
                    draft = t.get("answer_draft")
                    if draft is not None:
                        draft = st.text_area("✉️ 답변 초안 (발송되지 않아요)", draft, key=f"draft-{i}", height=180)
                    if t.get("pr_comment_summary"):
                        st.markdown(f"**PR 코멘트 요약**: {t['pr_comment_summary']}")
                    with st.expander("원문 발췌"):
                        st.text(t["source_excerpt"])
                edits = {k: v for k, v in {"content": content, "requester": requester, "due_date": due,
                                            "answer_draft": draft}.items() if v is not None and v != t.get(k)}
                decisions.append({"todo_index": i, "action": "reject" if act == "거절" else ("edit" if edits else "approve"),
                                  "edited_fields": edits or None})
            if st.button("결정 저장", type="primary", key="decide", use_container_width=True):
                out = agent.resume(ss.tid, decisions)
                if out.get("error"):
                    st.error(out["answer"])
                else:
                    n_reject = sum(d["action"] == "reject" for d in decisions)
                    ss.result, ss.clear_input = None, True
                    ss.done_msg = out["answer"] + (f" 거절 {n_reject}건은 저장하지 않았습니다." if n_reject else "")
                    st.rerun()
        else:
            st.info(r["answer"])
        if r.get("tool_calls") or r.get("steps"):
            with st.expander("🔍 에이전트가 한 일 (도구 호출 기록)"):
                for s in r.get("steps") or []:
                    st.markdown(f"- `{s}`")
                for c in r.get("tool_calls") or []:
                    st.markdown(f"- **{TOOL_LABEL.get(c['name'], c['name'])}** `{c['name']}` → {c.get('result_summary', '')}")
    if ss.get("done_msg"):
        st.success(ss.done_msg, icon="✅")

with right:
    todos = list_todos()
    open_ = [t for t in todos if t["status"] != "완료"]
    # 현황은 제목 옆 한 줄 배지로만 보여 주고 세로 공간은 할 일 목록에 쓴다
    soon = sum(1 for t in open_ if t["due_date"] and 0 <= (date.fromisoformat(t["due_date"]) - ref_date).days <= 2)
    late = sum(1 for t in open_ if t["due_date"] and date.fromisoformat(t["due_date"]) < ref_date)
    done_ = [t for t in todos if t["status"] == "완료"]
    st.markdown('<span style="font-size:1.35rem;font-weight:700;margin-right:10px">📋 내 할 일</span>'
                + badges((f"임박 {soon}", "amber"), (f"지남 {late}", "red")), unsafe_allow_html=True)
    # 할 일 / 완료 중 하나만 보여 주는 전환 스위치(완료를 고르면 완료한 것만)
    labels = {"open": f"📝 할 일 {len(open_)}", "done": f"✅ 완료 {len(done_)}"}
    view = st.segmented_control("보기", list(labels), format_func=labels.get, default="open", key="view",
                                label_visibility="collapsed") or "open"  # 선택을 풀면 할 일 보기로
    shown = done_ if view == "done" else open_
    if not shown:
        st.caption("완료한 할 일이 없어요." if view == "done" else
                   "미완료 할 일이 없어요. 왼쪽에 대화를 붙여넣고 승인하면 여기에 쌓여요.")
    for t in sorted(shown, key=lambda t: t["id"], reverse=True):  # 최근 등록한 할 일이 위로(id는 저장 순서대로 증가)
        done = t["status"] == "완료"
        with st.container(border=True):
            label = f"{t['content']} · {t['requester']} · 마감 {t['due_date'] or '없음'}"
            checked = st.checkbox(label, value=done, key=f"done-{t['id']}")
            st.markdown(badges(("✅ 완료", "gray") if done else dday(t["due_date"], ref_date)), unsafe_allow_html=True)
            with st.expander("📂 상세 보기 (처리 방법·답변 초안)"):
                if t["answer_draft"]:
                    st.markdown("**✉️ 답변 초안** — 오른쪽 위 복사 버튼으로 복사해 메일에 붙여넣으세요")
                    st.code(t["answer_draft"], language=None, wrap_lines=True)
                if t["guide_method"]:
                    st.markdown("**🧭 처리 방법**")
                    st.markdown(t["guide_method"])
                for d in filter(None, (t["evidence_doc_ids"] or "").split(",")):
                    title, url = CONFLUENCE.get(d, (d, ""))
                    st.markdown(f"📎 근거 {d} · [{title}]({url})")
                if t["pr_comment_summary"]:
                    st.markdown(f"**PR 코멘트 요약**: {t['pr_comment_summary']}")
                st.caption("원문 발췌")
                st.text(t["source_excerpt"] or "-")
            if checked != (t["status"] == "완료"):
                set_status(t["id"], checked)
                st.rerun()
