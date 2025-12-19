from __future__ import annotations

import hashlib
import time

from botocore.exceptions import ClientError

from .aws_clients import dynamodb_resource
from .settings import get_settings


def build_dedup_key(channel_id: str, user_id: str, text: str, bucket: int) -> str:
    raw = f"{channel_id}:{user_id}:{text}:{bucket}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def claim_dedup(dedup_key: str, ttl_seconds: int) -> bool:
    settings = get_settings()
    if not settings.dedup_table:
        return True

    table = dynamodb_resource().Table(settings.dedup_table)
    expires_at = int(time.time()) + ttl_seconds
    try:
        table.put_item(
            Item={"dedup_key": dedup_key, "expires_at": expires_at},
            ConditionExpression="attribute_not_exists(dedup_key)",
        )
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        raise
