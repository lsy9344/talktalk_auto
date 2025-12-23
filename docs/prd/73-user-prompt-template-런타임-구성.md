# 7.3 User Prompt Template (런타임 구성)

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
