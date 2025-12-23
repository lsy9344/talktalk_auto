"""
Ingest Lambda - Naver TalkTalk Webhook Handler

Receives webhook events from Naver TalkTalk and enqueues them to SQS.
Must respond within 5 seconds to meet TalkTalk's timeout requirements.

Reference: docs/stories/1.2.story.md
"""
import json
from typing import Any, Dict

import boto3
from pydantic import ValidationError

from talktalk_shared.config import get_aws_region, get_log_level, get_worker_queue_url
from talktalk_shared.models.pipeline_state import PipelineState
from talktalk_shared.models.webhook_event import WebhookEvent
from talktalk_shared.repositories.channel_config import ChannelConfigRepository
from talktalk_shared.repositories.deduplication import DeduplicationRepository
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__, level=get_log_level())

# Initialize clients (reused across invocations)
channel_config_repo = ChannelConfigRepository()
dedup_repo = DeduplicationRepository()
sqs_client = boto3.client("sqs", region_name=get_aws_region())
QUEUE_URL = get_worker_queue_url()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for TalkTalk webhook ingestion

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response

    Reference: docs/architecture.md#Components - Ingest Lambda
    """
    try:
        # Extract channel_id from path parameters
        channel_id = event.get("pathParameters", {}).get("channel_id")
        if not channel_id:
            logger.warning("Missing channel_id in path parameters")
            return _response(400, {"error": "Missing channel_id"})

        # Parse and validate webhook body
        try:
            body = json.loads(event.get("body", "{}"))
            webhook_event = WebhookEvent(**body)
        except json.JSONDecodeError:
            logger.warning("Invalid webhook payload: malformed JSON")
            return _response(400, {"error": "Invalid webhook payload"})
        except ValidationError as e:
            fields = sorted(
                {
                    ".".join(str(part) for part in err.get("loc", []))
                    for err in e.errors()
                    if err.get("loc")
                }
            )
            logger.warning(f"Invalid webhook payload: schema validation failed fields={fields}")
            return _response(400, {"error": "Invalid webhook payload"})

        # Get channel configuration
        channel_config = channel_config_repo.get(channel_id)
        if not channel_config:
            logger.info(f"Channel not found or disabled: {channel_id}")
            return _response(404, {"error": "Channel not found or disabled"})

        # Filter events - only process 'send' events
        if webhook_event.event != "send":
            logger.info(
                f"Ignoring non-send event: {webhook_event.event}",
                extra={"channel_id": channel_id, "event_type": webhook_event.event},
            )
            return _response(200, {"message": "Event ignored"})

        # Log RECEIVED state (valid 'send' event received)
        logger.info(
            "Valid send event received",
            extra={"channel_id": channel_id, "pipeline_state": PipelineState.RECEIVED.value},
        )

        # Check for duplicate (deduplication)
        is_new = dedup_repo.try_create(
            channel_id=channel_id,
            user_id=webhook_event.user,
            webhook_body=body,
            ttl_minutes=10,
        )

        if not is_new:
            # Duplicate detected - return 200 OK but don't enqueue
            logger.info(
                "Duplicate webhook event - skipping SQS enqueue",
                extra={"channel_id": channel_id},
            )
            return _response(200, {"message": "Duplicate event - already processed"})

        # Enqueue to SQS
        try:
            message_body = {
                "channel_id": channel_id,
                "webhook_event": body,
                "received_at": context.request_id if context else None,
                "pipeline_state": PipelineState.QUEUED.value,
            }

            sqs_client.send_message(
                QueueUrl=QUEUE_URL, MessageBody=json.dumps(message_body)
            )

            logger.info(
                "Message enqueued to SQS",
                extra={"channel_id": channel_id, "pipeline_state": PipelineState.QUEUED.value},
            )

            return _response(200, {"message": "Message enqueued"})

        except Exception as e:
            logger.error(
                f"Failed to send message to SQS: {str(e)}",
                extra={"channel_id": channel_id},
            )
            return _response(500, {"error": "Failed to enqueue message"})

    except Exception as e:
        logger.error(f"Unexpected error in Ingest Lambda: {str(e)}")
        return _response(500, {"error": "Internal server error"})


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create API Gateway response

    Args:
        status_code: HTTP status code
        body: Response body dict

    Returns:
        API Gateway formatted response
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
