"""
Worker Pipeline Module

Single entrypoint for message processing (both aggregated and non-aggregated).
This file exists to avoid circular imports between app.py and aggregator.py.

Reference: docs/stories/5.3.story.md (Task 3 - Google Sheets logging integration)
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from .alert_rules import evaluate_alert_triggers
    from .decision import make_send_decision
    from .operational_rules import compute_action_taken
    from .rag import retrieve_chunks
    from .sheets_logging import build_sheets_log_row
    from .telegram_message import (
        format_template_a_operator_review,
        format_template_b_system_error,
        format_template_c_prod_send_blocked,
    )
else:
    try:
        from alert_rules import evaluate_alert_triggers
        from decision import make_send_decision
        from operational_rules import compute_action_taken
        from rag import retrieve_chunks
        from sheets_logging import build_sheets_log_row
        from telegram_message import (
            format_template_a_operator_review,
            format_template_b_system_error,
            format_template_c_prod_send_blocked,
        )
    except ImportError:  # pragma: no cover
        from .alert_rules import evaluate_alert_triggers
        from .decision import make_send_decision
        from .operational_rules import compute_action_taken
        from .rag import retrieve_chunks
        from .sheets_logging import build_sheets_log_row
        from .telegram_message import (
            format_template_a_operator_review,
            format_template_b_system_error,
            format_template_c_prod_send_blocked,
        )

from talktalk_shared.clients.google_sheets_client import GoogleSheetsClient, GoogleSheetsError
from talktalk_shared.clients.telegram_client import TelegramClient
from talktalk_shared.repositories.channel_config import ChannelConfigRepository
from talktalk_shared.repositories.deduplication import DeduplicationRepository
from talktalk_shared.repositories.global_mode import GlobalModeRepository
from talktalk_shared.utils.circuit_breaker import CircuitBreakerOpenError
from talktalk_shared.utils.logger import get_logger
from talktalk_shared.utils.masking import mask_question, mask_user_id
from talktalk_shared.utils.question_hash import create_question_hash

logger = get_logger(__name__)


def process_single_message(
    channel_id: str,
    webhook_event: Dict[str, Any],
    aggregation_id: str = "-",
    message_count: int = 1,
) -> None:
    """
    Process a single message through the complete pipeline.

    Flow:
    1. Extract message and metadata
    2. Get channel config and global mode
    3. RAG retrieval
    4. LLM answer generation (placeholder)
    5. Make send decision
    6. Evaluate alert triggers
    7. Log to Google Sheets (inbox_log)
    8. Send Telegram alert if needed
    9. Send answer if approved (placeholder)

    Reference: docs/stories/5.3.story.md AC 1, 2, 3
    """
    start_time = time.time()
    user_id = webhook_event.get("user", "")
    event = webhook_event.get("event", "send")

    # Extract text
    text = ""
    text_content = webhook_event.get("textContent")
    if isinstance(text_content, dict):
        text = text_content.get("text", "")
    elif isinstance(text_content, str):
        text = text_content

    logger.info(
        "Processing message through pipeline",
        extra={
            "channel_id": channel_id,
            "event": event,
            "user_id_masked": mask_user_id(user_id) if user_id else "****",
            "question_masked": mask_question(text) if text else "",
        },
    )

    # Get channel config
    channel_repo = ChannelConfigRepository()
    channel_config = channel_repo.get(channel_id)
    if not channel_config:
        logger.error("Channel config not found", extra={"channel_id": channel_id})
        return

    channel_name = channel_config.get("channel_name", channel_id)
    raw_channel_mode = channel_config.get("channel_mode", "TEST")
    channel_mode: Literal["TEST", "PROD"] = (
        "PROD" if raw_channel_mode == "PROD" else "TEST"
    )

    # Get global mode
    global_mode_repo = GlobalModeRepository()
    global_mode: Literal["TEST", "PROD"] = global_mode_repo.get_mode()

    # Story 3.4: RAG retrieval
    kb_chunks: List[Dict[str, Any]] = []
    if text:
        try:
            retrieved_chunks = retrieve_chunks(channel_id, text)
            kb_chunks = [chunk.to_dict() for chunk in retrieved_chunks]
            logger.info(
                "RAG retrieval completed",
                extra={
                    "channel_id": channel_id,
                    "chunk_count": len(retrieved_chunks),
                },
            )
        except Exception as e:
            logger.error(
                "RAG retrieval failed",
                extra={
                    "channel_id": channel_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

    # TODO: LLM answer generation (placeholder)
    # For now, use default values
    draft_answer = "-"
    confidence = 0.0
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH"
    llm_response: Dict[str, Any] = {
        "send_to_user": False,
        "confidence": confidence,
        "risk_level": risk_level,
        "needs_operator": False,
        "policy_flags": [],
    }

    # Make send decision
    decision = make_send_decision(
        channel_config=channel_config,
        global_mode=global_mode,
        llm_response=llm_response,
    )
    send_to_user = decision["send_to_user"]

    # TODO: Send answer (placeholder)
    # For now, assume no send attempt
    send_success: Optional[bool] = None
    talktalk_send_result = "-"

    # Compute action_taken using operational rules
    action_taken = compute_action_taken(
        global_mode=global_mode,
        channel_mode=channel_mode,
        send_to_user=send_to_user,
        send_success=send_success,
    )

    # Evaluate alert triggers
    alert_decision = evaluate_alert_triggers(
        global_mode=global_mode,
        channel_mode=channel_mode,
        webhook_event=webhook_event,
        retrieved_chunks=kb_chunks,
        llm_response=llm_response,
        send_decision=decision,
        error_code=None,
    )
    telegram_alert_sent = False
    telegram_reasons = alert_decision["reasons"]

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    # Build SheetsLogRow
    log_row = build_sheets_log_row(
        channel_id=channel_id,
        channel_name=channel_name,
        user_id=user_id,
        event=event,
        messages=[text] if text else [],
        aggregation_id=aggregation_id,
        message_count=message_count,
        kb_chunks=kb_chunks,
        draft_answer=draft_answer,
        confidence=confidence,
        risk_level=risk_level,
        global_mode=global_mode,
        channel_mode=channel_mode,
        send_to_user=send_to_user,
        action_taken=action_taken,
        talktalk_send_result=talktalk_send_result,
        telegram_alert_sent=False,  # Will update after sending
        telegram_reasons=telegram_reasons,
        latency_ms_total=latency_ms,
        error_summary="-",
    )

    # Log to Google Sheets
    sheets_client = GoogleSheetsClient()
    sheets_error_code: Optional[str] = None

    try:
        sheets_client.append_log_row(log_row)
        logger.info(
            "Logged to Google Sheets inbox_log",
            extra={"channel_id": channel_id, "row_id": log_row.row_id},
        )
    except (GoogleSheetsError, CircuitBreakerOpenError) as e:
        sheets_error_code = "E005"
        logger.error(
            "Failed to log to Google Sheets (E005)",
            extra={
                "channel_id": channel_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        # Add E005 to alert reasons
        telegram_reasons.append("EXTERNAL_API_FAILURE_E005")
    except Exception as e:
        sheets_error_code = "E005"
        logger.error(
            "Unexpected error logging to Google Sheets (E005)",
            extra={
                "channel_id": channel_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        telegram_reasons.append("EXTERNAL_API_FAILURE_E005")

    # Send Telegram alert if needed
    if alert_decision["should_alert"] or sheets_error_code == "E005":
        # Story 6.3 AC1: Check for duplicate Telegram alert before sending
        question_hash = create_question_hash(text if text else "")
        dedup_repo = DeduplicationRepository()

        # Try to create dedup record (returns False if duplicate)
        should_send_telegram = dedup_repo.try_create_telegram_alert(
            channel_id=channel_id,
            user_id=user_id,
            question_hash=question_hash,
            ttl_minutes=10,  # AC3: 10 minutes TTL (within 5-10 min range)
        )

        if not should_send_telegram:
            # AC1: Skip Telegram alert if duplicate
            logger.info(
                "Skipping Telegram alert due to deduplication",
                extra={
                    "channel_id": channel_id,
                    "question_hash": question_hash,
                },
            )
        else:
            # No duplicate - proceed with Telegram alert
            telegram_client = TelegramClient()

            # Select appropriate template based on situation (Story 6.2 Task 2)
            # Template B: System error (E005 or other error codes)
            if sheets_error_code == "E005":
                alert_message = format_template_b_system_error(
                    channel_name=channel_name,
                    channel_id=channel_id,
                    user_id=user_id,
                    question=text if text else "",
                    stage="SHEETS_APPEND",
                    error_summary="Failed to append log row to Google Sheets",
                    attempt=1,
                    max_attempts=3,
                    aggregation_id=aggregation_id,
                    message_count=message_count,
                    row_id=log_row.row_id,
                )
            # Template C: PROD send blocked (both PROD but send_to_user is False)
            elif global_mode == "PROD" and channel_mode == "PROD" and not send_to_user:
                alert_message = format_template_c_prod_send_blocked(
                    channel_name=channel_name,
                    channel_id=channel_id,
                    user_id=user_id,
                    question=text if text else "",
                    draft_answer=draft_answer,
                    reasons=telegram_reasons,
                    confidence=confidence,
                    risk_level=risk_level,
                    aggregation_id=aggregation_id,
                    message_count=message_count,
                    row_id=log_row.row_id,
                )
            # Template A: Operator review needed (default for all other cases)
            else:
                alert_message = format_template_a_operator_review(
                    channel_name=channel_name,
                    channel_id=channel_id,
                    user_id=user_id,
                    global_mode=global_mode,
                    channel_mode=channel_mode,
                    question=text if text else "",
                    draft_answer=draft_answer,
                    reasons=telegram_reasons,
                    risk_level=risk_level,
                    confidence=confidence,
                    aggregation_id=aggregation_id,
                    message_count=message_count,
                    row_id=log_row.row_id,
                )

            try:
                telegram_alert_sent = asyncio.run(telegram_client.send_message(alert_message))
                logger.info(
                    "Telegram alert sent",
                    extra={
                        "channel_id": channel_id,
                        "reasons": telegram_reasons,
                        "sent": telegram_alert_sent,
                    },
                )
            except Exception as e:
                logger.error(
                    "Failed to send Telegram alert (non-blocking)",
                    extra={
                        "channel_id": channel_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

    logger.info(
        "Pipeline processing completed",
        extra={
            "channel_id": channel_id,
            "action_taken": action_taken,
            "telegram_alert_sent": telegram_alert_sent,
            "latency_ms": latency_ms,
        },
    )
