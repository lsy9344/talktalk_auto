"""VectorIndexMetadata Repository - DynamoDB access layer for vector index metadata"""
from typing import Any, Dict, Optional, cast

import boto3
from botocore.exceptions import ClientError

from talktalk_shared.config import get_aws_region, get_vector_index_metadata_table
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)


class VectorIndexMetadataRepository:
    """Repository for VectorIndexMetadata DynamoDB table"""

    def __init__(self) -> None:
        """Initialize repository with DynamoDB client"""
        self.table_name = get_vector_index_metadata_table()
        self.dynamodb = boto3.resource("dynamodb", region_name=get_aws_region())
        self.table = self.dynamodb.Table(self.table_name)

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get vector index metadata by doc_id

        Args:
            doc_id: Google Docs document ID

        Returns:
            Metadata dict if found, None otherwise
            Dict contains:
            - doc_id: str - Google Docs document ID (PK)
            - revision_id: str - Document revision ID for change detection
            - last_modified_time: str - ISO 8601 timestamp
            - embedding_model: str - Model used (e.g., "text-embedding-3-small")
            - index_s3_bucket: str - S3 bucket name
            - index_s3_key: str - S3 object key (e.g., "indices/{doc_id}.faiss")
            - doc_type: str - "CHANNEL_SPECIFIC" or "COMMON"
            - doc_title: Optional[str] - Document title

        Reference: docs/architecture.md#VectorIndexMetadata
        Story 3.2 AC3: Change detection using revision_id
        """
        try:
            response = self.table.get_item(Key={"doc_id": doc_id})

            if "Item" not in response:
                logger.info(f"Metadata not found for doc_id: {doc_id}")
                return None

            return cast(Dict[str, Any], response["Item"])

        except ClientError as e:
            logger.error(
                f"Failed to get vector index metadata for doc_id: {doc_id}",
                extra={"error": str(e)},
            )
            raise

    def put(self, metadata: Dict[str, Any]) -> None:
        """
        Create or update vector index metadata

        Args:
            metadata: Metadata dict containing:
                - doc_id (required): Google Docs document ID
                - revision_id (required): Document revision ID
                - last_modified_time (required): ISO 8601 timestamp
                - embedding_model (required): Model name
                - index_s3_bucket (required): S3 bucket name
                - index_s3_key (required): S3 object key
                - doc_type (optional): "CHANNEL_SPECIFIC" or "COMMON"
                - doc_title (optional): Document title
                - chunk_count (optional): Number of chunks
                - vector_dimension (optional): Embedding dimension

        Reference: Story 3.2 AC4 - Update metadata after indexing
        """
        try:
            self.table.put_item(Item=metadata)
            logger.info(
                "Saved vector index metadata",
                extra={
                    "doc_id": metadata.get("doc_id"),
                    "revision_id": metadata.get("revision_id"),
                },
            )

        except ClientError as e:
            logger.error(
                "Failed to save vector index metadata",
                extra={"doc_id": metadata.get("doc_id"), "error": str(e)},
            )
            raise

    def delete(self, doc_id: str) -> None:
        """
        Delete vector index metadata

        Args:
            doc_id: Google Docs document ID
        """
        try:
            self.table.delete_item(Key={"doc_id": doc_id})
            logger.info(f"Deleted vector index metadata for doc_id: {doc_id}")

        except ClientError as e:
            logger.error(
                f"Failed to delete vector index metadata for doc_id: {doc_id}",
                extra={"error": str(e)},
            )
            raise
