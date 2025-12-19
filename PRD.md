# PRD v1.0 — 네이버 톡톡(16개 wc 채널) 문의 응답 자동화 (RAG + OpenAI)

## 0. 문서 목적

본 PRD는 **네이버 톡톡(Chat Bot API V1)** 기반으로, **한 네이버 계정 내 16개 wc****** 채널**의 고객 문의를 수신하고 **RAG(채널별 Google Docs + 공통 Docs)**로 **초안 답변을 생성**하여

* **TEST 모드**: 톡톡으로 보내지 않고 **Google Sheets에 (질문/답변) 기록**
* **PROD 모드**: 조건 충족 시 **톡톡 보내기 API로 자동 응답**
  을 구현하기 위한 제품/기술 요구사항을 정의합니다.

---

## 1. 목표 / 비목표

### 1.1 목표 (Goals)

1. **16개 톡톡 채널(wc******) 문의 자동화** (향후 채널 수 증가에도 설정 추가로 확장)
2. **AWS 기반**으로 운영 (현재 AWS 사용 중)
3. **RAG 지식원 = Google Docs**

   * 채널별 문서 존재 + 공통 문서 존재
   * 문서 업데이트는 **월 1회 내외**
4. **TEST 모드 기본**

   * 실제 고객에게 AI 답변을 **절대 전송하지 않음(무응답)**
   * 대신 Google Sheets에 `질문/답변` 기록하여 검증
5. 검증 완료 후 **플래그 전환(TEST→PROD)**하여 실사용

### 1.2 비목표 (Non-Goals) — v1 범위 밖

* 네이버페이 연동
* 핸드오버 API로 “상담원 연결” 안내/전환 (요구사항상 **고객에게 안내 문구 자체를 보내지 않음**)
* 이미지/복합 메시지 자동 분석(이미지 OCR 등)
* 상담원 UI/CRM 구축(단, Telegram 알림은 포함)

---

## 2. 핵심 결정사항 (당신 확답 반영)

* 채널 구조: **1개 네이버 계정에 wc****** 채널 16개** (확장 예정)
* Webhook URL: **채널별로 설정 가능** → **채널별 고유 Webhook URL** 사용 (라우팅 안정화)
* TEST 모드 UX: **무응답(톡톡으로 아무 메시지도 보내지 않음)**

  * 대신 고객 메시지는 운영자 휴대폰 톡톡 앱에서 확인하고 수동 대응
* RAG: **채널별 Docs + 공통 Docs** (2-6: C)
* LLM: **OpenAI API, gpt-4o-mini**
* 트래픽: **일 1~50건 수준**, 목표 응답시간 **1분 이내**
* 플래그: **전역 + 채널별** 둘 다 (2-5: C)
* 답변 톤: **존댓말 + 친근 + 이모지 사용**
* “모른다/애매” 처리:

  * 고객에게 “모르겠습니다/상담원 연결” 같은 문구 **금지**
  * 애매/불확실 시 **무응답 유지**
  * 대신 **Telegram으로 운영자 알림(채널명, 상담자 id 포함)**
* 개인정보:

  * Sheet 저장은 원문 허용(2-10: A)
  * 단, **로그/텔레그램/모니터링에는 마스킹 적용**(요구 반영)

---

## 3. 외부 제약/연동 스펙 요약 (Naver TalkTalk)

### 3.1 Webhook 제약

* Webhook은 **TLS 기반**이어야 함
* ACL 필요 시 특정 IP 대역 allowlist 필요
* 톡톡 Webhook 호출 타임아웃: **Connection 3초 / Read 5초**
  → 따라서 Webhook은 **즉시 200 OK 반환 + 비동기 처리**가 사실상 필수 ([GitHub][1])

### 3.2 보내기 API(Outbound) — PROD에서만 사용

* 보내기 API 호출 예시(공식 문서)에는

  * `Authorization` 헤더 사용
  * Endpoint: `https://gw.talk.naver.com/chatbot/v1/event`
  * Body에 `"event":"send"`, `"user":"..."`, `"textContent":{"text":"..."}` 포함 ([GitHub][1])
