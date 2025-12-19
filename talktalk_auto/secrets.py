from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .aws_clients import secrets_client


_CACHE: dict[str, tuple[str, datetime]] = {}
_CACHE_TTL = timedelta(minutes=10)


def get_secret_string(secret_arn: str) -> str:
    if not secret_arn:
        return ""
    now = datetime.now(timezone.utc)
    cached = _CACHE.get(secret_arn)
    if cached and cached[1] > now:
        return cached[0]

    client = secrets_client()
    resp = client.get_secret_value(SecretId=secret_arn)
    value = resp.get("SecretString", "")
    _CACHE[secret_arn] = (value, now + _CACHE_TTL)
    return value
