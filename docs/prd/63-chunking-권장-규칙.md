# 6.3 Chunking 권장 규칙

* 제목/소제목 기준 분할 + 400~800 tokens 내외(너무 작으면 문맥 부족)
* chunk 메타데이터:

  * `doc_id`, `doc_title`, `section_path`, `updated_at`, `channel_id/common`, `chunk_id`
