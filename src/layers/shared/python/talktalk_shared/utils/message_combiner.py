"""
Message Combiner Utility

Combines multiple messages from aggregation into a single query text.
"""

from typing import List

from talktalk_shared.models.aggregation_state import AggregatedMessage

MAX_COMBINED_TEXT_LENGTH = 500


def combine_messages(messages: List[AggregatedMessage]) -> str:
    """
    Combine multiple messages into a single query text.

    Process:
    1. Sort messages by timestamp (chronological order)
    2. Join with newline
    3. Limit to last 500 characters if exceeded

    Args:
        messages: List of AggregatedMessage objects

    Returns:
        Combined text (max 500 chars)

    Reference: docs/stories/2.5.story.md#ac5-message-combination-algorithm
    """
    if not messages:
        return ""

    # Sort by timestamp (chronological order)
    sorted_messages = sorted(messages, key=lambda m: m.timestamp)

    # Extract text from each message
    texts = [msg.text for msg in sorted_messages if msg.text.strip()]

    # Join with newline
    combined = "\n".join(texts)

    # Limit to last 500 characters
    if len(combined) > MAX_COMBINED_TEXT_LENGTH:
        combined = combined[-MAX_COMBINED_TEXT_LENGTH:]

    return combined
