from __future__ import annotations

import requests

from .secrets import get_secret_string

SEND_API_URL = "https://gw.talk.naver.com/chatbot/v1/event"


def resolve_auth_token(secret_arn: str, direct_token: str | None = None) -> str:
    if direct_token:
        return direct_token
    if secret_arn:
        return get_secret_string(secret_arn)
    return ""


def send_message(auth_token: str, user_id: str, text: str) -> None:
    if not auth_token:
        raise ValueError("Authorization token is required")
    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json;charset=UTF-8",
    }
    payload = {
        "event": "send",
        "user": user_id,
        "textContent": {"text": text},
    }
    resp = requests.post(SEND_API_URL, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
