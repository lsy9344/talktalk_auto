"""Unit tests for sheets_logging module

Reference: docs/stories/5.3.story.md AC 3, 4
Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
"""
from src.functions.worker.sheets_logging import (
    _format_kb_used,
    _format_telegram_reason,
    build_sheets_log_row,
)
from talktalk_shared.models.sheets_log_row import SheetsLogRow


class TestFormatKbUsed:
    """Test _format_kb_used helper function"""

    def test_empty_chunks_returns_dash(self):
        """Empty kb_chunks should return '-'"""
        # Arrange
        kb_chunks = []

        # Act
        result = _format_kb_used(kb_chunks)

        # Assert
        assert result == "-"

    def test_none_chunks_returns_dash(self):
        """None kb_chunks should return '-'"""
        # Arrange
        kb_chunks = None

        # Act
        result = _format_kb_used(kb_chunks)

        # Assert
        assert result == "-"

    def test_single_chunk_formats_correctly(self):
        """Single chunk should format as 'doc_id:chunk_id'"""
        # Arrange
        kb_chunks = [{"doc_id": "doc123", "chunk_id": "c_01"}]

        # Act
        result = _format_kb_used(kb_chunks)

        # Assert
        assert result == "doc123:c_01"

    def test_multiple_chunks_format_with_semicolon(self):
        """Multiple chunks should be joined with ';'"""
        # Arrange
        kb_chunks = [
            {"doc_id": "doc123", "chunk_id": "c_01"},
            {"doc_id": "doc456", "chunk_id": "c_02"},
        ]

        # Act
        result = _format_kb_used(kb_chunks)

        # Assert
        assert result == "doc123:c_01;doc456:c_02"

    def test_missing_doc_id_uses_unknown(self):
        """Missing doc_id should use 'unknown'"""
        # Arrange
        kb_chunks = [{"chunk_id": "c_01"}]

        # Act
        result = _format_kb_used(kb_chunks)

        # Assert
        assert result == "unknown:c_01"


class TestFormatTelegramReason:
    """Test _format_telegram_reason helper function"""

    def test_empty_reasons_returns_dash(self):
        """Empty reasons list should return '-'"""
        # Arrange
        reasons = []

        # Act
        result = _format_telegram_reason(reasons)

        # Assert
        assert result == "-"

    def test_none_reasons_returns_dash(self):
        """None reasons should return '-'"""
        # Arrange
        reasons = None

        # Act
        result = _format_telegram_reason(reasons)

        # Assert
        assert result == "-"

    def test_single_reason_returns_as_is(self):
        """Single reason should be returned as-is"""
        # Arrange
        reasons = ["TEST_MODE"]

        # Act
        result = _format_telegram_reason(reasons)

        # Assert
        assert result == "TEST_MODE"

    def test_multiple_reasons_joined_with_semicolon(self):
        """Multiple reasons should be joined with ';'"""
        # Arrange
        reasons = ["TEST_MODE", "RAG_INSUFFICIENT_EVIDENCE", "RISK_LEVEL_HIGH"]

        # Act
        result = _format_telegram_reason(reasons)

        # Assert
        assert result == "TEST_MODE;RAG_INSUFFICIENT_EVIDENCE;RISK_LEVEL_HIGH"


