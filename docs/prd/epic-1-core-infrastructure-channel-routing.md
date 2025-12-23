# Epic 1: Core Infrastructure & Channel Routing

## Story 1.1: 배경/목표/정책 확정

### 1.1.1 목표

1. 한 네이버 계정에 속한 **wc****** 채널 16개**의 톡톡 문의 응답 자동화(향후 채널 추가 확장)
2. **AWS 기반** (비용 효율 우선)
3. **RAG 지식원: Google Docs**

   * 채널별 문서 존재
   * 공통 문서 존재
   * 업데이트 월 1회 수준
4. **TEST 기본 모드**

   * 톡톡으로 **절대 자동 전송하지 않음(무응답)**
   * Google Sheets에 **질문/답변(초안)** 기록
5. 검증 완료 후 **TEST→PROD 플래그 전환**으로 실사용

### 1.1.2 고객 커뮤니케이션 정책(매우 중요)

* **모른다는 말 금지**(고객에게 "모르겠습니다/애매합니다/추측입니다" 등 금지)
* **상담원 연결 안내 문구 금지**("상담원에게 연결할게요" 금지)
* 애매/불확실/리스크 케이스는:

  * 고객에게는 **무응답 유지**
  * 운영자에게 **Telegram 알림(채널명 + 상담자 id 포함)**

## Story 1.2: 외부 연동 제약(네이버 톡톡)

### 1.2.1 Webhook 운영 제약

* Webhook은 **TLS 기반**이어야 하며, ACL이 필요하면 지정된 IP 대역을 allowlist 해야 합니다. ([GitHub][1])
* 톡톡 Webhook 호출 타임아웃이 **Connection 3초 / Read 5초**로 짧습니다. ([GitHub][1])
  → 따라서 **Webhook은 즉시 200 OK 반환 + 비동기 처리**가 기본 설계입니다.

### 1.2.2 보내기 API(자동 응답 전송) — PROD에서만

* 보내기 API 호출 예시는 다음과 같습니다(공식):

  * `POST https://gw.talk.naver.com/chatbot/v1/event`
  * Header에 `Authorization` 필요
  * Body에 `"event":"send"`, `"user":"..."`, `"textContent":{"text":"..."}` ([GitHub][1])
* **Authorization(인증 키)** 는 파트너센터 "API 설정 > 보내기 API"에서 생성/재설정 가능합니다. ([GitHub][1])
* (참고) Naver Cloud 문서에서는 이 Authorization 값을 "channel access token"으로 설명합니다. ([NCloud Docs][2])

### 1.2.3 동기/비동기 응답 방식

* 공식 문서에서 "동기식(웹훅 응답 body로 send)"과 "비동기식(200 OK 후 보내기 API)"를 구분합니다. ([GitHub][1])
* 본 PRD는 **목표 응답 1분** + Webhook 5초 제약 때문에 **비동기식을 표준**으로 채택합니다.

### 1.2.4 이벤트/루프 위험(echo)

* `send` 이벤트는 user/partner 모두 발생 가능하며, 메시지 타입은 text/image/composite 등이 있습니다. ([GitHub][1])
* `echo` 이벤트는 상담사/챗봇이 보낸 메시지까지 다시 수신할 수 있어, 재전송하면 무한 루프 위험이 명시됩니다. ([GitHub][1])
  → 운영 안정성을 위해 **echo 이벤트는 기본 비활성**(필요 시 별도 테스트 후 제한적으로).

## Story 1.3: 시스템 개요(Architecture)

### 1.3.1 권장 AWS 구성(비용 효율 우선)

* **API Gateway**: `POST /naver/talktalk/{channel_id}/webhook`
* **Lambda(Ingest)**: 스키마 검증 → SQS enqueue → 즉시 200 OK
* **SQS**: 이벤트 큐(유실 방지)
* **Lambda(Worker)**: RAG → LLM → Sheets 기록 → (PROD 조건부) 보내기 API 호출 → Telegram 알림
* **DynamoDB**

  * ChannelConfig (채널별 설정/문서매핑/채널 모드)
  * GlobalMode (전역 모드) 또는 SSM Parameter Store
  * Dedup(TTL)
* **S3**

  * Google Docs 원문 스냅샷(선택)
  * 벡터 인덱스(FAISS 등) 저장(비용 절감)
* **EventBridge Scheduler**

  * 문서 동기화/재색인 스케줄(예: 매일/주1회 + 수동 트리거)
* **Secrets Manager**

  * OpenAI API Key
  * 채널별 톡톡 Authorization 토큰
  * Google SA 자격증명(가능하면 최소권한)
  * Telegram Bot Token

## Story 1.4: 핵심 기능 요구사항(요약)

### 1.4.1 채널 확장/라우팅

* 채널별 Webhook URL을 개별 등록 가능하므로(당신 확답), URL에 channel_id를 포함:

  * `/naver/talktalk/wc123.../webhook`
* channel_id 기반으로 ChannelConfig 로드

### 1.4.2 TEST 모드(기본)

* 고객 메시지 수신 → **무조건 무응답**(send API 호출 금지)
* Google Sheets에 질문/답변 초안 기록
* 불확실/오류 케이스는 Telegram 알림(운영자 대응)

### 1.4.3 PROD 모드(실사용)

* 전역 모드=PROD & 채널 모드=PROD & LLM 판단 send_to_user=true 인 경우만 자동 발송
* 그 외는 **무응답 + Telegram 알림**

---
