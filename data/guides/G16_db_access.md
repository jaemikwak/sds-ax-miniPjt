---
doc_id: G16
title: 원큐 DB 접근권한 신청
confluence: https://confluence.example.com/display/ONEQOPS/Access/DB-Access
owner_team: 인프라보안팀
updated: 2026-06-30
tags: [DB, Oracle, 데이터베이스, 접근권한, 조회 권한, DB 계정, 접근제어]
---

# 원큐 DB 접근권한 신청

원큐 Oracle 19c DB(개발 `ONEQ-DEV-DB01`, 운영 `ONEQ-PRD-DB01`) 조회·변경 권한 신청 방법입니다.

## 1. 개발 DB
- ITSM → [계정/권한] → **DB 접근권한 신청**, 소속 팀장 승인 후 당일 부여
- 접속 정보: `ONEQ-DEV-DB01:1521/ONEQDEV`, 개인 DB 계정 발급

## 2. 운영 DB
- 개인 조회 권한은 원칙적으로 부여하지 않습니다. DB 접근제어 솔루션을 통한 **1회성 조회 승인**만 가능합니다.
- 결재선: 신청자 → 팀장 → 시스템운영팀장 → 인프라보안팀
- 개인정보 테이블 조회는 개인정보보호 담당 추가 승인이 필요합니다.
