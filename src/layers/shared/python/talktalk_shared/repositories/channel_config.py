"""ChannelConfig Repository - DynamoDB access layer"""
from typing import Any, Dict, Optional, cast

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

        Reference: docs/architecture.md#Data Models - ChannelConfig
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
