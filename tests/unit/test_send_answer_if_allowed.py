"""Unit tests for send_answer_if_allowed function.

Reference: docs/stories/2.4.story.md AC 7
"""

from typing import Any, Dict, Optional

import pytest

from src.functions.worker.send_answer import send_answer_if_allowed
from talktalk_shared.utils.circuit_breaker import CircuitBreakerOpenError
from talktalk_shared.utils.secrets import SecretsManagerError

TEST_SECRET_ARN = (
    "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:test-secret"
)


class MockChannelConfigRepo:
    """Mock ChannelConfigRepository for testing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config
        self.should_raise = False
        self.raise_exception: Optional[Exception] = None

    def get(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if self.should_raise and self.raise_exception:
            raise self.raise_exception
        return self.config


class MockTalkTalkClient:
    """Mock TalkTalkClient for testing."""

    def __init__(self, should_succeed: bool = True) -> None:
        self.should_succeed = should_succeed
        self.should_raise_circuit_breaker = False
        self.calls: list[Dict[str, Any]] = []

    async def send_text_message(
        self, channel_auth_token: str, user_id: str, text: str
    ) -> bool:
        self.calls.append({
            "auth_token": channel_auth_token,
            "user_id": user_id,
            "text": text,
        })

        if self.should_raise_circuit_breaker:
            raise CircuitBreakerOpenError("Circuit breaker is open")

        return self.should_succeed


def mock_get_secret_string(secret_arn: str, **kwargs) -> str:
    """Mock get_secret_string for testing."""
    if secret_arn == TEST_SECRET_ARN:
        return "test_auth_token_from_secrets"
    raise SecretsManagerError(f"Secret not found: {secret_arn}")


@pytest.mark.asyncio
async def test_send_when_all_conditions_met() -> None:
    """Test send occurs when send_to_user=true and action=SEND_LOG_NO_ALERT."""
    # Arrange
    channel_config = {
        "channel_id": "wc123456",
        "channel_mode": "PROD",
        "confidence_threshold": 0.80,
        "talktalk_auth_secret_arn": TEST_SECRET_ARN,
    }
    llm_response = {
        "send_to_user": True,
        "needs_operator": False,
        "policy_flags": [],
        "risk_level": "LOW",
        "confidence": 0.90,
    }

    mock_repo = MockChannelConfigRepo(config=channel_config)
    mock_client = MockTalkTalkClient(should_succeed=True)

    # Mock secrets module
    import src.functions.worker.send_answer as send_answer_module
    original_get_secret = send_answer_module.get_secret_string
    send_answer_module.get_secret_string = mock_get_secret_string

    # Act
    result = await send_answer_if_allowed(
        channel_id="wc123456",
        user_id="user123",
        answer_text="Your answer here",
        global_mode="PROD",
        llm_response=llm_response,
        channel_config_repo=mock_repo,
        talktalk_client=mock_client,
    )

    # Restore
    send_answer_module.get_secret_string = original_get_secret

    # Assert
    assert result["sent"] is True
    assert result["reason"] == "SENT_SUCCESSFULLY"
    assert result["error"] is None
    assert len(mock_client.calls) == 1
    assert mock_client.calls[0]["auth_token"] == "test_auth_token_from_secrets"
    assert mock_client.calls[0]["user_id"] == "user123"


@pytest.mark.asyncio
async def test_no_send_when_global_mode_test() -> None:
    """Test no send when GlobalMode is TEST."""
    # Arrange
    channel_config = {
        "channel_id": "wc123456",
        "channel_mode": "PROD",
        "confidence_threshold": 0.80,
    }
    llm_response = {
        "send_to_user": True,
        "needs_operator": False,
        "policy_flags": [],
        "risk_level": "LOW",
        "confidence": 0.90,
    }

    mock_repo = MockChannelConfigRepo(config=channel_config)
    mock_client = MockTalkTalkClient(should_succeed=True)

    # Act
    result = await send_answer_if_allowed(
        channel_id="wc123456",
        user_id="user123",
        answer_text="Your answer here",
        global_mode="TEST",  # GlobalMode is TEST
        llm_response=llm_response,
        channel_config_repo=mock_repo,
        talktalk_client=mock_client,
    )

    # Assert
    assert result["sent"] is False
    assert result["reason"] == "GLOBAL_MODE_TEST"
    assert result["error"] is None
    assert len(mock_client.calls) == 0  # No API call


@pytest.mark.asyncio
async def test_no_send_when_channel_mode_test() -> None:
    """Test no send when channel_mode is TEST."""
    # Arrange
    channel_config = {
        "channel_id": "wc123456",
        "channel_mode": "TEST",  # Channel mode is TEST
        "confidence_threshold": 0.80,
    }
    llm_response = {
        "send_to_user": True,
        "needs_operator": False,
        "policy_flags": [],
        "risk_level": "LOW",
        "confidence": 0.90,
    }

    mock_repo = MockChannelConfigRepo(config=channel_config)
    mock_client = MockTalkTalkClient(should_succeed=True)

    # Act
    result = await send_answer_if_allowed(
        channel_id="wc123456",
        user_id="user123",
        answer_text="Your answer here",
        global_mode="PROD",
        llm_response=llm_response,
        channel_config_repo=mock_repo,
        talktalk_client=mock_client,
    )

    # Assert
    assert result["sent"] is False
    assert result["reason"] == "CHANNEL_MODE_TEST"
    assert result["error"] is None
    assert len(mock_client.calls) == 0


@pytest.mark.asyncio
async def test_no_send_when_llm_declined() -> None:
    """Test no send when LLM declined (send_to_user=false)."""
    # Arrange
    channel_config = {
        "channel_id": "wc123456",
        "channel_mode": "PROD",
        "confidence_threshold": 0.80,
    }
    llm_response = {
        "send_to_user": False,  # LLM declined
        "needs_operator": False,
        "policy_flags": [],
        "risk_level": "LOW",
        "confidence": 0.90,
    }

    mock_repo = MockChannelConfigRepo(config=channel_config)
    mock_client = MockTalkTalkClient(should_succeed=True)

    # Act
    result = await send_answer_if_allowed(
        channel_id="wc123456",
        user_id="user123",
        answer_text="Your answer here",
        global_mode="PROD",
        llm_response=llm_response,
        channel_config_repo=mock_repo,
        talktalk_client=mock_client,
    )

    # Assert
    assert result["sent"] is False
    assert result["reason"] == "LLM_DECLINED"
    assert result["error"] is None
    assert len(mock_client.calls) == 0


@pytest.mark.asyncio
async def test_use_auth_token_override() -> None:
    """Test using channel_auth_token_override for testing."""
    # Arrange
    channel_config = {
        "channel_id": "wc123456",
        "channel_mode": "PROD",
        "confidence_threshold": 0.80,
    }
    llm_response = {
        "send_to_user": True,
        "needs_operator": False,
        "policy_flags": [],
        "risk_level": "LOW",
        "confidence": 0.90,
    }

    mock_repo = MockChannelConfigRepo(config=channel_config)
    mock_client = MockTalkTalkClient(should_succeed=True)

    # Act: Use token override
    result = await send_answer_if_allowed(
        channel_id="wc123456",
        user_id="user123",
        answer_text="Your answer here",
        global_mode="PROD",
        llm_response=llm_response,
        channel_auth_token_override="override_token_123",  # Override
        channel_config_repo=mock_repo,
        talktalk_client=mock_client,
    )

    # Assert
    assert result["sent"] is True
    assert mock_client.calls[0]["auth_token"] == "override_token_123"


@pytest.mark.asyncio
async def test_error_when_channel_config_not_found() -> None:
    """Test error when channel config not found."""
    # Arrange
    llm_response = {
        "send_to_user": True,
        "needs_operator": False,
        "policy_flags": [],
        "risk_level": "LOW",
        "confidence": 0.90,
    }

    mock_repo = MockChannelConfigRepo(config=None)  # Not found
    mock_client = MockTalkTalkClient(should_succeed=True)

    # Act
    result = await send_answer_if_allowed(
        channel_id="wc_unknown",
        user_id="user123",
        answer_text="Your answer here",
        global_mode="PROD",
        llm_response=llm_response,
        channel_config_repo=mock_repo,
        talktalk_client=mock_client,
    )

    # Assert
    assert result["sent"] is False
    assert result["reason"] == "CHANNEL_CONFIG_NOT_FOUND"
    assert result["error"] is not None
    assert result["error"]["error_code"] == "E006"
    assert len(mock_client.calls) == 0


@pytest.mark.asyncio
async def test_error_when_send_api_fails() -> None:
    """Test error handling when Send API fails."""
    # Arrange
    channel_config = {
        "channel_id": "wc123456",
        "channel_mode": "PROD",
        "confidence_threshold": 0.80,
    }
    llm_response = {
        "send_to_user": True,
        "needs_operator": False,
        "policy_flags": [],
        "risk_level": "LOW",
        "confidence": 0.90,
    }

    mock_repo = MockChannelConfigRepo(config=channel_config)
    mock_client = MockTalkTalkClient(should_succeed=False)  # API fails

    # Act
    result = await send_answer_if_allowed(
        channel_id="wc123456",
        user_id="user123",
        answer_text="Your answer here",
        global_mode="PROD",
        llm_response=llm_response,
        channel_auth_token_override="test_token",
        channel_config_repo=mock_repo,
        talktalk_client=mock_client,
    )

    # Assert
    assert result["sent"] is False
    assert result["reason"] == "SEND_API_FAILED"
    assert result["error"] is not None
    assert result["error"]["error_code"] == "E006"


@pytest.mark.asyncio
async def test_error_when_circuit_breaker_open() -> None:
    """Test error handling when circuit breaker is open."""
    # Arrange
    channel_config = {
        "channel_id": "wc123456",
        "channel_mode": "PROD",
        "confidence_threshold": 0.80,
    }
    llm_response = {
        "send_to_user": True,
        "needs_operator": False,
        "policy_flags": [],
        "risk_level": "LOW",
        "confidence": 0.90,
    }

    mock_repo = MockChannelConfigRepo(config=channel_config)
    mock_client = MockTalkTalkClient()
    mock_client.should_raise_circuit_breaker = True

    # Act
    result = await send_answer_if_allowed(
        channel_id="wc123456",
        user_id="user123",
        answer_text="Your answer here",
        global_mode="PROD",
        llm_response=llm_response,
        channel_auth_token_override="test_token",
        channel_config_repo=mock_repo,
        talktalk_client=mock_client,
    )

    # Assert
    assert result["sent"] is False
    assert result["reason"] == "CIRCUIT_BREAKER_OPEN"
    assert result["error"] is not None
    assert result["error"]["error_code"] == "E006"
