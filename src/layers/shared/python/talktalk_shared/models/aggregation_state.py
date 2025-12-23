"""
AggregationState Model

Represents message aggregation state stored in DynamoDB.
Used for 30-second time window message collection.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class AggregationStatus(str, Enum):
    """Aggregation session status"""

    AGGREGATING = "AGGREGATING"  # Currently collecting messages
    COMPLETED = "COMPLETED"  # Finalized and processed
    CANCELLED = "CANCELLED"  # Cancelled due to error or timeout


class AggregatedMessage(BaseModel):
    """Single message within an aggregation session"""

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    text: str = Field(..., description="Message text content")
    webhook_event: Dict[str, Any] = Field(..., description="Original webhook event")


class AggregationState(BaseModel):
    """
    Message aggregation state model.

    Stores messages collected during 30-second time window.
    Maps to DynamoDB AggregationState table.

    Reference: docs/stories/2.5.story.md#ac1-message-aggregation-state
    """

    pk: str = Field(..., description="Partition key: {channel_id}#{user_id}")
    aggregation_id: str = Field(..., description="Sort key: ISO 8601 timestamp")
    messages: List[AggregatedMessage] = Field(
        default_factory=list, description="Collected messages (max 10)"
    )
    status: AggregationStatus = Field(
        default=AggregationStatus.AGGREGATING, description="Aggregation status"
    )
    started_at: str = Field(..., description="Session start timestamp (ISO 8601)")
    expires_at: str = Field(..., description="Session expiry timestamp (ISO 8601)")
    message_count: int = Field(default=0, description="Number of messages collected")
    ttl: int = Field(..., description="TTL Unix timestamp (auto-delete after 5 min)")

    def add_message(self, timestamp: str, text: str, webhook_event: Dict[str, Any]) -> None:
        """
        Add a message to the aggregation.

        Args:
            timestamp: ISO 8601 timestamp
            text: Message text
            webhook_event: Original webhook event dict
        """
        self.messages.append(
            AggregatedMessage(timestamp=timestamp, text=text, webhook_event=webhook_event)
        )
        self.message_count = len(self.messages)

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """
        Convert to DynamoDB item format.

        Returns:
            DynamoDB item dict
        """
        return {
            "pk": self.pk,
            "aggregation_id": self.aggregation_id,
            "messages": [msg.model_dump() for msg in self.messages],
            "status": self.status.value,
            "started_at": self.started_at,
            "expires_at": self.expires_at,
            "message_count": self.message_count,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "AggregationState":
        """
        Create from DynamoDB item.

        Args:
            item: DynamoDB item dict

        Returns:
            AggregationState instance
        """
        messages = [AggregatedMessage(**msg) for msg in item.get("messages", [])]
        return cls(
            pk=item["pk"],
            aggregation_id=item["aggregation_id"],
            messages=messages,
            status=AggregationStatus(item["status"]),
            started_at=item["started_at"],
            expires_at=item["expires_at"],
            message_count=item.get("message_count", len(messages)),
            ttl=item["ttl"],
        )

    @staticmethod
    def make_user_key(channel_id: str, user_id: str) -> str:
        """
        Create user key for partition key.

        Args:
            channel_id: Channel ID
            user_id: User ID

        Returns:
            User key: {channel_id}#{user_id}
        """
        return f"{channel_id}#{user_id}"

    @staticmethod
    def make_aggregation_id() -> str:
        """
        Generate aggregation ID (current timestamp).

        Returns:
            ISO 8601 timestamp
        """
        return datetime.utcnow().isoformat() + "Z"
