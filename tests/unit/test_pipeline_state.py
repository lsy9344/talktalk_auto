"""
Unit tests for Pipeline State Machine

Tests state transitions and validation logic.
Reference: docs/stories/2.1.story.md
"""
import pytest

from talktalk_shared.models.pipeline_state import (
    PipelineState,
    get_allowed_transitions,
    validate_transition,
)


class TestPipelineStateEnum:
    """Test PipelineState enum values"""

    def test_all_states_defined(self) -> None:
        """Verify all 8 required states are defined"""
        # Arrange
        expected_states = {
            "RECEIVED",
            "QUEUED",
            "PROCESSING",
            "LOGGED",
            "SENT",
            "NOT_SENT",
            "ALERTED",
            "FAILED",
        }

        # Act
        actual_states = {state.value for state in PipelineState}

        # Assert
        assert actual_states == expected_states

    def test_state_values_are_strings(self) -> None:
        """Verify all state values are strings (for JSON serialization)"""
        # Arrange & Act & Assert
        for state in PipelineState:
            assert isinstance(state.value, str)
            assert state.value == state.name


class TestValidTransitions:
    """Test valid state transitions (AC: normal flow)"""

    def test_normal_flow_received_to_queued(self) -> None:
        """Test: RECEIVED → QUEUED"""
        # Arrange
        from_state = PipelineState.RECEIVED
        to_state = PipelineState.QUEUED

        # Act & Assert (should not raise)
        validate_transition(from_state, to_state)

    def test_normal_flow_queued_to_processing(self) -> None:
        """Test: QUEUED → PROCESSING"""
        # Arrange
        from_state = PipelineState.QUEUED
        to_state = PipelineState.PROCESSING

        # Act & Assert
        validate_transition(from_state, to_state)

    def test_normal_flow_processing_to_logged(self) -> None:
        """Test: PROCESSING → LOGGED"""
        # Arrange
        from_state = PipelineState.PROCESSING
        to_state = PipelineState.LOGGED

        # Act & Assert
        validate_transition(from_state, to_state)

    def test_normal_flow_logged_to_not_sent(self) -> None:
        """Test: LOGGED → NOT_SENT (TEST mode, gate failure)"""
        # Arrange
        from_state = PipelineState.LOGGED
        to_state = PipelineState.NOT_SENT

        # Act & Assert
        validate_transition(from_state, to_state)

    def test_normal_flow_logged_to_sent(self) -> None:
        """Test: LOGGED → SENT (PROD mode, successful send)"""
        # Arrange
        from_state = PipelineState.LOGGED
        to_state = PipelineState.SENT

        # Act & Assert
        validate_transition(from_state, to_state)

    def test_complete_normal_flow_to_not_sent(self) -> None:
        """Test complete flow: RECEIVED → QUEUED → PROCESSING → LOGGED → NOT_SENT"""
        # Arrange
        flow = [
            (PipelineState.RECEIVED, PipelineState.QUEUED),
            (PipelineState.QUEUED, PipelineState.PROCESSING),
            (PipelineState.PROCESSING, PipelineState.LOGGED),
            (PipelineState.LOGGED, PipelineState.NOT_SENT),
        ]

        # Act & Assert
        for from_state, to_state in flow:
            validate_transition(from_state, to_state)

    def test_complete_normal_flow_to_sent(self) -> None:
        """Test complete flow: RECEIVED → QUEUED → PROCESSING → LOGGED → SENT"""
        # Arrange
        flow = [
            (PipelineState.RECEIVED, PipelineState.QUEUED),
            (PipelineState.QUEUED, PipelineState.PROCESSING),
            (PipelineState.PROCESSING, PipelineState.LOGGED),
            (PipelineState.LOGGED, PipelineState.SENT),
        ]

        # Act & Assert
        for from_state, to_state in flow:
            validate_transition(from_state, to_state)

    def test_alerted_transition_from_logged(self) -> None:
        """Test: LOGGED → ALERTED (operator notification)"""
        # Arrange
        from_state = PipelineState.LOGGED
        to_state = PipelineState.ALERTED

        # Act & Assert
        validate_transition(from_state, to_state)

    def test_alerted_transition_from_sent(self) -> None:
        """Test: SENT → ALERTED"""
        # Arrange
        from_state = PipelineState.SENT
        to_state = PipelineState.ALERTED

        # Act & Assert
        validate_transition(from_state, to_state)

    def test_alerted_transition_from_not_sent(self) -> None:
        """Test: NOT_SENT → ALERTED"""
        # Arrange
        from_state = PipelineState.NOT_SENT
        to_state = PipelineState.ALERTED

        # Act & Assert
        validate_transition(from_state, to_state)

    def test_failed_transition_from_any_non_terminal_state(self) -> None:
        """Test: Any state (except FAILED) → FAILED is allowed"""
        # Arrange
        non_terminal_states = [
            PipelineState.RECEIVED,
            PipelineState.QUEUED,
            PipelineState.PROCESSING,
            PipelineState.LOGGED,
            PipelineState.SENT,
            PipelineState.NOT_SENT,
            PipelineState.ALERTED,
        ]

        # Act & Assert
        for from_state in non_terminal_states:
            validate_transition(from_state, PipelineState.FAILED)


