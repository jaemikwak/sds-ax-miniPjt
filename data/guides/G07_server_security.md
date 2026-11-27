---
doc_id: G07
title: 원큐 서버 보안 기준(Windows·IIS·JBoss 하드닝)
confluence: https://confluence.example.com/display/ONEQOPS/Security/Hardening
owner_team: 인프라보안팀
updated: 2026-05-12
tags: [서버보안, 하드닝, 보안기준, Windows, IIS, JBoss, 패스워드 정책, 계정 잠금]
---

# 원큐 서버 보안 기준(Windows·IIS·JBoss 하드닝)

원큐 서버(Windows Server 2019, IIS 10, JBoss EAP 7.4, Oracle 19c)가 항상 지켜야 하는 보안 기준입니다. 점검 결과 조치는 G08을 참고하세요.

## 1. Windows 계정
- 기본 Administrator 계정 이름 변경·사용 금지, 개인 도메인 계정 + 관리자 그룹 최소 부여
- 패스워드 9자 이상, 90일 주기 변경, 5회 실패 시 계정 잠금(로컬 보안 정책)
- RDP는 네트워크 수준 인증(NLA) 필수, 유휴 세션 30분 후 연결 끊기

## 2. IIS
- 응답 헤더의 서버 버전 노출 제거(`removeServerHeader`), 디렉터리 검색 비활성화
- TLS 1.0/1.1 비활성화, TLS 1.2 이상만 허용

## 3. JBoss
- 관리 콘솔(9990)은 localhost 바인딩, 원격 접근 금지
- 기본 예제 애플리케이션(welcome-content) 제거

## 4. Oracle
- 기본 계정(SCOTT 등) 잠금, 리스너 패스워드 설정

## 5. 로그·패치
- 이벤트 로그·IIS 로그 1년 보관, Windows 보안 업데이트는 분기 1회 정기 작업에서 한 대씩 적용
