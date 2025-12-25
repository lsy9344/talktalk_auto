"""Deduplication Repository - DynamoDB access layer"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from talktalk_shared.config import get_aws_region, get_deduplication_table
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)


class DeduplicationRepository:
    """Repository for Deduplication DynamoDB table"""

    def __init__(self) -> None:
        """Initialize repository with DynamoDB client"""
        self.table_name = get_deduplication_table()
        self.dynamodb = boto3.resource("dynamodb", region_name=get_aws_region())
        self.table = self.dynamodb.Table(self.table_name)

    def _generate_message_hash(self, webhook_body: Dict[str, Any]) -> str:
        """
        Generate deterministic hash from webhook body

        Args:
            webhook_body: Complete webhook payload dict

        Returns:
            First 16 characters of SHA256 hash

        Reference: docs/stories/1.2.story.md#Dev Notes - Dedup 규칙
        """
        # Sort keys and create deterministic JSON string
        json_str = json.dumps(
            webhook_body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        hash_digest = hashlib.sha256(json_str.encode()).hexdigest()
        return hash_digest[:16]

    def try_create(
        self, channel_id: str, user_id: str, webhook_body: Dict[str, Any], ttl_minutes: int = 10
    ) -> bool:
        """
        Try to create deduplication record. Returns False if duplicate exists.

        Args:
            channel_id: Channel ID
            user_id: User ID from webhook
            webhook_body: Complete webhook payload for hashing
            ttl_minutes: TTL in minutes (default: 10)

        Returns:
            True if created (not duplicate), False if duplicate

        Reference: docs/architecture.md#Data Models - DeduplicationRecord
        """
        message_hash = self._generate_message_hash(webhook_body)
        dedup_key = f"{channel_id}#{user_id}#{message_hash}"

        # Calculate TTL (Unix timestamp)
        ttl_timestamp = int((datetime.utcnow() + timedelta(minutes=ttl_minutes)).timestamp())

        try:
            # Conditional put - fails if dedup_key already exists
            self.table.put_item(
                Item={
                    "dedup_key": dedup_key,
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "message_hash": message_hash,
                    "processed_at": datetime.utcnow().isoformat(),
                    "ttl": ttl_timestamp,
                },
                ConditionExpression="attribute_not_exists(dedup_key)",
            )

            logger.info(f"Dedup record created: {channel_id}#{message_hash}")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Duplicate detected
                logger.info(f"Duplicate message detected: {channel_id}#{message_hash}")
                return False
            else:
                # Other DynamoDB error
                logger.error(
                    f"Failed to create dedup record: {channel_id}#{message_hash}",
                    extra={"error": str(e)},
                )
                raise

    def try_create_telegram_alert(
        self,
        channel_id: str,
        user_id: str,
        question_hash: str,
        ttl_minutes: int = 10,
    ) -> bool:
        """
        Try to create Telegram alert deduplication record.

        This is different from webhook dedup - it prevents alert spam
        based on question content hash.

        Args:
            channel_id: Channel ID
            user_id: User ID
            question_hash: Question text hash (from create_question_hash)
            ttl_minutes: TTL in minutes (default: 10)

        Returns:
            True if created (alert should be sent), False if duplicate (skip alert)

        Reference:
            - docs/stories/6.3.story.md#task-2-telegram-dedup-repository
            - docs/prd/93-알림-중복-방지권장.md
        """
        # AC1: Use TG# prefix to avoid collision with webhook dedup
        dedup_key = f"TG#{channel_id}#{user_id}#{question_hash}"

        # AC3: Calculate TTL (Unix timestamp)
        ttl_timestamp = int((datetime.utcnow() + timedelta(minutes=ttl_minutes)).timestamp())

        try:
            # AC1: Conditional put - fails if dedup_key already exists
            self.table.put_item(
                Item={
                    "dedup_key": dedup_key,
                    "channel_id": channel_id,
                    "question_hash": question_hash,
                    "alert_type": "telegram",
                    "created_at": datetime.utcnow().isoformat(),
                    "ttl": ttl_timestamp,
                },
                ConditionExpression="attribute_not_exists(dedup_key)",
            )

            # AC4: Log only hash, not raw question
            logger.info(
                "Telegram alert dedup record created",
                extra={"channel_id": channel_id, "question_hash": question_hash},
            )
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # AC1: Duplicate detected - skip Telegram alert
                logger.info(
                    "Duplicate Telegram alert detected - skipping",
                    extra={"channel_id": channel_id, "question_hash": question_hash},
                )
                return False
            else:
                # Other DynamoDB error
                logger.error(
                    "Failed to create Telegram dedup record",
                    extra={
                        "channel_id": channel_id,
                        "question_hash": question_hash,
                        "error": str(e),
                    },
                )
                raise
