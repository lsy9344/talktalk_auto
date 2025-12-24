"""ChannelConfig Repository - DynamoDB access layer"""
from typing import Any, Dict, List, Optional, cast

import boto3
from botocore.exceptions import ClientError

from talktalk_shared.config import get_aws_region, get_channel_config_table
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)


class ChannelConfigRepository:
    """Repository for ChannelConfig DynamoDB table"""

    def __init__(self) -> None:
        """Initialize repository with DynamoDB client"""
        self.table_name = get_channel_config_table()
        self.dynamodb = boto3.resource("dynamodb", region_name=get_aws_region())
        self.table = self.dynamodb.Table(self.table_name)

    def get(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get channel configuration by channel_id

        Args:
            channel_id: Channel ID (e.g., "wc123456")

        Returns:
            Channel config dict if found and active, None otherwise
            Dict may contain:
            - doc_ids: List[str] - Channel-specific Google Docs document IDs (Story 3.1 AC1)
            - common_doc_enabled: bool - Whether to include common KB docs (Story 3.1 AC3)
            - Other channel configuration fields

        Reference: docs/architecture.md#Data Models - ChannelConfig
        Story 3.1 AC1, AC3: Document structure management
        """
        try:
            response = self.table.get_item(Key={"channel_id": channel_id})

            if "Item" not in response:
                logger.info(f"Channel not found: {channel_id}")
                return None

            item = cast(Dict[str, Any], response["Item"])

            # Check if channel is enabled
            if not item.get("enabled", False):
                logger.info(f"Channel disabled: {channel_id}")
                return None

            # Check channel mode (DISABLED means not active)
            channel_mode = item.get("channel_mode", "TEST")
            if channel_mode == "DISABLED":
                logger.info(f"Channel mode is DISABLED: {channel_id}")
                return None

            return item

        except ClientError as e:
            logger.error(
                f"Failed to get channel config: {channel_id}",
                extra={"error": str(e)},
            )
            raise

    def get_all_active_channels(self) -> List[Dict[str, Any]]:
        """
        Get all active channel configurations

        Returns:
            List of channel config dicts that are active (enabled=true and channel_mode != DISABLED)

        Reference: Story 3.2 AC2 - Get all active channels for document indexing
        """
        try:
            items: List[Dict[str, Any]] = []
            scan_kwargs: Dict[str, Any] = {}

            while True:
                response = self.table.scan(**scan_kwargs)
                items.extend(cast(List[Dict[str, Any]], response.get("Items", [])))

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

            # Filter for active channels
            active_channels = [
                item
                for item in items
                if item.get("enabled", False) and item.get("channel_mode", "TEST") != "DISABLED"
            ]

            logger.info(f"Found {len(active_channels)} active channels out of {len(items)} total")
            return active_channels

        except ClientError as e:
            logger.error(
                "Failed to scan channel configs",
                extra={"error": str(e)},
            )
            raise
