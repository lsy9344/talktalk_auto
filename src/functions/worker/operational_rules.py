"""Operational rules for logging and send action determination

Reference: docs/prd/83-운영-규칙.md
Reference: docs/architecture.md#test-vs-prod-mode-behavior
Reference: docs/stories/5.3.story.md
"""
from typing import Literal, Optional


def compute_action_taken(
    global_mode: Literal["TEST", "PROD"],
    channel_mode: Literal["TEST", "PROD", "DISABLED"],
    send_to_user: bool,
    send_success: Optional[bool] = None,
) -> Literal["NOT_SENT", "SENT", "FAILED"]:
    """
    Compute action_taken value for inbox_log based on operational rules

    Rules:
    1. TEST mode (global_mode=TEST or channel_mode=TEST) → always NOT_SENT
    2. PROD mode:
       - If send_to_user=False → NOT_SENT
       - If send_to_user=True and send attempted:
         - send_success=True → SENT
         - send_success=False → FAILED

    Args:
        global_mode: Global mode ("TEST" or "PROD")
        channel_mode: Channel mode ("TEST", "PROD", or "DISABLED")
        send_to_user: Whether automated send is allowed (from make_send_decision)
        send_success: Whether actual send succeeded (None if not attempted)

    Returns:
        "NOT_SENT", "SENT", or "FAILED"

    Reference: AC1, AC2 in docs/stories/5.3.story.md
    """
    # AC1: TEST mode always returns NOT_SENT
    if global_mode == "TEST" or channel_mode == "TEST":
        return "NOT_SENT"

    # AC2: PROD mode
    # If send_to_user is False, no send was attempted
    if not send_to_user:
        return "NOT_SENT"

    # send_to_user is True, check actual send result
    if send_success is None:
        # Send was approved but not attempted (shouldn't happen in normal flow)
        return "NOT_SENT"

    return "SENT" if send_success else "FAILED"
