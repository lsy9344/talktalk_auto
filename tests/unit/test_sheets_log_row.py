"""Unit tests for SheetsLogRow model

Story 5.2 AC4: Test column order, 500-char truncation, aggregation rules
Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
"""

import pytest

from talktalk_shared.models.sheets_log_row import (
    INBOX_LOG_COLUMNS,
    SheetsLogRow,
    combine_messages,
    truncate_from_end,
)


class TestInboxLogColumns:
    """Test INBOX_LOG_COLUMNS constant"""

    def test_column_count(self):
        """AC4: Verify column count is 23"""
        # Arrange & Act
        column_count = len(INBOX_LOG_COLUMNS)

        # Assert
        assert column_count == 23, "inbox_log must have exactly 23 columns"

    def test_column_order(self):
        """AC4: Verify column order matches PRD 8.2"""
        # Arrange
        expected_columns = [
            "row_id",
            "created_at_kst",
            "channel_id",
            "channel_name",
            "user_id",
            "event",
            "aggregation_id",
            "message_count",
            "question_raw",
            "question_masked",
            "kb_used",
            "draft_answer",
            "confidence",
            "risk_level",
            "send_to_user",
            "global_mode",
            "channel_mode",
            "action_taken",
            "talktalk_send_result",
            "telegram_alert_sent",
            "telegram_reason",
            "latency_ms_total",
            "error_summary",
        ]

        # Act & Assert
        assert INBOX_LOG_COLUMNS == expected_columns, "Column order must match PRD 8.2"


class TestTruncateFromEnd:
    """Test truncate_from_end helper function"""

    def test_text_shorter_than_limit(self):
        """AC3: Text shorter than limit should not be truncated"""
        # Arrange
        text = "안녕하세요"

        # Act
        result = truncate_from_end(text, max_length=500)

        # Assert
        assert result == text
        assert len(result) == 5

    def test_text_exactly_limit(self):
        """AC3: Text exactly at limit should not be truncated"""
        # Arrange
        text = "a" * 500

        # Act
        result = truncate_from_end(text, max_length=500)

        # Assert
        assert result == text
        assert len(result) == 500

    def test_text_longer_than_limit_truncates_from_end(self):
        """AC3: Text longer than limit should keep last 500 chars"""
        # Arrange
        text = "a" * 100 + "b" * 450  # 550 chars total

        # Act
        result = truncate_from_end(text, max_length=500)

        # Assert
        assert len(result) == 500
        # Should keep last 500 chars (50 'a's + 450 'b's)
        assert result.startswith("a" * 50)
        assert result.endswith("b" * 450)
        assert "a" * 51 not in result  # First 50 'a's should be gone

    def test_korean_text_truncation(self):
        """AC3: Korean text should be truncated correctly"""
        # Arrange
        # Each Korean char counts as 1 in Python len()
        text = "가" * 600

        # Act
        result = truncate_from_end(text, max_length=500)

        # Assert
        assert len(result) == 500
        assert result == "가" * 500

    def test_custom_max_length(self):
        """Test custom max_length parameter"""
        # Arrange
        text = "Hello World! This is a test message."

        # Act
        result = truncate_from_end(text, max_length=10)

        # Assert
        assert len(result) == 10
        assert result == "t message."  # Last 10 chars


class TestCombineMessages:
    """Test combine_messages helper function"""

    def test_single_message(self):
        """AC3: Single message should be returned as-is"""
        # Arrange
        messages = ["안녕하세요"]

        # Act
        result = combine_messages(messages)

        # Assert
        assert result == "안녕하세요"

    def test_multiple_messages_joined_with_newline(self):
        """AC3: Multiple messages should be joined with newline"""
        # Arrange
        messages = ["첫 번째 메시지", "두 번째 메시지", "세 번째 메시지"]

        # Act
        result = combine_messages(messages)

        # Assert
        assert result == "첫 번째 메시지\n두 번째 메시지\n세 번째 메시지"
        assert result.count("\n") == 2

    def test_empty_list(self):
        """Edge case: Empty message list"""
        # Arrange
        messages = []

        # Act
        result = combine_messages(messages)

        # Assert
        assert result == ""


