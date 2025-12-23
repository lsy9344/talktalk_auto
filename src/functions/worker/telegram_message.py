"""Telegram alert message formatter

Reference: docs/prd/epic-6-telegram-alerts-notifications.md
Reference: docs/architecture.md#handling-uncertain-cases
Reference: docs/stories/2.3.story.md AC 4
"""
from typing import List

from talktalk_shared.utils.masking import mask_question, mask_user_id


def format_alert_message(
    channel_name: str,
    channel_id: str,
    user_id: str,
    global_mode: str,
    channel_mode: str,
    question: str,
    reasons: List[str],
) -> str:
    """
    Format Telegram alert message with required information

    Includes:
    - Channel info (channel_name, channel_id)
    - User ID (masked)
    - Mode (global/channel)
    - Alert reasons
    - Question (masked)

    All PII must be masked according to masking rules.

    Args:
        channel_name: Channel name
        channel_id: Channel ID
        user_id: User ID (will be masked)
        global_mode: Global mode (TEST or PROD)
        channel_mode: Channel mode (TEST or PROD)
        question: Question text (will be masked)
        reasons: List of alert reasons

    Returns:
        Formatted alert message string

    Reference: docs/architecture.md#privacy-and-masking-requirements
    """
    masked_user = mask_user_id(user_id)
    masked_question = mask_question(question)

    # Format reasons as bullet points
    reasons_text = "\n".join([f"- {reason}" for reason in reasons])

    message = f"""🚨 운영자 개입 필요

📌 채널 정보
- 채널명: {channel_name}
- 채널ID: {channel_id}

👤 사용자: {masked_user}

⚙️ 모드
- Global: {global_mode}
- Channel: {channel_mode}

📋 알림 사유:
{reasons_text}

💬 질문:
{masked_question}
"""

    return message
