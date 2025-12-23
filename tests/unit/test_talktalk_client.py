"""Unit tests for TalkTalkClient (TalkTalk Send API).

Reference: docs/stories/2.4.story.md AC 7
"""

import pytest
from httpx import AsyncClient, Request, Response

from talktalk_shared.clients.talktalk_client import TalkTalkClient
from talktalk_shared.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)


@pytest.fixture
def mock_circuit_breaker() -> CircuitBreaker:
    """Create a fresh circuit breaker for each test."""
    return CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=5,
            timeout_seconds=600,
            success_threshold=1,
        )
    )


@pytest.mark.asyncio
async def test_send_text_message_success_200(mock_circuit_breaker: CircuitBreaker) -> None:
    """Test successful message send with 200 OK."""
    # Arrange
    async def mock_post(url: str, **kwargs) -> Response:
        # Verify request format
        assert url == "https://gw.talk.naver.com/chatbot/v1/event"
        assert kwargs["headers"]["Content-Type"] == "application/json;charset=UTF-8"
        assert kwargs["headers"]["Authorization"] == "test_token_123"
        assert kwargs["json"]["event"] == "send"
        assert kwargs["json"]["user"] == "user123"
        assert kwargs["json"]["textContent"]["text"] == "Hello, customer!"
        assert kwargs["timeout"] == 10

        # Return 200 OK
        return Response(
            status_code=200,
            json={"result": "success"},
            request=Request("POST", url),
        )

    # Mock httpx.AsyncClient
    mock_client = AsyncClient()
    mock_client.post = mock_post

    client = TalkTalkClient(
        circuit_breaker=mock_circuit_breaker,
        client=mock_client,
    )

    # Act
    result = await client.send_text_message(
        channel_auth_token="test_token_123",
        user_id="user123",
        text="Hello, customer!",
    )

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_send_text_message_4xx_no_retry(mock_circuit_breaker: CircuitBreaker) -> None:
    """Test 4xx error does not retry."""
    # Arrange
    call_count = 0

    async def mock_post(url: str, **kwargs) -> Response:
        nonlocal call_count
        call_count += 1
        return Response(
            status_code=400,
            json={"error": "bad request"},
            request=Request("POST", url),
        )

    mock_client = AsyncClient()
    mock_client.post = mock_post

    client = TalkTalkClient(
        circuit_breaker=mock_circuit_breaker,
        client=mock_client,
    )

    # Act
    result = await client.send_text_message(
        channel_auth_token="test_token",
        user_id="user123",
        text="Test",
    )

    # Assert
    assert result is False
    assert call_count == 1  # No retry for 4xx


@pytest.mark.asyncio
async def test_send_text_message_5xx_retry_once(mock_circuit_breaker: CircuitBreaker) -> None:
    """Test 5xx error retries once then fails."""
    # Arrange
    call_count = 0

    async def mock_post(url: str, **kwargs) -> Response:
        nonlocal call_count
        call_count += 1
        return Response(
            status_code=500,
            json={"error": "internal server error"},
            request=Request("POST", url),
        )

    mock_client = AsyncClient()
    mock_client.post = mock_post

    client = TalkTalkClient(
        circuit_breaker=mock_circuit_breaker,
        client=mock_client,
    )

    # Act
    result = await client.send_text_message(
        channel_auth_token="test_token",
        user_id="user123",
        text="Test",
    )

    # Assert
    assert result is False
    assert call_count == 2  # Initial attempt + 1 retry


@pytest.mark.asyncio
async def test_send_text_message_timeout_retry_once(
    mock_circuit_breaker: CircuitBreaker,
) -> None:
    """Test timeout retries once then fails."""
    # Arrange
    call_count = 0

    async def mock_post(url: str, **kwargs) -> Response:
        nonlocal call_count
        call_count += 1
        from httpx import TimeoutException

        raise TimeoutException("Request timeout")

    mock_client = AsyncClient()
    mock_client.post = mock_post

    client = TalkTalkClient(
        circuit_breaker=mock_circuit_breaker,
        client=mock_client,
    )

    # Act
    result = await client.send_text_message(
        channel_auth_token="test_token",
        user_id="user123",
        text="Test",
    )

    # Assert
    assert result is False
    assert call_count == 2  # Initial attempt + 1 retry


@pytest.mark.asyncio
async def test_send_text_message_5xx_then_success(
    mock_circuit_breaker: CircuitBreaker,
) -> None:
    """Test 5xx on first attempt, success on retry."""
    # Arrange
    call_count = 0

    async def mock_post(url: str, **kwargs) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(
                status_code=500,
                json={"error": "server error"},
                request=Request("POST", url),
            )
        else:
            return Response(
                status_code=200,
                json={"result": "success"},
                request=Request("POST", url),
            )

    mock_client = AsyncClient()
    mock_client.post = mock_post

    client = TalkTalkClient(
        circuit_breaker=mock_circuit_breaker,
        client=mock_client,
    )

    # Act
    result = await client.send_text_message(
        channel_auth_token="test_token",
        user_id="user123",
        text="Test",
    )

    # Assert
    assert result is True
    assert call_count == 2


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_when_open() -> None:
    """Test circuit breaker blocks requests when open."""
    # Arrange
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=2,  # Lower threshold for testing
            timeout_seconds=600,
            success_threshold=1,
        )
    )

    async def mock_post_fail(url: str, **kwargs) -> Response:
        return Response(
            status_code=500,
            json={"error": "server error"},
            request=Request("POST", url),
        )

    mock_client = AsyncClient()
    mock_client.post = mock_post_fail

    client = TalkTalkClient(
        circuit_breaker=breaker,
        client=mock_client,
    )

    # Act: Fail twice to open circuit
    await client.send_text_message("token", "user", "text1")
    await client.send_text_message("token", "user", "text2")

    # Assert: Circuit should be open, next call should raise
    with pytest.raises(CircuitBreakerOpenError):
        await client.send_text_message("token", "user", "text3")
