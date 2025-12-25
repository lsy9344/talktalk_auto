"""
Question Hash Utility

Creates a hash for question text to use in Telegram alert deduplication.

Story 6.3: Telegram 알림 중복 방지 (권장)
Reference: docs/prd/93-알림-중복-방지권장.md
"""

import hashlib


def create_question_hash(question_text: str, max_length: int = 500) -> str:
    """
    Create a hash for question text used in Telegram alert deduplication.

    Process:
    1. Apply 500-char limit (from end)
    2. Compute SHA256 hash
    3. Return first 16 characters

    Args:
        question_text: Final question text (already combined if aggregated)
        max_length: Maximum length to use (default 500)

    Returns:
        First 16 characters of SHA256 hash

    Example:
        >>> create_question_hash("안녕하세요 환불 문의")
        'a1b2c3d4e5f6g7h8'

    Reference:
        - docs/stories/6.3.story.md#ac2-질문해시-계산-규칙
        - docs/stories/1.2.story.md#dev-notes---dedup중복-방지-규칙
    """
    # AC2: Apply 500-char limit from end
    if len(question_text) > max_length:
        question_text = question_text[-max_length:]

    # AC2: Compute SHA256 hash
    hash_obj = hashlib.sha256(question_text.encode("utf-8"))
    full_hash = hash_obj.hexdigest()

    # AC2: Return first 16 characters
    return full_hash[:16]
