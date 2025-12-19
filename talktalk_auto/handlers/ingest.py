import base64
import json

from talktalk_auto.logger import get_logger
from talktalk_auto.queue import enqueue_event


logger = get_logger(__name__)


def _extract_channel_id(event: dict) -> str:
    params = event.get("pathParameters") or {}
    channel_id = params.get("channel_id")
    if channel_id:
        return channel_id
    raw_path = event.get("rawPath") or event.get("path") or ""
    parts = [p for p in raw_path.split("/") if p]
    if len(parts) >= 3:
        return parts[-2] if parts[-1] == "webhook" else parts[-1]
    return ""


def handler(event, _context):
    channel_id = _extract_channel_id(event)
    body = event.get("body") or ""
    if event.get("isBase64Encoded") and body:
        body = base64.b64decode(body).decode("utf-8")

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        logger.warning("Invalid JSON payload")
        return {"statusCode": 200, "body": "OK"}

    if not channel_id:
        logger.warning("Missing channel_id")
        return {"statusCode": 200, "body": "OK"}

    try:
        enqueue_event(channel_id, payload)
    except Exception:
        logger.exception("Failed to enqueue event")

    return {"statusCode": 200, "body": "OK"}
