# 3) 시스템 개요(Architecture)

## 3.1 권장 AWS 구성(비용 효율 우선)

* **API Gateway**: `POST /naver/talktalk/{channel_id}/webhook`
* **Lambda(Ingest)**: 스키마 검증 → SQS enqueue → 즉시 200 OK
* **SQS**:

  * 이벤트 큐(유실 방지)
  * (추가) 30초 딜레이 큐(메시지 조합 완료 트리거)
* **Lambda(Worker)**: (필요 시) 메시지 조합(최대 30초) → RAG → LLM → Sheets 기록 → (PROD 조건부) 보내기 API 호출 → Telegram 알림
* **DynamoDB**

  * ChannelConfig (채널별 설정/문서매핑/채널 모드)
  * GlobalMode (전역 모드) 또는 SSM Parameter Store
  * Dedup(TTL)
  * (추가) AggregationState (메시지 조합 상태/TTL)
* **S3**

  * Google Docs 원문 스냅샷(선택)
  * 벡터 인덱스(FAISS 등) 저장(비용 절감)
* **EventBridge Scheduler**

  * 문서 동기화/재색인 스케줄(예: 매일/주1회 + 수동 트리거)
* **SSM Parameter Store (SecureString)**

  * `/talktalk-auto/secrets/openai-api-key`
  * `/talktalk-auto/secrets/google-sa-json` (Advanced SecureString)
  * `/talktalk-auto/secrets/telegram-bot-token`
  * `/talktalk-auto/channels/{channel_id}/talktalk-auth-token`

---
