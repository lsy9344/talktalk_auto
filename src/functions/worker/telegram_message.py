"""Telegram alert message formatter

Reference: docs/prd/epic-6-telegram-alerts-notifications.md
Reference: docs/prd/91-공통-원칙.md
Reference: docs/prd/92-메시지-포맷plain-text-markdown-겸용.md
Reference: docs/architecture.md#handling-uncertain-cases
Reference: docs/stories/2.3.story.md AC 4
Reference: docs/stories/6.1.story.md AC 1, 2
Reference: docs/stories/6.2.story.md AC 1, 2, 3, 4
"""
from typing import List, Optional

from talktalk_shared.utils.masking import mask_question, mask_user_id


def format_template_a_operator_review(
    channel_name: str,
    channel_id: str,
    user_id: str,
    global_mode: str,
    channel_mode: str,
    question: str,
    draft_answer: str,
    reasons: List[str],
    risk_level: str,
    confidence: float,
    aggregation_id: str = "-",
    message_count: int = 1,
    row_id: str = "-",
    checklist_questions: Optional[List[str]] = None,
) -> str:
    """
    Template (A): Operator review needed for uncertain/risky cases

    This template is used when the system is uncertain about the answer
    or detects risks that require operator confirmation before sending.

    Args:
        channel_name: Channel name
        channel_id: Channel ID
        user_id: User ID (will be masked)
        global_mode: Global mode (TEST or PROD)
        channel_mode: Channel mode (TEST or PROD)
        question: Question text (will be masked as final defense)
        draft_answer: Draft answer from LLM
        reasons: List of alert reasons
        risk_level: Risk level (LOW/MEDIUM/HIGH)
        confidence: Confidence score (0.0-1.0)
        aggregation_id: Aggregation session ID (default "-" for single message)
        message_count: Number of messages aggregated (default 1 for single message)
        row_id: Sheets row ID (default "-")
        checklist_questions: Optional list of operator checklist questions

    Returns:
        Formatted alert message string (Template A)

    Reference: docs/prd/92-메시지-포맷plain-text-markdown-겸용.md (Template A)
    Reference: docs/stories/6.2.story.md AC1
    """
    # AC4: Apply masking as final defense (PII must not leak to Telegram)
    masked_user = mask_user_id(user_id)
    masked_question = mask_question(question)

    # Format reasons list as semicolon-separated string
    reasons_joined = "; ".join(reasons)

    # Default checklist questions if not provided
    if checklist_questions is None:
        checklist_questions = [
            "답변 내용이 정확한가?",
            "고객에게 전송해도 되는가?",
        ]

    # Format checklist as bullet points
    checklist_text = "\n".join([f"- {q}" for q in checklist_questions])

    message = f"""[톡톡 알림] 운영자 확인 필요 ⚠️
- 채널: {channel_name} ({channel_id})
- 상담자ID: {masked_user}
- 집계: {aggregation_id} / count={message_count}
- 모드: global={global_mode} / channel={channel_mode}
- 사유: {reasons_joined}
- 위험도: {risk_level} / confidence={confidence}

[고객 질문(마스킹)]
{masked_question}

[추천 답변 초안(고객에게는 아직 미전송)]
{draft_answer}

[운영자 체크 질문]
{checklist_text}

[시트 Row]
row_id={row_id}"""

    return message


def format_template_b_system_error(
    channel_name: str,
    channel_id: str,
    user_id: str,
    question: str,
    stage: str,
    error_summary: str,
    attempt: int,
    max_attempts: int,
    aggregation_id: str = "-",
    message_count: int = 1,
    row_id: str = "-",
) -> str:
    """
    Template (B): System error alert

    This template is used when system errors occur (e.g., LLM call failure,
    Sheets append failure, Send API failure).

    Args:
        channel_name: Channel name
        channel_id: Channel ID
        user_id: User ID (will be masked)
        question: Question text (will be masked as final defense)
        stage: Error stage (e.g., LLM_CALL, SHEETS_APPEND, SEND_API)
        error_summary: Error summary message
        attempt: Current attempt number
        max_attempts: Maximum retry attempts
        aggregation_id: Aggregation session ID (default "-" for single message)
        message_count: Number of messages aggregated (default 1 for single message)
        row_id: Sheets row ID (default "-")

    Returns:
        Formatted alert message string (Template B)

    Reference: docs/prd/92-메시지-포맷plain-text-markdown-겸용.md (Template B)
    Reference: docs/stories/6.2.story.md AC2
    """
    # AC4: Apply masking as final defense (PII must not leak to Telegram)
    masked_user = mask_user_id(user_id)
    masked_question = mask_question(question)

    message = f"""[톡톡 알림] 시스템 오류 🚨
- 채널: {channel_name} ({channel_id})
- 상담자ID: {masked_user}
- 집계: {aggregation_id} / count={message_count}
- 단계: {stage} (예: LLM_CALL / SHEETS_APPEND / SEND_API)
- 오류요약: {error_summary}

[고객 질문(마스킹)]
{masked_question}

[재시도]
- attempt={attempt} / max={max_attempts}
row_id={row_id}"""

    return message


