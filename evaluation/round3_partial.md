# Round 3 자체 평가 보고서

- 실행: 2026-11-26 13:58 · 소요 2.7분 · 모델 us.anthropic.claude-sonnet-4-6 / amazon.titan-embed-text-v2:0
- **통과 4/4** · guardrail 0/3
- 문항 통과 = 기계 채점(도구·경고·PII·검색 결과) + Claude 판정(expected_traits 전부 통과, forbidden 위반 없음)

| 문항 | 분류 | 결과 | 시간(초) | 실패 원인 |
|---|---|---|---|---|
| Q01 | positive | ✅ | 43.2 | - |
| Q05 | positive | ✅ | 19.4 | - |
| Q06 | positive | ✅ | 4.9 | - |
| Q13 | edge | ✅ | 21.7 | - |

## 지표

| 지표 | 값 | 목표 |
|---|---|---|
| 할 일 재현율 | 1.0 | ≥ 0.90 |
| 요청자 정확도 | 1.0 | ≥ 0.95 |
| 인용 적중률 | 1.0 | ≥ 0.80 |
| 마감일 정확도 | 1.0 | 측정 |
| 문의형 판정 정확도 | 1.0 | 측정 |
| context_recall (근사) | 1.0 | 측정 |
| context_precision (근사) | 0.917 | 측정 |
| faithfulness (근사) | 0.833 | 측정 |
| answer_relevancy (근사) | 0.535 | 측정 |
| draft_faithfulness (근사) | 0.833 | 측정 |

> RAGAS 지표는 ragas 라이브러리 없이 같은 정의로 직접 계산한 근사치(판정 LLM: Claude Sonnet 4.6, 임베딩: Titan v2). context_*는 샘플 단위 검색 상위 5개 기준.

## 기계 판독용

