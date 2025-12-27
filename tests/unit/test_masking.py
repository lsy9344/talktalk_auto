"""Unit tests for masking.py

Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
Reference: docs/stories/2.3.story.md AC 4
"""
from src.layers.shared.python.talktalk_shared.utils.masking import (
    mask_question,
    mask_user_id,
)


class TestMaskUserId:
    """Test mask_user_id function"""

    def test_mask_normal_user_id(self):
        """Normal user_id should show first 2 and last 2 chars"""
        # Arrange
        user_id = "abcdef123456"

        # Act
        result = mask_user_id(user_id)

        # Assert
        assert result == "ab********56"
        assert len(result) == len(user_id)

    def test_mask_short_user_id(self):
        """Short user_id (<=4 chars) should return ****"""
        # Arrange
        user_id = "abc"

        # Act
        result = mask_user_id(user_id)

        # Assert
        assert result == "****"

    def test_mask_empty_user_id(self):
        """Empty user_id should return ****"""
        # Arrange
        user_id = ""

        # Act
        result = mask_user_id(user_id)

        # Assert
        assert result == "****"


class TestMaskQuestion:
    """Test mask_question function"""

    def test_mask_phone_number_with_dashes(self):
        """Phone number with dashes should be masked"""
        # Arrange
        question = "제 전화번호는 010-1234-5678입니다"

        # Act
        result = mask_question(question)

        # Assert
        assert "[PHONE]" in result
        assert "010-1234-5678" not in result

    def test_mask_phone_number_without_dashes(self):
        """Phone number without dashes should be masked"""
        # Arrange
        question = "연락처 01012345678로 주세요"

        # Act
        result = mask_question(question)

        # Assert
        assert "[PHONE]" in result
        assert "01012345678" not in result

    def test_mask_email_address(self):
        """Email address should be masked"""
        # Arrange
        question = "이메일은 user@example.com입니다"

        # Act
        result = mask_question(question)

        # Assert
        assert "[EMAIL]" in result
        assert "user@example.com" not in result

    def test_mask_credit_card_number_continuous(self):
        """Credit card numbers (continuous digits) should be masked"""
        # Arrange
        question = "카드번호 1234567890123456"

        # Act
        result = mask_question(question)

        # Assert
        assert "[CARD]" in result
        assert "1234567890123456" not in result

    def test_mask_credit_card_number_with_hyphens(self):
        """Credit card numbers with hyphens should be masked"""
        # Arrange
        question = "카드번호 1234-5678-9012-3456입니다"

        # Act
        result = mask_question(question)

        # Assert
        assert "[CARD]" in result
        assert "1234-5678-9012-3456" not in result

    def test_mask_credit_card_number_with_spaces(self):
        """Credit card numbers with spaces should be masked"""
        # Arrange
        question = "카드번호 1234 5678 9012 3456"

        # Act
        result = mask_question(question)

        # Assert
        assert "[CARD]" in result
        assert "1234 5678 9012 3456" not in result

    def test_mask_credit_card_number_mixed_separators(self):
        """Credit card numbers with mixed hyphens and spaces should be masked"""
        # Arrange
        question = "카드: 1234-5678 9012-3456"

        # Act
        result = mask_question(question)

        # Assert
        assert "[CARD]" in result
        assert "1234-5678" not in result
        assert "9012-3456" not in result

    def test_mask_multiple_pii_types(self):
        """Multiple PII types should all be masked"""
        # Arrange
        question = "연락처 010-1234-5678, 이메일 test@test.com, 카드 1234123412341234"

        # Act
        result = mask_question(question)

        # Assert
        assert "[PHONE]" in result
        assert "[EMAIL]" in result
        assert "[CARD]" in result
        assert "010-1234-5678" not in result
        assert "test@test.com" not in result
        assert "1234123412341234" not in result

    def test_mask_no_pii_returns_unchanged(self):
        """Question without PII should remain unchanged"""
        # Arrange
        question = "배송은 언제 되나요?"

        # Act
        result = mask_question(question)

        # Assert
        assert result == question

    def test_mask_empty_question(self):
        """Empty question should return empty string"""
        # Arrange
        question = ""

        # Act
        result = mask_question(question)

        # Assert
        assert result == ""
