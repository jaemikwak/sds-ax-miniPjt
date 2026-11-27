---
doc_id: G15
title: 원큐 정기릴리즈 일정·반영 절차
confluence: https://confluence.example.com/display/ONEQOPS/Release/Schedule
owner_team: 시스템운영팀
updated: 2026-09-01
tags: [정기릴리즈, 일정, 반영, 배포 작업, 코드 프리즈, 작업 시간, JBoss 배포]
---

# 원큐 정기릴리즈 일정·반영 절차

서버 구성은 G17(Windows 2대 이중화, IIS + JBoss EAP 7.4, Oracle 19c)을 참고하세요.

## 1. 월간 일정
- 매월 **넷째 주 목요일 22:00~24:00** 반영
- 코드 프리즈: 반영일 1주 전 월요일, 통합 테스트: 프리즈 후 화~목

## 2. 반영 작업(시스템운영팀, 무중단 순차 배포)
1. 반영 전: 결재 완료 확인(G12), 작업계획서 등록, Oracle DB 백업(RMAN) 확인
2. DB 변경 스크립트가 있으면 먼저 `ONEQ-PRD-DB01`에 적용합니다.
3. 배치 노드인 `ONEQ-PRD-01`에서 배치 스케줄을 일시 중지합니다.
4. L4에서 `ONEQ-PRD-02` 제외 → JBoss 서비스 중지 → `standalone/deployments/`의 WAR 교체 → JBoss 기동 → IIS 정적 리소스 교체 → 확인 후 L4 복귀
5. `ONEQ-PRD-01`에 4단계를 반복한 뒤 배치 스케줄을 재개합니다.
6. 반영 후: 주요 화면 스모크 테스트, 품질관리팀에 반영 완료 공지
7. 이상 시 롤백 계획에 따라 이전 WAR로 원복합니다.

## 3. 연락
- 반영 당일 대기: 개발팀 담당자, 품질관리팀 PM, 시스템운영팀 운영 담당
