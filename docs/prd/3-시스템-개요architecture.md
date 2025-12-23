# 3) 시스템 개요(Architecture)

## 3.1 권장 AWS 구성(비용 효율 우선)

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
