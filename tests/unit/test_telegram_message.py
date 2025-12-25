"""Unit tests for telegram_message.py

Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
Reference: docs/stories/2.3.story.md AC 4
Reference: docs/stories/6.1.story.md AC 3
Reference: docs/stories/6.2.story.md AC 5
"""
from src.functions.worker.telegram_message import (
    format_alert_message,
    format_template_a_operator_review,
    format_template_b_system_error,
    format_template_c_prod_send_blocked,
)


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
        draft_answer = "배송은 1-2일 소요됩니다."
        reasons = ["TEST_MODE"]

        # Act
        result = format_alert_message(
            channel_name=channel_name,
            channel_id=channel_id,
            user_id=user_id,
            global_mode=global_mode,
            channel_mode=channel_mode,
            question=question,
            draft_answer=draft_answer,
            reasons=reasons,
        )

        # Assert
        assert "TestChannel" in result
        assert "ch_123" in result
        assert "TEST" in result
        assert "TEST_MODE" in result
        assert "배송은 언제 되나요?" in result
        assert "배송은 1-2일 소요됩니다." in result

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
            draft_answer="-",
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
            draft_answer="-",
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
            draft_answer="-",
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
            draft_answer="-",
            reasons=reasons,
        )

        # Assert
        assert "🚨" in result
        assert "📌" in result
        assert "👤" in result
        assert "⚙️" in result
        assert "📋" in result
        assert "💬" in result
        assert "📝" in result
        assert "📊" in result


class TestFormatAlertMessageAC1:
    """Test AC1: Common fields always included (Story 6.1)"""

    def test_includes_channel_name_and_id(self):
        """AC1: Message must include channel_name and channel_id"""
        # Arrange & Act
        result = format_alert_message(
            channel_name="MyStore",
            channel_id="wc123456",
            user_id="user1",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
        )

        # Assert
        assert "MyStore" in result
        assert "wc123456" in result

    def test_includes_masked_user_id(self):
        """AC1: Message must include masked user_id"""
        # Arrange & Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_abcd1234",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
        )

        # Assert
        assert "user_abcd1234" not in result  # Raw user_id should not appear
        assert "us*********34" in result  # Masked user_id should appear (13 chars = 2+9+2)

    def test_includes_masked_question(self):
        """AC1: Message must include masked question"""
        # Arrange & Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="TEST",
            channel_mode="TEST",
            question="문의입니다",
            draft_answer="-",
            reasons=["TEST"],
        )

        # Assert
        assert "문의입니다" in result

    def test_includes_draft_answer(self):
        """AC1: Message must include draft_answer"""
        # Arrange & Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="답변입니다",
            reasons=["TEST"],
        )

        # Assert
        assert "답변입니다" in result

    def test_includes_draft_answer_default_value(self):
        """AC1: draft_answer can be '-' when not available"""
        # Arrange & Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
        )

        # Assert
        assert "추천 답변 초안:" in result
        assert "-" in result

    def test_includes_reasons(self):
        """AC1: Message must include reasons"""
        # Arrange & Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["REASON_1", "REASON_2"],
        )

        # Assert
        assert "REASON_1" in result
        assert "REASON_2" in result

    def test_includes_aggregation_id_single_message(self):
        """AC1: Single message should have aggregation_id='-'"""
        # Arrange & Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
            aggregation_id="-",
            message_count=1,
        )

        # Assert
        assert "Aggregation ID: -" in result
        assert "Message Count: 1" in result

    def test_includes_aggregation_id_aggregated_message(self):
        """AC1: Aggregated message should have actual aggregation_id and count"""
        # Arrange & Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
            aggregation_id="2025-12-25T10:30:00Z",
            message_count=3,
        )

        # Assert
        assert "Aggregation ID: 2025-12-25T10:30:00Z" in result
        assert "Message Count: 3" in result


