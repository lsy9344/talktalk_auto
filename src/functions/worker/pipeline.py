"""
Worker Pipeline Module

Single entrypoint for message processing (both aggregated and non-aggregated).
This file exists to avoid circular imports between app.py and aggregator.py.
"""

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .rag import retrieve_chunks
else:
    try:
        from rag import retrieve_chunks
    except ImportError:  # pragma: no cover
        from .rag import retrieve_chunks

from talktalk_shared.utils.logger import get_logger
from talktalk_shared.utils.masking import mask_question, mask_user_id

logger = get_logger(__name__)


def process_single_message(channel_id: str, webhook_event: Dict[str, Any]) -> None:
    """
    Process a single message through the existing pipeline.

    NOTE: The full RAG + LLM pipeline is out of scope here; this function currently logs
    a masked summary only (no PII).
    """
    user_id = webhook_event.get("user", "")

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
            "event": webhook_event.get("event"),
            "user_id_masked": mask_user_id(user_id) if user_id else "****",
            "question_masked": mask_question(text) if text else "",
        },
    )

    # Story 3.4: RAG retrieval (no PII in logs)
    if text:
        try:
            chunks = retrieve_chunks(channel_id, text)
            logger.info(
                "RAG retrieval completed",
                extra={
                    "channel_id": channel_id,
                    "chunk_count": len(chunks),
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

    # TODO: Implement LLM answer generation + decision + sending