* **중요**: `Authorization` 값은 **Webhook에서 “제공되는 값”이 아니라**, 파트너센터의 “보내기 API”에서 **생성/재설정해 사용하는 인증 키(토큰)**임 ([GitHub][1])

### 3.3 이벤트 선택 주의

* send/open만 활성화 권장 (echo는 루프 위험)
* `echo` 이벤트는 상담사/챗봇이 보낸 메시지까지 다시 수신할 수 있으며, 재전송하면 무한 송수신 루프 위험이 명시됨 ([GitHub][1])

---

## 4. 사용자 시나리오 (User Flows)

### 4.1 TEST 모드 (기본)

1. 고객이 톡톡으로 메시지 전송 → 톡톡이 Webhook으로 `send` 이벤트 전달
2. 시스템은 **즉시 200 OK** 반환 (3~5초 제약 준수) ([GitHub][1])
3. 비동기 워커가:

   * 채널별+공통 Docs에서 RAG 검색
   * gpt-4o-mini로 답변 초안 생성
   * Google Sheets에 `(질문, 답변, 채널, user id, confidence, 근거요약...)` 기록
4. 고객에게는 **아무 메시지도 보내지 않음(무응답)**
5. 운영자는 휴대폰 톡톡 앱으로 실시간 문의를 확인하고 필요 시 직접 응대

### 4.2 PROD 모드

1~3) 동일
4) 아래 조건이 모두 충족되면 자동 발송:

* 전역 플래그 = PROD
* 해당 채널 플래그 = PROD
* 답변 confidence가 기준 이상(정의는 7.3 참조)
* “금지 카테고리/불확실” 트리거 없음(정의는 7.4 참조)

5. 조건 미충족 시:

* **무응답 유지**
* 운영자에게 **Telegram 알림** 전송 (채널명, 상담자 id, 질문, 추천 답변 초안 포함)

---

## 5. 기능 요구사항 (Functional Requirements)

### 5.1 채널 라우팅 / 확장성

* 각 채널(wc******)은 파트너센터에서 **Webhook URL을 채널별로 개별 설정 가능**하므로, 다음 형태로 구성:

  * `POST /naver/talktalk/{channel_id}/webhook`
* 장점:

  * 이벤트 payload에 channel id가 없더라도 **URL path로 확정 라우팅**
  * 16→N 확장 시 **API Gateway 라우트는 동일**, DynamoDB/설정만 추가

### 5.2 Webhook 수신 처리

* 수신 이벤트: `open`, `send`만 처리 대상으로 설정 (echo 비활성 권장) ([NCloud Docs][2])
* Webhook 핸들러는 항상:

  * 입력 JSON 최소 스키마 검증
  * 내부 큐(SQS)로 적재
  * **즉시 200 OK 반환**

### 5.3 메시지 파싱

* 처리 대상:

  * `event == "send"`
  * `textContent.text` 존재 시 텍스트 문의로 처리
* 처리 제외/특이 케이스:

  * imageContent / compositeContent만 온 경우 → “불확실 케이스”로 분류
  * 텍스트가 너무 짧음(예: “?”, “ㅇㅇ”, “문의”, “안녕”) → “불확실 케이스”
* `send` 이벤트는 사용자와 파트너 모두 발생 가능함이 명시됨
  → 이벤트 루프 방지를 위해 echo를 꺼두고, 혹시 켜져 있으면 echo는 무시 ([GitHub][1])

### 5.4 RAG (Google Docs)

* 입력 지식원:

  * 채널별 Google Docs 묶음 (필수)
  * 공통 Google Docs 묶음 (필수)
* 인덱싱:

  * 문서 업데이트 월 1회 수준 → **스케줄 동기화(예: 매일/매주 변경감지 후 재색인)** + **수동 재색인 트리거** 제공
* 검색:

  * 채널 index topK + 공통 index topK를 결합하여 컨텍스트 구성

### 5.5 LLM 답변 생성 (gpt-4o-mini)

* LLM의 결과는 반드시 **구조화된 JSON**으로 반환 (후처리/검증/로그 목적)
* 산출물:

  * `draft_answer` (시트 기록용 초안)
  * `confidence` (0~1)
  * `send_to_user` (boolean)
  * `needs_operator` (boolean)
  * `reasons` (왜 무응답/알림인지)
  * `citations` (내부용: 어떤 문서 chunk를 근거로 했는지)

