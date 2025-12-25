"""Test that TEST mode always triggers Telegram alerts and handles failures gracefully.

This test file validates AC3 (Story 7.1):
- TEST mode must always call Telegram alert (should_alert=True)
- PROD mode with error/uncertain cases must trigger Telegram alerts
- Telegram send failures must NOT crash the pipeline (non-blocking)

Reference: docs/stories/7.1.story.md AC3, AC5
Reference: src/functions/worker/alert_rules.py
Reference: src/functions/worker/pipeline.py
Reference: src/layers/shared/python/talktalk_shared/clients/telegram_client.py
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.functions.worker.alert_rules import evaluate_alert_triggers
from src.functions.worker.pipeline import process_single_message


class TestTelegramAlertTestMode:
    """Test that TEST mode always triggers Telegram alerts."""

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
        """Webhook event fixture"""
        return {
            "event": "send",
            "user": "user_abc",
            "textContent": {"text": "안녕하세요"},
            "options": None,
            "composingEnd": True,
        }

    def test_alert_rules_test_global_mode_always_alerts(self):
        """Arrange: global_mode=TEST, perfect scenario (chunks, low risk)
        Act: Call evaluate_alert_triggers
        Assert: should_alert=True, reasons=["TEST_MODE"]
        """
        # Arrange
        webhook_event = {"textContent": {"text": "Normal question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW", "confidence": 0.95}
        send_decision = {"action": "SEND_LOG_NO_ALERT", "reason": "ALL_GATES_PASSED"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="TEST",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert - CRITICAL: TEST mode MUST alert
        assert result["should_alert"] is True
        assert "TEST_MODE" in result["reasons"]

    def test_alert_rules_test_channel_mode_always_alerts(self):
        """Arrange: channel_mode=TEST, perfect scenario
        Act: Call evaluate_alert_triggers
        Assert: should_alert=True, reasons=["TEST_MODE"]
        """
        # Arrange
        webhook_event = {"textContent": {"text": "Normal question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = {"action": "SEND_LOG_NO_ALERT", "reason": "ALL_GATES_PASSED"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="TEST",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "TEST_MODE" in result["reasons"]

    def test_alert_rules_prod_mode_high_risk_alerts(self):
        """Verify PROD mode alerts on HIGH risk (one of the error/uncertain cases)"""
        # Arrange
        webhook_event = {"textContent": {"text": "Question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "HIGH"}
        send_decision = {"action": "LOG_AND_ALERT", "reason": "HIGH_RISK"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "RISK_LEVEL_HIGH" in result["reasons"]

    def test_alert_rules_prod_mode_rag_insufficient_alerts(self):
        """Verify PROD mode alerts on RAG insufficient evidence"""
        # Arrange
        webhook_event = {"textContent": {"text": "Question"}}
        retrieved_chunks = []  # Empty chunks
        llm_response = {"risk_level": "LOW"}
        send_decision = None

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "RAG_INSUFFICIENT_EVIDENCE" in result["reasons"]

    def test_alert_rules_prod_mode_external_api_failure_alerts(self):
        """Verify PROD mode alerts on external API failure (E004/E005/E006)"""
        # Arrange
        webhook_event = {"textContent": {"text": "Question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = {"action": "SEND_LOG_NO_ALERT", "reason": "ALL_GATES_PASSED"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
            error_code="E005",  # Google Sheets failure
        )

        # Assert
        assert result["should_alert"] is True
        assert "EXTERNAL_API_FAILURE_E005" in result["reasons"]

    @patch("src.functions.worker.pipeline.TelegramClient")
    @patch("src.functions.worker.pipeline.DeduplicationRepository")
    @patch("src.functions.worker.pipeline.GoogleSheetsClient")
    @patch("src.functions.worker.pipeline.GlobalModeRepository")
    @patch("src.functions.worker.pipeline.ChannelConfigRepository")
    @patch("src.functions.worker.pipeline.retrieve_chunks")
    def test_pipeline_test_mode_calls_telegram(
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
        """Arrange: TEST mode, valid message
        Act: Call process_single_message
        Assert: TelegramClient.send_message called
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
        mock_telegram_client.send_message.return_value = True
        mock_telegram_client_cls.return_value = mock_telegram_client

        mock_retrieve_chunks.return_value = []

        # Act
        process_single_message(
            channel_id="wc123456",
            webhook_event=mock_webhook_event,
        )

        # Assert - CRITICAL: Telegram MUST be called in TEST mode
        mock_telegram_client.send_message.assert_called_once()

    @patch("src.functions.worker.pipeline.TelegramClient")
    @patch("src.functions.worker.pipeline.DeduplicationRepository")
    @patch("src.functions.worker.pipeline.GoogleSheetsClient")
    @patch("src.functions.worker.pipeline.GlobalModeRepository")
    @patch("src.functions.worker.pipeline.ChannelConfigRepository")
    @patch("src.functions.worker.pipeline.retrieve_chunks")
    def test_pipeline_telegram_failure_doesnt_crash(
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
        """Arrange: TEST mode, Telegram send_message raises exception
        Act: Call process_single_message
        Assert: Pipeline completes without raising (non-blocking error handling)
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
        # Telegram send_message raises exception
        mock_telegram_client.send_message.side_effect = Exception("Telegram API failed")
        mock_telegram_client_cls.return_value = mock_telegram_client

        mock_retrieve_chunks.return_value = []

        # Act - should NOT raise exception (Telegram failure is non-blocking)
        process_single_message(
            channel_id="wc123456",
            webhook_event=mock_webhook_event,
        )

        # Assert
        # Telegram was attempted
        mock_telegram_client.send_message.assert_called_once()

        # Pipeline completed (didn't crash)
        # If we get here without exception, test passes

