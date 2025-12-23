# 9.2 메시지 포맷(Plain Text / Markdown 겸용)

## (A) 불확실/리스크로 무응답 처리

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

## (B) 시스템 오류(OpenAI/Sheets/Send API 실패 등)

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

## (C) PROD인데 정책으로 발송 막힘

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
