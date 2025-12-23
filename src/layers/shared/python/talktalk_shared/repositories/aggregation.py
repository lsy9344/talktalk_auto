"""
AggregationRepository - DynamoDB access layer for message aggregation

Handles CRUD operations for AggregationState table.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from talktalk_shared.config import (
    get_aggregation_state_table,
    get_aggregation_window_seconds,
    get_aws_region,
)
from talktalk_shared.models.aggregation_state import AggregationState, AggregationStatus
from talktalk_shared.utils.logger import get_logger
from talktalk_shared.utils.masking import mask_user_id

logger = get_logger(__name__)


def _mask_user_key(user_key: str) -> Dict[str, str]:
    if "#" not in user_key:
        return {"user_key": "****"}
    channel_id, user_id = user_key.split("#", 1)
    return {"channel_id": channel_id, "user_id_masked": mask_user_id(user_id)}


class AggregationRepository:
    """Repository for AggregationState DynamoDB table"""

    def __init__(self) -> None:
        """Initialize repository with DynamoDB client"""
        self.table_name = get_aggregation_state_table()
        self.dynamodb = boto3.resource("dynamodb", region_name=get_aws_region())
        self.table = self.dynamodb.Table(self.table_name)

    def get_active(self, user_key: str) -> Optional[AggregationState]:
        """
        Get active aggregation for a user.

        Queries for AGGREGATING status using pk only (latest aggregation_id).

        Args:
            user_key: User key (channel_id#user_id)

        Returns:
            AggregationState if active aggregation exists, None otherwise
        """
        try:
            # Query all items for this user_key, sort by aggregation_id descending
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                FilterExpression="#status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":pk": user_key,
                    ":status": AggregationStatus.AGGREGATING.value,
                },
                ScanIndexForward=False,  # Latest first
                Limit=1,
            )

            items = response.get("Items", [])
            if not items:
                logger.info("No active aggregation found", extra=_mask_user_key(user_key))
                return None

            state = AggregationState.from_dynamodb_item(items[0])
            logger.info(
                "Active aggregation found",
                extra={**_mask_user_key(user_key), "aggregation_id": state.aggregation_id},
            )
            return state

        except ClientError as e:
            logger.error(
                "Failed to query active aggregation",
                extra={**_mask_user_key(user_key), "error": str(e)},
                exc_info=True,
            )
            raise

    def get(self, user_key: str, aggregation_id: str) -> Optional[AggregationState]:
        """
        Get specific aggregation by user_key and aggregation_id.

        Args:
            user_key: User key (channel_id#user_id)
            aggregation_id: Aggregation ID (ISO 8601 timestamp)

        Returns:
            AggregationState if exists, None otherwise
        """
        try:
            response = self.table.get_item(Key={"pk": user_key, "aggregation_id": aggregation_id})

            item = response.get("Item")
            if not item:
                logger.info(
                    "Aggregation not found",
                    extra={**_mask_user_key(user_key), "aggregation_id": aggregation_id},
                )
                return None

            state = AggregationState.from_dynamodb_item(item)
            logger.info(
                "Aggregation retrieved",
                extra={
                    **_mask_user_key(user_key),
                    "aggregation_id": aggregation_id,
                    "message_count": state.message_count,
                },
            )
            return state

        except ClientError as e:
            logger.error(
                "Failed to get aggregation",
                extra={
                    **_mask_user_key(user_key),
                    "aggregation_id": aggregation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def create(self, user_key: str, webhook_event: Dict[str, Any]) -> AggregationState:
        """
        Create new aggregation session.

        Args:
            user_key: User key (channel_id#user_id)
            webhook_event: Initial webhook event

        Returns:
            Created AggregationState
        """
        aggregation_id = AggregationState.make_aggregation_id()
        now = datetime.utcnow()
        window_seconds = get_aggregation_window_seconds()
        started_at = now.isoformat() + "Z"
        expires_at = (now + timedelta(seconds=window_seconds)).isoformat() + "Z"
        ttl = int((now + timedelta(minutes=5)).timestamp())

        # Extract message text
        text = ""
        if webhook_event.get("textContent"):
            text = webhook_event["textContent"].get("text", "")

        # Create state
        state = AggregationState(
            pk=user_key,
            aggregation_id=aggregation_id,
            messages=[],
            status=AggregationStatus.AGGREGATING,
            started_at=started_at,
            expires_at=expires_at,
            message_count=0,
            ttl=ttl,
        )

        # Add first message
        state.add_message(timestamp=started_at, text=text, webhook_event=webhook_event)

        try:
            # Conditional put - ensure aggregation_id doesn't exist
            self.table.put_item(
                Item=state.to_dynamodb_item(),
                ConditionExpression="attribute_not_exists(aggregation_id)",
            )

            logger.info(
                "Aggregation created",
                extra={**_mask_user_key(user_key), "aggregation_id": aggregation_id},
            )
            return state

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning(
                    "Aggregation already exists",
                    extra={**_mask_user_key(user_key), "aggregation_id": aggregation_id},
                )
                raise ValueError(f"Aggregation {aggregation_id} already exists")
            else:
                logger.error(
                    "Failed to create aggregation",
                    extra={**_mask_user_key(user_key), "error": str(e)},
                    exc_info=True,
                )
                raise

    def add_message(
        self, user_key: str, aggregation_id: str, webhook_event: Dict[str, Any]
    ) -> AggregationState:
        """
        Add message to existing aggregation.

        Args:
            user_key: User key (channel_id#user_id)
            aggregation_id: Aggregation ID
            webhook_event: Webhook event to add

        Returns:
            Updated AggregationState
        """
        # Extract message text and timestamp
        text = ""
        if webhook_event.get("textContent"):
            text = webhook_event["textContent"].get("text", "")
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            # Update using atomic list append
            response = self.table.update_item(
                Key={"pk": user_key, "aggregation_id": aggregation_id},
                UpdateExpression=(
                    "SET messages = list_append(messages, :msg), "
                    "message_count = message_count + :inc"
                ),
                ExpressionAttributeValues={
                    ":msg": [
                        {"timestamp": timestamp, "text": text, "webhook_event": webhook_event}
                    ],
                    ":inc": 1,
                    ":status": AggregationStatus.AGGREGATING.value,
                },
                ConditionExpression="#status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ReturnValues="ALL_NEW",
            )

            updated_item = response["Attributes"]
            state = AggregationState.from_dynamodb_item(updated_item)

            logger.info(
                "Message added to aggregation",
                extra={
                    **_mask_user_key(user_key),
                    "aggregation_id": aggregation_id,
                    "message_count": state.message_count,
                },
            )
            return state

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning(
                    "Cannot add message - aggregation not AGGREGATING",
                    extra={**_mask_user_key(user_key), "aggregation_id": aggregation_id},
                )
                raise ValueError(f"Aggregation {aggregation_id} is not in AGGREGATING status")
            else:
                logger.error(
                    "Failed to add message to aggregation",
                    extra={
                        **_mask_user_key(user_key),
                        "aggregation_id": aggregation_id,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

    def complete(self, user_key: str, aggregation_id: str) -> None:
        """
        Mark aggregation as completed.

        Args:
            user_key: User key (channel_id#user_id)
            aggregation_id: Aggregation ID
        """
        try:
            self.table.update_item(
                Key={"pk": user_key, "aggregation_id": aggregation_id},
                UpdateExpression="SET #status = :completed",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":completed": AggregationStatus.COMPLETED.value,
                    ":aggregating": AggregationStatus.AGGREGATING.value,
                },
                ConditionExpression="#status = :aggregating",
            )

            logger.info(
                "Aggregation completed",
                extra={**_mask_user_key(user_key), "aggregation_id": aggregation_id},
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning(
                    "Cannot complete - aggregation not AGGREGATING",
                    extra={**_mask_user_key(user_key), "aggregation_id": aggregation_id},
                )
            else:
                logger.error(
                    "Failed to complete aggregation",
                    extra={
                        **_mask_user_key(user_key),
                        "aggregation_id": aggregation_id,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

    def cancel(self, user_key: str, aggregation_id: str) -> None:
        """
        Cancel aggregation (mark as CANCELLED).

        Args:
            user_key: User key (channel_id#user_id)
            aggregation_id: Aggregation ID
        """
        try:
            self.table.update_item(
                Key={"pk": user_key, "aggregation_id": aggregation_id},
                UpdateExpression="SET #status = :cancelled",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":cancelled": AggregationStatus.CANCELLED.value},
            )

            logger.info(
                "Aggregation cancelled",
                extra={**_mask_user_key(user_key), "aggregation_id": aggregation_id},
            )

        except ClientError as e:
            logger.error(
                "Failed to cancel aggregation",
                extra={
                    **_mask_user_key(user_key),
                    "aggregation_id": aggregation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
