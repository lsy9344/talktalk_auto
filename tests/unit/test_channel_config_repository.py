"""Unit tests for ChannelConfigRepository - Story 3.2 new methods"""
from unittest.mock import MagicMock, patch

import pytest

from talktalk_shared.repositories.channel_config import ChannelConfigRepository


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource"""
    with patch("boto3.resource") as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table


@pytest.fixture
def repository(mock_dynamodb):
    """Create repository instance with mocked DynamoDB"""
    with patch(
        "talktalk_shared.repositories.channel_config.get_channel_config_table",
        return_value="test-table",
    ):
        repo = ChannelConfigRepository()
        repo.table = mock_dynamodb
        return repo


def test_get_all_active_channels_filters_correctly(repository, mock_dynamodb):
    """Test get_all_active_channels returns only active channels"""
    # Arrange
    all_channels = [
        {"channel_id": "ch1", "enabled": True, "channel_mode": "TEST"},
        {"channel_id": "ch2", "enabled": True, "channel_mode": "LIVE"},
        {"channel_id": "ch3", "enabled": False, "channel_mode": "TEST"},  # Not enabled
        {"channel_id": "ch4", "enabled": True, "channel_mode": "DISABLED"},  # Disabled mode
        {"channel_id": "ch5", "enabled": True, "channel_mode": "TEST"},
    ]
    mock_dynamodb.scan.return_value = {"Items": all_channels}

    # Act
    result = repository.get_all_active_channels()

    # Assert
    assert len(result) == 3
    assert result[0]["channel_id"] == "ch1"
    assert result[1]["channel_id"] == "ch2"
    assert result[2]["channel_id"] == "ch5"
    mock_dynamodb.scan.assert_called_once()


def test_get_all_active_channels_empty(repository, mock_dynamodb):
    """Test get_all_active_channels with no active channels"""
    # Arrange
    mock_dynamodb.scan.return_value = {"Items": []}

    # Act
    result = repository.get_all_active_channels()

    # Assert
    assert len(result) == 0
    mock_dynamodb.scan.assert_called_once()


def test_get_all_active_channels_all_disabled(repository, mock_dynamodb):
    """Test get_all_active_channels when all channels are disabled"""
    # Arrange
    all_channels = [
        {"channel_id": "ch1", "enabled": False, "channel_mode": "TEST"},
        {"channel_id": "ch2", "enabled": True, "channel_mode": "DISABLED"},
    ]
    mock_dynamodb.scan.return_value = {"Items": all_channels}

    # Act
    result = repository.get_all_active_channels()

    # Assert
    assert len(result) == 0
    mock_dynamodb.scan.assert_called_once()


def test_get_all_active_channels_paginates(repository, mock_dynamodb):
    """Test get_all_active_channels handles DynamoDB Scan pagination"""
    # Arrange
    mock_dynamodb.scan.side_effect = [
        {
            "Items": [{"channel_id": "ch1", "enabled": True, "channel_mode": "TEST"}],
            "LastEvaluatedKey": {"channel_id": "ch1"},
        },
        {"Items": [{"channel_id": "ch2", "enabled": True, "channel_mode": "TEST"}]},
    ]

    # Act
    result = repository.get_all_active_channels()

    # Assert
    assert [item["channel_id"] for item in result] == ["ch1", "ch2"]
    assert mock_dynamodb.scan.call_count == 2
    mock_dynamodb.scan.assert_any_call()
    mock_dynamodb.scan.assert_any_call(ExclusiveStartKey={"channel_id": "ch1"})
