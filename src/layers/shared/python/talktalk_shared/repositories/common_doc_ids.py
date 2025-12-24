"""CommonDocIds Repository - DynamoDB access layer for common KB document list"""
from typing import List

import boto3
from botocore.exceptions import ClientError

from talktalk_shared.config import get_aws_region, get_global_mode_table
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)


class CommonDocIdsRepository:
    """Repository for common KB document IDs stored in GlobalMode table"""

    def __init__(self) -> None:
        """Initialize repository with DynamoDB client"""
        self.table_name = get_global_mode_table()
        self.dynamodb = boto3.resource("dynamodb", region_name=get_aws_region())
        self.table = self.dynamodb.Table(self.table_name)

    def get_common_doc_ids(self) -> List[str]:
        """
        Get common KB document IDs from GlobalMode table

        Returns:
            List of Google Docs document IDs. Returns empty list if not found (safe default)

        Reference: docs/architecture.md#GlobalMode (전역 모드)
        Story 3.1 AC2: Common KB document list storage
        """
        try:
            response = self.table.get_item(Key={"config_key": "COMMON_DOC_IDS"})

            if "Item" not in response:
                logger.info("COMMON_DOC_IDS not found in GlobalMode table, returning empty list")
                return []

            item = response["Item"]
            doc_ids = item.get("doc_ids", [])

            # Ensure it's a list
            if not isinstance(doc_ids, list):
                logger.warning(
                    f"COMMON_DOC_IDS.doc_ids is not a list: {type(doc_ids)}, returning empty list"
                )
                return []

            logger.info(f"Retrieved {len(doc_ids)} common document IDs")
            return doc_ids

        except ClientError as e:
            logger.error(
                "Failed to get COMMON_DOC_IDS from GlobalMode table, returning empty list",
                extra={"error": str(e)},
            )
            # Safe default: return empty list on any error
            return []
