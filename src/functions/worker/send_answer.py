"""Send answer to customer via TalkTalk Send API.

Reference: docs/architecture.md#naver-talktalk-send-api
Reference: docs/stories/2.4.story.md AC 2, 3, 4, 6
"""

import logging
from typing import Any, Dict, Literal, Optional, TypedDict

from src.functions.worker.decision import SendDecision, make_send_decision
from talktalk_shared.clients.talktalk_client import TalkTalkClient
from talktalk_shared.repositories.channel_config import ChannelConfigRepository
from talktalk_shared.utils.circuit_breaker import CircuitBreakerOpenError
from talktalk_shared.utils.secrets import ParameterStoreError, get_parameter

logger = logging.getLogger(__name__)


class SendError(TypedDict):
    """Send error information for upstream handling."""

    error_code: str
    error_message: str
    should_alert: bool


class SendResult(TypedDict):
    """Result of send_answer_if_allowed function."""

    sent: bool
    reason: str
    error: Optional[SendError]


async def send_answer_if_allowed(
    channel_id: str,
    user_id: str,
    answer_text: str,
    global_mode: Literal["TEST", "PROD"],
    llm_response: Dict[str, Any],
    channel_auth_token_override: Optional[str] = None,
    channel_config_repo: Optional[ChannelConfigRepository] = None,
    talktalk_client: Optional[TalkTalkClient] = None,
) -> SendResult:
    """Send answer to customer if decision logic allows.

    This function orchestrates:
    1. Get channel config from DynamoDB
    2. Make send decision using 3-gate system
    3. Get auth token from SSM Parameter Store (or use override for testing)
    4. Call TalkTalk Send API if approved

    Args:
        channel_id: Channel ID (e.g., "wc123456")
        user_id: TalkTalk user ID
        answer_text: Answer text to send
        global_mode: Global mode ("TEST" or "PROD")
        llm_response: LLM response dict with send_to_user, confidence, etc.
        channel_auth_token_override: Optional auth token override for testing/local
        channel_config_repo: Optional ChannelConfigRepository instance (for testing)
        talktalk_client: Optional TalkTalkClient instance (for testing)

    Returns:
        SendResult with sent status, reason, and optional error

    Reference: docs/architecture.md#decision-logic-implementation
    Reference: docs/stories/2.4.story.md AC 2, 3, 4, 6
    """
    # Initialize dependencies
    repo = channel_config_repo or ChannelConfigRepository()
    client = talktalk_client or TalkTalkClient()

    # Step 1: Get channel config
    try:
        channel_config = repo.get(channel_id)
        if channel_config is None:
            logger.error(
                "Channel config not found or disabled",
                extra={"channel_id": channel_id},
            )
            return {
                "sent": False,
                "reason": "CHANNEL_CONFIG_NOT_FOUND",
                "error": {
                    "error_code": "E006",
                    "error_message": "Channel config not found or disabled",
                    "should_alert": True,
                },
            }
    except Exception as e:
        logger.error(
            "Failed to get channel config",
            extra={
                "channel_id": channel_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return {
            "sent": False,
            "reason": "CHANNEL_CONFIG_ERROR",
            "error": {
                "error_code": "E006",
                "error_message": f"Failed to get channel config: {type(e).__name__}",
                "should_alert": True,
            },
        }

    # Step 2: Make send decision
    decision: SendDecision = make_send_decision(
        channel_config=channel_config,
        global_mode=global_mode,
        llm_response=llm_response,
    )

    # If decision is not to send, return early
    if not decision["send_to_user"]:
        logger.info(
            "Send decision blocked",
            extra={
                "channel_id": channel_id,
                "reason": decision["reason"],
                "action": decision["action"],
            },
        )
        return {
            "sent": False,
            "reason": decision["reason"],
            "error": None,
        }

    # Only proceed if action is SEND_LOG_NO_ALERT
    if decision["action"] != "SEND_LOG_NO_ALERT":
        logger.warning(
            "Send decision approved but action is not SEND_LOG_NO_ALERT",
            extra={
                "channel_id": channel_id,
                "action": decision["action"],
            },
        )
        return {
            "sent": False,
            "reason": "UNEXPECTED_ACTION",
            "error": None,
        }

    # Step 3: Get auth token
    try:
        if channel_auth_token_override:
            # Use override for testing/local
            auth_token = channel_auth_token_override
            logger.debug("Using auth token override")
        else:
            # Get from SSM Parameter Store (SecureString)
            parameter_name = channel_config.get("talktalk_auth_parameter_name")

            if not parameter_name:
                logger.error(
                    "Missing talktalk_auth_parameter_name in channel config",
                    extra={"channel_id": channel_id},
                )
                return {
                    "sent": False,
                    "reason": "MISSING_AUTH_PARAMETER_NAME",
                    "error": {
                        "error_code": "E006",
                        "error_message": "Missing talktalk_auth_parameter_name",
                        "should_alert": True,
                    },
                }

            auth_token = get_parameter(parameter_name)

    except ParameterStoreError as e:
        logger.error(
            "Failed to get auth token from SSM Parameter Store",
            extra={
                "channel_id": channel_id,
                "error": str(e),
            },
        )
        return {
            "sent": False,
            "reason": "AUTH_TOKEN_RETRIEVAL_FAILED",
            "error": {
                "error_code": "E006",
                "error_message": "Failed to retrieve auth token",
                "should_alert": True,
            },
        }

    # Step 4: Send message via TalkTalk API
    try:
        success = await client.send_text_message(
            channel_auth_token=auth_token,
            user_id=user_id,
            text=answer_text,
        )

        if success:
            logger.info(
                "Answer sent successfully to customer",
                extra={
                    "channel_id": channel_id,
                    "user_id": user_id[:8] + "***",
                },
            )
            return {
                "sent": True,
                "reason": "SENT_SUCCESSFULLY",
                "error": None,
            }
        else:
            logger.error(
                "Failed to send answer to customer",
                extra={
                    "channel_id": channel_id,
                    "user_id": user_id[:8] + "***",
                },
            )
            return {
                "sent": False,
                "reason": "SEND_API_FAILED",
                "error": {
                    "error_code": "E006",
                    "error_message": "TalkTalk Send API failed",
                    "should_alert": True,
                },
            }

    except CircuitBreakerOpenError as e:
        logger.error(
            "Circuit breaker is open - cannot send",
            extra={
                "channel_id": channel_id,
                "user_id": user_id[:8] + "***",
                "error": str(e),
            },
        )
        return {
            "sent": False,
            "reason": "CIRCUIT_BREAKER_OPEN",
            "error": {
                "error_code": "E006",
                "error_message": "Circuit breaker is open",
                "should_alert": True,
            },
        }

    except Exception as e:
        logger.error(
            "Unexpected error sending answer",
            extra={
                "channel_id": channel_id,
                "user_id": user_id[:8] + "***",
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return {
            "sent": False,
            "reason": "UNEXPECTED_ERROR",
            "error": {
                "error_code": "E006",
                "error_message": f"Unexpected error: {type(e).__name__}",
                "should_alert": True,
            },
        }
