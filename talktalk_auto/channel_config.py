from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .aws_clients import dynamodb_resource
from .models import ChannelConfig
from .settings import get_settings


_CACHE: dict[str, tuple[ChannelConfig, datetime]] = {}
_CACHE_TTL = timedelta(minutes=5)


def get_channel_config(channel_id: str) -> ChannelConfig | None:
    if not channel_id:
        return None
    cached = _CACHE.get(channel_id)
    now = datetime.now(timezone.utc)
    if cached and cached[1] > now:
        return cached[0]

    settings = get_settings()
    if not settings.channel_config_table:
        return None

    table = dynamodb_resource().Table(settings.channel_config_table)
    resp = table.get_item(Key={"channel_id": channel_id})
    item = resp.get("Item")
    if not item:
        return None

    config = ChannelConfig.from_item(item)
    _CACHE[channel_id] = (config, now + _CACHE_TTL)
    return config
