# talktalk_auto

Serverless webhook + worker pipeline for Naver TalkTalk auto-draft replies with RAG (Google Docs) and OpenAI.

## Components

- `talktalk_auto/handlers/ingest.py` - API Gateway webhook Lambda. Validates payload, enqueues to SQS, returns 200 OK quickly.
- `talktalk_auto/handlers/worker.py` - SQS worker Lambda. Runs RAG + LLM, writes to Sheets, optional TalkTalk send, Telegram alerts.
- `scripts/build_index.py` - Build FAISS index from Google Docs and upload to S3.

## Requirements

- Python 3.11+
- AWS: API Gateway, SQS, Lambda, DynamoDB, SSM, S3, Secrets Manager
- Google Docs + Sheets service account access
- OpenAI API key
- Telegram bot token (optional but recommended)

## Environment

Use `.env.example` as a base.

Required at runtime:

- `SQS_QUEUE_URL`
- `CHANNEL_CONFIG_TABLE`
- `DEDUP_TABLE`
- `OPENAI_API_KEY`
- `COMMON_INDEX_S3_URI`
- `DEFAULT_SHEET_ID` (or channel-level `sheet_id` in DynamoDB)
- `TELEGRAM_BOT_TOKEN` or `TELEGRAM_BOT_TOKEN_SECRET_ARN`
- `DEFAULT_TELEGRAM_TARGET` (fallback chat_id when channel config is missing)
- `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_SERVICE_ACCOUNT_FILE`
- `FORBIDDEN_KEYWORDS` should be customized with Korean keywords for production

## DynamoDB

Channel config table (`CHANNEL_CONFIG_TABLE`) expects items like:

```
{
  "channel_id": "wc******",
  "channel_name": "My Channel",
  "channel_mode": "TEST",
  "docs_channel_ids": ["docId1", "docId2"],
  "docs_common_ids": ["commonDoc1"],
  "talktalk_auth_secret_arn": "arn:aws:secretsmanager:...",
  "sheet_id": "...",
  "sheet_tab": "Sheet1",
  "telegram_target": "123456789",
  "index_s3_uri": "s3://bucket/prefix",
  "index_version": "v1"
}
```

Dedup table (`DEDUP_TABLE`) uses `dedup_key` (PK) and `expires_at` (TTL).

## Index build

```
PYTHONPATH=. python scripts/build_index.py \
  --doc-ids "docId1,docId2" \
  --output-s3-uri "s3://bucket/prefix"
```

This uploads:

- `index.faiss`
- `metadata.jsonl`

## Lambda handlers

- Ingest handler: `talktalk_auto.handlers.ingest.handler`
- Worker handler: `talktalk_auto.handlers.worker.handler`

## Notes

- Webhook always returns 200 OK quickly and processes asynchronously.
- TEST mode records to Sheets and does not send messages.
- PROD mode requires both global + channel mode to be `PROD` and RAG thresholds.
