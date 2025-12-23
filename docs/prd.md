# PRD v1.1 — 네이버 톡톡(16개 wc 채널) 문의 응답 자동화

**RAG(Google Docs) + OpenAI(gpt-4o-mini) + AWS + TEST(시트 기록) / PROD(자동 발송)**

## 0) 변경 이력

* **v1.0**: 범위/아키텍처/플래그/보안/테스트 정의
* **v1.1(이번 문서)**:

  * **LLM Prompt Pack(전문)** 추가
  * **Google Sheets 스키마/템플릿** 추가
  * **Telegram 알림 템플릿** 추가
  * **자동 발송/무응답/알림 의사결정 규칙** 구체화
  * **Naver TalkTalk API 핵심 스펙 근거(공식 문서) 반영**

---

## 1) 배경/목표/정책(확정)

### 1.1 목표

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

### 1.2 고객 커뮤니케이션 정책(매우 중요)

* **모른다는 말 금지**(고객에게 “모르겠습니다/애매합니다/추측입니다” 등 금지)
* **상담원 연결 안내 문구 금지**(“상담원에게 연결할게요” 금지)
* 애매/불확실/리스크 케이스는:

  * 고객에게는 **무응답 유지**
  * 운영자에게 **Telegram 알림(채널명 + 상담자 id 포함)**

---

## 2) 외부 연동 제약(네이버 톡톡)

### 2.1 Webhook 운영 제약

* Webhook은 **TLS 기반**이어야 하며, ACL이 필요하면 지정된 IP 대역을 allowlist 해야 합니다. ([GitHub][1])
* 톡톡 Webhook 호출 타임아웃이 **Connection 3초 / Read 5초**로 짧습니다. ([GitHub][1])
  → 따라서 **Webhook은 즉시 200 OK 반환 + 비동기 처리**가 기본 설계입니다.

### 2.2 보내기 API(자동 응답 전송) — PROD에서만

* 보내기 API 호출 예시는 다음과 같습니다(공식):

  * `POST https://gw.talk.naver.com/chatbot/v1/event`
  * Header에 `Authorization` 필요
  * Body에 `"event":"send"`, `"user":"..."`, `"textContent":{"text":"..."}` ([GitHub][1])
* **Authorization(인증 키)** 는 파트너센터 “API 설정 > 보내기 API”에서 생성/재설정 가능합니다. ([GitHub][1])
* (참고) Naver Cloud 문서에서는 이 Authorization 값을 “channel access token”으로 설명합니다. ([NCloud Docs][2])

### 2.3 동기/비동기 응답 방식

* 공식 문서에서 “동기식(웹훅 응답 body로 send)”과 “비동기식(200 OK 후 보내기 API)”를 구분합니다. ([GitHub][1])
* 본 PRD는 **목표 응답 1분** + Webhook 5초 제약 때문에 **비동기식을 표준**으로 채택합니다.

### 2.4 이벤트/루프 위험(echo)

* `send` 이벤트는 user/partner 모두 발생 가능하며, 메시지 타입은 text/image/composite 등이 있습니다. ([GitHub][1])
* `echo` 이벤트는 상담사/챗봇이 보낸 메시지까지 다시 수신할 수 있어, 재전송하면 무한 루프 위험이 명시됩니다. ([GitHub][1])
  → 운영 안정성을 위해 **echo 이벤트는 기본 비활성**(필요 시 별도 테스트 후 제한적으로).

---

## 3) 시스템 개요(Architecture)

### 3.1 권장 AWS 구성(비용 효율 우선)

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

---

## 4) 핵심 기능 요구사항(요약)

### 4.1 채널 확장/라우팅

* 채널별 Webhook URL을 개별 등록 가능하므로(당신 확답), URL에 channel_id를 포함:

  * `/naver/talktalk/wc123.../webhook`
* channel_id 기반으로 ChannelConfig 로드

### 4.2 TEST 모드(기본)

* 고객 메시지 수신 → **무조건 무응답**(send API 호출 금지)
* Google Sheets에 질문/답변 초안 기록
* 불확실/오류 케이스는 Telegram 알림(운영자 대응)

### 4.3 PROD 모드(실사용)

* 전역 모드=PROD & 채널 모드=PROD & LLM 판단 send_to_user=true 인 경우만 자동 발송
* 그 외는 **무응답 + Telegram 알림**

---

# 5) 의사결정 로직(매우 구체화)

