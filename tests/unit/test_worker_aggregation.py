"""Unit tests for Worker aggregation logic (Story 2.5)"""

from unittest.mock import MagicMock, patch

from src.functions.worker import aggregator
from talktalk_shared.models.aggregation_state import AggregationStatus


class TestWorkerAggregation:
    def test_handle_aggregation_no_active_creates_and_sends_trigger(self) -> None:
        webhook_event = {"event": "send", "user": "user123", "textContent": {"text": "Hello"}}
        user_key = "wc123#user123"

        mock_repo = MagicMock()
        mock_repo.get_active.return_value = None

        mock_state = MagicMock()
        mock_state.aggregation_id = "agg-1"
        mock_repo.create.return_value = mock_state

        with patch.object(aggregator, "AggregationRepository", return_value=mock_repo):
            with patch.object(
                aggregator, "send_aggregation_trigger"
            ) as mock_send_trigger:
                with patch.object(
                    aggregator, "get_aggregation_window_seconds", return_value=30
                ):
                    aggregator.handle_aggregation("wc123", webhook_event)

        mock_repo.get_active.assert_called_once_with(user_key)
        mock_repo.create.assert_called_once_with(user_key, webhook_event)
        mock_send_trigger.assert_called_once_with(user_key, "agg-1", 30)

    def test_handle_aggregation_active_adds_message(self) -> None:
        webhook_event = {"event": "send", "user": "user123", "textContent": {"text": "Hello"}}
        user_key = "wc123#user123"

        mock_repo = MagicMock()
        active_state = MagicMock()
        active_state.aggregation_id = "agg-1"
        active_state.message_count = 1
        active_state.expires_at = "2999-01-01T00:00:00Z"
        mock_repo.get_active.return_value = active_state

        updated_state = MagicMock()
        updated_state.message_count = 2
        mock_repo.add_message.return_value = updated_state

        with patch.object(aggregator, "AggregationRepository", return_value=mock_repo):
            with patch.object(
                aggregator, "get_max_messages_per_aggregation", return_value=10
            ):
                aggregator.handle_aggregation("wc123", webhook_event)

        mock_repo.get_active.assert_called_once_with(user_key)
        mock_repo.add_message.assert_called_once_with(user_key, "agg-1", webhook_event)

    def test_handle_aggregation_max_messages_reached_ignores(self) -> None:
        webhook_event = {"event": "send", "user": "user123", "textContent": {"text": "Hello"}}

        mock_repo = MagicMock()
        active_state = MagicMock()
        active_state.aggregation_id = "agg-1"
        active_state.message_count = 10
        active_state.expires_at = "2999-01-01T00:00:00Z"
        mock_repo.get_active.return_value = active_state

        with patch.object(aggregator, "AggregationRepository", return_value=mock_repo):
            with patch.object(
                aggregator, "get_max_messages_per_aggregation", return_value=10
            ):
                aggregator.handle_aggregation("wc123", webhook_event)

        mock_repo.create.assert_not_called()
        mock_repo.add_message.assert_not_called()

    def test_handle_aggregation_expired_active_starts_new(self) -> None:
        webhook_event = {"event": "send", "user": "user123", "textContent": {"text": "Hello"}}
        user_key = "wc123#user123"

        mock_repo = MagicMock()
        active_state = MagicMock()
        active_state.aggregation_id = "old-agg"
        active_state.message_count = 1
        active_state.expires_at = "2000-01-01T00:00:00Z"
        mock_repo.get_active.return_value = active_state

        new_state = MagicMock()
        new_state.aggregation_id = "new-agg"
        mock_repo.create.return_value = new_state

        with patch.object(aggregator, "AggregationRepository", return_value=mock_repo):
            with patch.object(
                aggregator, "send_aggregation_trigger"
            ) as mock_send_trigger:
                with patch.object(
                    aggregator, "get_aggregation_window_seconds", return_value=30
                ):
                    aggregator.handle_aggregation("wc123", webhook_event)

        mock_repo.get_active.assert_called_once_with(user_key)
        mock_repo.create.assert_called_once_with(user_key, webhook_event)
        mock_send_trigger.assert_called_once_with(user_key, "new-agg", 30)

    def test_handle_aggregation_media_message_finalizes_immediately(self) -> None:
        webhook_event = {
            "event": "send",
            "user": "user123",
            "imageContent": {"imageUrl": "https://example.com/image.jpg"},
        }
        user_key = "wc123#user123"

        mock_repo = MagicMock()
        mock_repo.get_active.return_value = None

        mock_state = MagicMock()
        mock_state.aggregation_id = "agg-1"
        mock_repo.create.return_value = mock_state

        with patch.object(aggregator, "AggregationRepository", return_value=mock_repo):
            with patch.object(aggregator, "send_aggregation_trigger"):
                with patch.object(
                    aggregator, "get_aggregation_window_seconds", return_value=30
                ):
                    with patch.object(
                        aggregator, "finalize_aggregation"
                    ) as mock_finalize:
                        aggregator.handle_aggregation("wc123", webhook_event)

        mock_finalize.assert_called_once_with({"user_key": user_key, "aggregation_id": "agg-1"})

    def test_finalize_aggregation_processes_and_completes(self) -> None:
        msg = MagicMock()
        msg.webhook_event = {"event": "send", "user": "user123", "textContent": {"text": "Hello"}}

        state = MagicMock()
        state.status = AggregationStatus.AGGREGATING
        state.messages = [msg]
        state.message_count = 2

        mock_repo = MagicMock()
        mock_repo.get.return_value = state

        with patch.object(aggregator, "AggregationRepository", return_value=mock_repo):
            with patch.object(aggregator, "combine_messages", return_value="Hello\nWorld"):
                with patch.object(
                    aggregator, "process_single_message"
                ) as mock_process:
                    aggregator.finalize_aggregation(
                        {"user_key": "wc123#user123", "aggregation_id": "agg-1"}
                    )

        mock_process.assert_called_once()
        (called_channel_id, called_event), called_kwargs = mock_process.call_args
        assert called_channel_id == "wc123"
        assert called_event["user"] == "user123"
        assert called_event["textContent"]["text"] == "Hello\nWorld"
        assert called_kwargs["aggregation_id"] == "agg-1"
        assert called_kwargs["message_count"] == 2

        mock_repo.complete.assert_called_once_with("wc123#user123", "agg-1")

    def test_finalize_aggregation_skips_when_not_aggregating(self) -> None:
        state = MagicMock()
        state.status = AggregationStatus.COMPLETED

        mock_repo = MagicMock()
        mock_repo.get.return_value = state

        with patch.object(aggregator, "AggregationRepository", return_value=mock_repo):
            with patch.object(aggregator, "process_single_message") as mock_process:
                aggregator.finalize_aggregation(
                    {"user_key": "wc123#user123", "aggregation_id": "agg-1"}
                )

        mock_process.assert_not_called()
        mock_repo.complete.assert_not_called()

    def test_finalize_aggregation_missing_state_returns(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch.object(aggregator, "AggregationRepository", return_value=mock_repo):
            with patch.object(aggregator, "process_single_message") as mock_process:
                aggregator.finalize_aggregation(
                    {"user_key": "wc123#user123", "aggregation_id": "agg-1"}
                )

        mock_process.assert_not_called()
        mock_repo.complete.assert_not_called()
