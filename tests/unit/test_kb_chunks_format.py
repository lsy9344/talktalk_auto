"""Unit tests for KB chunks formatter

Reference: Story 4.4 AC3
"""
from talktalk_shared.prompts.kb_chunks_format import format_kb_chunks


class TestFormatKBChunks:
    """Test suite for format_kb_chunks function"""

    def test_empty_chunks_returns_empty_kb_block(self):
        """AC2: Empty chunks should return <KB>\n</KB>"""
        # Arrange
        chunks = []

        # Act
        result = format_kb_chunks(chunks)

        # Assert
        assert result == "<KB>\n</KB>"

    def test_single_chunk_format_matches_prd_spec(self):
        """AC1: Single chunk should follow PRD 7.4 format exactly"""
        # Arrange
        chunks = [
            {
                "doc_id": "1ABC123",
                "doc_title": "사용자 가이드",
                "section_path": "대제목 > 소제목",
                "updated_at": "2025-12-25T10:00:00Z",
                "chunk_id": "c_001",
                "text": "이것은 첫 번째 청크입니다.",
            }
        ]

        # Act
        result = format_kb_chunks(chunks)

        # Assert
        expected = (
            "<KB>\n"
            "[1] doc_id=1ABC123 | title=사용자 가이드 | section=대제목 > 소제목 | "
            "updated_at=2025-12-25T10:00:00Z | chunk_id=c_001\n"
            "이것은 첫 번째 청크입니다.\n"
            "</KB>"
        )
        assert result == expected

    def test_two_chunks_format_with_numbering_and_spacing(self):
        """AC1: Multiple chunks should be numbered [1], [2] with blank line separation"""
        # Arrange
        chunks = [
            {
                "doc_id": "1ABC123",
                "doc_title": "가이드 A",
                "section_path": "섹션 1",
                "updated_at": "2025-12-25T10:00:00Z",
                "chunk_id": "c_001",
                "text": "첫 번째 청크 텍스트",
            },
            {
                "doc_id": "2DEF456",
                "doc_title": "가이드 B",
                "section_path": "섹션 2 > 하위섹션",
                "updated_at": "2025-12-25T11:30:00Z",
                "chunk_id": "c_002",
                "text": "두 번째 청크 텍스트",
            },
        ]

        # Act
        result = format_kb_chunks(chunks)

        # Assert
        expected = (
            "<KB>\n"
            "[1] doc_id=1ABC123 | title=가이드 A | section=섹션 1 | "
            "updated_at=2025-12-25T10:00:00Z | chunk_id=c_001\n"
            "첫 번째 청크 텍스트\n"
            "\n"
            "[2] doc_id=2DEF456 | title=가이드 B | section=섹션 2 > 하위섹션 | "
            "updated_at=2025-12-25T11:30:00Z | chunk_id=c_002\n"
            "두 번째 청크 텍스트\n"
            "</KB>"
        )
        assert result == expected

    def test_three_chunks_maintains_format_consistency(self):
        """AC1: Format should remain consistent with 3+ chunks"""
        # Arrange
        chunks = [
            {
                "doc_id": "doc1",
                "doc_title": "타이틀1",
                "section_path": "섹션A",
                "updated_at": "2025-12-25T10:00:00Z",
                "chunk_id": "c_001",
                "text": "텍스트1",
            },
            {
                "doc_id": "doc2",
                "doc_title": "타이틀2",
                "section_path": "섹션B",
                "updated_at": "2025-12-25T11:00:00Z",
                "chunk_id": "c_002",
                "text": "텍스트2",
            },
            {
                "doc_id": "doc3",
                "doc_title": "타이틀3",
                "section_path": "섹션C",
                "updated_at": "2025-12-25T12:00:00Z",
                "chunk_id": "c_003",
                "text": "텍스트3",
            },
        ]

        # Act
        result = format_kb_chunks(chunks)

        # Assert
        assert result.startswith("<KB>")
        assert result.endswith("</KB>")
        assert "[1] doc_id=doc1" in result
        assert "[2] doc_id=doc2" in result
        assert "[3] doc_id=doc3" in result
        assert "텍스트1" in result
        assert "텍스트2" in result
        assert "텍스트3" in result

    def test_chunk_with_missing_fields_uses_empty_strings(self):
        """Edge case: Missing fields should be handled gracefully with empty strings"""
        # Arrange
        chunks = [
            {
                "doc_id": "123",
                # Missing doc_title, section_path, etc.
                "text": "부분 데이터만 있는 청크",
            }
        ]

        # Act
        result = format_kb_chunks(chunks)

        # Assert
        assert "<KB>" in result
        assert "</KB>" in result
        assert "[1] doc_id=123" in result
        assert "부분 데이터만 있는 청크" in result

    def test_chunk_with_multiline_text_preserves_newlines(self):
        """Format should preserve newlines within chunk text"""
        # Arrange
        chunks = [
            {
                "doc_id": "multi",
                "doc_title": "멀티라인 테스트",
                "section_path": "테스트",
                "updated_at": "2025-12-25T10:00:00Z",
                "chunk_id": "c_001",
                "text": "첫 번째 줄\n두 번째 줄\n세 번째 줄",
            }
        ]

        # Act
        result = format_kb_chunks(chunks)

        # Assert
        assert "첫 번째 줄\n두 번째 줄\n세 번째 줄" in result

    def test_chunk_with_special_characters_in_metadata(self):
        """Format should handle special characters in metadata fields"""
        # Arrange
        chunks = [
            {
                "doc_id": "special_123",
                "doc_title": "제목: 특수문자 & 테스트 | 샘플",
                "section_path": "섹션 > 하위 > 더하위",
                "updated_at": "2025-12-25T10:00:00Z",
                "chunk_id": "c_001",
                "text": "특수문자가 포함된 텍스트: <example> & more",
            }
        ]

        # Act
        result = format_kb_chunks(chunks)

        # Assert
        assert "제목: 특수문자 & 테스트 | 샘플" in result
        assert "섹션 > 하위 > 더하위" in result
        assert "특수문자가 포함된 텍스트: <example> & more" in result

    def test_large_number_of_chunks_performance(self):
        """Performance test: Should handle many chunks efficiently"""
        # Arrange
        chunks = [
            {
                "doc_id": f"doc_{i}",
                "doc_title": f"타이틀 {i}",
                "section_path": f"섹션 {i}",
                "updated_at": "2025-12-25T10:00:00Z",
                "chunk_id": f"c_{i:03d}",
                "text": f"청크 텍스트 {i}",
            }
            for i in range(1, 101)  # 100 chunks
        ]

        # Act
        result = format_kb_chunks(chunks)

        # Assert
        assert result.startswith("<KB>")
        assert result.endswith("</KB>")
        assert "[1] doc_id=doc_1" in result
        assert "[100] doc_id=doc_100" in result