## 5.1 파이프라인 상태 머신

* `RECEIVED` (Webhook 수신)
* `QUEUED` (SQS 적재)
* `PROCESSING` (Worker 처리 중)
* `LOGGED` (Sheets 기록 완료)
* `SENT` (PROD 발송 성공)
* `NOT_SENT` (정책상 무응답)
* `ALERTED` (Telegram 전송 완료)
* `FAILED` (재시도 후 실패/데드레터)

## 5.2 자동 발송(send_to_user=true) 허용 조건

아래 모두 충족 시에만 발송:

1. `GLOBAL_MODE == PROD`
2. `CHANNEL_MODE[channel_id] == PROD`
3. `confidence >= threshold` (초기 권장 0.75~0.85로 보수적 시작)
4. `risk_level != HIGH`
5. `policy_flags`에 금지 항목 없음

## 5.3 무응답 + Telegram 알림 트리거(운영자 개입 필요)

* RAG 근거 부족(검색 결과 부실/유사도 낮음)
* 주문/결제/개인정보/분쟁 등 리스크 HIGH로 분류
* 이미지/복합 메시지인데 텍스트 부재
* 질문이 지나치게 짧거나(“?”, “ㅇㅇ”, “문의요”) 정보 부족
* LLM 출력 검증 실패(JSON 파싱 실패 등)
* 외부 연동 실패(OpenAI/Sheets/Send API 오류)

---

# 6) RAG 설계(구현 지침 포함)

## 6.1 문서 구조

* **채널 전용 KB**: channel_id → doc_id 리스트
* **공통 KB**: common_doc_id 리스트 (모든 채널에 공통 적용)

## 6.2 수집/동기화(월 1회 업데이트 최적화)

* 스케줄: **주 1회**(혹은 매일 변경 감지) + 수동 재색인
* 변경 감지:

  * Google Docs revisionId/modifiedTime 비교(가능한 API 범위 내)
  * 변경 없으면 스킵하여 비용 최소화

## 6.3 Chunking 권장 규칙

* 제목/소제목 기준 분할 + 400~800 tokens 내외(너무 작으면 문맥 부족)
* chunk 메타데이터:

  * `doc_id`, `doc_title`, `section_path`, `updated_at`, `channel_id/common`, `chunk_id`

## 6.4 Retrieval 전략(저비용/충분성)

* 1차(채널 KB): topK=4~6
* 2차(공통 KB): topK=2~4
* 결과 합쳐 6~10 chunks 이내로 제한(토큰 비용 관리)

---

# 7) LLM Prompt Pack (전문)

> 아래 프롬프트는 그대로 **코드에 박아도 되는 “템플릿”**입니다.
> `{{변수}}`는 런타임 치환값입니다.

---

## 7.1 System Prompt (고정)

```text
당신은 네이버 톡톡에서 고객 문의에 답변 초안을 작성하는 담당자입니다.

목표:
- 제공된 지식베이스(KB) 내용에 근거해, 고객에게 보낼 수 있는 “답변 초안”을 생성합니다.
- 답변이 불확실하거나 리스크가 크면 고객에게 보내지 말고(무응답), 운영자에게 알릴 수 있도록 구조화된 신호를 출력합니다.

말투/톤:
- 한국어
- 존댓말 + 친근한 말투
- 이모지는 0~2개 정도로 과하지 않게 사용

절대 금지(고객에게 나갈 문장 기준):
- “모르겠습니다 / 확실하지 않습니다 / 잘 모르겠어요 / 추측입니다” 등 무지/불확실을 직접 표현
- “상담원에게 연결해드릴게요 / 담당자 연결” 등 안내 문구
- KB에 없는 사실을 단정하거나, 정책/기간/금액을 임의로 생성

불확실/애매/리스크가 있으면:
- 고객에게는 보내지 않습니다(send_to_user=false)
- needs_operator=true로 표시하고, reasons에 왜 그런지 적습니다.
- 운영자가 바로 판단할 수 있도록 followup_questions_for_operator를 최대한 구체적으로 작성합니다.

출력은 반드시 JSON 형식만 반환합니다(설명 텍스트 금지).
```

---

## 7.2 Developer Prompt (정책/스키마 강제)

