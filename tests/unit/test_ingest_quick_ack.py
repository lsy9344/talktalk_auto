"""Test Ingest Lambda for quick 200 OK response (Story 7.1 AC4).

This test file validates AC4 (Story 7.1):
- Ingest returns 200 OK quickly (within webhook timeout constraints)
- Ingest only does: validation + SQS enqueue + immediate response
- Ingest does NOT call Worker/OpenAI/Google Sheets/Telegram (heavy work is async)

Reference: docs/stories/7.1.story.md AC4, AC5
Reference: src/functions/ingest/app.py
Reference: docs/architecture.md#naver-talktalk-webhook-api (3s/5s timeouts)
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Setup paths for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/functions/ingest"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/layers/shared/python"))


@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    context = MagicMock()
    context.request_id = "test-request-id"
    return context


@pytest.fixture
def valid_send_event():
    """Valid send webhook event"""
    return {
        "event": "send",
        "user": "user_abc123",
        "textContent": {"text": "안녕하세요"},
        "options": None,
        "imageContent": None,
        "compositeContent": None,
        "composingEnd": True,
    }


@pytest.fixture
def api_gateway_event(valid_send_event):
    """Valid API Gateway event"""
    return {
        "pathParameters": {"channel_id": "wc123456"},
        "body": json.dumps(valid_send_event),
    }


@pytest.fixture
def valid_channel_config():
    """Valid channel configuration"""
    return {
        "channel_id": "wc123456",
        "channel_name": "Test Channel",
        "enabled": True,
        "channel_mode": "TEST",
    }


class TestIngestQuickAck:
    """Test that Ingest returns 200 OK quickly without heavy processing."""

    @patch("app.sqs_client")
    @patch("app.dedup_repo")
    @patch("app.channel_config_repo")
    def test_ingest_returns_200_ok_for_valid_send_event(
        self,
        mock_channel_repo,
        mock_dedup_repo,
        mock_sqs,
        api_gateway_event,
        valid_channel_config,
        mock_context,
    ):
        """Arrange: Valid send event
        Act: Call lambda_handler
        Assert: Returns 200 OK, enqueues to SQS
        """
        # Import after mocking
        from app import lambda_handler

        # Arrange
        mock_channel_repo.get.return_value = valid_channel_config
        mock_dedup_repo.try_create.return_value = True
        mock_sqs.send_message.return_value = {}

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert - CRITICAL: 200 OK must be returned
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "Message enqueued" in body["message"]

        # Verify SQS enqueue was called
        mock_sqs.send_message.assert_called_once()

    @patch("app.sqs_client")
    @patch("app.dedup_repo")
    @patch("app.channel_config_repo")
    def test_ingest_does_not_call_worker_operations(
        self,
        mock_channel_repo,
        mock_dedup_repo,
        mock_sqs,
        api_gateway_event,
        valid_channel_config,
        mock_context,
    ):
        """Arrange: Valid send event
        Act: Call lambda_handler
        Assert: No Worker/heavy operations called (RAG, LLM, Sheets, Telegram)

        This test verifies that Ingest does NOT do heavy processing,
        which is critical for meeting the 3s/5s timeout constraints.
        """
        # Import after mocking
        from app import lambda_handler

        # Arrange
        mock_channel_repo.get.return_value = valid_channel_config
        mock_dedup_repo.try_create.return_value = True
        mock_sqs.send_message.return_value = {}

        # Mock heavy operations that should NEVER be called by Ingest
        with patch("app.retrieve_chunks", create=True) as mock_rag, \
             patch("app.OpenAIClient", create=True) as mock_openai, \
             patch("app.GoogleSheetsClient", create=True) as mock_sheets, \
             patch("app.TelegramClient", create=True) as mock_telegram:

            # Act
            response = lambda_handler(api_gateway_event, mock_context)

            # Assert
            assert response["statusCode"] == 200

            # CRITICAL: Heavy operations must NOT be called by Ingest
            mock_rag.assert_not_called()
            mock_openai.assert_not_called()
            mock_sheets.assert_not_called()
            mock_telegram.assert_not_called()

    @patch("app.sqs_client")
    @patch("app.dedup_repo")
    @patch("app.channel_config_repo")
    def test_ingest_only_validates_enqueues_responds(
        self,
        mock_channel_repo,
        mock_dedup_repo,
        mock_sqs,
        api_gateway_event,
        valid_channel_config,
        mock_context,
    ):
        """Verify Ingest's workflow: validate → enqueue → respond

        This is the "즉시 ACK" (immediate ACK) pattern required for
        meeting TalkTalk webhook timeout constraints.
        """
        # Import after mocking
        from app import lambda_handler

        # Arrange
        mock_channel_repo.get.return_value = valid_channel_config
        mock_dedup_repo.try_create.return_value = True
        mock_sqs.send_message.return_value = {}

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert - Verify the 3-step workflow
        # Step 1: Validation (channel config retrieval)
        mock_channel_repo.get.assert_called_once_with("wc123456")

        # Step 2: Enqueue to SQS (Worker will process asynchronously)
        assert mock_sqs.send_message.call_count == 1
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        assert message_body["channel_id"] == "wc123456"
        assert message_body["pipeline_state"] == "QUEUED"

        # Step 3: Immediate response
        assert response["statusCode"] == 200

    @patch("app.sqs_client")
    @patch("app.dedup_repo")
    @patch("app.channel_config_repo")
    def test_ingest_duplicate_event_returns_200_without_enqueue(
        self,
        mock_channel_repo,
        mock_dedup_repo,
        mock_sqs,
        api_gateway_event,
        valid_channel_config,
        mock_context,
    ):
        """Arrange: Duplicate event (dedup returns False)
        Act: Call lambda_handler
        Assert: Returns 200 OK but does NOT enqueue to SQS

        This ensures webhook always gets 200 OK, even for duplicates.
        """
        # Import after mocking
        from app import lambda_handler

        # Arrange
        mock_channel_repo.get.return_value = valid_channel_config
        mock_dedup_repo.try_create.return_value = False  # Duplicate!
        mock_sqs.send_message.return_value = {}

        # Act
        response = lambda_handler(api_gateway_event, mock_context)

        # Assert - Still returns 200 OK
        assert response["statusCode"] == 200

        # But SQS enqueue should NOT be called for duplicates
        mock_sqs.send_message.assert_not_called()

    @patch("app.sqs_client")
    @patch("app.dedup_repo")
    @patch("app.channel_config_repo")
    def test_ingest_non_send_event_returns_200_without_enqueue(
        self,
        mock_channel_repo,
        mock_dedup_repo,
        mock_sqs,
        valid_channel_config,
        mock_context,
    ):
        """Arrange: Non-send event (e.g., 'open' event)
        Act: Call lambda_handler
        Assert: Returns 200 OK but does NOT enqueue
        """
        # Import after mocking
        from app import lambda_handler

        # Arrange
        non_send_event = {
            "pathParameters": {"channel_id": "wc123456"},
            "body": json.dumps({
                "event": "open",  # Not 'send'
                "user": "user_abc123",
            }),
        }

        mock_channel_repo.get.return_value = valid_channel_config

        # Act
        response = lambda_handler(non_send_event, mock_context)

        # Assert
        assert response["statusCode"] == 200

        # SQS should not be called for non-send events
        mock_sqs.send_message.assert_not_called()
        mock_dedup_repo.try_create.assert_not_called()

    @patch("app.sqs_client")
    @patch("app.dedup_repo")
    @patch("app.channel_config_repo")
    def test_ingest_echo_event_returns_200_without_enqueue(
        self,
        mock_channel_repo,
        mock_dedup_repo,
        mock_sqs,
        valid_channel_config,
        mock_context,
    ):
        """Story 7.2 AC3 - echo event must return 200 OK without enqueue (loop prevention)

        Arrange: echo event (response message echoed back)
        Act: Call lambda_handler
        Assert: Returns 200 OK but does NOT enqueue to SQS (prevents infinite loop)
        """
        # Import after mocking
        from app import lambda_handler

        # Arrange
        echo_event = {
            "pathParameters": {"channel_id": "wc123456"},
            "body": json.dumps({
                "event": "echo",  # Echo event - dangerous for loops
                "user": "user_abc123",
                "textContent": {"text": "Our bot's response echoed back"},
            }),
        }

        mock_channel_repo.get.return_value = valid_channel_config

        # Act
        response = lambda_handler(echo_event, mock_context)

        # Assert - Must return 200 OK (acknowledge webhook)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "Event ignored" in body["message"]

        # CRITICAL: Must NOT enqueue or process (prevents infinite echo loop)
        mock_sqs.send_message.assert_not_called()
        mock_dedup_repo.try_create.assert_not_called()
