"""Builder for creating SheetsLogRow for inbox_log

Reference: docs/stories/5.3.story.md (Task 2)
Reference: docs/prd/82-inboxlog-컬럼-정의권장-스키마.md
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from talktalk_shared.models.sheets_log_row import SheetsLogRow, combine_messages, truncate_from_end
from talktalk_shared.utils.masking import mask_question


def build_sheets_log_row(
    # Webhook and channel info
    channel_id: str,
    channel_name: str,
    user_id: str,
    event: str,
    # Message aggregation info
    messages: List[str],
    aggregation_id: str = "-",
    message_count: int = 1,
    # RAG and LLM info
    kb_chunks: Optional[List[Dict[str, Any]]] = None,
    draft_answer: str = "-",
    confidence: float = 0.0,
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH",
    # Mode and decision info
    global_mode: Literal["TEST", "PROD"] = "TEST",
    channel_mode: Literal["TEST", "PROD", "DISABLED"] = "TEST",
    send_to_user: bool = False,
    action_taken: Literal["NOT_SENT", "SENT", "FAILED"] = "NOT_SENT",
    talktalk_send_result: str = "-",
    # Telegram alert info
    telegram_alert_sent: bool = False,
    telegram_reasons: Optional[List[str]] = None,
    # Timing and error info
    latency_ms_total: int = 0,
    error_summary: str = "-",
    # Timestamp override (for testing)
    created_at: Optional[datetime] = None,
) -> SheetsLogRow:
    """
    Build a complete SheetsLogRow with all 23 columns populated

    Args:
        channel_id: Channel identifier
        channel_name: Human-readable channel name (or channel_id if not available)
        user_id: User identifier
        event: Event name (e.g., "send")
        messages: List of message texts (will be combined with \\n)
        aggregation_id: Aggregation session ID (default "-" for single message)
        message_count: Number of messages aggregated (default 1)
        kb_chunks: List of retrieved KB chunks with doc_id and chunk_id
        draft_answer: LLM draft answer (default "-")
        confidence: Confidence score 0-1 (default 0.0)
        risk_level: Risk level LOW/MEDIUM/HIGH (default "HIGH")
        global_mode: Global mode TEST/PROD (default "TEST")
        channel_mode: Channel mode TEST/PROD/DISABLED (default "TEST")
        send_to_user: Whether automated send is allowed (default False)
        action_taken: Action taken NOT_SENT/SENT/FAILED (default "NOT_SENT")
        talktalk_send_result: TalkTalk send API result (default "-")
        telegram_alert_sent: Whether Telegram alert was sent (default False)
        telegram_reasons: List of alert reasons (default None)
        latency_ms_total: Total processing latency in ms (default 0)
        error_summary: Error summary if any (default "-")
        created_at: Timestamp override for testing (default None = now)

    Returns:
        SheetsLogRow with all 23 columns populated

    Reference: AC in docs/stories/5.3.story.md
    """
    # AC: Generate row_id and created_at_kst
    row_id = SheetsLogRow.generate_row_id()
    created_at_kst = SheetsLogRow.format_created_at_kst(created_at)

    # AC3: Combine messages and apply 500-char truncation
    combined_raw = combine_messages(messages)
    question_raw = truncate_from_end(combined_raw, max_length=500)

    # AC3: Mask PII and apply same truncation
    question_masked = mask_question(question_raw)

    # AC: Format kb_used from kb_chunks
    kb_used = _format_kb_used(kb_chunks)

    # AC: Format telegram_reason from reasons list
    telegram_reason = _format_telegram_reason(telegram_reasons)

    return SheetsLogRow(
        row_id=row_id,
        created_at_kst=created_at_kst,
        channel_id=channel_id,
        channel_name=channel_name,
        user_id=user_id,
        event=event,
        aggregation_id=aggregation_id,
        message_count=message_count,
        question_raw=question_raw,
        question_masked=question_masked,
        kb_used=kb_used,
        draft_answer=draft_answer,
        confidence=confidence,
        risk_level=risk_level,
        send_to_user=send_to_user,
        global_mode=global_mode,
        channel_mode=channel_mode,
        action_taken=action_taken,
        talktalk_send_result=talktalk_send_result,
        telegram_alert_sent=telegram_alert_sent,
        telegram_reason=telegram_reason,
        latency_ms_total=latency_ms_total,
        error_summary=error_summary,
    )


def _format_kb_used(kb_chunks: Optional[List[Dict[str, Any]]]) -> str:
    """
    Format kb_chunks into "{doc_id}:{chunk_id}" joined by ";"

    Args:
        kb_chunks: List of chunks with doc_id and chunk_id fields

    Returns:
        Formatted string like "doc123:c_04;doc999:c_02" or "-" if empty

    Reference: Dev Notes in docs/stories/5.3.story.md
    """
    if not kb_chunks or len(kb_chunks) == 0:
        return "-"

    parts = []
    for chunk in kb_chunks:
        doc_id = chunk.get("doc_id", "unknown")
        chunk_id = chunk.get("chunk_id", "unknown")
        parts.append(f"{doc_id}:{chunk_id}")

    return ";".join(parts)


def _format_telegram_reason(reasons: Optional[List[str]]) -> str:
    """
    Format telegram alert reasons list into ";" separated string

    Args:
        reasons: List of alert reason strings

    Returns:
        Reasons joined by ";" or "-" if empty

    Reference: Dev Notes in docs/stories/5.3.story.md
    """
    if not reasons or len(reasons) == 0:
        return "-"

    return ";".join(reasons)