### 5.6 Google Sheets 기록 (TEST 필수, PROD 선택)

* TEST 모드: 모든 문의에 대해 **반드시 기록**
* PROD 모드: 기본은 기록 유지(품질/감사 추적), 다만 비용/정책에 따라 옵션화 가능
* 기록 최소 컬럼(필수):

  * timestamp(KST)
  * channel_id
  * channel_name
  * user_id (톡톡 이벤트의 user)
  * question_raw
  * answer_draft
  * confidence
  * global_mode, channel_mode
  * send_to_user 결과(“NOT_SENT/ SENT”)
  * telegram_alert_sent(Y/N)
* 권장 컬럼:

  * retrieved_sources(문서명/섹션)
  * failure_reason / error_stack_id
  * latency_ms (RAG/LLM/Sheet 각각)

### 5.7 Telegram 알림

* 트리거:

  1. `needs_operator == true` (불확실/정책상 무응답)
  2. 시스템 오류(문서 인덱스 없음, OpenAI 실패, Sheets 실패 등)
  3. (옵션) PROD에서 `send_to_user==false`인 모든 케이스
* 알림 내용(필수 포함):

  * 채널명, 채널ID
  * 상담자 id(user_id)
  * 질문 원문(또는 마스킹된 원문)
  * 추천 답변 초안(draft_answer)
  * “왜 알림인지” 요약(reasons)
* 보안:

  * Telegram 메시지에는 **전화번호/이메일 등 PII 마스킹 적용**(6.3 참조)

### 5.8 실사용 자동응답(보내기 API)

* 전송 조건: 4.2의 조건 충족 시에만
* 전송 방식: **비동기식** 권장

  * Webhook은 200 OK로 즉시 응답 후, 별도로 보내기 API 호출
  * 공식 문서에서도 동기/비동기 방식을 구분하며, 비동기식은 200 OK 후 보내기 API로 전송하는 방식으로 설명됨 ([GitHub][1])
* 헤더:

  * `Authorization: <채널별 토큰>`
  * `Content-Type: application/json;charset=UTF-8`
* 토큰 관리:

  * 채널별 Authorization 토큰은 **Secrets Manager**에 저장
  * 파트너센터에서 유출 시 재설정 가능(운영 런북 포함) ([GitHub][1])

---

## 6. 비기능 요구사항 (NFR)

### 6.1 성능

* Webhook ACK: **< 500ms 목표**, 최대한 빠르게(네이버 타임아웃 3s/5s) ([GitHub][1])
* E2E(수신→Sheet 기록): **1분 이내** 목표
* 일 최대 50건 기준, 동시성은 낮으나 **스파이크(짧은 시간 5~10건)**는 흡수 가능해야 함

### 6.2 안정성/재처리

* SQS 기반 at-least-once 처리
* idempotency(중복 처리 방지):

  * `dedup_key = hash(channel_id + user_id + normalized_text + time_bucket)`
  * DynamoDB TTL(예: 10분)로 중복 방지

### 6.3 보안/마스킹 정책

* Google Sheets: 원문 저장 허용(요구)
* 그 외(CloudWatch 로그, Telegram, 오류 알림, 대시보드): **마스킹 필수**

  * 전화번호/이메일/긴 숫자열(주문번호 추정) 정규식 마스킹
  * 마스킹 예: `010-1234-5678 → 010-****-5678`, `abc@domain.com → a***@domain.com`

### 6.4 비용 효율

* 저트래픽(일 50건) 기준:

  * **서버리스 우선**(API Gateway + Lambda + SQS)
  * 벡터DB는 상시 과금형 대신 **S3에 인덱스 저장(FAISS 등)** 방식을 1순위로 권장(7.2 참조)
  * OpenAI 호출 최적화(짧은 컨텍스트, topK 제한, 캐시)

---

## 7. 권장 아키텍처 (AWS, 비용 효율 우선)

### 7.1 컴포넌트

