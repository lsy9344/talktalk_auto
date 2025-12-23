"""Circuit Breaker implementation for external API calls.

연속 실패 시 요청을 일정 기간 차단하여 연쇄 실패를 방지합니다.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    """Circuit Breaker 상태."""

    CLOSED = "CLOSED"  # 정상: 모든 요청 허용
    OPEN = "OPEN"  # 차단: 모든 요청 거부
    HALF_OPEN = "HALF_OPEN"  # 시험: 1개 요청만 허용


@dataclass
class CircuitBreakerConfig:
    """Circuit Breaker 설정."""

    failure_threshold: int = 5  # 연속 실패 횟수 임계값
    timeout_seconds: int = 600  # Open 상태 유지 시간(초) - 10분
    success_threshold: int = 1  # Half-Open → Closed 전환에 필요한 성공 횟수


class CircuitBreaker:
    """Circuit Breaker 구현.

    연속 실패 시 일정 기간 요청을 차단하여 외부 시스템 과부하와 연쇄 실패를 방지합니다.

    사용 예:
        breaker = CircuitBreaker()
        if not breaker.allow_request():
            raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = call_external_api()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
            raise
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None) -> None:
        """Circuit Breaker 초기화.

        Args:
            config: Circuit Breaker 설정 (None이면 기본값 사용)
        """
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._half_open_trial_used = False

    def allow_request(self) -> bool:
        """요청 허용 여부를 반환합니다.

        Returns:
            True: 요청 허용, False: 요청 거부
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Open 상태에서 timeout이 지났는지 확인
            if self._should_attempt_reset():
                self._transition_to_half_open()
                # Half-Open 상태에서는 1개 요청만 허용
                self._half_open_trial_used = True
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Half-Open 상태에서는 1개 요청만 허용
            if self._half_open_trial_used:
                return False
            self._half_open_trial_used = True
            return True

        return False

    def record_success(self) -> None:
        """성공 기록."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Closed 상태에서 성공 시 failure_count 리셋
            self.failure_count = 0

    def record_failure(self) -> None:
        """실패 기록."""
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Half-Open에서 실패하면 다시 Open으로
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()

    def _should_attempt_reset(self) -> bool:
        """Open 상태에서 Half-Open으로 전환할 시점인지 확인."""
        if self.last_failure_time is None:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.timeout_seconds

    def _transition_to_closed(self) -> None:
        """Closed 상태로 전환."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self._half_open_trial_used = False

    def _transition_to_open(self) -> None:
        """Open 상태로 전환."""
        self.state = CircuitState.OPEN
        self.failure_count = 0
        self.success_count = 0
        self._half_open_trial_used = False

    def _transition_to_half_open(self) -> None:
        """Half-Open 상태로 전환."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self._half_open_trial_used = False


class CircuitBreakerOpenError(Exception):
    """Circuit Breaker가 Open 상태일 때 발생하는 예외."""

    pass
