"""Unit tests for WebhookEvent Pydantic model"""
import pytest
from pydantic import ValidationError

from talktalk_shared.models.webhook_event import WebhookEvent


def test_webhook_event_valid_send(webhook_events):
    """Test valid send event parsing"""
    # Arrange
    event_data = webhook_events["valid_send_event"]

    # Act
    webhook_event = WebhookEvent(**event_data)

    # Assert
    assert webhook_event.event == "send"
    assert webhook_event.user == "U1234567890abcdef"
    assert webhook_event.textContent is not None
    assert webhook_event.textContent.text == "교환 가능한가요?"
    assert webhook_event.options is not None
    assert webhook_event.options.mobile is True


def test_webhook_event_echo(webhook_events):
    """Test echo event parsing"""
    # Arrange
    event_data = webhook_events["echo_event"]

    # Act
    webhook_event = WebhookEvent(**event_data)

    # Assert
    assert webhook_event.event == "echo"
    assert webhook_event.user == "U1234567890abcdef"


def test_webhook_event_open(webhook_events):
    """Test open event parsing"""
    # Arrange
    event_data = webhook_events["open_event"]

    # Act
    webhook_event = WebhookEvent(**event_data)

    # Assert
    assert webhook_event.event == "open"
    assert webhook_event.textContent is None


def test_webhook_event_missing_required_field(webhook_events):
    """Test validation error on missing required field"""
    # Arrange
    event_data = webhook_events["invalid_event_missing_required"]

    # Act & Assert
    with pytest.raises(ValidationError):
        WebhookEvent(**event_data)
