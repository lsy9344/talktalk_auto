"""Test pipeline.py to ensure Sheets row 100% creation and failure handling.

This test file validates AC2 (Story 7.1):
- Worker processes send events and always attempts to create Sheets log rows
- On Sheets append failure (E005), system doesn't crash but adds E005 to alert reasons
- Telegram alert is triggered when Sheets logging fails

Reference: docs/stories/7.1.story.md AC2, AC3, AC5
Reference: src/functions/worker/pipeline.py
Reference: src/layers/shared/python/talktalk_shared/clients/google_sheets_client.py
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.functions.worker.pipeline import process_single_message
from talktalk_shared.clients.google_sheets_client import GoogleSheetsError
from talktalk_shared.utils.circuit_breaker import CircuitBreakerOpenError


class TestPipelineSheetsLogging:
    """Test that send events always attempt Sheets logging with proper error handling."""

    @pytest.fixture
    def mock_channel_config(self) -> Dict[str, Any]:
        """Channel config fixture"""
        return {
            "channel_id": "wc123456",
            "channel_name": "Test Channel",
            "channel_mode": "TEST",
            "enabled": True,
            "confidence_threshold": 0.80,
        }

    @pytest.fixture
    def mock_webhook_event(self) -> Dict[str, Any]:
        """Webhook event fixture for send event"""
        return {
            "event": "send",
            "user": "user_abc",
            "textContent": {"text": "안녕하세요"},
            "options": None,
            "composingEnd": True,
        }

    @patch("src.functions.worker.pipeline.TelegramClient")
    @patch("src.functions.worker.pipeline.DeduplicationRepository")
    @patch("src.functions.worker.pipeline.GoogleSheetsClient")
    @patch("src.functions.worker.pipeline.GlobalModeRepository")
    @patch("src.functions.worker.pipeline.ChannelConfigRepository")
    @patch("src.functions.worker.pipeline.retrieve_chunks")
    def test_sheets_append_success(
        self,
        mock_retrieve_chunks,
        mock_channel_repo_cls,
        mock_global_repo_cls,
        mock_sheets_client_cls,
        mock_dedup_repo_cls,
        mock_telegram_client_cls,
        mock_channel_config,
        mock_webhook_event,
    ):
        """Arrange: Valid send event, Sheets append succeeds
        Act: Call process_single_message
        Assert: append_log_row called once, no E005 in alert reasons
        """
        # Arrange
        mock_channel_repo = MagicMock()
        mock_channel_repo.get.return_value = mock_channel_config
        mock_channel_repo_cls.return_value = mock_channel_repo

        mock_global_repo = MagicMock()
        mock_global_repo.get_mode.return_value = "TEST"
        mock_global_repo_cls.return_value = mock_global_repo

        mock_sheets_client = MagicMock()
        mock_sheets_client.append_log_row.return_value = None  # Success
        mock_sheets_client_cls.return_value = mock_sheets_client

        mock_dedup_repo = MagicMock()
        mock_dedup_repo.try_create_telegram_alert.return_value = True
        mock_dedup_repo_cls.return_value = mock_dedup_repo

        mock_telegram_client = MagicMock()
        # pipeline uses asyncio.run(send_message()) not send_alert_with_retry
        mock_telegram_client.send_message.return_value = True
        mock_telegram_client_cls.return_value = mock_telegram_client

        mock_retrieve_chunks.return_value = []

        # Act
        process_single_message(
            channel_id="wc123456",
            webhook_event=mock_webhook_event,
        )

        # Assert
        # CRITICAL: append_log_row MUST be called for every send event
        mock_sheets_client.append_log_row.assert_called_once()

        # Telegram alert should be sent (TEST mode always alerts)
        mock_telegram_client.send_message.assert_called_once()

        # Check that E005 is NOT in the alert message (success case)
        call_args = mock_telegram_client.send_message.call_args
        alert_message = call_args[0][0] if call_args else ""
        assert "E005" not in alert_message

    @patch("src.functions.worker.pipeline.TelegramClient")
    @patch("src.functions.worker.pipeline.DeduplicationRepository")
    @patch("src.functions.worker.pipeline.GoogleSheetsClient")
    @patch("src.functions.worker.pipeline.GlobalModeRepository")
    @patch("src.functions.worker.pipeline.ChannelConfigRepository")
    @patch("src.functions.worker.pipeline.retrieve_chunks")
    def test_sheets_append_failure_google_sheets_error(
        self,
        mock_retrieve_chunks,
        mock_channel_repo_cls,
        mock_global_repo_cls,
        mock_sheets_client_cls,
        mock_dedup_repo_cls,
        mock_telegram_client_cls,
        mock_channel_config,
        mock_webhook_event,
    ):
        """Arrange: Valid send event, Sheets append raises GoogleSheetsError
        Act: Call process_single_message
        Assert: E005 added to alert reasons, Telegram alert sent, pipeline doesn't crash
        """
        # Arrange
        mock_channel_repo = MagicMock()
        mock_channel_repo.get.return_value = mock_channel_config
        mock_channel_repo_cls.return_value = mock_channel_repo

        mock_global_repo = MagicMock()
        mock_global_repo.get_mode.return_value = "TEST"
        mock_global_repo_cls.return_value = mock_global_repo

        mock_sheets_client = MagicMock()
        mock_sheets_client.append_log_row.side_effect = GoogleSheetsError(
            "Failed to append row"
        )
        mock_sheets_client_cls.return_value = mock_sheets_client

        mock_dedup_repo = MagicMock()
        mock_dedup_repo.try_create_telegram_alert.return_value = True
        mock_dedup_repo_cls.return_value = mock_dedup_repo

        mock_telegram_client = MagicMock()
        mock_telegram_client.send_message.return_value = True
        mock_telegram_client_cls.return_value = mock_telegram_client

        mock_retrieve_chunks.return_value = []

        # Act - should NOT raise exception
        process_single_message(
            channel_id="wc123456",
            webhook_event=mock_webhook_event,
        )

        # Assert
        # append_log_row was called (attempted)
        mock_sheets_client.append_log_row.assert_called_once()

        # Telegram alert MUST be sent
        mock_telegram_client.send_message.assert_called_once()

        # Alert message MUST contain E005 error code
        call_args = mock_telegram_client.send_message.call_args
        alert_message = call_args[0][0] if call_args else ""
        assert "E005" in alert_message or "SHEETS_APPEND" in alert_message

    @patch("src.functions.worker.pipeline.TelegramClient")
    @patch("src.functions.worker.pipeline.DeduplicationRepository")
    @patch("src.functions.worker.pipeline.GoogleSheetsClient")
    @patch("src.functions.worker.pipeline.GlobalModeRepository")
    @patch("src.functions.worker.pipeline.ChannelConfigRepository")
    @patch("src.functions.worker.pipeline.retrieve_chunks")
    def test_sheets_append_failure_circuit_breaker_open(
        self,
        mock_retrieve_chunks,
        mock_channel_repo_cls,
        mock_global_repo_cls,
        mock_sheets_client_cls,
        mock_dedup_repo_cls,
        mock_telegram_client_cls,
        mock_channel_config,
        mock_webhook_event,
    ):
        """Arrange: Valid send event, Circuit breaker open for Sheets
        Act: Call process_single_message
        Assert: E005 added to reasons, Telegram alert sent, pipeline doesn't crash
        """
        # Arrange
        mock_channel_repo = MagicMock()
        mock_channel_repo.get.return_value = mock_channel_config
        mock_channel_repo_cls.return_value = mock_channel_repo

        mock_global_repo = MagicMock()
        mock_global_repo.get_mode.return_value = "TEST"
        mock_global_repo_cls.return_value = mock_global_repo

        mock_sheets_client = MagicMock()
        mock_sheets_client.append_log_row.side_effect = CircuitBreakerOpenError(
            "Circuit breaker is open"
        )
        mock_sheets_client_cls.return_value = mock_sheets_client

        mock_dedup_repo = MagicMock()
        mock_dedup_repo.try_create_telegram_alert.return_value = True
        mock_dedup_repo_cls.return_value = mock_dedup_repo

        mock_telegram_client = MagicMock()
        mock_telegram_client.send_message.return_value = True
        mock_telegram_client_cls.return_value = mock_telegram_client

        mock_retrieve_chunks.return_value = []

        # Act - should NOT raise exception
        process_single_message(
            channel_id="wc123456",
            webhook_event=mock_webhook_event,
        )

        # Assert
        mock_sheets_client.append_log_row.assert_called_once()
        mock_telegram_client.send_message.assert_called_once()

        # Alert message should contain E005
        call_args = mock_telegram_client.send_message.call_args
        alert_message = call_args[0][0] if call_args else ""
        assert "E005" in alert_message or "SHEETS_APPEND" in alert_message

    @patch("src.functions.worker.pipeline.TelegramClient")
    @patch("src.functions.worker.pipeline.DeduplicationRepository")
    @patch("src.functions.worker.pipeline.GoogleSheetsClient")
    @patch("src.functions.worker.pipeline.GlobalModeRepository")
    @patch("src.functions.worker.pipeline.ChannelConfigRepository")
    @patch("src.functions.worker.pipeline.retrieve_chunks")
    def test_sheets_append_failure_unexpected_exception(
        self,
        mock_retrieve_chunks,
        mock_channel_repo_cls,
        mock_global_repo_cls,
        mock_sheets_client_cls,
        mock_dedup_repo_cls,
        mock_telegram_client_cls,
        mock_channel_config,
        mock_webhook_event,
    ):
        """Arrange: Valid send event, Sheets append raises unexpected exception
        Act: Call process_single_message
        Assert: E005 added to reasons, Telegram alert sent, pipeline doesn't crash
        """
        # Arrange
        mock_channel_repo = MagicMock()
        mock_channel_repo.get.return_value = mock_channel_config
        mock_channel_repo_cls.return_value = mock_channel_repo

        mock_global_repo = MagicMock()
        mock_global_repo.get_mode.return_value = "TEST"
        mock_global_repo_cls.return_value = mock_global_repo

        mock_sheets_client = MagicMock()
        mock_sheets_client.append_log_row.side_effect = ValueError(
            "Unexpected error"
        )
        mock_sheets_client_cls.return_value = mock_sheets_client

        mock_dedup_repo = MagicMock()
        mock_dedup_repo.try_create_telegram_alert.return_value = True
        mock_dedup_repo_cls.return_value = mock_dedup_repo

        mock_telegram_client = MagicMock()
        mock_telegram_client.send_message.return_value = True
        mock_telegram_client_cls.return_value = mock_telegram_client

        mock_retrieve_chunks.return_value = []

        # Act - should NOT raise exception
        process_single_message(
            channel_id="wc123456",
            webhook_event=mock_webhook_event,
        )

        # Assert
        mock_sheets_client.append_log_row.assert_called_once()
        mock_telegram_client.send_message.assert_called_once()

        # Alert message should contain E005
        call_args = mock_telegram_client.send_message.call_args
        alert_message = call_args[0][0] if call_args else ""
        assert "E005" in alert_message or "SHEETS_APPEND" in alert_message

    @patch("src.functions.worker.pipeline.TelegramClient")
    @patch("src.functions.worker.pipeline.DeduplicationRepository")
    @patch("src.functions.worker.pipeline.GoogleSheetsClient")
    @patch("src.functions.worker.pipeline.GlobalModeRepository")
    @patch("src.functions.worker.pipeline.ChannelConfigRepository")
    @patch("src.functions.worker.pipeline.retrieve_chunks")
    def test_multiple_send_events_each_creates_sheets_row(
        self,
        mock_retrieve_chunks,
        mock_channel_repo_cls,
        mock_global_repo_cls,
        mock_sheets_client_cls,
        mock_dedup_repo_cls,
        mock_telegram_client_cls,
        mock_channel_config,
    ):
        """Arrange: Multiple send events
        Act: Process each event through pipeline
        Assert: append_log_row called N times for N events (100% coverage)
        """
        # Arrange
        mock_channel_repo = MagicMock()
        mock_channel_repo.get.return_value = mock_channel_config
        mock_channel_repo_cls.return_value = mock_channel_repo

        mock_global_repo = MagicMock()
        mock_global_repo.get_mode.return_value = "TEST"
        mock_global_repo_cls.return_value = mock_global_repo

        mock_sheets_client = MagicMock()
        mock_sheets_client_cls.return_value = mock_sheets_client

        mock_dedup_repo = MagicMock()
        mock_dedup_repo.try_create_telegram_alert.return_value = True
        mock_dedup_repo_cls.return_value = mock_dedup_repo

        mock_telegram_client = MagicMock()
        mock_telegram_client_cls.return_value = mock_telegram_client

        mock_retrieve_chunks.return_value = []

        # Act - process 3 events
        for i in range(3):
            webhook_event = {
                "event": "send",
                "user": f"user_{i}",
                "textContent": {"text": f"Message {i}"},
                "options": None,
                "composingEnd": True,
            }
            process_single_message(
                channel_id="wc123456",
                webhook_event=webhook_event,
            )

        # Assert - CRITICAL: 100% Sheets row creation for all send events
        assert mock_sheets_client.append_log_row.call_count == 3
