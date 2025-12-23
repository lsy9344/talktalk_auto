"""GlobalMode Repository - DynamoDB access layer"""
from typing import Literal

import boto3
from botocore.exceptions import ClientError

from talktalk_shared.config import get_aws_region, get_global_mode_table
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)

ModeType = Literal["TEST", "PROD"]


class GlobalModeRepository:
    """Repository for GlobalMode DynamoDB table"""

    def __init__(self) -> None:
        """Initialize repository with DynamoDB client"""
        self.table_name = get_global_mode_table()
        self.dynamodb = boto3.resource("dynamodb", region_name=get_aws_region())
        self.table = self.dynamodb.Table(self.table_name)

    def get_mode(self) -> ModeType:
        """
        Get global mode (TEST or PROD)

        Returns:
            "TEST" or "PROD". Defaults to "TEST" if not found or on error (safe default)

        Reference: docs/architecture.md#GlobalMode (전역 모드)
        """
        try:
            response = self.table.get_item(Key={"config_key": "GLOBAL_MODE"})

            if "Item" not in response:
                logger.warning("GlobalMode not found in DynamoDB, defaulting to TEST")
                return "TEST"

            item = response["Item"]
            raw_mode = item.get("mode")

            if raw_mode == "PROD":
                logger.info("GlobalMode retrieved: PROD")
                return "PROD"

            if raw_mode == "TEST" or raw_mode is None:
                logger.info("GlobalMode retrieved: TEST")
                return "TEST"

            logger.warning(f"Invalid GlobalMode value: {raw_mode}, defaulting to TEST")
            return "TEST"

        except ClientError as e:
            logger.error(
                "Failed to get GlobalMode from DynamoDB, defaulting to TEST",
                extra={"error": str(e)},
            )
            # Safe default: return TEST on any error
            return "TEST"
