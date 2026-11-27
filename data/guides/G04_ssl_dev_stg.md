---
doc_id: G04
title: 개발·스테이징 SSL 인증서 발급 및 교체
confluence: https://confluence.example.com/display/ONEQOPS/Infra/SSL/Dev-Staging
owner_team: 시스템운영팀
updated: 2026-07-21
tags: [SSL, 인증서, 개발서버, 스테이징, 사설인증서, 만료 알림, IIS]
---

# 개발·스테이징 SSL 인증서 발급 및 교체

원큐 **개발(`ONEQ-DEV-01`, oneq-dev.example.local)·스테이징(`ONEQ-STG-01`, oneq-stg.example.local)** 서버의 SSL 인증서 절차입니다.
운영 인증서는 G03을 따르세요. 개발·스테이징은 사내 사설 CA 인증서를 사용합니다.

## 1. 만료 알림을 받았을 때
- 모니터링에서 "개발서버 SSL 만료 D-7" 알림이 오면 시스템운영팀이 교체합니다.
- 변경관리 승인은 필요 없고, 개발팀 공지 채널에 작업 시간만 공지합니다.

## 2. 교체 절차
1. 사내 PKI 포털 → [사설 인증서 발급]에서 CN=`oneq-dev.example.local`로 재발급합니다(유효기간 1년, .pfx 형식).
2. `ONEQ-DEV-01`에 RDP 접속 → 인증서를 [로컬 컴퓨터 > 개인] 저장소로 가져오기 → IIS 관리자에서 443 바인딩 인증서를 교체합니다.
3. IIS 재시작은 필요 없지만, 바인딩 변경 후 `iisreset /status`로 서비스 상태를 확인합니다.
4. 개발자 PC에서 인증서 오류가 나면 사내 루트 CA 설치 여부를 확인합니다(G05의 3단계).

## 3. 참고
- 단일 서버라 교체 중 1~2분 접속이 끊길 수 있습니다. 통합 테스트 기간에는 품질관리팀(한지민 책임)과 시간을 협의합니다.
