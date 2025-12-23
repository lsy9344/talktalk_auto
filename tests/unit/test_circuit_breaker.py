"""Unit tests for Circuit Breaker.

Reference: docs/stories/2.4.story.md AC 7
"""

import time

from talktalk_shared.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)


def test_circuit_breaker_initial_state() -> None:
    """Test circuit breaker starts in CLOSED state."""
    # Arrange & Act
    breaker = CircuitBreaker()

    # Assert
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True


def test_circuit_breaker_opens_after_threshold_failures() -> None:
    """Test circuit breaker opens after reaching failure threshold."""
    # Arrange
    config = CircuitBreakerConfig(
        failure_threshold=3,
        timeout_seconds=600,
        success_threshold=1,
    )
    breaker = CircuitBreaker(config)

    # Act: Record 3 failures
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()

    # Assert: Should transition to OPEN
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_circuit_breaker_stays_open_before_timeout() -> None:
    """Test circuit breaker stays OPEN before timeout expires."""
    # Arrange
    config = CircuitBreakerConfig(
        failure_threshold=2,
        timeout_seconds=10,  # 10 seconds
        success_threshold=1,
    )
    breaker = CircuitBreaker(config)

    # Act: Open the circuit
    breaker.record_failure()
    breaker.record_failure()

    # Assert: Should be OPEN and block requests
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False

    # Wait less than timeout
    time.sleep(0.1)
    assert breaker.allow_request() is False


def test_circuit_breaker_transitions_to_half_open_after_timeout() -> None:
    """Test circuit breaker transitions to HALF_OPEN after timeout."""
    # Arrange
    config = CircuitBreakerConfig(
        failure_threshold=2,
        timeout_seconds=1,  # 1 second for fast testing
        success_threshold=1,
    )
    breaker = CircuitBreaker(config)

    # Act: Open the circuit
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    # Wait for timeout
    time.sleep(1.1)

    # Assert: Should allow one request and transition to HALF_OPEN
    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN
    # Half-Open 상태에서는 1개 요청만 허용
    assert breaker.allow_request() is False


def test_circuit_breaker_half_open_success_closes() -> None:
    """Test HALF_OPEN → CLOSED on success."""
    # Arrange
    config = CircuitBreakerConfig(
        failure_threshold=2,
        timeout_seconds=1,
        success_threshold=1,
    )
    breaker = CircuitBreaker(config)

    # Open circuit
    breaker.record_failure()
    breaker.record_failure()

    # Wait and transition to HALF_OPEN
    time.sleep(1.1)
    breaker.allow_request()  # Transitions to HALF_OPEN

    # Act: Record success
    breaker.record_success()

    # Assert: Should transition to CLOSED
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True


def test_circuit_breaker_half_open_failure_reopens() -> None:
    """Test HALF_OPEN → OPEN on failure."""
    # Arrange
    config = CircuitBreakerConfig(
        failure_threshold=2,
        timeout_seconds=1,
        success_threshold=1,
    )
    breaker = CircuitBreaker(config)

    # Open circuit
    breaker.record_failure()
    breaker.record_failure()

    # Wait and transition to HALF_OPEN
    time.sleep(1.1)
    breaker.allow_request()

    # Act: Record failure in HALF_OPEN
    breaker.record_failure()

    # Assert: Should go back to OPEN
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_circuit_breaker_closed_success_resets_failure_count() -> None:
    """Test success in CLOSED state resets failure count."""
    # Arrange
    config = CircuitBreakerConfig(
        failure_threshold=3,
        timeout_seconds=600,
        success_threshold=1,
    )
    breaker = CircuitBreaker(config)

    # Act: Record some failures then success
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.failure_count == 2

    breaker.record_success()

    # Assert: Failure count should reset
    assert breaker.failure_count == 0
    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_default_config() -> None:
    """Test default circuit breaker configuration."""
    # Arrange & Act
    breaker = CircuitBreaker()

    # Assert: Check default values
    assert breaker.config.failure_threshold == 5
    assert breaker.config.timeout_seconds == 600
    assert breaker.config.success_threshold == 1


def test_circuit_breaker_custom_config() -> None:
    """Test circuit breaker with custom configuration."""
    # Arrange
    config = CircuitBreakerConfig(
        failure_threshold=10,
        timeout_seconds=300,
        success_threshold=2,
    )

    # Act
    breaker = CircuitBreaker(config)

    # Assert
    assert breaker.config.failure_threshold == 10
    assert breaker.config.timeout_seconds == 300
    assert breaker.config.success_threshold == 2