class TestSheetsLogRow:
    """Test SheetsLogRow model"""

    @pytest.fixture
    def sample_log_row(self):
        """Fixture: Sample SheetsLogRow for testing"""
        return SheetsLogRow(
            row_id="20251219-143022",
            created_at_kst="2025-12-19 14:30:22",
            channel_id="wc_test_123",
            channel_name="Test Store",
            user_id="al-user-456",
            event="send",
            aggregation_id="-",
            message_count=1,
            question_raw="교환 어떻게 해요?",
            question_masked="교환 어떻게 해요?",
            kb_used="doc123:c_04",
            draft_answer="안녕하세요...",
            confidence=0.86,
            risk_level="LOW",
            send_to_user=False,
            global_mode="TEST",
            channel_mode="TEST",
            action_taken="NOT_SENT",
            talktalk_send_result="-",
            telegram_alert_sent=True,
            telegram_reason="KB 부족",
            latency_ms_total=8421,
            error_summary="-",
        )

    def test_to_sheets_values_returns_correct_length(self, sample_log_row):
        """AC2: to_sheets_values() should return list of 23 values"""
        # Act
        values = sample_log_row.to_sheets_values()

        # Assert
        assert len(values) == 23, "to_sheets_values() must return 23 values"

    def test_to_sheets_values_correct_order(self, sample_log_row):
        """AC2: to_sheets_values() should match column order"""
        # Act
        values = sample_log_row.to_sheets_values()

        # Assert - verify first few and last few columns
        assert values[0] == "20251219-143022"  # row_id
        assert values[1] == "2025-12-19 14:30:22"  # created_at_kst
        assert values[2] == "wc_test_123"  # channel_id
        assert values[3] == "Test Store"  # channel_name
        assert values[4] == "al-user-456"  # user_id
        assert values[5] == "send"  # event
        assert values[6] == "-"  # aggregation_id
        assert values[7] == 1  # message_count
        assert values[8] == "교환 어떻게 해요?"  # question_raw
        assert values[9] == "교환 어떻게 해요?"  # question_masked
        assert values[20] == "KB 부족"  # telegram_reason
        assert values[21] == 8421  # latency_ms_total
        assert values[22] == "-"  # error_summary

    def test_single_message_default_values(self):
        """AC3: Single message should have aggregation_id='-', message_count=1"""
        # Arrange & Act
        log_row = SheetsLogRow(
            row_id="20251219-000001",
            created_at_kst="2025-12-19 10:00:00",
            channel_id="wc_test",
            channel_name="Test",
            user_id="user_1",
            event="send",
            aggregation_id="-",  # AC3: Single message
            message_count=1,  # AC3: Single message
            question_raw="단일 메시지",
            question_masked="단일 메시지",
            kb_used="-",
            draft_answer="답변",
            confidence=0.9,
            risk_level="LOW",
            send_to_user=False,
            global_mode="TEST",
            channel_mode="TEST",
            action_taken="NOT_SENT",
            talktalk_send_result="-",
            telegram_alert_sent=False,
            telegram_reason="-",
            latency_ms_total=100,
            error_summary="-",
        )

        # Assert
        assert log_row.aggregation_id == "-"
        assert log_row.message_count == 1

    def test_aggregated_messages_values(self):
        """AC3: Aggregated messages should have aggregation_id (timestamp) and count > 1"""
        # Arrange & Act
        log_row = SheetsLogRow(
            row_id="20251219-000002",
            created_at_kst="2025-12-19 10:30:00",
            channel_id="wc_test",
            channel_name="Test",
            user_id="user_1",
            event="send",
            aggregation_id="2025-12-24T10:30:00Z",  # AC3: Aggregated
            message_count=3,  # AC3: 3 messages aggregated
            question_raw="메시지1\n메시지2\n메시지3",
            question_masked="메시지1\n메시지2\n메시지3",
            kb_used="-",
            draft_answer="답변",
            confidence=0.9,
            risk_level="LOW",
            send_to_user=False,
            global_mode="TEST",
            channel_mode="TEST",
            action_taken="NOT_SENT",
            talktalk_send_result="-",
            telegram_alert_sent=False,
            telegram_reason="-",
            latency_ms_total=30100,
            error_summary="-",
        )

        # Assert
        assert log_row.aggregation_id == "2025-12-24T10:30:00Z"
        assert log_row.message_count == 3
        assert "\n" in log_row.question_raw

    def test_generate_row_id_format(self):
        """AC1: row_id should follow YYYYMMDD-###### format"""
        # Act
        row_id = SheetsLogRow.generate_row_id()

        # Assert
        assert len(row_id) == 15, "row_id should be 15 chars (YYYYMMDD-######)"
        assert row_id[8] == "-", "9th char should be hyphen"
        assert row_id[:8].isdigit(), "First 8 chars should be date (YYYYMMDD)"
        assert row_id[9:].isdigit(), "Last 6 chars should be digits (HHMMSS)"

    def test_format_created_at_kst_default(self):
        """AC1: format_created_at_kst() should return YYYY-MM-DD HH:MM:SS format"""
        # Act
        timestamp = SheetsLogRow.format_created_at_kst()

        # Assert
        assert len(timestamp) == 19, "Timestamp should be 19 chars"
        assert timestamp[4] == "-", "5th char should be hyphen"
        assert timestamp[7] == "-", "8th char should be hyphen"
        assert timestamp[10] == " ", "11th char should be space"
        assert timestamp[13] == ":", "14th char should be colon"
        assert timestamp[16] == ":", "17th char should be colon"

    def test_format_created_at_kst_with_datetime(self):
        """AC1: format_created_at_kst() should accept datetime param"""
        # Arrange
        from datetime import datetime, timedelta, timezone

        kst = timezone(timedelta(hours=9))
        dt = datetime(2025, 12, 19, 14, 22, 11, tzinfo=kst)

        # Act
        timestamp = SheetsLogRow.format_created_at_kst(dt)

        # Assert
        assert timestamp == "2025-12-19 14:22:11"


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""

    def test_complete_single_message_workflow(self):
        """Integration: Create and convert single message log row"""
        # Arrange
        row_id = SheetsLogRow.generate_row_id()
        created_at = SheetsLogRow.format_created_at_kst()

        # Act
        log_row = SheetsLogRow(
            row_id=row_id,
            created_at_kst=created_at,
            channel_id="wc_store_a",
            channel_name="A스토어",
            user_id="al-customer-789",
            event="send",
            aggregation_id="-",
            message_count=1,
            question_raw="배송 언제 오나요?",
            question_masked="배송 언제 오나요?",
            kb_used="doc999:c_02",
            draft_answer="배송은 2-3일 소요됩니다.",
            confidence=0.92,
            risk_level="LOW",
            send_to_user=False,
            global_mode="TEST",
            channel_mode="TEST",
            action_taken="NOT_SENT",
            talktalk_send_result="-",
            telegram_alert_sent=False,
            telegram_reason="-",
            latency_ms_total=3200,
            error_summary="-",
        )

        values = log_row.to_sheets_values()

        # Assert
        assert len(values) == 23
        assert values[0] == row_id
        assert values[6] == "-"  # aggregation_id
        assert values[7] == 1  # message_count

    def test_complete_aggregated_message_workflow(self):
        """Integration: Create and convert aggregated message log row"""
        # Arrange
        messages = ["안녕하세요", "배송 문의드립니다", "언제 오나요?"]
        combined_text = combine_messages(messages)
        truncated_text = truncate_from_end(combined_text, max_length=500)

        row_id = SheetsLogRow.generate_row_id()
        created_at = SheetsLogRow.format_created_at_kst()

        # Act
        log_row = SheetsLogRow(
            row_id=row_id,
            created_at_kst=created_at,
            channel_id="wc_store_b",
            channel_name="B스토어",
            user_id="al-customer-123",
            event="send",
            aggregation_id="2025-12-24T10:30:00Z",
            message_count=3,
            question_raw=truncated_text,
            question_masked=truncated_text,
            kb_used="doc123:c_04;doc999:c_02",
            draft_answer="배송은 2-3일 소요됩니다.",
            confidence=0.88,
            risk_level="MEDIUM",
            send_to_user=False,
            global_mode="TEST",
            channel_mode="TEST",
            action_taken="NOT_SENT",
            talktalk_send_result="-",
            telegram_alert_sent=True,
            telegram_reason="Medium risk",
            latency_ms_total=32500,
            error_summary="-",
        )

        values = log_row.to_sheets_values()

        # Assert
        assert len(values) == 23
        assert values[6] == "2025-12-24T10:30:00Z"  # aggregation_id
        assert values[7] == 3  # message_count
        assert "\n" in values[8]  # question_raw contains newlines

    def test_500_char_truncation_applied_correctly(self):
        """AC4: Verify 500-char limit works from end"""
        # Arrange
        long_text = "X" * 100 + "Y" * 500  # 600 chars total
        truncated = truncate_from_end(long_text, max_length=500)

        row_id = SheetsLogRow.generate_row_id()
        created_at = SheetsLogRow.format_created_at_kst()

        # Act
        log_row = SheetsLogRow(
            row_id=row_id,
            created_at_kst=created_at,
            channel_id="wc_test",
            channel_name="Test",
            user_id="user_1",
            event="send",
            aggregation_id="-",
            message_count=1,
            question_raw=truncated,
            question_masked=truncated,
            kb_used="-",
            draft_answer="답변",
            confidence=0.9,
            risk_level="LOW",
            send_to_user=False,
            global_mode="TEST",
            channel_mode="TEST",
            action_taken="NOT_SENT",
            talktalk_send_result="-",
            telegram_alert_sent=False,
            telegram_reason="-",
            latency_ms_total=100,
            error_summary="-",
        )

        values = log_row.to_sheets_values()

        # Assert
        assert len(values[8]) == 500  # question_raw
        assert len(values[9]) == 500  # question_masked
        # Should keep last 500 chars (no X's, all Y's)
        assert "X" not in values[8]
        assert values[8] == "Y" * 500
