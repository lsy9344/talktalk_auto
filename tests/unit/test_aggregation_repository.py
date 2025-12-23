"""Unit tests for AggregationRepository"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from talktalk_shared.models.aggregation_state import AggregationStatus
from talktalk_shared.repositories.aggregation import AggregationRepository

# Set environment variables for testing
os.environ["AGGREGATION_STATE_TABLE"] = "test-aggregation-state"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["AGGREGATION_TRIGGER_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/test"


@pytest.fixture
def mock_webhook_event():
    """Mock webhook event"""
    return {
        "event": "send",
        "user": "user123",
        "textContent": {"text": "Hello", "inputType": "typing"},
    }


@pytest.fixture
def mock_aggregation_item():
    """Mock DynamoDB aggregation item"""
    now = datetime.utcnow()
    return {
        "pk": "wc123#user123",
        "aggregation_id": now.isoformat() + "Z",
        "messages": [
            {
                "timestamp": now.isoformat() + "Z",
                "text": "Hello",
                "webhook_event": {
                    "event": "send",
                    "user": "user123",
                    "textContent": {"text": "Hello"},
                },
            }
        ],
        "status": AggregationStatus.AGGREGATING.value,
        "started_at": now.isoformat() + "Z",
        "expires_at": (now + timedelta(seconds=30)).isoformat() + "Z",
        "message_count": 1,
        "ttl": int((now + timedelta(minutes=5)).timestamp()),
    }


class TestAggregationRepository:
    """Tests for AggregationRepository"""

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_get_active_found(self, mock_boto3, mock_aggregation_item):
        """Test get_active returns active aggregation"""
        # Arrange
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": [mock_aggregation_item]}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act
        result = repo.get_active("wc123#user123")

        # Assert
        assert result is not None
        assert result.pk == "wc123#user123"
        assert result.status == AggregationStatus.AGGREGATING
        assert result.message_count == 1
        mock_table.query.assert_called_once()

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_get_active_not_found(self, mock_boto3):
        """Test get_active returns None when no active aggregation"""
        # Arrange
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act
        result = repo.get_active("wc123#user123")

        # Assert
        assert result is None

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_get_found(self, mock_boto3, mock_aggregation_item):
        """Test get returns specific aggregation"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": mock_aggregation_item}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()
        aggregation_id = mock_aggregation_item["aggregation_id"]

        # Act
        result = repo.get("wc123#user123", aggregation_id)

        # Assert
        assert result is not None
        assert result.pk == "wc123#user123"
        assert result.aggregation_id == aggregation_id
        mock_table.get_item.assert_called_once_with(
            Key={"pk": "wc123#user123", "aggregation_id": aggregation_id}
        )

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_get_not_found(self, mock_boto3):
        """Test get returns None when aggregation doesn't exist"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act
        result = repo.get("wc123#user123", "2025-12-24T00:00:00Z")

        # Assert
        assert result is None

    @patch("talktalk_shared.repositories.aggregation.boto3")
    @patch("talktalk_shared.repositories.aggregation.datetime")
    def test_create_success(self, mock_datetime, mock_boto3, mock_webhook_event):
        """Test creating new aggregation succeeds"""
        # Arrange
        now = datetime(2025, 12, 24, 10, 30, 0)
        mock_datetime.utcnow.return_value = now

        mock_table = MagicMock()
        mock_table.put_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act
        result = repo.create("wc123#user123", mock_webhook_event)

        # Assert
        assert result is not None
        assert result.pk == "wc123#user123"
        assert result.status == AggregationStatus.AGGREGATING
        assert result.message_count == 1
        assert len(result.messages) == 1
        assert result.messages[0].text == "Hello"
        mock_table.put_item.assert_called_once()

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_create_duplicate_fails(self, mock_boto3, mock_webhook_event):
        """Test creating duplicate aggregation fails"""
        # Arrange
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act & Assert
        with pytest.raises(ValueError, match="already exists"):
            repo.create("wc123#user123", mock_webhook_event)

    @patch("talktalk_shared.repositories.aggregation.boto3")
    @patch("talktalk_shared.repositories.aggregation.datetime")
    def test_add_message_success(
        self, mock_datetime, mock_boto3, mock_webhook_event, mock_aggregation_item
    ):
        """Test adding message to aggregation succeeds"""
        # Arrange
        now = datetime(2025, 12, 24, 10, 30, 5)
        mock_datetime.utcnow.return_value = now

        updated_item = mock_aggregation_item.copy()
        updated_item["message_count"] = 2
        updated_item["messages"].append(
            {
                "timestamp": now.isoformat() + "Z",
                "text": "World",
                "webhook_event": mock_webhook_event,
            }
        )

        mock_table = MagicMock()
        mock_table.update_item.return_value = {"Attributes": updated_item}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()
        aggregation_id = mock_aggregation_item["aggregation_id"]

        # Act
        result = repo.add_message("wc123#user123", aggregation_id, mock_webhook_event)

        # Assert
        assert result is not None
        assert result.message_count == 2
        mock_table.update_item.assert_called_once()

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_add_message_not_aggregating_fails(self, mock_boto3, mock_webhook_event):
        """Test adding message to non-AGGREGATING aggregation fails"""
        # Arrange
        mock_table = MagicMock()
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act & Assert
        with pytest.raises(ValueError, match="not in AGGREGATING status"):
            repo.add_message("wc123#user123", "2025-12-24T00:00:00Z", mock_webhook_event)

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_complete_success(self, mock_boto3):
        """Test completing aggregation succeeds"""
        # Arrange
        mock_table = MagicMock()
        mock_table.update_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act
        repo.complete("wc123#user123", "2025-12-24T00:00:00Z")

        # Assert
        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args[1]
        assert (
            call_kwargs["ExpressionAttributeValues"][":completed"]
            == AggregationStatus.COMPLETED.value
        )

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_complete_not_aggregating_warning(self, mock_boto3):
        """Test completing non-AGGREGATING aggregation logs warning"""
        # Arrange
        mock_table = MagicMock()
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act (should not raise, just log warning)
        repo.complete("wc123#user123", "2025-12-24T00:00:00Z")

        # Assert
        mock_table.update_item.assert_called_once()

    @patch("talktalk_shared.repositories.aggregation.boto3")
    def test_cancel_success(self, mock_boto3):
        """Test cancelling aggregation succeeds"""
        # Arrange
        mock_table = MagicMock()
        mock_table.update_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = AggregationRepository()

        # Act
        repo.cancel("wc123#user123", "2025-12-24T00:00:00Z")

        # Assert
        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args[1]
        assert (
            call_kwargs["ExpressionAttributeValues"][":cancelled"]
            == AggregationStatus.CANCELLED.value
        )