```text
너는 반드시 아래 JSON 스키마를 준수해서만 출력한다.
추가 텍스트/코드블록/마크다운/설명 문장을 출력하면 실패로 간주된다.

[JSON 스키마]
{
  "draft_answer": "string",
  "confidence": "number (0.0~1.0)",
  "send_to_user": "boolean",
  "needs_operator": "boolean",
  "risk_level": "string (LOW|MEDIUM|HIGH)",
  "reasons": ["string", "..."],
  "citations": [
    {
      "doc_id": "string",
      "doc_title": "string",
      "section_path": "string",
      "chunk_id": "string"
    }
  ],
  "followup_questions_for_operator": ["string", "..."],
  "suggested_quick_reply": ["string", "..."]
}

[추가 규칙]
- draft_answer는 “고객에게 보내도 되는 완성형 문장”으로 작성하되,
  send_to_user=false인 경우에도 운영자 참고용으로 최대한 도움이 되게 작성한다.
- KB 근거가 충분하지 않으면 send_to_user=false로 한다.
- citations는 실제로 참고한 KB chunk만 넣는다(없으면 빈 배열).
- risk_level HIGH인 경우는 원칙적으로 send_to_user=false.
```

---

## 7.3 User Prompt Template (런타임 구성)

```text
[채널 정보]
- channel_id: {{channel_id}}
- channel_name: {{channel_name}}

[운영 모드]
- global_mode: {{global_mode}}   (TEST|PROD)
- channel_mode: {{channel_mode}} (TEST|PROD|DISABLED)

[고객 메시지]
- user_id: {{user_id}}
- message: {{question_raw}}

[추가 컨텍스트(있으면 제공)]
- inflow: {{inflow}}
- referer: {{referer}}
- from: {{from}}

[지식베이스(KB) - 발췌]
아래 KB 내용만 근거로 사용해 답변 초안을 작성하라.
KB에 없는 정보는 단정하지 말고, 운영자 확인이 필요하면 send_to_user=false로 하라.

{{kb_chunks}}
```

---

## 7.4 KB Chunks 포맷(권장)

```text
<KB>
[1] doc_id={{doc_id}} | title={{doc_title}} | section={{section_path}} | updated_at={{updated_at}} | chunk_id={{chunk_id}}
{{chunk_text}}

[2] doc_id=...
...
</KB>
```

---

## 7.5 LLM 출력 예시(샘플)

### (A) 자동 발송 가능(LOW)

```json
{
  "draft_answer": "안녕하세요 😊 교환은 상품 수령 후 7일 이내에 가능하세요. 교환 접수는 ① 주문번호 ② 교환 사유 ③ 희망 옵션을 알려주시면 순서대로 도와드릴게요!",
  "confidence": 0.86,
  "send_to_user": true,
  "needs_operator": false,
  "risk_level": "LOW",
  "reasons": ["KB에 교환 기간/절차가 명확히 기재됨"],
  "citations": [
    {"doc_id":"doc123","doc_title":"교환/환불 정책","section_path":"교환 > 접수 방법","chunk_id":"c_04"}
  ],
  "followup_questions_for_operator": [],
  "suggested_quick_reply": ["주문번호를 알려주세요", "교환 사유를 알려주세요"]
}
```

### (B) 애매/리스크(무응답 + Telegram)

```json
{
  "draft_answer": "확인해보면 더 정확히 안내드릴 수 있어요 😊 주문번호(또는 구매 채널)와 문제가 된 상황(불량/오배송/단순변심 등)을 알려주시면 처리 절차를 정리해드릴게요.",
  "confidence": 0.42,
  "send_to_user": false,
  "needs_operator": true,
  "risk_level": "HIGH",
  "reasons": ["주문/개인정보/결제 관련 가능성", "KB 근거 부족"],
  "citations": [],
  "followup_questions_for_operator": ["고객 주문번호 확인 필요", "결제/환불 상태 확인 필요", "채널별 정책 예외 여부 확인 필요"],
  "suggested_quick_reply": ["주문번호를 알려주세요", "구매처(스마트스토어/자사몰)를 알려주세요"]
}
```

---

# 8) Google Sheets 템플릿(공용 1개 시트)

## 8.1 시트 구성(권장)

* Google Spreadsheet 1개 파일
* 탭(시트) 2개 권장:

  * `inbox_log` : 모든 기록(질문/답변/상태)
  * `config_snapshot` : (선택) 현재 채널 모드/전역 모드 스냅샷(읽기용)

> 탭을 1개만 쓰고 싶으면 `inbox_log`만 운영해도 됩니다.