class TestFormatAlertMessageAC2:
    """Test AC2: PII masking (Story 6.1)"""

    def test_masks_phone_number(self):
        """AC2: Phone numbers must be masked"""
        # Arrange
        question = "010-1234-5678로 연락주세요"

        # Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            draft_answer="-",
            reasons=["TEST"],
        )

        # Assert
        assert "010-1234-5678" not in result
        assert "[PHONE]" in result

    def test_masks_email_address(self):
        """AC2: Email addresses must be masked"""
        # Arrange
        question = "test@example.com으로 보내주세요"

        # Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            draft_answer="-",
            reasons=["TEST"],
        )

        # Assert
        assert "test@example.com" not in result
        assert "[EMAIL]" in result

    def test_masks_credit_card_number(self):
        """AC2: Credit card numbers must be masked"""
        # Arrange
        question = "카드번호 1234567890123456 입니다"

        # Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            draft_answer="-",
            reasons=["TEST"],
        )

        # Assert
        assert "1234567890123456" not in result
        assert "[CARD]" in result

    def test_masks_multiple_pii_types(self):
        """AC2: Multiple PII types should all be masked"""
        # Arrange
        question = "010-1234-5678 또는 test@example.com으로 연락주세요"

        # Act
        result = format_alert_message(
            channel_name="Store",
            channel_id="ch1",
            user_id="user1",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            draft_answer="-",
            reasons=["TEST"],
        )

        # Assert
        assert "010-1234-5678" not in result
        assert "test@example.com" not in result
        assert "[PHONE]" in result
        assert "[EMAIL]" in result


class TestTemplateAOperatorReview:
    """Test Template A: Operator review needed (Story 6.2 AC1)"""

    def test_template_a_includes_all_required_fields(self):
        """Template A must include all required fields from PRD"""
        # Arrange & Act
        result = format_template_a_operator_review(
            channel_name="MyStore",
            channel_id="wc123",
            user_id="user_abc123",
            global_mode="PROD",
            channel_mode="PROD",
            question="배송은 언제 되나요?",
            draft_answer="배송은 1-2일 소요됩니다.",
            reasons=["RAG_INSUFFICIENT_EVIDENCE", "RISK_LEVEL_HIGH"],
            risk_level="HIGH",
            confidence=0.65,
            aggregation_id="2025-12-25T10:30:00Z",
            message_count=3,
            row_id="row_20251225_001",
        )

        # Assert: Check required lines/fields
        assert "[톡톡 알림] 운영자 확인 필요 ⚠️" in result
        assert "- 채널: MyStore (wc123)" in result
        assert "- 집계: 2025-12-25T10:30:00Z / count=3" in result
        assert "- 모드: global=PROD / channel=PROD" in result
        assert "- 사유: RAG_INSUFFICIENT_EVIDENCE; RISK_LEVEL_HIGH" in result
        assert "- 위험도: HIGH / confidence=0.65" in result
        assert "[고객 질문(마스킹)]" in result
        assert "[추천 답변 초안(고객에게는 아직 미전송)]" in result
        assert "[운영자 체크 질문]" in result
        assert "[시트 Row]" in result
        assert "row_id=row_20251225_001" in result

    def test_template_a_masks_user_id(self):
        """Template A must mask user_id"""
        # Arrange & Act
        result = format_template_a_operator_review(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_abcdef123456",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
            risk_level="LOW",
            confidence=0.9,
        )

        # Assert
        assert "user_abcdef123456" not in result
        assert "us*************56" in result

    def test_template_a_masks_question_pii(self):
        """Template A must mask PII in question"""
        # Arrange
        question = "전화번호 010-1234-5678로 연락주세요"

        # Act
        result = format_template_a_operator_review(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            draft_answer="-",
            reasons=["TEST"],
            risk_level="LOW",
            confidence=0.8,
        )

        # Assert
        assert "010-1234-5678" not in result
        assert "[PHONE]" in result

    def test_template_a_formats_reasons_as_semicolon_separated(self):
        """Template A must join reasons with semicolons"""
        # Arrange & Act
        result = format_template_a_operator_review(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            global_mode="PROD",
            channel_mode="PROD",
            question="test",
            draft_answer="-",
            reasons=["REASON_1", "REASON_2", "REASON_3"],
            risk_level="MEDIUM",
            confidence=0.7,
        )

        # Assert
        assert "- 사유: REASON_1; REASON_2; REASON_3" in result

    def test_template_a_default_checklist_questions(self):
        """Template A should include default checklist questions"""
        # Arrange & Act
        result = format_template_a_operator_review(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            global_mode="PROD",
            channel_mode="PROD",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
            risk_level="LOW",
            confidence=0.9,
        )

        # Assert
        assert "- 답변 내용이 정확한가?" in result
        assert "- 고객에게 전송해도 되는가?" in result

    def test_template_a_custom_checklist_questions(self):
        """Template A should accept custom checklist questions"""
        # Arrange
        custom_questions = ["질문 A", "질문 B"]

        # Act
        result = format_template_a_operator_review(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            global_mode="PROD",
            channel_mode="PROD",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
            risk_level="LOW",
            confidence=0.9,
            checklist_questions=custom_questions,
        )

        # Assert
        assert "- 질문 A" in result
        assert "- 질문 B" in result

    def test_template_a_single_message_defaults(self):
        """Template A should handle single message defaults"""
        # Arrange & Act
        result = format_template_a_operator_review(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
            risk_level="LOW",
            confidence=0.9,
        )

        # Assert
        assert "- 집계: - / count=1" in result
        assert "row_id=-" in result


