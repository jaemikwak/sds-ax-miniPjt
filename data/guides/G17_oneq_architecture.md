---
doc_id: G17
title: 원큐 시스템 아키텍처 구성 및 서버 정보
confluence: https://confluence.example.com/display/ONEQOPS/Home/Architecture
owner_team: 시스템운영팀
updated: 2026-11-05
tags: [아키텍처, 서버 정보, 구성도, 호스트명, IP, 포트, IIS, JBoss, Oracle, Windows, 이중화]
---

# 원큐 시스템 아키텍처 구성 및 서버 정보

원큐(OneQ) 업무시스템의 서버 구성과 접속 정보입니다. 모든 서버는 Windows Server 기반입니다.

## 1. 운영 구성 (이중화)
```
사용자 → L4 (VIP oneq.example.com:443, Round-Robin + Health Check)
          ├─ ONEQ-PRD-01 (Windows Server 2019) : IIS 10(웹, 443) → JBoss EAP 7.4(WAS, 8080)
          └─ ONEQ-PRD-02 (Windows Server 2019) : IIS 10(웹, 443) → JBoss EAP 7.4(WAS, 8080)
                                   ↓ JDBC 1521
                          ONEQ-PRD-DB01 (Oracle 19c, Windows Server 2019)
```
- 웹/WAS는 **Windows 2대 Active-Active 이중화**입니다. 각 서버에 IIS와 JBoss가 함께 설치되어 있고, IIS가 정적 리소스를 처리하고 동적 요청을 같은 서버의 JBoss(8080)로 전달합니다(IIS ARR 리버스 프록시).
- 세션은 JBoss 클러스터 세션 복제(Infinispan)로 두 서버 간 공유합니다. 한 대 장애 시 L4가 다른 서버로만 트래픽을 보냅니다.
- 배치(정산 SETL_CLOSE, 알림 NOTI_SEND, 인사연동 HR_SYNC)는 **ONEQ-PRD-01의 JBoss에서만** 실행됩니다(중복 실행 방지).
- DB는 Oracle 19c 단일 인스턴스이며, 매일 02:00 RMAN 전체 백업을 백업 서버로 보관합니다.

## 2. 서버 목록
| 구분 | 호스트명 | IP | 역할 | 주요 포트 |
|---|---|---|---|---|
| 운영 | ONEQ-PRD-01 | 10.10.1.11 | IIS + JBoss (배치 실행 노드) | 443, 8080, 9990(JBoss 관리), 3389(RDP) |
| 운영 | ONEQ-PRD-02 | 10.10.1.12 | IIS + JBoss | 443, 8080, 9990, 3389 |
| 운영 | ONEQ-PRD-DB01 | 10.10.1.21 | Oracle 19c | 1521 |
| 스테이징 | ONEQ-STG-01 | 10.20.1.11 | IIS + JBoss (단일) | 443, 8080, 3389 |
| 개발 | ONEQ-DEV-01 | 10.30.1.11 | IIS + JBoss (단일) | 443, 8080, 3389 |
| 개발 | ONEQ-DEV-DB01 | 10.30.1.21 | Oracle 19c (개발) | 1521 |
| 공통 | JUMP-PRD01 | 10.10.9.5 | 운영 접속용 점프서버(RDP) | 3389 |

## 3. 소프트웨어 버전
- OS: Windows Server 2019 Standard
- 웹: IIS 10 (URL Rewrite, ARR 설치)
- WAS: JBoss EAP 7.4, JDK 17 (Temurin)
- DB: Oracle Database 19c Enterprise Edition (문자셋 AL32UTF8)

## 4. 운영 원칙
- 운영 서버 작업(배포, 인증서 교체, 패치)은 **한 대씩 L4에서 제외 → 작업 → 복귀** 순서로 무중단 진행합니다.
- 운영 서버 접속은 점프서버(JUMP-PRD01) RDP 경유만 허용됩니다.
