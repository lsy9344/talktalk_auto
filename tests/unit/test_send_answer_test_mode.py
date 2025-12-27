"""Test send_answer.py to ensure TEST mode results in zero automatic sends.

This test file validates AC1 (Story 7.1):
- TEST mode (global_mode=TEST OR channel_mode=TEST) must result in 0 sends to customer
- Decision logic must block all sends when either mode is TEST
- No TalkTalk Send API calls should be made in TEST mode

Reference: docs/stories/7.1.story.md AC1, AC5
Reference: src/functions/worker/send_answer.py
Reference: src/functions/worker/decision.py
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.functions.worker.decision import make_send_decision
from src.functions.worker.send_answer import send_answer_if_allowed


class TestSendAnswerTestModeZeroSends:
    """Test that TEST mode always results in zero automatic sends."""

    @pytest.fixture
    def mock_channel_config_prod(self) -> Dict[str, Any]:
        """Channel config with PROD mode"""
        return {
            "channel_id": "wc123456",
            "channel_mode": "PROD",
            "enabled": True,
            "confidence_threshold": 0.80,
            "talktalk_auth_parameter_name": "/talktalk-auto/channels/wc123456/auth-token",
        }

    @pytest.fixture
    def mock_channel_config_test(self) -> Dict[str, Any]:
        """Channel config with TEST mode"""
        return {
            "channel_id": "wc123456",
            "channel_mode": "TEST",
            "enabled": True,
            "confidence_threshold": 0.80,
            "talktalk_auth_parameter_name": "/talktalk-auto/channels/wc123456/auth-token",
        }

    @pytest.fixture
    def mock_llm_response_approved(self) -> Dict[str, Any]:
        """LLM response that approves send"""
        return {
            "send_to_user": True,
            "needs_operator": False,
            "policy_flags": [],
            "risk_level": "LOW",
            "confidence": 0.95,
        }

    @pytest.mark.asyncio
    async def test_global_test_mode_blocks_send(
        self, mock_channel_config_prod, mock_llm_response_approved
    ):
        """Arrange: global_mode=TEST, channel_mode=PROD, LLM approves
        Act: Call send_answer_if_allowed
        Assert: sent=False, reason=GLOBAL_MODE_TEST, TalkTalk API not called
        """
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get.return_value = mock_channel_config_prod

        mock_client = AsyncMock()

        # Act
        result = await send_answer_if_allowed(
            channel_id="wc123456",
            user_id="user_abc",
            answer_text="Test answer",
            global_mode="TEST",
            llm_response=mock_llm_response_approved,
            channel_auth_token_override="test_token",
            channel_config_repo=mock_repo,
            talktalk_client=mock_client,
        )

        # Assert
        assert result["sent"] is False
        assert result["reason"] == "GLOBAL_MODE_TEST"
        assert result["error"] is None

        # CRITICAL: TalkTalk API must NOT be called
        mock_client.send_text_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_channel_test_mode_blocks_send(
        self, mock_channel_config_test, mock_llm_response_approved
    ):
        """Arrange: global_mode=PROD, channel_mode=TEST, LLM approves
        Act: Call send_answer_if_allowed
        Assert: sent=False, reason=CHANNEL_MODE_TEST, TalkTalk API not called
        """
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get.return_value = mock_channel_config_test

        mock_client = AsyncMock()

        # Act
        result = await send_answer_if_allowed(
            channel_id="wc123456",
            user_id="user_abc",
            answer_text="Test answer",
            global_mode="PROD",
            llm_response=mock_llm_response_approved,
            channel_auth_token_override="test_token",
            channel_config_repo=mock_repo,
            talktalk_client=mock_client,
        )

        # Assert
        assert result["sent"] is False
        assert result["reason"] == "CHANNEL_MODE_TEST"
        assert result["error"] is None

        # CRITICAL: TalkTalk API must NOT be called
        mock_client.send_text_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_both_test_modes_blocks_send(
        self, mock_channel_config_test, mock_llm_response_approved
    ):
        """Arrange: global_mode=TEST, channel_mode=TEST, LLM approves
        Act: Call send_answer_if_allowed
        Assert: sent=False, reason=GLOBAL_MODE_TEST (first gate), TalkTalk API not called
        """
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get.return_value = mock_channel_config_test

        mock_client = AsyncMock()

        # Act
        result = await send_answer_if_allowed(
            channel_id="wc123456",
            user_id="user_abc",
            answer_text="Test answer",
            global_mode="TEST",
            llm_response=mock_llm_response_approved,
            channel_auth_token_override="test_token",
            channel_config_repo=mock_repo,
            talktalk_client=mock_client,
        )

        # Assert
        assert result["sent"] is False
        assert result["reason"] == "GLOBAL_MODE_TEST"
        assert result["error"] is None

        # CRITICAL: TalkTalk API must NOT be called
        mock_client.send_text_message.assert_not_called()

    def test_decision_logic_global_test_mode(self, mock_channel_config_prod):
        """Test make_send_decision directly for global TEST mode"""
        # Arrange
        llm_response = {
            "send_to_user": True,
            "needs_operator": False,
            "policy_flags": [],
            "risk_level": "LOW",
            "confidence": 0.95,
        }

        # Act
        decision = make_send_decision(
            channel_config=mock_channel_config_prod,
            global_mode="TEST",
            llm_response=llm_response,
        )

        # Assert
        assert decision["send_to_user"] is False
        assert decision["reason"] == "GLOBAL_MODE_TEST"
        assert decision["action"] == "LOG_AND_ALERT"

    def test_decision_logic_channel_test_mode(self, mock_channel_config_test):
        """Test make_send_decision directly for channel TEST mode"""
        # Arrange
        llm_response = {
            "send_to_user": True,
            "needs_operator": False,
            "policy_flags": [],
            "risk_level": "LOW",
            "confidence": 0.95,
        }

        # Act
        decision = make_send_decision(
            channel_config=mock_channel_config_test,
            global_mode="PROD",
            llm_response=llm_response,
        )

        # Assert
        assert decision["send_to_user"] is False
        assert decision["reason"] == "CHANNEL_MODE_TEST"
        assert decision["action"] == "LOG_AND_ALERT"

    @pytest.mark.asyncio
    async def test_prod_mode_allows_send(
        self, mock_channel_config_prod, mock_llm_response_approved
    ):
        """Verify that PROD mode (both global and channel) allows sending

        This test serves as a control - proving that send blocking is
        specifically due to TEST mode, not other issues.
        """
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get.return_value = mock_channel_config_prod

        mock_client = AsyncMock()
        mock_client.send_text_message.return_value = True

        # Act
        result = await send_answer_if_allowed(
            channel_id="wc123456",
            user_id="user_abc",
            answer_text="Test answer",
            global_mode="PROD",
            llm_response=mock_llm_response_approved,
            channel_auth_token_override="test_token",
            channel_config_repo=mock_repo,
            talktalk_client=mock_client,
        )

        # Assert
        assert result["sent"] is True
        assert result["reason"] == "SENT_SUCCESSFULLY"
        assert result["error"] is None

        # In PROD mode with all approvals, API MUST be called
        mock_client.send_text_message.assert_called_once()