```json
{
 "round": 3,
 "pass_count": 4,
 "total": 4,
 "passed_ids": [
  "Q01",
  "Q05",
  "Q06",
  "Q13"
 ],
 "failed_ids": [],
 "guardrail_pass": 0,
 "recall": 1.0,
 "requester_accuracy": 1.0,
 "citation_hit_rate": 1.0,
 "deadline_accuracy": 1.0,
 "is_inquiry_accuracy": 1.0,
 "context_recall": 1.0,
 "context_precision": 0.917,
 "faithfulness": 0.833,
 "answer_relevancy": 0.535,
 "draft_faithfulness": 0.833,
 "judge_reasons": {
  "Q01": [
   "O 나에게 온 할 일 2건 추출(방화벽 신청 방법 안내, 개발서버 SSL 만료 확인) — extracted_todos에 '이서준 책임의 원큐 개발서버 방화벽 신청 방법 안내'와 '원큐 개발서버 SSL 인증서 만료 확인 및 조치' 2건이 정확히 추출되어 있다.",
   "O 요청자 이서준 — 두 extracted_todos 항목 모두 requester 필드에 '이서준'이 명시되어 있다.",
   "O SSL 건 마감일 2026-11-25 — SSL 인증서 만료 확인 항목의 due_date가 '2026-11-25'로 정확히 기재되어 있다.",
   "O 방화벽 건은 문의형으로 G01 근거 답변 초안 포함(ITSM 방화벽 오픈 신청, ONEQ-DEV-01 RDP 3389) — is_inquiry가 true이고, evidence_doc_ids에 G01이 포함되며, answer_draft에 'ITSM 포털 → 방화벽 오픈 신청', 'ONEQ-DEV-01', 'RDP(3389)' 내용이 모두 포함되어 있다.",
   "O SSL 건은 G04(개발·스테이징) 인용 — SSL 인증서 항목의 evidence_doc_ids에 'G04'가 포함되어 있고, guide_method에도 '[G04] 개발·스테이징 SSL 인증서 발급 및 교체'로 명시되어 있다.",
   "O 컨플루언스 위치 표시 — 방화벽 건 guide_method 및 answer_draft에 'https://confluence.example.com/display/ONEQOPS/Infra/Firewall/Request', SSL 건 guide_method에 'https://confluence.example.com/display/ONEQOPS/Infra/SSL/Dev-Staging' URL이 명시되어 있다.",
   "금지준수 SSL 건 근거로 운영 절차(G03) 인용 — SSL 항목의 evidence_doc_ids에는 G04만 있고 G03은 포함되지 않는다. guide_method에서 G03을 언급하지만 '이번 건과 무관합니다'라고 명시하며 근거로 사용하지 않았다.",
   "금지준수 승인 전 저장 — hitl 필드에 따르면 run()은 interrupt에서 멈춰 저장 0건이었고, 평가자가 approve로 resume()한 이후에 save_todos가 실행되었으므로 승인 전 저장은 발생하지 않았다."
  ],
  "Q05": [
   "O 할 일 1건(IF-ONEQ-ERP-002 인터페이스 실패 확인·재처리) — extracted_todos에 IF-ONEQ-ERP-002 실패 확인 및 재처리 조치 1건이 정확히 추출되어 있고, answer에도 '할 일 1건'으로 명시되어 있다.",
   "O 요청자 DIMS(시스템 알림) — extracted_todos의 requester 필드가 'DIMS', kind 필드가 'dims'로 정확히 기재되어 있다.",
   "O 마감일 2026-11-25(메일의 재처리 기한) — due_date가 '2026-11-25'로 정확히 일치하며, due_expression에도 '재처리 기한 2026-11-25 18:00'으로 명시되어 있다.",
   "O G18 근거로 소스 ERP.GL_RESULT → 타겟 ONEQ.TB_SETL_SLIP_RESULT 데이터 확인 필요 명시 — evidence_doc_ids에 G18이 포함되어 있고, guide_method ②에서 G18을 근거로 소스 ERP.GL_RESULT와 타겟 ONEQ.TB_SETL_SLIP_RESULT 데이터 확인 절차가 명시되어 있다.",
   "O G20 근거로 ORA-00001(타겟 중복 키) 조치와 DIMS 콘솔 재처리 안내 — evidence_doc_ids에 G20이 포함되어 있고, guide_method ③에서 G20 근거로 ORA-00001(unique constraint) 타겟 중복 키 조치가, ④에서 DIMS 콘솔 재처리 절차가 상세히 안내되어 있다.",
   "O 문의형 아님 — extracted_todos의 is_inquiry 필드가 false로 명시되어 있다.",
   "금지준수 다른 IF ID(IF-ONEQ-ERP-001 등)의 테이블로 안내 — 출력 전체에서 IF-ONEQ-ERP-002 외의 다른 인터페이스 ID나 그에 속한 테이블로 안내한 내용이 없다.",
   "금지준수 정의서에 없는 테이블명 지어내기 — 안내에 사용된 테이블명(ERP.GL_RESULT, ONEQ.TB_SETL_SLIP_RESULT)은 G18 정의서를 근거로 제시된 것이며, 임의로 지어낸 테이블명은 확인되지 않는다.",
   "금지준수 답변 초안 생성 — extracted_todos의 answer_draft 필드가 null로 비어 있어 답변 초안이 생성되지 않았다."
  ],
  "Q06": [
   "O PR #482 내용 검토 할 일 1건 — extracted_todos에 'PR #482(정산 배치 중복 실행 방지 락 개선) 내용 검토' 항목이 정확히 1건 존재하며, answer에도 '할 일 1건을 찾았습니다'로 명시되어 있음.",
   "O 요청자 오태양(PR 작성자) — extracted_todos의 requester 필드에 '오태양'이 명시되어 있으며, source_excerpt에도 'taeyang-oh'가 PR 작성자임이 확인됨.",
   "O pr_comment_summary에 finally 락 해제 반영·30분 자동 만료·11/30 마감일 모니터링 요청 포함 — pr_comment_summary에 'finally에서 락 해제하도록 수정', '남은 락은 30분 후 자동 만료', '마감일(11/30) 첫 실행 모니터링 요청' 세 가지 내용이 모두 포함되어 있음.",
   "금지준수 요청자를 GitHub Enterprise(봇)로 기재 — requester 필드에 '오태양'(실제 사람)으로 기재되어 있으며, 봇으로 기재된 흔적 없음.",
   "금지준수 버그 가능성 판정 — 출력 어디에도 버그 가능성을 판정하거나 단정하는 표현이 없음. pr_comment_summary는 리뷰어 코멘트를 요약한 것으로 OpsMate 자체의 판정이 아님.",
   "금지준수 답변 초안 생성 — extracted_todos의 answer_draft 필드가 null이며, 출력 전체에서 답변 초안을 생성한 흔적이 없음."
  ],
  "Q13": [
   "O 할 일 1건(퇴사자 박지훈 명의 방화벽 정책 3건 해제 대리 신청) — extracted_todos에 1건이 있으며, content에 '퇴사한 박지훈 책임 명의 방화벽 정책 3건(FW-2025-0812, FW-2025-0813, FW-2026-0101) 해제 신청 대리 접수'로 정확히 기술되어 있다.",
   "O 요청자 서하린 — extracted_todos[0].requester 필드에 '서하린'으로 정확히 기재되어 있다.",
   "O 마감일 2026-11-27 — extracted_todos[0].due_date가 '2026-11-27'로 정확히 일치한다.",
   "O G02(정책 해제) 인용 — evidence_doc_ids에 'G02'가 포함되어 있고, guide_method에도 'G02 – 방화벽 정책 해제·회수 절차'로 명시되어 있다.",
   "O 긴 입력 요약 미들웨어 발동(trace) — steps 필드에 'summarize(624 tokens)'가 기록되어 있어 요약 미들웨어가 발동했음을 확인할 수 있다.",
   "금지준수 G01(신규 오픈) 절차로 안내 — G01은 tool_calls의 search_guides 결과에만 등장하고, evidence_doc_ids에는 포함되지 않았으며 guide_method에도 인용되지 않았다. 검색만 됐을 뿐 안내에 사용되지 않았다.",
   "금지준수 인용된 과거 메일 속 요청을 별도 할 일로 중복 추출 — extracted_todos에 할 일이 1건만 존재하며, 중복 추출된 항목이 없다."
  ]
 }
}
```
