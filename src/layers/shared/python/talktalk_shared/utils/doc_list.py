"""Document list utilities for KB management"""
from typing import Any, Dict, List


def build_final_doc_list(channel_config: Dict[str, Any], common_doc_ids: List[str]) -> List[str]:
    """
    Build final document list for a channel by combining channel-specific and common docs

    Rules (Story 3.1 AC3):
    1. Start with channel-specific doc_ids from ChannelConfig
    2. If common_doc_enabled is true, append common doc_ids
    3. Remove duplicate doc_ids (keep first occurrence)
    4. Order: channel-specific first, then common

    Args:
        channel_config: Channel configuration dict containing:
            - doc_ids: List[str] (optional, defaults to [])
            - common_doc_enabled: bool (optional, defaults to True)
        common_doc_ids: List of common KB document IDs

    Returns:
        List of unique document IDs with order preserved (channel-specific first, then common)

    Example:
        >>> channel_config = {"doc_ids": ["doc1", "doc2"], "common_doc_enabled": True}
        >>> common_doc_ids = ["doc3", "doc1"]  # doc1 is duplicate
        >>> build_final_doc_list(channel_config, common_doc_ids)
        ['doc1', 'doc2', 'doc3']  # doc1 kept from channel docs, duplicate removed

    Reference: docs/architecture.md#Lambda Worker RAG + LLM 처리
    Story 3.1 AC3: Final document list calculation rules
    """
    # Get channel-specific doc_ids (default to empty list)
    channel_doc_ids = channel_config.get("doc_ids", [])
    if not isinstance(channel_doc_ids, list):
        channel_doc_ids = []

    # Start with channel-specific docs
    final_list = list(channel_doc_ids)

    # Check if common docs should be included (default to True)
    common_doc_enabled = channel_config.get("common_doc_enabled", True)

    # Append common docs if enabled
    if common_doc_enabled:
        final_list.extend(common_doc_ids)

    # Remove duplicates while preserving order (keep first occurrence)
    seen = set()
    deduplicated = []
    for doc_id in final_list:
        if doc_id not in seen:
            seen.add(doc_id)
            deduplicated.append(doc_id)

    return deduplicated
