import re

from .settings import get_settings

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    lowered = text.strip().lower()
    return _WHITESPACE_RE.sub(" ", lowered)


def is_too_short(text: str) -> bool:
    settings = get_settings()
    normalized = normalize_text(text)
    cleaned = re.sub(r"[^\w\s]", "", normalized)
    return len(cleaned) < settings.min_text_length


def contains_forbidden(text: str) -> bool:
    settings = get_settings()
    normalized = normalize_text(text)
    for keyword in settings.forbidden_keywords:
        if keyword and keyword.lower() in normalized:
            return True
    return False
