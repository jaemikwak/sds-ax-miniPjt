---
doc_id: G05
title: 원큐 로컬 개발환경 세팅 가이드
confluence: https://confluence.example.com/display/ONEQDEV/Onboarding/Local-Setup
owner_team: 시스템운영팀
updated: 2026-11-02
tags: [개발환경, 세팅, 온보딩, JDK, JBoss, IDE, 신규입사, 로컬]
---

# 원큐 로컬 개발환경 세팅 가이드

신규 입사자나 새 PC에서 원큐 프로젝트를 빌드·실행하기 위한 가이드입니다. 서버 구성은 G17을 참고하세요.

## 1. 필수 설치
- JDK **17** (Temurin 17.0.x). 운영 JBoss EAP 7.4가 JDK 17로 동작하므로 JDK 21은 사용하지 않습니다.
- JBoss EAP **7.4** (사내 배포본, `\\fileserver\dev-tools\jboss-eap-7.4.zip`) — 로컬 standalone 모드로 실행
- IntelliJ IDEA(사내 라이선스) + JBoss 플러그인, Gradle 8.x(래퍼 사용), Git 2.4x
- Oracle SQL Developer 또는 DBeaver (개발 DB `ONEQ-DEV-DB01:1521/ONEQDEV` 접속용)

## 2. 저장소 접근
1. 사내 GitHub Enterprise `oneq/oneq-core`, `oneq/oneq-web` 저장소 권한을 소속 팀장 승인으로 요청합니다.
2. SSH 키를 등록하고 `git clone`합니다.

## 3. 사내 인증서·프록시
- 사내 루트 CA를 JDK cacerts와 Windows 인증서 저장소에 설치해야 Gradle 의존성 다운로드와 개발서버 HTTPS 접속이 됩니다.
- 프록시: `http://proxy.example.local:8080`, Gradle `gradle.properties`에 설정합니다.

## 4. 로컬 실행
1. `gradlew.bat build`로 `oneq-core.war`를 빌드합니다.
2. JBoss `standalone/deployments/`에 WAR를 복사하고 `standalone.bat -c standalone-oneq.xml`로 실행합니다.
3. 데이터소스(`java:/OneqDS`)는 개발 DB를 바라보도록 `standalone-oneq.xml`에 설정되어 있습니다. 개발 DB 계정은 G16을 참고합니다.

## 5. 개발서버 접속이 필요한 경우
- 개발서버(`ONEQ-DEV-01`) RDP 접속은 방화벽 오픈(G01)과 서버 계정 신청(G06)이 모두 필요합니다.
