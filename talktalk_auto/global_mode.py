from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .aws_clients import ssm_client
from .settings import get_settings


_CACHE: tuple[str, datetime] | None = None
_CACHE_TTL = timedelta(minutes=2)


def get_global_mode() -> str:
    global _CACHE
    now = datetime.now(timezone.utc)
    if _CACHE and _CACHE[1] > now:
        return _CACHE[0]

    settings = get_settings()
    client = ssm_client()
    try:
        resp = client.get_parameter(Name=settings.global_mode_param)
        value = resp.get("Parameter", {}).get("Value", "TEST")
    except client.exceptions.ParameterNotFound:
        value = "TEST"

    mode = value.strip().upper() if value else "TEST"
    _CACHE = (mode, now + _CACHE_TTL)
    return mode