* **API Gateway**: `POST /naver/talktalk/{channel_id}/webhook`
* **Lambda(ingest)**: 검증 → SQS enqueue → 200 OK
* **SQS**: 이벤트 큐
* **Lambda(worker)**: RAG + LLM + Sheets + (조건부) send API + Telegram
* **DynamoDB**

  * ChannelConfig 테이블(채널명, 문서매핑, 채널모드, secrets arn 등)
  * Dedup 테이블(TTL)
  * (옵션) Conversation state(최근 메시지)
* **S3**

  * Google Docs 원문 스냅샷
  * 채널별/공통 벡터 인덱스 파일(FAISS) + 메타데이터(JSONL)
* **EventBridge Scheduler**

  * 문서 동기화/인덱스 재생성 주기 실행(매일 변경 감지 or 주 1회)
* **Secrets Manager**

  * OpenAI API Key
  * 채널별 톡톡 Authorization 토큰
  * Google Service Account key(가능하면 keyless 권장)
  * Telegram Bot Token

### 7.2 벡터 인덱스 전략 (권장안)

**권장(저비용)**: “S3 + FAISS 인덱스 파일”

* 장점: 상시 과금형 벡터DB 불필요, 월 1회 업데이트에 적합
* 단점: 워커가 S3에서 인덱스를 가져오는 비용/시간(캐시로 완화)

**대안**: OpenSearch Serverless(Vector) / Aurora PGVector

* 데이터가 급증하거나, 문서/질문량이 커지면 전환 고려

### 7.3 Confidence 산정 (운영 규칙)

`send_to_user = true` 조건(예시, 튜닝 가능):

* RAG top1 유사도 ≥ T1 AND topK 평균 ≥ T2
* 답변이 문서 근거에 의해 “정책/절차/기간/방법” 형태로 구성 가능
* 금지 트리거 없음(7.4)

그 외는:

* `send_to_user=false`, `needs_operator=true`, Telegram 알림

### 7.4 “무응답 + Telegram” 트리거 (불확실/금지)

* 문의가 너무 짧거나 맥락 없음
* 문서 근거 부족(유사도 낮음 / 검색 결과 0)
* 이미지/복합 메시지(텍스트 부재)
* 법적/환불 분쟁/개인정보/주문조회 등 “실수 리스크 높은” 키워드 포함(초기엔 보수적으로)
* LLM이 내부적으로 “확신 낮음” 판단(confidence 하락)

> 고객에게 “상담원 연결” 등 안내 메시지를 보내지 않고, **그냥 무응답**이 정책입니다.

---

## 8. 데이터 모델

### 8.1 ChannelConfig (DynamoDB)

* `channel_id` (PK) 예: wc******
* `channel_name` (운영자 표시명)
* `channel_mode` : `TEST | PROD | DISABLED`
* `docs_channel_ids[]` : 채널 전용 Google Doc ID 리스트
* `docs_common_ids[]` : 공통 Doc ID 리스트(보통 전역 공통을 참조)
* `talktalk_auth_secret_arn` : 보내기 API용 Authorization 토큰(채널별)
* `sheet_id`, `sheet_tab`
* `telegram_target` (chat_id 또는 대상 그룹)
* `index_s3_uri` (채널 인덱스 최신 경로)
* `index_version`, `updated_at`

### 8.2 GlobalMode (SSM Parameter Store 권장)

* Key: `TT_GLOBAL_MODE`
* Value: `TEST | PROD`

**모드 결정 로직**

* global=TEST → 무조건 무응답 + Sheet 기록
* global=PROD → channel_mode=PROD인 채널만 자동응답 후보

---

## 9. LLM 프롬프트/출력 규격 (LLM 구현 핵심)

### 9.1 System Prompt(요약)

* 당신은 해당 채널의 고객응대 담당자
* 말투: 존댓말 + 친근 + 이모지(과하지 않게)
* 절대 금지:

  * “모르겠습니다/확실치 않습니다/추측입니다”
  * “상담원에게 연결해드릴게요” 류
* 근거는 RAG 컨텍스트만 사용(문서에 없는 내용은 단정 금지)
* 불확실하면:

  * `send_to_user=false`
  * `needs_operator=true`
  * `reasons`에 이유 기재
  * `draft_answer`는 운영자 참고용으로 최대한 도움이 되게 작성(고객에게 보내지 않음)

