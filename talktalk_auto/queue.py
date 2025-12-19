import json
from datetime import datetime, timezone

from .aws_clients import sqs_client
from .settings import get_settings


def enqueue_event(channel_id: str, payload: dict) -> None:
    settings = get_settings()
    if not settings.sqs_queue_url:
        raise ValueError("SQS_QUEUE_URL is not configured")

    body = {
        "channel_id": channel_id,
        "payload": payload,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    sqs_client().send_message(
        QueueUrl=settings.sqs_queue_url,
        MessageBody=json.dumps(body, ensure_ascii=False),
    )
