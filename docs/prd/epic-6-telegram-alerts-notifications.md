# Epic 6: Telegram Alerts & Notifications

## Story 6.1: 공통 원칙

* Telegram에는 **민감정보 마스킹된 텍스트**를 기본으로 보냄
* 반드시 포함:

  * **채널명**
  * **channel_id**
  * **상담자 id(user_id)**
  * 질문 요약/원문(마스킹)
  * 추천 답변 초안(draft_answer)
  * 왜 알림인지(reasons)

## Story 6.2: 메시지 포맷(Plain Text / Markdown 겸용)

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

## Story 6.3: 알림 중복 방지(권장)

* 동일 `channel_id + user_id + 질문해시` 조합은 **5~10분 TTL**로 Telegram 중복 발송 방지

---
