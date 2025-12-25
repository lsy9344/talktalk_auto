"""Send decision logic - 3-gate system for TEST/PROD mode"""
from typing import Any, Dict, Literal, TypedDict


class SendDecision(TypedDict):
    """Result of make_send_decision function"""

    send_to_user: bool
    reason: str
    action: Literal["LOG_AND_ALERT", "SEND_LOG_NO_ALERT"]


def make_send_decision(
    channel_config: Dict[str, Any],
    global_mode: Literal["TEST", "PROD"],
    llm_response: Dict[str, Any],
) -> SendDecision:
    """
    Determine whether to send automated response to user using 3-gate system

    Gate 1: GlobalMode must be PROD
    Gate 2: Channel mode must be PROD
    Gate 3: LLM approval with safety checks:
        - send_to_user=true (LLM approves)
        - needs_operator=false (no operator intervention needed)
        - policy_flags empty or absent (no policy violations)
        - risk_level!=HIGH (risk acceptable)
        - confidence>=threshold (confidence meets requirements)

    Args:
        channel_config: Channel configuration dict with channel_mode and confidence_threshold
        global_mode: Global mode ("TEST" or "PROD")
        llm_response: LLM response dict with send_to_user, needs_operator, policy_flags,
                     confidence, risk_level

    Returns:
        SendDecision with send_to_user, reason, and action

    Reference: docs/architecture.md#Decision Logic Implementation
    Reference: docs/stories/2.2.story.md
    """
    # Gate 1: Global Mode Check
    if global_mode != "PROD":
        return {
            "send_to_user": False,
            "reason": "GLOBAL_MODE_TEST",
            "action": "LOG_AND_ALERT",
        }

    # Gate 2: Channel Mode Check
    channel_mode = channel_config.get("channel_mode", "TEST")
    if channel_mode != "PROD":
        return {
            "send_to_user": False,
            "reason": "CHANNEL_MODE_TEST",
            "action": "LOG_AND_ALERT",
        }

    # Gate 3: LLM Decision Checks
    # 3a: Check if LLM declined
    llm_send = llm_response.get("send_to_user", False)
    if not llm_send:
        return {
            "send_to_user": False,
            "reason": "LLM_DECLINED",
            "action": "LOG_AND_ALERT",
        }

    # 3b: Check if operator intervention is needed
    needs_operator = llm_response.get("needs_operator", False)
    if needs_operator:
        return {
            "send_to_user": False,
            "reason": "NEEDS_OPERATOR",
            "action": "LOG_AND_ALERT",
        }

    # 3c: Check for policy flags (any flag present blocks send)
    policy_flags = llm_response.get("policy_flags", [])
    if policy_flags and len(policy_flags) > 0:
        return {
            "send_to_user": False,
            "reason": "POLICY_FLAGS_PRESENT",
            "action": "LOG_AND_ALERT",
        }

    # 3d: Check risk level
    risk_level = llm_response.get("risk_level", "HIGH")
    if risk_level == "HIGH":
        return {
            "send_to_user": False,
            "reason": "HIGH_RISK",
            "action": "LOG_AND_ALERT",
        }

    # 3e: Check confidence threshold
    # Story 7.2 AC1: Default to 0.85 for missing threshold (PROD safety)
    confidence = llm_response.get("confidence", 0.0)
    threshold = channel_config.get("confidence_threshold", 0.85)
    if confidence < threshold:
        return {
            "send_to_user": False,
            "reason": f"LOW_CONFIDENCE_{confidence:.2f}",
            "action": "LOG_AND_ALERT",
        }

    # All gates passed - safe to send
    return {
        "send_to_user": True,
        "reason": "ALL_GATES_PASSED",
        "action": "SEND_LOG_NO_ALERT",
    }
