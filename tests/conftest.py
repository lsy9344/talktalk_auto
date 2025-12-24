"""Pytest configuration and shared fixtures"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Ensure shared Lambda Layer code is importable (talktalk_shared)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHARED_LAYER_PYTHON_PATH = PROJECT_ROOT / "src" / "layers" / "shared" / "python"
sys.path.insert(0, str(SHARED_LAYER_PYTHON_PATH))


@pytest.fixture(autouse=True)
def setup_env_vars() -> None:
    """Setup environment variables for tests"""
    os.environ.setdefault("AWS_REGION", "ap-northeast-2")
    os.environ.setdefault("CHANNEL_CONFIG_TABLE", "test-ChannelConfig")
    os.environ.setdefault("DEDUPLICATION_TABLE", "test-Deduplication")
    os.environ.setdefault("GLOBAL_MODE_TABLE", "test-GlobalMode")
    os.environ.setdefault(
        "WORKER_QUEUE_URL",
        "https://sqs.ap-northeast-2.amazonaws.com/123456789012/test-queue",
    )
    os.environ.setdefault("LOG_LEVEL", "ERROR")
    os.environ.setdefault("SERVICE_NAME", "test-talktalk-auto")


@pytest.fixture
def webhook_events() -> Dict[str, Any]:
    """Load webhook event fixtures"""
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "webhook_events.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def valid_channel_config() -> Dict[str, Any]:
    """Valid channel configuration"""
    return {
        "channel_id": "wc123456",
        "channel_name": "Test Channel",
        "channel_mode": "TEST",
        "enabled": True,
        "confidence_threshold": 0.8,
    }


@pytest.fixture
def disabled_channel_config() -> Dict[str, Any]:
    """Disabled channel configuration"""
    return {
        "channel_id": "wc_disabled",
        "channel_name": "Disabled Channel",
        "channel_mode": "DISABLED",
        "enabled": True,
    }


@pytest.fixture
def api_gateway_event(webhook_events: Dict[str, Any]) -> Dict[str, Any]:
    """API Gateway event template"""
    return {
        "pathParameters": {"channel_id": "wc123456"},
        "body": json.dumps(webhook_events["valid_send_event"]),
        "requestContext": {"requestId": "test-request-id"},
    }
