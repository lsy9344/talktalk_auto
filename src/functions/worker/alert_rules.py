"""Alert trigger rules for operator intervention

Reference: docs/prd/53-무응답-telegram-알림-트리거운영자-개입-필요.md
Reference: docs/architecture.md#telegram-alert-triggers
Reference: docs/stories/2.3.story.md
"""
from typing import Any, Dict, List, Literal, Optional, TypedDict


class AlertDecision(TypedDict):
    """Result of evaluate_alert_triggers function"""

    should_alert: bool
    reasons: List[str]


def evaluate_alert_triggers(
    global_mode: Literal["TEST", "PROD"],
    channel_mode: Literal["TEST", "PROD"],
    webhook_event: Dict[str, Any],
    retrieved_chunks: List[Any],
    llm_response: Optional[Dict[str, Any]],
    send_decision: Optional[Dict[str, Any]],
    error_code: Optional[str] = None,
) -> AlertDecision:
    """
    Evaluate if operator should be alerted via Telegram

    In TEST mode: Always alert
    In PROD mode: Alert if any trigger condition is met

    Trigger conditions:
    - RAG lacks evidence (empty retrieved_chunks)
    - High risk level (risk_level == "HIGH")
    - Image/composite message without text
    - Question too short (<= 3 chars or specific patterns)
    - LLM validation failure
    - External API failure (error codes: E004/E005/E006)
    - Send decision blocked (action == "LOG_AND_ALERT")

    Args:
        global_mode: Global mode ("TEST" or "PROD")
        channel_mode: Channel mode ("TEST" or "PROD")
        webhook_event: Webhook event dict with textContent, imageContent, compositeContent
        retrieved_chunks: List of RAG retrieved chunks
        llm_response: LLM response dict with risk_level
        send_decision: Send decision dict with action and reason
        error_code: Error code if external API failed (E004/E005/E006)

    Returns:
        AlertDecision with should_alert flag and list of reasons

    Reference: docs/architecture.md#telegram-alert-triggers
    Reference: docs/architecture.md#test-vs-prod-mode-behavior
    """
    reasons: List[str] = []

    # TEST mode: Always alert
    if global_mode == "TEST" or channel_mode == "TEST":
        reasons.append("TEST_MODE")
        return {"should_alert": True, "reasons": reasons}

    # PROD mode: Check individual triggers

    # 1. RAG evidence insufficient (empty chunks)
    if not retrieved_chunks or len(retrieved_chunks) == 0:
        reasons.append("RAG_INSUFFICIENT_EVIDENCE")

    # 2. LLM response validation/parsing failure
    # If LLM output couldn't be parsed/validated, llm_response may be None.
    if llm_response is None:
        reasons.append("LLM_VALIDATION_FAILED")

    # 3. High risk level
    if llm_response and llm_response.get("risk_level") == "HIGH":
        reasons.append("RISK_LEVEL_HIGH")

    # 4. Image/composite message without text
    has_image = webhook_event.get("imageContent") is not None
    has_composite = webhook_event.get("compositeContent") is not None

    text_content = webhook_event.get("textContent")
    text = ""
    if text_content and isinstance(text_content, dict):
        text = text_content.get("text", "")
    elif isinstance(text_content, str):
        text = text_content

    if (has_image or has_composite) and not text:
        reasons.append("IMAGE_OR_COMPOSITE_WITHOUT_TEXT")

    # 5. Question too short
    if text:
        stripped = text.strip()
        if len(stripped) <= 3:
            reasons.append("QUESTION_TOO_SHORT")
        elif stripped in ["?", "ㅇㅇ", "문의요", "ㅎㅇ", "안녕", "ㄱㄱ"]:
            reasons.append("QUESTION_TOO_SHORT")

    # 6. External API failure (error codes)
    if error_code in ["E004", "E005", "E006"]:
        reasons.append(f"EXTERNAL_API_FAILURE_{error_code}")

    # 7. Send decision blocked
    if send_decision and send_decision.get("action") == "LOG_AND_ALERT":
        reason = send_decision.get("reason", "UNKNOWN")
        reasons.append(f"SEND_BLOCKED_{reason}")

    # Return alert decision
    return {
        "should_alert": len(reasons) > 0,
        "reasons": reasons,
    }
