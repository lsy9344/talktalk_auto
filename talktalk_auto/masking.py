import re

_EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_PHONE_RE = re.compile(r"\b(01[016789])[-\s]?\d{3,4}[-\s]?\d{4}\b")
_LONG_DIGIT_RE = re.compile(r"\b(\d{7,})\b")


def _mask_email(match: re.Match) -> str:
    first = match.group(1)
    rest = match.group(2)
    domain = match.group(3)
    if not rest:
        return f"{first}***{domain}"
    return f"{first}{'*' * min(3, len(rest))}{domain}"


def _mask_phone(match: re.Match) -> str:
    value = match.group(0)
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10:
        return value
    return f"{digits[:3]}-****-{digits[-4:]}"


def _mask_long_digits(match: re.Match) -> str:
    value = match.group(1)
    if len(value) <= 4:
        return value
    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"


def mask_pii(text: str) -> str:
    if not text:
        return ""
    masked = _EMAIL_RE.sub(_mask_email, text)
    masked = _PHONE_RE.sub(_mask_phone, masked)
    masked = _LONG_DIGIT_RE.sub(_mask_long_digits, masked)
    return masked
