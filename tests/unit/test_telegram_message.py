"""Unit tests for telegram_message.py

Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
Reference: docs/stories/2.3.story.md AC 4
"""
from src.functions.worker.telegram_message import format_alert_message


class TestFormatAlertMessage:
    """Test format_alert_message function"""

    def test_format_basic_alert_message(self):
        """Basic alert message should include all required fields"""
        # Arrange
        channel_name = "TestChannel"
        channel_id = "ch_123"
        user_id = "user_abcdef123456"
        global_mode = "TEST"
        channel_mode = "TEST"
        question = "배송은 언제 되나요?"
        reasons = ["TEST_MODE"]

        # Act
        result = format_alert_message(
            channel_name=channel_name,
            channel_id=channel_id,
            user_id=user_id,
            global_mode=global_mode,
            channel_mode=channel_mode,
            question=question,
            reasons=reasons,
        )

        # Assert
        assert "TestChannel" in result
        assert "ch_123" in result
        assert "TEST" in result
        assert "TEST_MODE" in result
        assert "배송은 언제 되나요?" in result

    def test_format_masks_user_id(self):
        """User ID should be masked in alert message"""
        # Arrange
        user_id = "user_abcdef123456"

        # Act
        result = format_alert_message(
            channel_name="Channel",
            channel_id="ch_1",
            user_id=user_id,
            global_mode="PROD",
            channel_mode="PROD",
            question="Question",
            reasons=["REASON"],
        )

        # Assert
        assert "user_abcdef123456" not in result
        assert "us*************56" in result  # 17 chars -> 2 + 13 asterisks + 2

    def test_format_masks_question_pii(self):
        """PII in question should be masked"""
        # Arrange
        question = "전화번호 010-1234-5678로 연락주세요"

        # Act
        result = format_alert_message(
            channel_name="Channel",
            channel_id="ch_1",
            user_id="user_123",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            reasons=["REASON"],
        )

        # Assert
        assert "010-1234-5678" not in result
        assert "[PHONE]" in result

    def test_format_multiple_reasons(self):
        """Multiple reasons should be listed as bullet points"""
        # Arrange
        reasons = [
            "RAG_INSUFFICIENT_EVIDENCE",
            "RISK_LEVEL_HIGH",
            "QUESTION_TOO_SHORT",
        ]

        # Act
        result = format_alert_message(
            channel_name="Channel",
            channel_id="ch_1",
            user_id="user_123",
            global_mode="PROD",
            channel_mode="PROD",
            question="?",
            reasons=reasons,
        )

        # Assert
        assert "- RAG_INSUFFICIENT_EVIDENCE" in result
        assert "- RISK_LEVEL_HIGH" in result
        assert "- QUESTION_TOO_SHORT" in result

    def test_format_includes_emoji_and_structure(self):
        """Message should include emoji and proper structure"""
        # Arrange
        reasons = ["TEST_MODE"]

        # Act
        result = format_alert_message(
            channel_name="Channel",
            channel_id="ch_1",
            user_id="user_123",
            global_mode="TEST",
            channel_mode="TEST",
            question="Question",
            reasons=reasons,
        )

        # Assert
        assert "🚨" in result
        assert "📌" in result
        assert "👤" in result
        assert "⚙️" in result
        assert "📋" in result
        assert "💬" in result
