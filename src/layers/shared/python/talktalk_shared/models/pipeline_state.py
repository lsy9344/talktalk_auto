"""
Pipeline State Machine

Defines pipeline states and transition rules for message processing.
Reference: docs/prd/51-파이프라인-상태-머신.md
Reference: docs/stories/2.1.story.md
"""
from enum import Enum
from typing import Set


class PipelineState(str, Enum):
    """
    Pipeline states for tracking message processing progress.

    States:
        RECEIVED: Ingest received valid 'send' event and started processing
        QUEUED: Ingest successfully enqueued message to SQS
        PROCESSING: Worker received SQS message and started processing
        LOGGED: Worker logged message to Google Sheets
        SENT: (PROD) Message sent via TalkTalk Send API
        NOT_SENT: Message not sent due to policy (TEST mode, gate failure)
        ALERTED: Telegram notification sent to operator
        FAILED: Processing failed after retries or moved to DLQ
    """

    RECEIVED = "RECEIVED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    LOGGED = "LOGGED"
    SENT = "SENT"
    NOT_SENT = "NOT_SENT"
    ALERTED = "ALERTED"
    FAILED = "FAILED"


# Allowed state transitions
# Format: {from_state: {allowed_to_states}}
_ALLOWED_TRANSITIONS: dict[PipelineState, Set[PipelineState]] = {
    PipelineState.RECEIVED: {PipelineState.QUEUED, PipelineState.FAILED},
    PipelineState.QUEUED: {PipelineState.PROCESSING, PipelineState.FAILED},
    PipelineState.PROCESSING: {PipelineState.LOGGED, PipelineState.FAILED},
    PipelineState.LOGGED: {
        PipelineState.SENT,
        PipelineState.NOT_SENT,
        PipelineState.ALERTED,
        PipelineState.FAILED,
    },
    PipelineState.SENT: {PipelineState.ALERTED, PipelineState.FAILED},
    PipelineState.NOT_SENT: {PipelineState.ALERTED, PipelineState.FAILED},
    PipelineState.ALERTED: {PipelineState.FAILED},
    PipelineState.FAILED: set(),  # Terminal state - no transitions allowed
}


def validate_transition(from_state: PipelineState, to_state: PipelineState) -> None:
    """
    Validate if a state transition is allowed.

    Args:
        from_state: Current pipeline state
        to_state: Target pipeline state

    Raises:
        ValueError: If transition is not allowed

    Example:
        >>> validate_transition(PipelineState.RECEIVED, PipelineState.QUEUED)  # OK
        >>> validate_transition(PipelineState.RECEIVED, PipelineState.SENT)  # ValueError
    """
    allowed = _ALLOWED_TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise ValueError(
            f"Invalid state transition: {from_state.value} -> {to_state.value}. "
            f"Allowed transitions from {from_state.value}: "
            f"{', '.join(s.value for s in allowed) if allowed else 'none (terminal state)'}"
        )


def get_allowed_transitions(from_state: PipelineState) -> Set[PipelineState]:
    """
    Get set of allowed transitions from a given state.

    Args:
        from_state: Current pipeline state

    Returns:
        Set of allowed target states
    """
    return _ALLOWED_TRANSITIONS.get(from_state, set()).copy()
