"""TalkTalk Send API client for sending messages to customers.

Reference: docs/architecture.md#naver-talktalk-send-api
Reference: docs/prd/101-요청-형태공식-예시-기반.md
Reference: docs/stories/2.4.story.md AC 1, 5
"""

import logging
from typing import Optional

import httpx

from talktalk_shared.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)

logger = logging.getLogger(__name__)


class TalkTalkClient:
    """TalkTalk Send API client for sending text messages.

    Implements timeout, retry logic, and circuit breaker pattern
    to prevent cascading failures.

    Reference: docs/architecture.md#naver-talktalk-send-api
    """

    BASE_URL = "https://gw.talk.naver.com"
    SEND_ENDPOINT = "/chatbot/v1/event"
    TIMEOUT_SECONDS = 10
    MAX_RETRIES = 1  # 1회 재시도 (총 2번 시도)

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Initialize TalkTalk client.

        Args:
            circuit_breaker: Circuit breaker instance (creates default if None)
            client: httpx AsyncClient instance (creates default if None)
        """
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=600,  # 10분
                success_threshold=1,
            )
        )
        self._client = client

    async def send_text_message(
        self, channel_auth_token: str, user_id: str, text: str
    ) -> bool:
        """Send text message to TalkTalk user.

        Args:
            channel_auth_token: Channel authorization token
            user_id: TalkTalk user ID
            text: Message text to send

        Returns:
            True if sent successfully, False otherwise

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open

        Reference: docs/architecture.md#naver-talktalk-send-api
        Reference: docs/prd/101-요청-형태공식-예시-기반.md
        """
        # Circuit breaker check
        if not self.circuit_breaker.allow_request():
            logger.error(
                "Circuit breaker is open - request blocked",
                extra={"user_id": user_id[:8] + "***"},  # PII masking
            )
            raise CircuitBreakerOpenError("TalkTalk API circuit breaker is open")

        url = f"{self.BASE_URL}{self.SEND_ENDPOINT}"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": channel_auth_token,
        }
        payload = {
            "event": "send",
            "user": user_id,
            "textContent": {"text": text},
        }

        # Attempt with retry
        last_exception: Optional[Exception] = None

        # Get or create client once
        if self._client is not None:
            client = self._client
            should_close = False
        else:
            client = httpx.AsyncClient()
            should_close = True

        try:
            for attempt in range(self.MAX_RETRIES + 1):
                try:
                    response = await client.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=self.TIMEOUT_SECONDS,
                    )

                    if response.status_code == 200:
                        self.circuit_breaker.record_success()
                        logger.info(
                            "TalkTalk message sent successfully",
                            extra={
                                "user_id": user_id[:8] + "***",
                                "status_code": response.status_code,
                                "attempt": attempt + 1,
                            },
                        )
                        return True

                    # 4xx errors - do not retry
                    if 400 <= response.status_code < 500:
                        self.circuit_breaker.record_failure()
                        logger.error(
                            "TalkTalk API client error - no retry",
                            extra={
                                "status_code": response.status_code,
                                "user_id": user_id[:8] + "***",
                                "attempt": attempt + 1,
                            },
                        )
                        return False

                    # 5xx errors - retry once
                    if 500 <= response.status_code < 600:
                        last_exception = httpx.HTTPStatusError(
                            f"Server error: {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                        logger.warning(
                            "TalkTalk API server error - will retry",
                            extra={
                                "status_code": response.status_code,
                                "user_id": user_id[:8] + "***",
                                "attempt": attempt + 1,
                                "max_retries": self.MAX_RETRIES + 1,
                            },
                        )
                        continue

                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    last_exception = e
                    logger.warning(
                        "TalkTalk API timeout/connection error - will retry",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "user_id": user_id[:8] + "***",
                            "attempt": attempt + 1,
                            "max_retries": self.MAX_RETRIES + 1,
                        },
                    )
                    continue

                except Exception as e:
                    # Unexpected errors - do not retry
                    self.circuit_breaker.record_failure()
                    logger.error(
                        "Unexpected error calling TalkTalk API",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "user_id": user_id[:8] + "***",
                            "attempt": attempt + 1,
                        },
                    )
                    return False
        finally:
            if should_close:
                await client.aclose()

        # All retries exhausted
        self.circuit_breaker.record_failure()
        logger.error(
            "TalkTalk API call failed after all retries",
            extra={
                "user_id": user_id[:8] + "***",
                "max_retries": self.MAX_RETRIES + 1,
                "last_error": str(last_exception) if last_exception else "Unknown",
            },
        )
        return False
