---
doc_id: G19
title: DIMS 인터페이스 정의서 — 원큐 결재·인사·영업 연계
confluence: https://confluence.example.com/display/ONEQOPS/Interface/DIMS/HR-Sales
owner_team: 시스템운영팀
updated: 2026-10-30
tags: [DIMS, 인터페이스, IF ID, 소스 테이블, 타겟 테이블, 인사, 조직, 영업, 결재, 인터페이스 정의서]
---

# DIMS 인터페이스 정의서 — 원큐 결재·인사·영업 연계

원큐와 인사시스템·영업포털 사이 인터페이스 목록입니다. 정산·ERP 연계는 G18, 실패 대응은 G20을 참고하세요.

| IF ID | 인터페이스명 | 방향 | 소스 (시스템.테이블) | 타겟 (시스템.테이블) | 주기 | 방식 | 원큐 측 담당 |
|---|---|---|---|---|---|---|---|
| IF-ONEQ-HR-001 | 조직도 수신 | 인사 → 원큐 | HR.ORG_UNIT | ONEQ.TB_ORG | 매일 01:00 | DB to DB | 정하늘 선임 |
| IF-ONEQ-HR-002 | 사원 정보 수신 | 인사 → 원큐 | HR.EMP_MASTER | ONEQ.TB_EMP | 매일 01:10 | DB to DB | 정하늘 선임 |
| IF-ONEQ-HR-003 | 부재·위임 정보 수신 | 인사 → 원큐 | HR.EMP_ABSENCE | ONEQ.TB_APRV_DELEGATE | 매시 정각 | DB to DB | 정하늘 선임 |
| IF-ONEQ-SALES-001 | 영업 계약 정보 수신 | 영업포털 → 원큐 | SALES.CONTRACT | ONEQ.TB_CONTRACT | 매일 06:00 | File(CSV, SFTP) | 강준호 선임 |
| IF-ONEQ-SALES-002 | 결재 완료 결과 송신 | 원큐 → 영업포털 | ONEQ.TB_APRV_DOC | SALES.APRV_RESULT | 10분 | DB to DB | 강준호 선임 |

## 키·제약 메모
- IF-ONEQ-HR-001/002가 실패하면 결재선 계산에 쓰는 조직·사원 정보가 하루 전 상태로 남아, 결재 `ROUTE_ERROR`(G10 Q1 원인 2)가 날 수 있습니다. 성공 후 배치 `HR_SYNC`가 실행되어야 반영됩니다.
- IF-ONEQ-HR-003 실패 시 퇴사·전배자의 위임 정보가 남아 결재가 `DELEGATE_WAIT`로 멈출 수 있습니다(G10 Q1 원인 1).
- IF-ONEQ-SALES-001은 파일 수신 방식이라, 영업포털이 파일을 늦게 올리면 "파일 없음(FILE_NOT_FOUND)"으로 실패합니다.