### 9.2 RAG 컨텍스트 포맷

* `<KB>` 블록에 chunk를 넣고
* chunk마다 `{doc_title, section, updated_at, chunk_text}` 메타 포함
* 모델이 `citations`에 chunk id를 반환하도록 유도

### 9.3 LLM 출력 JSON 스키마 (강제)

```json
{
  "draft_answer": "고객에게 보낼 수 있는 형태의 답변 초안(존댓말+친근+이모지)",
  "confidence": 0.0,
  "send_to_user": false,
  "needs_operator": true,
  "reasons": ["근거 부족", "질문이 너무 짧음"],
  "citations": [
    {"doc_id":"...", "doc_title":"...", "section":"...", "chunk_id":"..."}
  ],
  "followup_questions_for_operator": ["운영자가 확인해야 할 질문(내부용)"]
}
```

---

## 10. 운영/모니터링

### 10.1 메트릭 (CloudWatch)

* webhook_request_count / 2xx 비율
* queue_depth, worker_success_rate
* openai_latency_ms, openai_error_rate
* sheets_append_success_rate
* telegram_alert_count
* (PROD) talktalk_send_success_rate

### 10.2 알람

* SQS 적체(큐 길이 임계치)
* OpenAI 에러율 급증
* Sheets 기록 실패 연속 N회
* (PROD) 보내기 API 실패 연속 N회

### 10.3 런북(요약)

* 보내기 API 토큰 유출/노출 시: 파트너센터에서 재설정 → Secrets Manager 업데이트 → 배포 ([GitHub][1])
* echo 이벤트 켜짐 감지 시: 파트너센터 Event 선택에서 echo 비활성(루프 위험) ([GitHub][1])

---

## 11. 테스트/검수 계획

### 11.1 TEST 모드 수용 기준

* 톡톡으로 **어떠한 자동 메시지도 발송되지 않음**(0건)
* 모든 `send` 이벤트에 대해 Google Sheets row가 생성됨
* RAG 근거/답변 초안이 정상 생성됨
* 불확실 케이스에서 Telegram 알림이 전송됨(채널명, user_id 포함)

### 11.2 PROD 전환(부분 롤아웃)

* global=PROD 전환 전:

  * 특정 1~2개 채널만 channel_mode=PROD로 먼저 테스트
* 자동응답이 실제 고객에게 나가므로,

  * 초기에는 threshold를 보수적으로(더 많이 무응답+알림) 설정

---

## 12. 구현 체크리스트 (필요 입력값/리소스)

PRD 기준으로 개발 착수 시 아래 값들이 준비되면 바로 구현 가능합니다.

* 채널 목록: `channel_id(wc******)` 16개 + 채널명 매핑
* 채널별:

  * 파트너센터 Webhook URL 등록 (send/open 선택)
  * 보내기 API Authorization 토큰 생성 후 안전 보관(Secrets Manager 입력)
* Google Docs:

  * 채널별 문서 ID 리스트
  * 공통 문서 ID 리스트
  * 서비스 계정(또는 OAuth) 접근 권한 부여
* Google Sheets:

  * Sheet ID, Tab 이름, 컬럼 정의
  * 서비스 계정 접근 권한 부여
* Telegram:

  * Bot Token
  * 알림 받을 chat_id(개인/그룹)
* OpenAI:

  * API Key
  * 사용 모델: gpt-4o-mini (+ embeddings 모델 1종)

---

## 13. 참고(왜 이렇게 설계했는가)

* 톡톡 Webhook 타임아웃이 짧아(3초/5초) 즉시 ACK + 비동기 처리가 안전합니다. ([GitHub][1])
* 보내기 API는 Authorization 헤더를 포함해 `gw.talk.naver.com/chatbot/v1/event`로 전송하는 방식이 문서에 제시되어 있고, 인증 키는 파트너센터에서 생성/재설정하는 것으로 명시됩니다. ([GitHub][1])
* echo 이벤트는 루프 위험이 명시되어 있어, 본 프로젝트는 기본적으로 echo를 사용하지 않는 구성이 안정적입니다. ([GitHub][1])