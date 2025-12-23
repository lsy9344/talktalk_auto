"""Unit tests for Ingest Lambda"""
import json
import os

# Import after mocking to ensure mocks are applied
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/functions/ingest"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/layers/shared/python"))


@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    context = MagicMock()
    context.request_id = "test-request-id"
    return context


@pytest.fixture
def mock_dependencies():
    """Mock all dependencies"""
    with patch("app.channel_config_repo") as mock_channel_repo, patch(
        "app.dedup_repo"
    ) as mock_dedup_repo, patch("app.sqs_client") as mock_sqs:
        yield {
            "channel_repo": mock_channel_repo,
            "dedup_repo": mock_dedup_repo,
            "sqs_client": mock_sqs,
        }


class TestIngestLambda:
    """Tests for Ingest Lambda handler"""

    def test_valid_send_event_success(
        self, api_gateway_event, valid_channel_config, mock_context, mock_dependencies
    ):
        """Test valid send event is enqueued successfully"""
        # Import here to ensure mocks are applied
        from app import lambda_handler

        # Arrange
        mock_dependencies["channel_repo"].get.return_value = valid_channel_config
        mock_dependencies["dedup_repo"].try_create.return_value = True
        mock_dependencies["sqs_client"].send_message.return_value = {}

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert
        assert response["statusCode"] == 200
        assert "Message enqueued" in response["body"]
        mock_dependencies["channel_repo"].get.assert_called_once_with("wc123456")
        mock_dependencies["dedup_repo"].try_create.assert_called_once()
        mock_dependencies["sqs_client"].send_message.assert_called_once()

    def test_missing_channel_id(self, webhook_events, mock_context, mock_dependencies):
        """Test missing channel_id returns 400"""
        from app import lambda_handler

        # Arrange
        event = {
            "pathParameters": {},  # Missing channel_id
            "body": json.dumps(webhook_events["valid_send_event"]),
        }

        # Act
        response = lambda_handler(event, mock_context)

        # Assert
        assert response["statusCode"] == 400
        assert "Missing channel_id" in response["body"]

    def test_invalid_webhook_payload(self, mock_context, mock_dependencies):
        """Test invalid JSON payload returns 400"""
        from app import lambda_handler

        # Arrange
        event = {
            "pathParameters": {"channel_id": "wc123"},
            "body": "invalid json",
        }

        # Act
        response = lambda_handler(event, mock_context)

        # Assert
        assert response["statusCode"] == 400
        assert "Invalid webhook payload" in response["body"]

    def test_channel_not_found(
        self, api_gateway_event, mock_context, mock_dependencies
    ):
        """Test nonexistent channel returns 404"""
        from app import lambda_handler

        # Arrange
        mock_dependencies["channel_repo"].get.return_value = None

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert
        assert response["statusCode"] == 404
        assert "Channel not found or disabled" in response["body"]

    def test_channel_disabled(
        self, api_gateway_event, disabled_channel_config, mock_context, mock_dependencies
    ):
        """Test disabled channel returns 404"""
        from app import lambda_handler

        # Arrange
        mock_dependencies["channel_repo"].get.return_value = None  # Repo returns None for disabled

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert
        assert response["statusCode"] == 404

    def test_non_send_event_ignored(
        self, webhook_events, valid_channel_config, mock_context, mock_dependencies
    ):
        """Test non-send events (echo, open, leave) are ignored"""
        from app import lambda_handler

        # Arrange
        event = {
            "pathParameters": {"channel_id": "wc123456"},
            "body": json.dumps(webhook_events["echo_event"]),
        }
        mock_dependencies["channel_repo"].get.return_value = valid_channel_config

        # Act
        response = lambda_handler(event, mock_context)

        # Assert
        assert response["statusCode"] == 200
        assert "Event ignored" in response["body"]
        # Should NOT call dedup or SQS
        mock_dependencies["dedup_repo"].try_create.assert_not_called()
        mock_dependencies["sqs_client"].send_message.assert_not_called()

    def test_duplicate_event_skipped(
        self, api_gateway_event, valid_channel_config, mock_context, mock_dependencies
    ):
        """Test duplicate event returns 200 but doesn't enqueue"""
        from app import lambda_handler

        # Arrange
        mock_dependencies["channel_repo"].get.return_value = valid_channel_config
        mock_dependencies["dedup_repo"].try_create.return_value = False  # Duplicate

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert
        assert response["statusCode"] == 200
        assert "Duplicate event" in response["body"]
        # Should NOT enqueue to SQS
        mock_dependencies["sqs_client"].send_message.assert_not_called()

    def test_sqs_failure_returns_500(
        self, api_gateway_event, valid_channel_config, mock_context, mock_dependencies
    ):
        """Test SQS send failure returns 500"""
        from app import lambda_handler

        # Arrange
        mock_dependencies["channel_repo"].get.return_value = valid_channel_config
        mock_dependencies["dedup_repo"].try_create.return_value = True
        mock_dependencies["sqs_client"].send_message.side_effect = Exception(
            "SQS error"
        )

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert
        assert response["statusCode"] == 500
        assert "Failed to enqueue message" in response["body"]

    def test_sqs_message_includes_pipeline_state(
        self, api_gateway_event, valid_channel_config, mock_context, mock_dependencies
    ):
        """Test SQS message includes pipeline_state field with QUEUED value"""
        from app import lambda_handler

        # Arrange
        mock_dependencies["channel_repo"].get.return_value = valid_channel_config
        mock_dependencies["dedup_repo"].try_create.return_value = True
        mock_dependencies["sqs_client"].send_message.return_value = {}

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert
        assert response["statusCode"] == 200

        # Verify SQS was called
        assert mock_dependencies["sqs_client"].send_message.called

        # Get the message body sent to SQS
        call_args = mock_dependencies["sqs_client"].send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])

        # Verify pipeline_state is present and set to QUEUED (string value)
        assert "pipeline_state" in message_body
        assert message_body["pipeline_state"] == "QUEUED"