def format_template_c_prod_send_blocked(
    channel_name: str,
    channel_id: str,
    user_id: str,
    question: str,
    draft_answer: str,
    reasons: List[str],
    confidence: float,
    risk_level: str,
    aggregation_id: str = "-",
    message_count: int = 1,
    row_id: str = "-",
) -> str:
    """
    Template (C): PROD send blocked by policy

    This template is used when in PROD mode but sending is blocked
    by operational policy rules.

    Args:
        channel_name: Channel name
        channel_id: Channel ID
        user_id: User ID (will be masked)
        question: Question text (will be masked as final defense)
        draft_answer: Draft answer from LLM
        reasons: List of blocking reasons
        confidence: Confidence score (0.0-1.0)
        risk_level: Risk level (LOW/MEDIUM/HIGH)
        aggregation_id: Aggregation session ID (default "-" for single message)
        message_count: Number of messages aggregated (default 1 for single message)
        row_id: Sheets row ID (default "-")

    Returns:
        Formatted alert message string (Template C)

    Reference: docs/prd/92-메시지-포맷plain-text-markdown-겸용.md (Template C)
    Reference: docs/stories/6.2.story.md AC3
    """
    # AC4: Apply masking as final defense (PII must not leak to Telegram)
    masked_user = mask_user_id(user_id)
    masked_question = mask_question(question)

    # Format reasons list as semicolon-separated string
    reasons_joined = "; ".join(reasons)

    message = f"""[톡톡 알림] PROD 발송 보류 ⛔
- 채널: {channel_name} ({channel_id})
- 상담자ID: {masked_user}
- 집계: {aggregation_id} / count={message_count}
- 사유: {reasons_joined}
- confidence={confidence} / risk={risk_level}

질문(마스킹): {masked_question}
초안: {draft_answer}
row_id={row_id}"""

    return message


def format_alert_message(
    channel_name: str,
    channel_id: str,
    user_id: str,
    global_mode: str,
    channel_mode: str,
    question: str,
    draft_answer: str,
    reasons: List[str],
    aggregation_id: str = "-",
    message_count: int = 1,
) -> str:
    """
    Format Telegram alert message with required common fields

    DEPRECATED: This function is kept for backward compatibility.
    New code should use the specific template formatters:
    - format_template_a_operator_review()
    - format_template_b_system_error()
    - format_template_c_prod_send_blocked()

    Common fields (AC1 - Story 6.1):
    - Channel info (channel_name, channel_id)
    - User ID (masked)
    - Mode (global/channel)
    - Question (masked for PII)
    - Draft answer
    - Alert reasons
    - Message aggregation info (aggregation_id, message_count)

    All PII must be masked according to masking rules (AC2 - Story 6.1).
    Applies final defense masking via mask_question() even if already masked.

    Args:
        channel_name: Channel name
        channel_id: Channel ID
        user_id: User ID (will be masked)
        global_mode: Global mode (TEST or PROD)
        channel_mode: Channel mode (TEST or PROD)
        question: Question text (will be masked as final defense)
        draft_answer: Draft answer from LLM (use "-" if not available)
        reasons: List of alert reasons
        aggregation_id: Aggregation session ID (default "-" for single message)
        message_count: Number of messages aggregated (default 1 for single message)

    Returns:
        Formatted alert message string

    Reference: docs/architecture.md#privacy-and-masking-requirements
    Reference: docs/prd/91-공통-원칙.md
    Reference: docs/stories/6.1.story.md
    """
    # AC2: Apply masking as final defense (PII must not leak to Telegram)
    masked_user = mask_user_id(user_id)
    masked_question = mask_question(question)

    # Format reasons as bullet points
    reasons_text = "\n".join([f"- {reason}" for reason in reasons])

    # AC1: Include all common fields
    message = f"""🚨 운영자 개입 필요

📌 채널 정보
- 채널명: {channel_name}
- 채널ID: {channel_id}

👤 사용자: {masked_user}

⚙️ 모드
- Global: {global_mode}
- Channel: {channel_mode}

📊 메시지 집계
- Aggregation ID: {aggregation_id}
- Message Count: {message_count}

📋 알림 사유:
{reasons_text}

💬 질문 (마스킹):
{masked_question}

📝 추천 답변 초안:
{draft_answer}
"""

    return message