class TestTemplateBSystemError:
    """Test Template B: System error (Story 6.2 AC2)"""

    def test_template_b_includes_all_required_fields(self):
        """Template B must include all required fields from PRD"""
        # Arrange & Act
        result = format_template_b_system_error(
            channel_name="MyStore",
            channel_id="wc123",
            user_id="user_abc123",
            question="배송은 언제 되나요?",
            stage="SHEETS_APPEND",
            error_summary="Failed to append log row to Google Sheets",
            attempt=2,
            max_attempts=3,
            aggregation_id="2025-12-25T10:30:00Z",
            message_count=3,
            row_id="row_20251225_001",
        )

        # Assert: Check required lines/fields
        assert "[톡톡 알림] 시스템 오류 🚨" in result
        assert "- 채널: MyStore (wc123)" in result
        assert "- 집계: 2025-12-25T10:30:00Z / count=3" in result
        assert "- 단계: SHEETS_APPEND (예: LLM_CALL / SHEETS_APPEND / SEND_API)" in result
        assert "- 오류요약: Failed to append log row to Google Sheets" in result
        assert "[고객 질문(마스킹)]" in result
        assert "[재시도]" in result
        assert "- attempt=2 / max=3" in result
        assert "row_id=row_20251225_001" in result

    def test_template_b_masks_user_id(self):
        """Template B must mask user_id"""
        # Arrange & Act
        result = format_template_b_system_error(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_abcdef123456",
            question="test",
            stage="LLM_CALL",
            error_summary="OpenAI API timeout",
            attempt=1,
            max_attempts=3,
        )

        # Assert
        assert "user_abcdef123456" not in result
        assert "us*************56" in result

    def test_template_b_masks_question_pii(self):
        """Template B must mask PII in question"""
        # Arrange
        question = "이메일 test@example.com으로 보내주세요"

        # Act
        result = format_template_b_system_error(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            question=question,
            stage="SEND_API",
            error_summary="Send API failed",
            attempt=1,
            max_attempts=3,
        )

        # Assert
        assert "test@example.com" not in result
        assert "[EMAIL]" in result

    def test_template_b_different_error_stages(self):
        """Template B should work with different error stages"""
        # Test LLM_CALL
        result_llm = format_template_b_system_error(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            question="test",
            stage="LLM_CALL",
            error_summary="LLM timeout",
            attempt=1,
            max_attempts=3,
        )
        assert "- 단계: LLM_CALL" in result_llm

        # Test SHEETS_APPEND
        result_sheets = format_template_b_system_error(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            question="test",
            stage="SHEETS_APPEND",
            error_summary="Sheets error",
            attempt=2,
            max_attempts=3,
        )
        assert "- 단계: SHEETS_APPEND" in result_sheets

        # Test SEND_API
        result_send = format_template_b_system_error(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            question="test",
            stage="SEND_API",
            error_summary="Send failed",
            attempt=3,
            max_attempts=3,
        )
        assert "- 단계: SEND_API" in result_send