class TestBuildSheetsLogRow:
    """Test build_sheets_log_row function"""

    def test_minimal_log_row_has_all_23_columns(self):
        """Minimal log row should have all 23 columns"""
        # Arrange
        channel_id = "wc123456"
        channel_name = "Test Channel"
        user_id = "user123"
        event = "send"
        messages = ["안녕하세요"]

        # Act
        log_row = build_sheets_log_row(
            channel_id=channel_id,
            channel_name=channel_name,
            user_id=user_id,
            event=event,
            messages=messages,
        )

        # Assert
        assert isinstance(log_row, SheetsLogRow)
        values = log_row.to_sheets_values()
        assert len(values) == 23

    def test_question_raw_truncates_at_500_chars(self):
        """question_raw should be truncated to 500 chars from end"""
        # Arrange
        long_message = "a" * 600
        messages = [long_message]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
        )

        # Assert
        assert len(log_row.question_raw) == 500
        assert log_row.question_raw == "a" * 500

    def test_question_masked_applies_masking(self):
        """question_masked should mask PII"""
        # Arrange
        messages = ["전화번호는 010-1234-5678 입니다"]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
        )

        # Assert
        assert "[PHONE]" in log_row.question_masked
        assert "010-1234-5678" not in log_row.question_masked

    def test_question_masked_masks_email(self):
        """question_masked should mask email addresses"""
        # Arrange
        messages = ["이메일은 test@example.com 입니다"]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
        )

        # Assert
        assert "[EMAIL]" in log_row.question_masked
        assert "test@example.com" not in log_row.question_masked

    def test_question_masked_masks_credit_card(self):
        """question_masked should mask credit card numbers"""
        # Arrange
        messages = ["카드번호는 4111111111111111 입니다"]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
        )

        # Assert
        assert "[CARD]" in log_row.question_masked
        assert "4111111111111111" not in log_row.question_masked

    def test_multiple_messages_combined_with_newline(self):
        """Multiple messages should be combined with \\n"""
        # Arrange
        messages = ["첫 번째 메시지", "두 번째 메시지", "세 번째 메시지"]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
        )

        # Assert
        assert log_row.question_raw == "첫 번째 메시지\n두 번째 메시지\n세 번째 메시지"

    def test_kb_chunks_formatted_correctly(self):
        """kb_chunks should be formatted as 'doc:chunk;doc:chunk'"""
        # Arrange
        kb_chunks = [
            {"doc_id": "doc1", "chunk_id": "c_01"},
            {"doc_id": "doc2", "chunk_id": "c_02"},
        ]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=["test"],
            kb_chunks=kb_chunks,
        )

        # Assert
        assert log_row.kb_used == "doc1:c_01;doc2:c_02"

    def test_telegram_reasons_formatted_correctly(self):
        """telegram_reasons should be formatted with ';' separator"""
        # Arrange
        telegram_reasons = ["TEST_MODE", "RISK_LEVEL_HIGH"]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=["test"],
            telegram_reasons=telegram_reasons,
        )

        # Assert
        assert log_row.telegram_reason == "TEST_MODE;RISK_LEVEL_HIGH"

    def test_default_values_applied(self):
        """Default values should be applied for missing fields"""
        # Arrange
        messages = ["test"]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
        )

        # Assert
        assert log_row.aggregation_id == "-"
        assert log_row.message_count == 1
        assert log_row.draft_answer == "-"
        assert log_row.confidence == 0.0
        assert log_row.risk_level == "HIGH"
        assert log_row.global_mode == "TEST"
        assert log_row.channel_mode == "TEST"
        assert log_row.send_to_user is False
        assert log_row.action_taken == "NOT_SENT"
        assert log_row.talktalk_send_result == "-"
        assert log_row.telegram_alert_sent is False
        assert log_row.error_summary == "-"

    def test_test_mode_values_set_correctly(self):
        """TEST mode values should be set correctly"""
        # Arrange
        messages = ["test"]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
            global_mode="TEST",
            channel_mode="TEST",
            send_to_user=False,
            action_taken="NOT_SENT",
        )

        # Assert
        assert log_row.global_mode == "TEST"
        assert log_row.channel_mode == "TEST"
        assert log_row.send_to_user is False
        assert log_row.action_taken == "NOT_SENT"

    def test_prod_mode_sent_values_set_correctly(self):
        """PROD mode SENT values should be set correctly"""
        # Arrange
        messages = ["test"]

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
            global_mode="PROD",
            channel_mode="PROD",
            send_to_user=True,
            action_taken="SENT",
            talktalk_send_result="200_OK",
        )

        # Assert
        assert log_row.global_mode == "PROD"
        assert log_row.channel_mode == "PROD"
        assert log_row.send_to_user is True
        assert log_row.action_taken == "SENT"
        assert log_row.talktalk_send_result == "200_OK"

    def test_empty_messages_handled(self):
        """Empty messages list should be handled gracefully"""
        # Arrange
        messages = []

        # Act
        log_row = build_sheets_log_row(
            channel_id="wc123",
            channel_name="Test",
            user_id="user1",
            event="send",
            messages=messages,
        )

        # Assert
        assert log_row.question_raw == ""
        assert log_row.question_masked == ""