class TestInvalidTransitions:
    """Test invalid state transitions raise ValueError"""

    def test_received_to_sent_is_invalid(self) -> None:
        """Test: RECEIVED → SENT is forbidden (skips QUEUED/PROCESSING/LOGGED)"""
        # Arrange
        from_state = PipelineState.RECEIVED
        to_state = PipelineState.SENT

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid state transition"):
            validate_transition(from_state, to_state)

    def test_queued_to_sent_is_invalid(self) -> None:
        """Test: QUEUED → SENT is forbidden (skips PROCESSING/LOGGED)"""
        # Arrange
        from_state = PipelineState.QUEUED
        to_state = PipelineState.SENT

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid state transition"):
            validate_transition(from_state, to_state)

    def test_processing_to_sent_is_invalid(self) -> None:
        """Test: PROCESSING → SENT is forbidden (skips LOGGED)"""
        # Arrange
        from_state = PipelineState.PROCESSING
        to_state = PipelineState.SENT

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid state transition"):
            validate_transition(from_state, to_state)

    def test_failed_to_any_state_is_invalid(self) -> None:
        """Test: FAILED → any state is forbidden (terminal state)"""
        # Arrange
        all_states = list(PipelineState)

        # Act & Assert
        for to_state in all_states:
            with pytest.raises(ValueError, match="Invalid state transition"):
                validate_transition(PipelineState.FAILED, to_state)

    def test_received_to_processing_is_invalid(self) -> None:
        """Test: RECEIVED → PROCESSING is forbidden (skips QUEUED)"""
        # Arrange
        from_state = PipelineState.RECEIVED
        to_state = PipelineState.PROCESSING

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid state transition"):
            validate_transition(from_state, to_state)


class TestGetAllowedTransitions:
    """Test get_allowed_transitions helper function"""

    def test_received_allowed_transitions(self) -> None:
        """Test allowed transitions from RECEIVED"""
        # Arrange & Act
        allowed = get_allowed_transitions(PipelineState.RECEIVED)

        # Assert
        assert allowed == {PipelineState.QUEUED, PipelineState.FAILED}

    def test_logged_allowed_transitions(self) -> None:
        """Test allowed transitions from LOGGED (multiple options)"""
        # Arrange & Act
        allowed = get_allowed_transitions(PipelineState.LOGGED)

        # Assert
        assert allowed == {
            PipelineState.SENT,
            PipelineState.NOT_SENT,
            PipelineState.ALERTED,
            PipelineState.FAILED,
        }

    def test_failed_allowed_transitions(self) -> None:
        """Test allowed transitions from FAILED (terminal state - none)"""
        # Arrange & Act
        allowed = get_allowed_transitions(PipelineState.FAILED)

        # Assert
        assert allowed == set()

    def test_get_allowed_transitions_returns_copy(self) -> None:
        """Test that get_allowed_transitions returns a copy (immutability)"""
        # Arrange
        allowed1 = get_allowed_transitions(PipelineState.RECEIVED)

        # Act
        allowed1.add(PipelineState.SENT)  # Modify returned set
        allowed2 = get_allowed_transitions(PipelineState.RECEIVED)

        # Assert
        assert PipelineState.SENT not in allowed2  # Original unchanged