class TestTemplateCProdSendBlocked:
    """Test Template C: PROD send blocked (Story 6.2 AC3)"""

    def test_template_c_includes_all_required_fields(self):
        """Template C must include all required fields from PRD"""
        # Arrange & Act
        result = format_template_c_prod_send_blocked(
            channel_name="MyStore",
            channel_id="wc123",
            user_id="user_abc123",
            question="배송은 언제 되나요?",
            draft_answer="배송은 1-2일 소요됩니다.",
            reasons=["POLICY_BLOCK_HIGH_RISK", "CONFIDENCE_TOO_LOW"],
            confidence=0.55,
            risk_level="HIGH",
            aggregation_id="2025-12-25T10:30:00Z",
            message_count=3,
            row_id="row_20251225_001",
        )

        # Assert: Check required lines/fields
        assert "[톡톡 알림] PROD 발송 보류 ⛔" in result
        assert "- 채널: MyStore (wc123)" in result
        assert "- 집계: 2025-12-25T10:30:00Z / count=3" in result
        assert "- 사유: POLICY_BLOCK_HIGH_RISK; CONFIDENCE_TOO_LOW" in result
        assert "- confidence=0.55 / risk=HIGH" in result
        assert "질문(마스킹):" in result
        assert "초안:" in result
        assert "row_id=row_20251225_001" in result

    def test_template_c_masks_user_id(self):
        """Template C must mask user_id"""
        # Arrange & Act
        result = format_template_c_prod_send_blocked(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_abcdef123456",
            question="test",
            draft_answer="-",
            reasons=["TEST"],
            confidence=0.8,
            risk_level="MEDIUM",
        )

        # Assert
        assert "user_abcdef123456" not in result
        assert "us*************56" in result

    def test_template_c_masks_question_pii(self):
        """Template C must mask PII in question"""
        # Arrange
        question = "카드번호 1234567890123456 입니다"

        # Act
        result = format_template_c_prod_send_blocked(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            question=question,
            draft_answer="-",
            reasons=["TEST"],
            confidence=0.7,
            risk_level="HIGH",
        )

        # Assert
        assert "1234567890123456" not in result
        assert "[CARD]" in result

    def test_template_c_formats_reasons_as_semicolon_separated(self):
        """Template C must join reasons with semicolons"""
        # Arrange & Act
        result = format_template_c_prod_send_blocked(
            channel_name="Store",
            channel_id="ch1",
            user_id="user_123",
            question="test",
            draft_answer="-",
            reasons=["REASON_A", "REASON_B", "REASON_C"],
            confidence=0.6,
            risk_level="MEDIUM",
        )

        # Assert
        assert "- 사유: REASON_A; REASON_B; REASON_C" in result