## 8.2 `inbox_log` 컬럼 정의(권장 스키마)

| 컬럼명                  | 타입       | 예시                        | 설명                                 |
| -------------------- | -------- | ------------------------- | ---------------------------------- |
| row_id               | string   | `20251219-000123`         | 내부 식별자(시간+증가값)                     |
| created_at_kst       | datetime | `2025-12-19 14:22:11`     | 기록 시각                              |
| channel_id           | string   | `wc******`                | 채널 식별                              |
| channel_name         | string   | `A스토어`                    | 사람이 알아보기 위한 이름                     |
| user_id              | string   | `al-...`                  | 톡톡 사용자 식별값(변하지 않는 값) ([GitHub][1]) |
| event                | string   | `send`                    | 이벤트명                               |
| question_raw         | string   | `교환 어떻게 해요?`              | 고객 원문(원문 저장 허용)                    |
| question_masked      | string   | `교환 어떻게 해요?`              | 로그/텔레그램용 마스킹 버전                    |
| kb_used              | string   | `doc123:c_04;doc999:c_02` | 사용한 chunk 요약(내부용)                  |
| draft_answer         | string   | `안녕하세요 😊 ...`            | LLM 답변 초안                          |
| confidence           | number   | `0.86`                    | 0~1                                |
| risk_level           | string   | `LOW`                     | LOW/MEDIUM/HIGH                    |
| send_to_user         | boolean  | `FALSE`                   | 자동 발송 여부(결과)                       |
| global_mode          | string   | `TEST`                    | TEST/PROD                          |
| channel_mode         | string   | `TEST`                    | TEST/PROD/DISABLED                 |
| action_taken         | string   | `NOT_SENT`                | NOT_SENT/SENT/FAILED               |
| talktalk_send_result | string   | `-`                       | PROD일 때 API 응답(성공/코드)              |
| telegram_alert_sent  | boolean  | `TRUE`                    | 알림 여부                              |
| telegram_reason      | string   | `KB 부족`                   | 알림 사유                              |
| latency_ms_total     | number   | `8421`                    | 처리 총 시간                            |
| error_summary        | string   | `-`                       | 오류 있으면 요약                          |

## 8.3 운영 규칙

* **TEST 모드**: `send_to_user`는 항상 `FALSE`, `action_taken=NOT_SENT`
* **PROD 모드**: 발송 성공 시 `action_taken=SENT`, 실패 시 `FAILED` + Telegram 알림
* PII 정책:

  * `question_raw`는 원문 저장 허용(요구사항)
  * `question_masked`는 마스킹 적용(텔레그램/로그에 사용)

---

# 9) Telegram 알림 템플릿(상황별)

## 9.1 공통 원칙

* Telegram에는 **민감정보 마스킹된 텍스트**를 기본으로 보냄
* 반드시 포함:

  * **채널명**
  * **channel_id**
  * **상담자 id(user_id)**
  * 질문 요약/원문(마스킹)
  * 추천 답변 초안(draft_answer)
  * 왜 알림인지(reasons)

## 9.2 메시지 포맷(Plain Text / Markdown 겸용)

### (A) 불확실/리스크로 무응답 처리

```text
[톡톡 알림] 운영자 확인 필요 ⚠️
- 채널: {{channel_name}} ({{channel_id}})
- 상담자ID: {{user_id}}
- 모드: global={{global_mode}} / channel={{channel_mode}}
- 사유: {{reasons_joined}}
- 위험도: {{risk_level}} / confidence={{confidence}}

[고객 질문(마스킹)]
{{question_masked}}

[추천 답변 초안(고객에게는 아직 미전송)]
{{draft_answer}}

[운영자 체크 질문]
- {{q1}}
- {{q2}}

[시트 Row]
row_id={{row_id}}
```

### (B) 시스템 오류(OpenAI/Sheets/Send API 실패 등)

```text
[톡톡 알림] 시스템 오류 🚨
- 채널: {{channel_name}} ({{channel_id}})
- 상담자ID: {{user_id}}
- 단계: {{stage}} (예: LLM_CALL / SHEETS_APPEND / SEND_API)
- 오류요약: {{error_summary}}

[고객 질문(마스킹)]
{{question_masked}}

[재시도]
- attempt={{attempt}} / max={{max_attempts}}
row_id={{row_id}}
```

### (C) PROD인데 정책으로 발송 막힘

