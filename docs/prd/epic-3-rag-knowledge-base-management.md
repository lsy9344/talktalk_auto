# Epic 3: RAG & Knowledge Base Management

## Story 3.1: 문서 구조

* **채널 전용 KB**: channel_id → doc_id 리스트
* **공통 KB**: common_doc_id 리스트 (모든 채널에 공통 적용)

## Story 3.2: 수집/동기화(월 1회 업데이트 최적화)

* 스케줄: **주 1회**(혹은 매일 변경 감지) + 수동 재색인
* 변경 감지:

  * Google Docs revisionId/modifiedTime 비교(가능한 API 범위 내)
  * 변경 없으면 스킵하여 비용 최소화

## Story 3.3: Chunking 권장 규칙

* 제목/소제목 기준 분할 + 400~800 tokens 내외(너무 작으면 문맥 부족)
* chunk 메타데이터:

  * `doc_id`, `doc_title`, `section_path`, `updated_at`, `channel_id/common`, `chunk_id`

## Story 3.4: Retrieval 전략(저비용/충분성)

* 1차(채널 KB): topK=4~6
* 2차(공통 KB): topK=2~4
* 결과 합쳐 6~10 chunks 이내로 제한(토큰 비용 관리)

---
