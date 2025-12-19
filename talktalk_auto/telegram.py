from __future__ import annotations

import requests

from .masking import mask_pii
from .secrets import get_secret_string
from .settings import get_settings


def _get_bot_token() -> str:
    settings = get_settings()
    if settings.telegram_bot_token:
        return settings.telegram_bot_token
    if settings.telegram_bot_token_secret_arn:
        return get_secret_string(settings.telegram_bot_token_secret_arn)
    return ""


def send_alert(chat_id: str, message: str) -> None:
    token = _get_bot_token()
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mask_pii(message),
        "disable_web_page_preview": True,
    }
    requests.post(url, json=payload, timeout=10)