```text
[톡톡 알림] PROD 발송 보류 ⛔
- 채널: {{channel_name}} ({{channel_id}})
- 상담자ID: {{user_id}}
- 사유: {{reasons_joined}}
- confidence={{confidence}} / risk={{risk_level}}

질문(마스킹): {{question_masked}}
초안: {{draft_answer}}
row_id={{row_id}}
```

## 9.3 알림 중복 방지(권장)

* 동일 `channel_id + user_id + 질문해시` 조합은 **5~10분 TTL**로 Telegram 중복 발송 방지

---

# 10) PROD 전송(보내기 API) 명세(확정)

## 10.1 요청 형태(공식 예시 기반)

```bash
curl -X POST \
  -H "Content-Type: application/json;charset=UTF-8" \
  -H "Authorization: <CHANNEL_AUTH_TOKEN>" \
  -d '{ "event": "send", "user": "<USER_ID>", "textContent": { "text": "hello world" } }' \
  "https://gw.talk.naver.com/chatbot/v1/event"
```

([GitHub][1])

* Authorization 토큰은 파트너센터에서 생성/재설정 가능 ([GitHub][1])
* Naver Cloud 문서에서도 이 값이 channel access token으로 사용됨을 언급 ([NCloud Docs][2])

## 10.2 비동기 처리 원칙

* Webhook은 200 OK로 즉시 응답 후, Worker에서 send API 호출
* 동기식은 5초 내 응답 가능할 때만 권장(공식) ([GitHub][1])

---

# 11) 테스트 체크리스트(확장)

## 11.1 TEST 모드 필수 통과 조건

* 톡톡으로 **자동 발송 0건**
* `send` 이벤트 수신 시 **Sheets row 100% 생성**
* 불확실/오류 케이스에서 Telegram 알림이 **누락 없이 도착**
* Webhook은 타임아웃 없이 안정적으로 200 OK 반환(3s/5s 제약 준수) ([GitHub][1])

## 11.2 PROD 전환 전 “안전장치”

* threshold를 높게(보수적으로) 시작: 0.85 권장
* risk_level HIGH는 무조건 무응답+알림
* echo 이벤트 비활성 유지(루프 위험) ([GitHub][1])

---

# 12) Go-Live 절차(운영 관점)

1. 16개 채널 모두 `channel_mode=TEST`, `global_mode=TEST`로 시작
2. 1~2주간 Sheet 검증(초안 품질/근거 적절성/알림 빈도 확인)
3. 채널별로 문서 보강(월 1회 업데이트 플로우에 반영)
4. 일부 채널만 `channel_mode=PROD`로 올려 “부분 준비”
5. 마지막에 `global_mode=PROD` 전환
6. 초기 1~3일은 Telegram 알림을 촘촘히 모니터링하며 threshold 튜닝

---

## 13) 구현자에게 중요한 메모(실수 방지)

* `user_id`는 변하지 않는 사용자 식별값으로 문서에 명시되어 있으며(대화 상대 식별), 이를 키로 상태/중복방지를 설계합니다. ([GitHub][1])
* `send` 이벤트는 text/image/composite 중 **하나만 선택**해야 합니다(발송 시). ([GitHub][1])
* echo는 루프 위험이 명시되어 있으므로 기본 비활성 권장 ([GitHub][1])
* Webhook 타임아웃(3s/5s) 때문에 “즉시 ACK + 비동기”가 안전합니다. ([GitHub][1])

---

원하면 다음 단계로 **PRD v1.2**도 바로 확장해드릴 수 있어요(질문 없이 진행 가능):

* “채널별 금지 키워드/리스크 룰” 초기 세트(환불/분쟁/개인정보 등)
* “RAG 품질을 올리는 문서 작성 가이드(운영자용)”
* “Sheet 기반으로 간단한 QA 워크플로(검수 상태: PASS/FAIL/수정필요)” 설계

원하시는 방향이 **(A) 리스크 룰부터**인지, **(B) 문서 작성 가이드부터**인지, 아니면 **둘 다**인지 한 줄로만 답 주시면 그걸로 이어서 v1.2까지 정리해드릴게요.

[1]: https://github.com/navertalk/chatbot-api "GitHub - navertalk/chatbot-api: 네이버톡톡 챗봇API V1"
[2]: https://guide.ncloud-docs.com/release-20250918/docs/en/chatbot-chatbot-5-3 "Connect to TalkTalk"
