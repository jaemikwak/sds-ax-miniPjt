---
doc_id: G18
title: DIMS 인터페이스 정의서 — 원큐 정산·ERP 연계
confluence: https://confluence.example.com/display/ONEQOPS/Interface/DIMS/Settlement-ERP
owner_team: 시스템운영팀
updated: 2026-10-30
tags: [DIMS, 인터페이스, IF ID, 소스 테이블, 타겟 테이블, ERP, 정산, 전표, 인터페이스 정의서]
---

# DIMS 인터페이스 정의서 — 원큐 정산·ERP 연계

DIMS(사내 데이터 연계 시스템)가 원큐와 ERP 사이에서 수행하는 인터페이스 목록입니다.
실패 시 대응 절차는 G20을 참고하세요. 원큐 DB는 Oracle 19c `ONEQ-PRD-DB01`(스키마 `ONEQ`)입니다(G17).

| IF ID | 인터페이스명 | 방향 | 소스 (시스템.테이블) | 타겟 (시스템.테이블) | 주기 | 방식 | 원큐 측 담당 |
|---|---|---|---|---|---|---|---|
| IF-ONEQ-ERP-001 | 정산 전표 송신 | 원큐 → ERP | ONEQ.TB_SETL_SLIP | ERP.GL_INTERFACE | 매일 23:50 (2차 확정 마감 후) | DB to DB | 송미래 책임 |
| IF-ONEQ-ERP-002 | 전표 처리 결과 수신 | ERP → 원큐 | ERP.GL_RESULT | ONEQ.TB_SETL_SLIP_RESULT | 매일 03:00 | DB to DB | 송미래 책임 |
| IF-ONEQ-ERP-003 | 거래처 마스터 수신 | ERP → 원큐 | ERP.AP_VENDOR | ONEQ.TB_VENDOR_MST | 매일 05:00 | DB to DB | 강준호 선임 |
| IF-ONEQ-ERP-010 | 예산 잔액 조회 | 원큐 → ERP | (실시간 요청) | ERP.BUDGET_API | 실시간 | REST API | 이서준 책임(개발) |
| IF-ONEQ-ERP-011 | 계정과목 코드 수신 | ERP → 원큐 | ERP.GL_ACCOUNT | ONEQ.TB_ACCT_CODE | 매주 월 04:00 | DB to DB | 강준호 선임 |

## 키·제약 메모
- `ONEQ.TB_SETL_SLIP_RESULT`의 PK는 (`SLIP_NO`, `RESULT_SEQ`)입니다. ERP에서 같은 전표 결과를 두 번 보내면 `ORA-00001`(unique constraint)로 실패합니다.
- `ONEQ.TB_VENDOR_MST`는 전체 삭제 후 재적재(Truncate & Insert) 방식이라, 실패 시 거래처 조회 화면이 빈 값으로 보일 수 있습니다.
- IF-ONEQ-ERP-010은 실시간 API라 DIMS 배치 재처리 대상이 아닙니다(개발팀 확인 대상).