class TestTemplatesPIIMasking:
    """Test AC4: PII masking across all templates (Story 6.2 AC4)"""

    def test_all_templates_mask_phone_numbers(self):
        """All templates must mask phone numbers"""
        question = "전화번호 010-9876-5432로 연락주세요"

        # Template A
        result_a = format_template_a_operator_review(
            channel_name="S",
            channel_id="c",
            user_id="u",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            draft_answer="-",
            reasons=["T"],
            risk_level="LOW",
            confidence=0.9,
        )
        assert "010-9876-5432" not in result_a
        assert "[PHONE]" in result_a

        # Template B
        result_b = format_template_b_system_error(
            channel_name="S",
            channel_id="c",
            user_id="u",
            question=question,
            stage="LLM_CALL",
            error_summary="error",
            attempt=1,
            max_attempts=3,
        )
        assert "010-9876-5432" not in result_b
        assert "[PHONE]" in result_b

        # Template C
        result_c = format_template_c_prod_send_blocked(
            channel_name="S",
            channel_id="c",
            user_id="u",
            question=question,
            draft_answer="-",
            reasons=["T"],
            confidence=0.8,
            risk_level="LOW",
        )
        assert "010-9876-5432" not in result_c
        assert "[PHONE]" in result_c

    def test_all_templates_mask_email_addresses(self):
        """All templates must mask email addresses"""
        question = "이메일 contact@company.com으로 연락주세요"

        # Template A
        result_a = format_template_a_operator_review(
            channel_name="S",
            channel_id="c",
            user_id="u",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            draft_answer="-",
            reasons=["T"],
            risk_level="LOW",
            confidence=0.9,
        )
        assert "contact@company.com" not in result_a
        assert "[EMAIL]" in result_a

        # Template B
        result_b = format_template_b_system_error(
            channel_name="S",
            channel_id="c",
            user_id="u",
            question=question,
            stage="SEND_API",
            error_summary="error",
            attempt=1,
            max_attempts=3,
        )
        assert "contact@company.com" not in result_b
        assert "[EMAIL]" in result_b

        # Template C
        result_c = format_template_c_prod_send_blocked(
            channel_name="S",
            channel_id="c",
            user_id="u",
            question=question,
            draft_answer="-",
            reasons=["T"],
            confidence=0.8,
            risk_level="LOW",
        )
        assert "contact@company.com" not in result_c
        assert "[EMAIL]" in result_c

    def test_all_templates_mask_credit_card_numbers(self):
        """All templates must mask credit card numbers"""
        question = "카드번호 9876543210987654"

        # Template A
        result_a = format_template_a_operator_review(
            channel_name="S",
            channel_id="c",
            user_id="u",
            global_mode="PROD",
            channel_mode="PROD",
            question=question,
            draft_answer="-",
            reasons=["T"],
            risk_level="LOW",
            confidence=0.9,
        )
        assert "9876543210987654" not in result_a
        assert "[CARD]" in result_a

        # Template B
        result_b = format_template_b_system_error(
            channel_name="S",
            channel_id="c",
            user_id="u",
            question=question,
            stage="LLM_CALL",
            error_summary="error",
            attempt=1,
            max_attempts=3,
        )
        assert "9876543210987654" not in result_b
        assert "[CARD]" in result_b

        # Template C
        result_c = format_template_c_prod_send_blocked(
            channel_name="S",
            channel_id="c",
            user_id="u",
            question=question,
            draft_answer="-",
            reasons=["T"],
            confidence=0.8,
            risk_level="LOW",
        )
        assert "9876543210987654" not in result_c
        assert "[CARD]" in result_c


class TestTemplatesAggregationFields:
    """Test aggregation_id and message_count fields across templates (Story 6.2 AC5)"""

    def test_template_a_single_message_case(self):
        """Template A should handle single message (aggregation_id='-', count=1)"""
        result = format_template_a_operator_review(
            channel_name="S",
            channel_id="c",
            user_id="u",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["T"],
            risk_level="LOW",
            confidence=0.9,
            aggregation_id="-",
            message_count=1,
        )
        assert "- 집계: - / count=1" in result

    def test_template_a_aggregated_message_case(self):
        """Template A should handle aggregated messages"""
        result = format_template_a_operator_review(
            channel_name="S",
            channel_id="c",
            user_id="u",
            global_mode="TEST",
            channel_mode="TEST",
            question="test",
            draft_answer="-",
            reasons=["T"],
            risk_level="LOW",
            confidence=0.9,
            aggregation_id="2025-12-25T10:00:00Z",
            message_count=5,
        )
        assert "- 집계: 2025-12-25T10:00:00Z / count=5" in result

    def test_template_b_aggregated_case(self):
        """Template B should handle aggregated messages"""
        result = format_template_b_system_error(
            channel_name="S",
            channel_id="c",
            user_id="u",
            question="test",
            stage="LLM_CALL",
            error_summary="error",
            attempt=1,
            max_attempts=3,
            aggregation_id="2025-12-25T10:00:00Z",
            message_count=3,
        )
        assert "- 집계: 2025-12-25T10:00:00Z / count=3" in result

    def test_template_c_aggregated_case(self):
        """Template C should handle aggregated messages"""
        result = format_template_c_prod_send_blocked(
            channel_name="S",
            channel_id="c",
            user_id="u",
            question="test",
            draft_answer="-",
            reasons=["T"],
            confidence=0.8,
            risk_level="LOW",
            aggregation_id="2025-12-25T10:00:00Z",
            message_count=4,
        )
        assert "- 집계: 2025-12-25T10:00:00Z / count=4" in result
