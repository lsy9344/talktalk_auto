"""Unit tests for Repository modules"""
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from talktalk_shared.repositories.channel_config import ChannelConfigRepository
from talktalk_shared.repositories.deduplication import DeduplicationRepository
from talktalk_shared.repositories.global_mode import GlobalModeRepository


class TestChannelConfigRepository:
    """Tests for ChannelConfigRepository"""

    @patch("talktalk_shared.repositories.channel_config.boto3")
    def test_get_existing_enabled_channel(self, mock_boto3, valid_channel_config):
        """Test getting existing enabled channel"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": valid_channel_config}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = ChannelConfigRepository()

        # Act
        result = repo.get("wc123456")

        # Assert
        assert result == valid_channel_config
        mock_table.get_item.assert_called_once_with(Key={"channel_id": "wc123456"})

    @patch("talktalk_shared.repositories.channel_config.boto3")
    def test_get_nonexistent_channel(self, mock_boto3):
        """Test getting nonexistent channel returns None"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = ChannelConfigRepository()

        # Act
        result = repo.get("wc_nonexistent")

        # Assert
        assert result is None

    @patch("talktalk_shared.repositories.channel_config.boto3")
    def test_get_disabled_channel(self, mock_boto3):
        """Test getting disabled channel returns None"""
        # Arrange
        disabled_config = {
            "channel_id": "wc123",
            "enabled": False,
            "channel_mode": "TEST",
        }
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": disabled_config}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = ChannelConfigRepository()

        # Act
        result = repo.get("wc123")

        # Assert
        assert result is None

    @patch("talktalk_shared.repositories.channel_config.boto3")
    def test_get_channel_mode_disabled(self, mock_boto3):
        """Test getting channel with mode=DISABLED returns None"""
        # Arrange
        disabled_config = {
            "channel_id": "wc123",
            "enabled": True,
            "channel_mode": "DISABLED",
        }
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": disabled_config}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = ChannelConfigRepository()

        # Act
        result = repo.get("wc123")

        # Assert
        assert result is None


class TestDeduplicationRepository:
    """Tests for DeduplicationRepository"""

    @patch("talktalk_shared.repositories.deduplication.boto3")
    def test_try_create_new_record(self, mock_boto3, webhook_events):
        """Test creating new dedup record succeeds"""
        # Arrange
        mock_table = MagicMock()
        mock_table.put_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = DeduplicationRepository()

        # Act
        result = repo.try_create(
            channel_id="wc123",
            user_id="U123",
            webhook_body=webhook_events["valid_send_event"],
        )

        # Assert
        assert result is True
        mock_table.put_item.assert_called_once()

    @patch("talktalk_shared.repositories.deduplication.boto3")
    def test_try_create_duplicate_record(self, mock_boto3, webhook_events):
        """Test creating duplicate record returns False"""
        # Arrange
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = DeduplicationRepository()

        # Act
        result = repo.try_create(
            channel_id="wc123",
            user_id="U123",
            webhook_body=webhook_events["valid_send_event"],
        )

        # Assert
        assert result is False

    @patch("talktalk_shared.repositories.deduplication.boto3")
    def test_try_create_other_error_raises(self, mock_boto3, webhook_events):
        """Test other DynamoDB errors are raised"""
        # Arrange
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError"}}, "PutItem"
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = DeduplicationRepository()

        # Act & Assert
        with pytest.raises(ClientError):
            repo.try_create(
                channel_id="wc123",
                user_id="U123",
                webhook_body=webhook_events["valid_send_event"],
            )

    def test_generate_message_hash_deterministic(self, webhook_events):
        """Test message hash is deterministic"""
        # Arrange
        repo = DeduplicationRepository()
        webhook_body = webhook_events["valid_send_event"]

        # Act
        hash1 = repo._generate_message_hash(webhook_body)
        hash2 = repo._generate_message_hash(webhook_body)

        # Assert
        assert hash1 == hash2
        assert len(hash1) == 16  # First 16 chars of SHA256


class TestGlobalModeRepository:
    """Tests for GlobalModeRepository"""

    @patch("talktalk_shared.repositories.global_mode.get_global_mode_table")
    @patch("talktalk_shared.repositories.global_mode.boto3")
    def test_get_mode_returns_prod(self, mock_boto3, mock_get_table):
        """Test get_mode returns PROD when configured"""
        # Arrange
        mock_get_table.return_value = "test-global-mode-table"
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"config_key": "GLOBAL_MODE", "mode": "PROD"}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = GlobalModeRepository()

        # Act
        result = repo.get_mode()

        # Assert
        assert result == "PROD"
        mock_table.get_item.assert_called_once_with(Key={"config_key": "GLOBAL_MODE"})

    @patch("talktalk_shared.repositories.global_mode.get_global_mode_table")
    @patch("talktalk_shared.repositories.global_mode.boto3")
    def test_get_mode_returns_test(self, mock_boto3, mock_get_table):
        """Test get_mode returns TEST when configured"""
        # Arrange
        mock_get_table.return_value = "test-global-mode-table"
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"config_key": "GLOBAL_MODE", "mode": "TEST"}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = GlobalModeRepository()

        # Act
        result = repo.get_mode()

        # Assert
        assert result == "TEST"

    @patch("talktalk_shared.repositories.global_mode.get_global_mode_table")
    @patch("talktalk_shared.repositories.global_mode.boto3")
    def test_get_mode_not_found_defaults_to_test(self, mock_boto3, mock_get_table):
        """Test get_mode defaults to TEST when GlobalMode not found"""
        # Arrange
        mock_get_table.return_value = "test-global-mode-table"
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = GlobalModeRepository()

        # Act
        result = repo.get_mode()

        # Assert
        assert result == "TEST"

    @patch("talktalk_shared.repositories.global_mode.get_global_mode_table")
    @patch("talktalk_shared.repositories.global_mode.boto3")
    def test_get_mode_invalid_value_defaults_to_test(self, mock_boto3, mock_get_table):
        """Test get_mode defaults to TEST when mode value is invalid"""
        # Arrange
        mock_get_table.return_value = "test-global-mode-table"
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"config_key": "GLOBAL_MODE", "mode": "INVALID"}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = GlobalModeRepository()

        # Act
        result = repo.get_mode()

        # Assert
        assert result == "TEST"

    @patch("talktalk_shared.repositories.global_mode.get_global_mode_table")
    @patch("talktalk_shared.repositories.global_mode.boto3")
    def test_get_mode_db_error_defaults_to_test(self, mock_boto3, mock_get_table):
        """Test get_mode defaults to TEST on DynamoDB error (safe default)"""
        # Arrange
        mock_get_table.return_value = "test-global-mode-table"
        mock_table = MagicMock()
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError"}}, "GetItem"
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = GlobalModeRepository()

        # Act
        result = repo.get_mode()

        # Assert
        assert result == "TEST"
