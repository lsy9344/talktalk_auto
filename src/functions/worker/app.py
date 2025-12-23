"""
Worker Lambda: Message Processing Worker

Processes messages from WorkerQueue and AggregationTriggerQueue.
Handles message aggregation (30s window) and RAG + LLM pipeline.
"""

import json
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .aggregator import finalize_aggregation, handle_aggregation, is_aggregation_trigger
    from .pipeline import process_single_message
else:
    try:
        from aggregator import finalize_aggregation, handle_aggregation, is_aggregation_trigger
    except ImportError:  # pragma: no cover
        from .aggregator import finalize_aggregation, handle_aggregation, is_aggregation_trigger

    try:
        from pipeline import process_single_message
    except ImportError:  # pragma: no cover
        from .pipeline import process_single_message

from talktalk_shared.config import get_enable_message_aggregation
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Worker Lambda main handler.

    Processes SQS messages from:
    - WorkerQueue: Webhook events for processing
    - AggregationTriggerQueue: 30s delayed triggers for aggregation finalization

    Args:
        event: SQS event containing Records
        context: Lambda context

    Returns:
        Response with processed count
    """
    logger.info("Worker Lambda invoked", extra={"record_count": len(event.get("Records", []))})

    processed = 0
    failed = 0

    for record in event.get("Records", []):
        try:
            process_message(record)
            processed += 1
        except Exception as e:
            logger.error(
                "Failed to process message",
                extra={"message_id": record.get("messageId"), "error": str(e)},
                exc_info=True,
            )
            failed += 1

    logger.info("Worker Lambda completed", extra={"processed": processed, "failed": failed})

    return {"statusCode": 200, "body": json.dumps({"processed": processed, "failed": failed})}


def process_message(record: Dict[str, Any]) -> None:
    """
    Process a single SQS message.

    Routes message to appropriate handler based on message type:
    - FINALIZE_AGGREGATION: Aggregation trigger
    - Regular webhook: Normal processing (or aggregation if enabled)

    Args:
        record: SQS record
    """
    body = json.loads(record["body"])

    logger.info(
        "Processing message",
        extra={"message_id": record.get("messageId"), "body_keys": list(body.keys())},
    )

    # Check if aggregation trigger
    if is_aggregation_trigger(body):
        logger.info("Processing aggregation trigger")
        finalize_aggregation(body)
        return

    # Regular webhook event
    channel_id = body.get("channel_id")
    if not channel_id:
        logger.warning("No channel_id in message body, skipping")
        return

    webhook_event = body.get("webhook_event")
    if not webhook_event:
        logger.warning("No webhook_event in message body, skipping")
        return

    # Check if aggregation is enabled
    aggregation_enabled = get_enable_message_aggregation()

    if aggregation_enabled:
        logger.info("Message aggregation enabled, handling aggregation")
        handle_aggregation(channel_id, webhook_event)
    else:
        logger.info("Message aggregation disabled, processing directly")
        process_single_message(channel_id, webhook_event)
