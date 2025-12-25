"""
Message Aggregator Module

Handles message aggregation logic for Worker Lambda.
Implements 30-second time window message collection.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

import boto3

from talktalk_shared.config import (
    get_aggregation_trigger_queue_url,
    get_aggregation_window_seconds,
    get_aws_region,
    get_max_messages_per_aggregation,
)
from talktalk_shared.models.aggregation_state import AggregationState, AggregationStatus
from talktalk_shared.repositories.aggregation import AggregationRepository
from talktalk_shared.utils.logger import get_logger
from talktalk_shared.utils.masking import mask_question, mask_user_id
from talktalk_shared.utils.message_combiner import combine_messages

logger = get_logger(__name__)


if TYPE_CHECKING:
    from .pipeline import process_single_message
else:
    try:
        from pipeline import process_single_message
    except ImportError:  # pragma: no cover
        from .pipeline import process_single_message


def _split_user_key(user_key: str) -> Optional[Tuple[str, str]]:
    if "#" not in user_key:
        return None
    channel_id, user_id = user_key.split("#", 1)
    if not channel_id or not user_id:
        return None
    return channel_id, user_id


def _parse_iso8601_utc(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.removesuffix("Z"))
    except ValueError:
        return None


def is_aggregation_trigger(message_body: Dict[str, Any]) -> bool:
    """
    Check if message is an aggregation finalization trigger.

    Args:
        message_body: SQS message body (parsed JSON)

    Returns:
        True if message is a trigger, False otherwise
    """
    return message_body.get("action") == "FINALIZE_AGGREGATION"


def is_media_message(webhook_event: Dict[str, Any]) -> bool:
    """
    Check if webhook event contains media (image/file).

    Media messages should trigger immediate aggregation finalization.

    Args:
        webhook_event: Webhook event dict

    Returns:
        True if media message, False otherwise
    """
    return bool(webhook_event.get("imageContent") or webhook_event.get("compositeContent"))


def send_aggregation_trigger(user_key: str, aggregation_id: str, delay_seconds: int) -> None:
    """
    Send aggregation finalization trigger to AggregationTriggerQueue.

    Args:
        user_key: User key (channel_id#user_id)
        aggregation_id: Aggregation ID
        delay_seconds: Delay in seconds (default: 30)
    """
    queue_url = get_aggregation_trigger_queue_url()
    sqs_client = boto3.client("sqs", region_name=get_aws_region())

    message_body = {
        "action": "FINALIZE_AGGREGATION",
        "user_key": user_key,
        "aggregation_id": aggregation_id,
    }

    split = _split_user_key(user_key)
    channel_id = split[0] if split else None
    user_id_masked = mask_user_id(split[1]) if split else None

    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            DelaySeconds=delay_seconds,
        )

        logger.info(
            "Aggregation trigger sent",
            extra={
                "channel_id": channel_id,
                "user_id_masked": user_id_masked,
                "aggregation_id": aggregation_id,
                "delay_seconds": delay_seconds,
                "message_id": response.get("MessageId"),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to send aggregation trigger",
            extra={
                "channel_id": channel_id,
                "user_id_masked": user_id_masked,
                "aggregation_id": aggregation_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def handle_aggregation(channel_id: str, webhook_event: Dict[str, Any]) -> None:
    """
    Handle message aggregation logic for incoming webhook event.

    Process:
    1. Extract user_key from webhook event
    2. Check for active aggregation
    3. If none exists, create new aggregation + send trigger
    4. If exists, add message to aggregation
    5. If media message, finalize immediately

    Args:
        channel_id: TalkTalk channel ID
        webhook_event: Webhook event dict
    """
    user_id = webhook_event.get("user")
    if not user_id:
        logger.warning(
            "Missing user in webhook_event, skipping aggregation",
            extra={"channel_id": channel_id},
        )
        return

    user_key = AggregationState.make_user_key(channel_id, user_id)
    masked_user = mask_user_id(user_id)

    repo = AggregationRepository()

    # Check for active aggregation
    active = repo.get_active(user_key)

    # If the window has already expired, start a new session (AC7)
    if active:
        expires_at = _parse_iso8601_utc(active.expires_at)
        if expires_at and expires_at <= datetime.utcnow():
            logger.info(
                "Active aggregation window expired, starting new session",
                extra={
                    "channel_id": channel_id,
                    "user_id_masked": masked_user,
                    "previous_aggregation_id": active.aggregation_id,
                },
            )
            active = None

    if not active:
        # No active aggregation - create new one
        logger.info(
            "Creating new aggregation",
            extra={"channel_id": channel_id, "user_id_masked": masked_user},
        )
        state = repo.create(user_key, webhook_event)

        # Send trigger for finalization after window
        window_seconds = get_aggregation_window_seconds()
        send_aggregation_trigger(user_key, state.aggregation_id, window_seconds)

        logger.info(
            "New aggregation started",
            extra={
                "channel_id": channel_id,
                "user_id_masked": masked_user,
                "aggregation_id": state.aggregation_id,
                "window_seconds": window_seconds,
            },
        )

    else:
        # Active aggregation exists - add message
        logger.info(
            "Adding message to existing aggregation",
            extra={
                "channel_id": channel_id,
                "user_id_masked": masked_user,
                "aggregation_id": active.aggregation_id,
            },
        )

        # Check message limit
        max_messages = get_max_messages_per_aggregation()
        if active.message_count >= max_messages:
            logger.warning(
                "Max messages reached, ignoring additional message",
                extra={
                    "channel_id": channel_id,
                    "user_id_masked": masked_user,
                    "aggregation_id": active.aggregation_id,
                    "max_messages": max_messages,
                },
            )
            return

        state = repo.add_message(user_key, active.aggregation_id, webhook_event)

        logger.info(
            "Message added to aggregation",
            extra={
                "channel_id": channel_id,
                "user_id_masked": masked_user,
                "aggregation_id": active.aggregation_id,
                "message_count": state.message_count,
            },
        )

    # Check if media message - finalize immediately
    if is_media_message(webhook_event):
        logger.info(
            "Media message detected, finalizing aggregation immediately",
            extra={
                "channel_id": channel_id,
                "user_id_masked": masked_user,
                "aggregation_id": state.aggregation_id,
            },
        )
        finalize_aggregation({"user_key": user_key, "aggregation_id": state.aggregation_id})


def finalize_aggregation(trigger_message: Dict[str, Any]) -> None:
    """
    Finalize aggregation and process combined message.

    Process:
    1. Retrieve aggregation state
    2. Check if still AGGREGATING (avoid duplicate/late triggers)
    3. Combine messages
    4. Process combined text through existing pipeline
    5. Mark aggregation as COMPLETED

    Args:
        trigger_message: Trigger message dict (user_key, aggregation_id)
    """
    user_key = trigger_message.get("user_key")
    aggregation_id = trigger_message.get("aggregation_id")
    if not user_key or not aggregation_id:
        logger.warning(
            "Invalid trigger message, skipping finalization",
            extra={"trigger_keys": sorted(trigger_message.keys())},
        )
        return

    split = _split_user_key(user_key)
    if not split:
        logger.warning(
            "Invalid user_key format, skipping finalization",
            extra={"aggregation_id": aggregation_id},
        )
        return

    channel_id, user_id = split
    masked_user = mask_user_id(user_id)

    logger.info(
        "Finalizing aggregation",
        extra={
            "channel_id": channel_id,
            "user_id_masked": masked_user,
            "aggregation_id": aggregation_id,
        },
    )

    repo = AggregationRepository()

    # Retrieve aggregation
    state = repo.get(user_key, aggregation_id)
    if not state:
        logger.warning(
            "Aggregation not found (late/duplicate trigger?)",
            extra={
                "channel_id": channel_id,
                "user_id_masked": masked_user,
                "aggregation_id": aggregation_id,
            },
        )
        return

    # Check if still AGGREGATING
    if state.status != AggregationStatus.AGGREGATING:
        logger.warning(
            "Aggregation not AGGREGATING, skipping",
            extra={
                "channel_id": channel_id,
                "user_id_masked": masked_user,
                "aggregation_id": aggregation_id,
                "status": state.status.value,
            },
        )
        return

    # Combine messages
    combined_text = combine_messages(state.messages)
    question_masked = mask_question(combined_text)

    logger.info(
        "Messages combined",
        extra={
            "channel_id": channel_id,
            "user_id_masked": masked_user,
            "aggregation_id": aggregation_id,
            "message_count": state.message_count,
            "combined_length": len(combined_text),
            "question_masked": question_masked,
        },
    )

    aggregated_event: Dict[str, Any] = {}
    if state.messages:
        aggregated_event = dict(state.messages[-1].webhook_event)
    aggregated_event.setdefault("event", "send")
    aggregated_event["user"] = user_id

    text_content = aggregated_event.get("textContent")
    if isinstance(text_content, dict):
        aggregated_event["textContent"] = {**text_content, "text": combined_text}
    else:
        aggregated_event["textContent"] = {"text": combined_text}

    process_single_message(
        channel_id,
        aggregated_event,
        aggregation_id=aggregation_id,
        message_count=getattr(state, "message_count", 1),
    )

    # Mark as completed
    repo.complete(user_key, aggregation_id)

    logger.info(
        "Aggregation finalized",
        extra={
            "channel_id": channel_id,
            "user_id_masked": masked_user,
            "aggregation_id": aggregation_id,
        },
    )
