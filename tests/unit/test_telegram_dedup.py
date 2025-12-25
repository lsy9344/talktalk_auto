"""
Unit tests for Telegram alert deduplication.

Story 6.3: Telegram 알림 중복 방지 (권장)
Reference: docs/stories/6.3.story.md AC5
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from talktalk_shared.repositories.deduplication import DeduplicationRepository


class TestTelegramAlertDeduplication:
    """Test Telegram alert deduplication logic"""

    @patch("talktalk_shared.repositories.deduplication.boto3.resource")
    def test_first_alert_is_sent(self, mock_boto3_resource: MagicMock) -> None:
        """
        AC5: First alert should be sent (returns True)
        """
        # Arrange
        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {}  # Success

        repo = DeduplicationRepository()
        channel_id = "wc123"
        user_id = "al-user456"
        question_hash = "a1b2c3d4e5f6g7h8"

        # Act
        result = repo.try_create_telegram_alert(
            channel_id=channel_id,
            user_id=user_id,
            question_hash=question_hash,
            ttl_minutes=10,
        )

        # Assert
        assert result is True
        mock_table.put_item.assert_called_once()

        # Verify dedup_key format
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]
        assert item["dedup_key"] == f"TG#{channel_id}#{user_id}#{question_hash}"
        assert item["channel_id"] == channel_id
        assert item["question_hash"] == question_hash
        assert item["alert_type"] == "telegram"
        assert "ttl" in item
        assert "created_at" in item

    @patch("talktalk_shared.repositories.deduplication.boto3.resource")
    def test_duplicate_alert_is_skipped(self, mock_boto3_resource: MagicMock) -> None:
        """
        AC5: Duplicate alert within TTL should be skipped (returns False)
        """
        # Arrange
        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table

        # Simulate ConditionalCheckFailedException (duplicate)
        error_response = {"Error": {"Code": "ConditionalCheckFailedException"}}
        mock_table.put_item.side_effect = ClientError(error_response, "PutItem")

        repo = DeduplicationRepository()
        channel_id = "wc123"
        user_id = "al-user456"
        question_hash = "a1b2c3d4e5f6g7h8"

        # Act
        result = repo.try_create_telegram_alert(
            channel_id=channel_id,
            user_id=user_id,
            question_hash=question_hash,
            ttl_minutes=10,
        )

        # Assert
        assert result is False

    @patch("talktalk_shared.repositories.deduplication.boto3.resource")
    def test_ttl_is_calculated_correctly(self, mock_boto3_resource: MagicMock) -> None:
        """
        AC3: TTL should be 10 minutes (default)
        """
        # Arrange
        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {}

        repo = DeduplicationRepository()

        # Act
        with patch("talktalk_shared.repositories.deduplication.datetime") as mock_dt:
            mock_now = datetime(2025, 12, 25, 10, 0, 0)
            mock_dt.utcnow.return_value = mock_now

            repo.try_create_telegram_alert(
                channel_id="wc123",
                user_id="al-user456",
                question_hash="abc123",
                ttl_minutes=10,
            )

        # Assert
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        # TTL should be 10 minutes from now
        expected_ttl = int((mock_now + timedelta(minutes=10)).timestamp())
        assert item["ttl"] == expected_ttl

    @patch("talktalk_shared.repositories.deduplication.boto3.resource")
    def test_different_questions_are_not_duplicates(
        self, mock_boto3_resource: MagicMock
    ) -> None:
        """
        AC5: Same user with different question hashes should not be treated as duplicate
        """
        # Arrange
        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {}

        repo = DeduplicationRepository()
        channel_id = "wc123"
        user_id = "al-user456"

        # Act
        result1 = repo.try_create_telegram_alert(
            channel_id=channel_id,
            user_id=user_id,
            question_hash="hash1",
            ttl_minutes=10,
        )
        result2 = repo.try_create_telegram_alert(
            channel_id=channel_id,
            user_id=user_id,
            question_hash="hash2",  # Different hash
            ttl_minutes=10,
        )

        # Assert
        assert result1 is True
        assert result2 is True
        assert mock_table.put_item.call_count == 2

        # Verify different dedup_keys
        call1 = mock_table.put_item.call_args_list[0]
        call2 = mock_table.put_item.call_args_list[1]
        key1 = call1.kwargs["Item"]["dedup_key"]
        key2 = call2.kwargs["Item"]["dedup_key"]
        assert key1 != key2

    @patch("talktalk_shared.repositories.deduplication.boto3.resource")
    def test_dedup_key_has_telegram_prefix(self, mock_boto3_resource: MagicMock) -> None:
        """
        AC1: Telegram dedup key should have TG# prefix to avoid collision
        """
        # Arrange
        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {}

        repo = DeduplicationRepository()

        # Act
        repo.try_create_telegram_alert(
            channel_id="wc123",
            user_id="al-user456",
            question_hash="abc123",
            ttl_minutes=10,
        )

        # Assert
        call_args = mock_table.put_item.call_args
        dedup_key = call_args.kwargs["Item"]["dedup_key"]
        assert dedup_key.startswith("TG#")

    @patch("talktalk_shared.repositories.deduplication.boto3.resource")
    def test_dynamodb_error_is_raised(self, mock_boto3_resource: MagicMock) -> None:
        """
        Other DynamoDB errors should be raised
        """
        # Arrange
        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table

        # Simulate ProvisionedThroughputExceededException
        error_response = {"Error": {"Code": "ProvisionedThroughputExceededException"}}
        mock_table.put_item.side_effect = ClientError(error_response, "PutItem")

        repo = DeduplicationRepository()

        # Act & Assert
        with pytest.raises(ClientError):
            repo.try_create_telegram_alert(
                channel_id="wc123",
                user_id="al-user456",
                question_hash="abc123",
                ttl_minutes=10,
            )
