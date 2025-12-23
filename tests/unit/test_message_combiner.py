"""Unit tests for message_combiner utility"""

from talktalk_shared.models.aggregation_state import AggregatedMessage
from talktalk_shared.utils.message_combiner import combine_messages


class TestMessageCombiner:
    """Tests for combine_messages function"""

    def test_combine_empty_list(self):
        """Test combining empty list returns empty string"""
        # Act
        result = combine_messages([])

        # Assert
        assert result == ""

    def test_combine_single_message(self):
        """Test combining single message"""
        # Arrange
        messages = [
            AggregatedMessage(
                timestamp="2025-12-24T10:30:00Z",
                text="Hello",
                webhook_event={"event": "send", "user": "user123"},
            )
        ]

        # Act
        result = combine_messages(messages)

        # Assert
        assert result == "Hello"

    def test_combine_multiple_messages_chronological(self):
        """Test combining multiple messages in chronological order"""
        # Arrange
        messages = [
            AggregatedMessage(
                timestamp="2025-12-24T10:30:00Z",
                text="Hello",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:05Z",
                text="How are you?",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:10Z",
                text="Nice to meet you",
                webhook_event={},
            ),
        ]

        # Act
        result = combine_messages(messages)

        # Assert
        assert result == "Hello\nHow are you?\nNice to meet you"

    def test_combine_messages_sorts_by_timestamp(self):
        """Test combining messages sorts by timestamp"""
        # Arrange - Messages in wrong order
        messages = [
            AggregatedMessage(
                timestamp="2025-12-24T10:30:10Z",
                text="Third",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:00Z",
                text="First",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:05Z",
                text="Second",
                webhook_event={},
            ),
        ]

        # Act
        result = combine_messages(messages)

        # Assert
        assert result == "First\nSecond\nThird"

    def test_combine_messages_skips_empty_text(self):
        """Test combining messages skips empty text"""
        # Arrange
        messages = [
            AggregatedMessage(
                timestamp="2025-12-24T10:30:00Z",
                text="Hello",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:05Z",
                text="   ",  # Whitespace only
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:10Z",
                text="World",
                webhook_event={},
            ),
        ]

        # Act
        result = combine_messages(messages)

        # Assert
        assert result == "Hello\nWorld"

    def test_combine_messages_truncates_to_500_chars(self):
        """Test combining messages truncates to last 500 characters"""
        # Arrange - Create messages totaling more than 500 chars
        long_text = "A" * 200
        messages = [
            AggregatedMessage(
                timestamp="2025-12-24T10:30:00Z",
                text=long_text,  # 200 chars
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:05Z",
                text=long_text,  # 200 chars
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:10Z",
                text=long_text,  # 200 chars
                webhook_event={},
            ),
        ]

        # Act
        result = combine_messages(messages)

        # Assert
        # Total would be 200 + 1(\n) + 200 + 1(\n) + 200 = 602 chars
        # Should truncate to last 500 chars
        assert len(result) == 500
        # Should end with the last message
        assert result.endswith("A")

    def test_combine_messages_exactly_500_chars(self):
        """Test combining messages with exactly 500 characters"""
        # Arrange
        text1 = "A" * 250
        text2 = "B" * 249  # 250 + 1(\n) + 249 = 500
        messages = [
            AggregatedMessage(
                timestamp="2025-12-24T10:30:00Z",
                text=text1,
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:05Z",
                text=text2,
                webhook_event={},
            ),
        ]

        # Act
        result = combine_messages(messages)

        # Assert
        assert len(result) == 500
        assert result == text1 + "\n" + text2

    def test_combine_messages_under_500_chars(self):
        """Test combining messages under 500 characters (no truncation)"""
        # Arrange
        messages = [
            AggregatedMessage(
                timestamp="2025-12-24T10:30:00Z",
                text="Short message 1",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:05Z",
                text="Short message 2",
                webhook_event={},
            ),
        ]

        # Act
        result = combine_messages(messages)

        # Assert
        assert len(result) < 500
        assert result == "Short message 1\nShort message 2"

    def test_combine_korean_messages(self):
        """Test combining Korean messages"""
        # Arrange
        messages = [
            AggregatedMessage(
                timestamp="2025-12-24T10:30:00Z",
                text="안녕하세요",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:05Z",
                text="내일 예약하려고 하는데",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:10Z",
                text="인화지가 총 몇장 제공되는지",
                webhook_event={},
            ),
            AggregatedMessage(
                timestamp="2025-12-24T10:30:15Z",
                text="문의드려요",
                webhook_event={},
            ),
        ]

        # Act
        result = combine_messages(messages)

        # Assert
        expected = "안녕하세요\n내일 예약하려고 하는데\n인화지가 총 몇장 제공되는지\n문의드려요"
        assert result == expected
