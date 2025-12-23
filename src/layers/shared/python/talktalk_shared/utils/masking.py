"""PII masking utilities for logs and notifications

Reference: docs/architecture.md#privacy-and-masking-requirements
"""
import re


def mask_user_id(user_id: str) -> str:
    """
    Mask user_id by showing first 2 and last 2 characters only

    Example: "abcdef123456" -> "ab******56"

    Args:
        user_id: User identifier to mask

    Returns:
        Masked user_id string
    """
    if not user_id or len(user_id) <= 4:
        return "****"

    return f"{user_id[:2]}{'*' * (len(user_id) - 4)}{user_id[-2:]}"


def mask_question(question: str) -> str:
    """
    Mask sensitive information in question text

    Masks:
    - Phone numbers (010-1234-5678 pattern)
    - Email addresses
    - Credit card numbers (continuous 13-16 digits)

    Args:
        question: Question text to mask

    Returns:
        Question with PII masked

    Reference: docs/architecture.md#privacy-and-masking-requirements
    """
    if not question:
        return ""

    masked = question

    # Mask phone numbers (Korean format: 010-xxxx-xxxx or 01012345678)
    masked = re.sub(
        r"01[0-9]-?\d{3,4}-?\d{4}",
        "[PHONE]",
        masked
    )

    # Mask email addresses
    masked = re.sub(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "[EMAIL]",
        masked
    )

    # Mask credit card numbers (13-16 continuous digits)
    masked = re.sub(
        r"\b\d{13,16}\b",
        "[CARD]",
        masked
    )

    return masked
