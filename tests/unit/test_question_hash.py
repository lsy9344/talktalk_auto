"""
Unit tests for question_hash utility.

Story 6.3: Telegram 알림 중복 방지 (권장)
Reference: docs/stories/6.3.story.md AC5
"""

import hashlib

from talktalk_shared.utils.question_hash import create_question_hash


class TestCreateQuestionHash:
    """Test question hash creation for Telegram dedup"""

    def test_creates_consistent_hash(self) -> None:
        """
        AC5: Same question should produce same hash
        """
        # Arrange
        question = "환불 문의드립니다"

        # Act
        hash1 = create_question_hash(question)
        hash2 = create_question_hash(question)

        # Assert
        assert hash1 == hash2
        assert len(hash1) == 16  # First 16 chars of SHA256

    def test_applies_500_char_limit_from_end(self) -> None:
        """
        AC2, AC5: 500-char limit should be applied from end
        """
        # Arrange
        # Create 600-char question (100 chars will be truncated)
        question = "X" * 100 + "Y" * 500

        # Expected hash: only "Y" * 500 should be hashed
        expected_text = "Y" * 500
        expected_hash = hashlib.sha256(expected_text.encode("utf-8")).hexdigest()[:16]

        # Act
        result = create_question_hash(question)

        # Assert
        assert result == expected_hash
        assert len(result) == 16

    def test_handles_short_question(self) -> None:
        """
        AC2: Questions shorter than 500 chars should use full text
        """
        # Arrange
        question = "안녕하세요"
        expected_hash = hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]

        # Act
        result = create_question_hash(question)

        # Assert
        assert result == expected_hash

    def test_different_questions_produce_different_hashes(self) -> None:
        """
        AC5: Different questions should produce different hashes
        """
        # Arrange
        question1 = "환불 문의"
        question2 = "배송 문의"

        # Act
        hash1 = create_question_hash(question1)
        hash2 = create_question_hash(question2)

        # Assert
        assert hash1 != hash2

    def test_multiline_question_hashing(self) -> None:
        """
        AC5: Multiline questions (aggregated messages) should hash correctly
        """
        # Arrange
        question = "안녕하세요\n환불 문의드립니다\n영수증 첨부합니다"
        expected_hash = hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]

        # Act
        result = create_question_hash(question)

        # Assert
        assert result == expected_hash
        assert len(result) == 16

    def test_empty_string_produces_hash(self) -> None:
        """
        Edge case: Empty string should still produce a hash
        """
        # Arrange
        question = ""
        expected_hash = hashlib.sha256("".encode("utf-8")).hexdigest()[:16]

        # Act
        result = create_question_hash(question)

        # Assert
        assert result == expected_hash
        assert len(result) == 16
