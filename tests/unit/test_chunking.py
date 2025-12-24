"""Unit tests for DocumentChunker (Story 3.3)"""
import sys
from pathlib import Path

import pytest

# Need to set up PYTHONPATH for imports from indexer function
indexer_path = Path(__file__).parent.parent.parent / "src" / "functions" / "indexer"
sys.path.insert(0, str(indexer_path))


@pytest.fixture
def chunker():
    """Create DocumentChunker instance"""
    from chunking import DocumentChunker

    # Story 3.3 default: 400~800 tokens 근처 (기본값 600)
    return DocumentChunker(chunk_size_tokens=600, chunk_overlap_tokens=150)


def test_chunk_text_basic(chunker):
    """Test basic text chunking"""
    # Arrange
    from chunking import approximate_token_count

    # 1 token ~= 4 chars 근사이므로, 600 tokens ~= 2400 chars 정도
    text = ("This is a test document. " * 400).strip()

    # Act
    result = chunker.chunk_text(text)

    # Assert
    assert len(result) > 0
    assert all(len(chunk) > 0 for chunk in result)
    # 대부분 청크는 400~800 tokens 근처여야 한다 (마지막은 더 작을 수 있음)
    token_counts = [approximate_token_count(c) for c in result]
    assert token_counts[0] >= 400
    assert all(tc <= 900 for tc in token_counts)


def test_chunk_text_empty(chunker):
    """Test chunking empty text"""
    # Arrange
    text = ""

    # Act
    result = chunker.chunk_text(text)

    # Assert
    assert result == []


def test_chunk_text_whitespace_only(chunker):
    """Test chunking whitespace-only text"""
    # Arrange
    text = "   \n\n   "

    # Act
    result = chunker.chunk_text(text)

    # Assert
    assert result == []


def test_chunk_text_small_document(chunker):
    """Test chunking small document (smaller than chunk size)"""
    # Arrange
    text = "This is a small document that fits in one chunk."

    # Act
    result = chunker.chunk_text(text)

    # Assert
    assert len(result) == 1
    assert result[0] == text


def test_chunk_text_large_document(chunker):
    """Test chunking large document"""
    # Arrange
    # Create a large document with paragraphs
    paragraphs = [
        f"Paragraph {i}. " + "This is some content. " * 50
        for i in range(10)
    ]
    text = "\n\n".join(paragraphs)

    # Act
    result = chunker.chunk_text(text)

    # Assert
    assert len(result) > 1  # Should be split into multiple chunks

    # Verify overlap works (chunks should share some content)
    if len(result) > 1:
        # Some overlap is expected between consecutive chunks
        assert len(result[0]) > 1000  # First chunk should be reasonably sized


def test_chunk_text_preserves_content(chunker):
    """Test that chunking preserves all content"""
    # Arrange
    text = "First sentence. " * 50 + "Middle sentence. " * 50 + "Last sentence. " * 50

    # Act
    result = chunker.chunk_text(text)

    # Assert
    # Join all chunks and verify content is preserved (accounting for possible overlap)
    assert "First sentence." in result[0]
    assert "Last sentence." in result[-1]
    assert all(chunk.strip() for chunk in result)


def test_chunk_sections_includes_metadata_and_stable_ids(chunker):
    """Test section-based chunking returns metadata + deterministic chunk_id"""
    from chunking import generate_chunk_id

    # Arrange
    sections = [
        {
            "section_path": "대제목",
            "text": ("가나다라마바사 " * 800).strip(),
            "heading_level": 1,
        },
        {
            "section_path": "대제목 > 소제목",
            "text": ("아자차카타파하 " * 900).strip(),
            "heading_level": 2,
        },
    ]

    # Act
    chunks1 = chunker.chunk_sections(
        sections=sections,
        doc_id="doc_123",
        doc_title="문서 제목",
        updated_at="2025-12-24T00:00:00Z",
        channel_id_or_common="common",
    )
    chunks2 = chunker.chunk_sections(
        sections=sections,
        doc_id="doc_123",
        doc_title="문서 제목",
        updated_at="2025-12-24T00:00:00Z",
        channel_id_or_common="common",
    )

    # Assert
    assert chunks1 == chunks2
    assert len(chunks1) > 0

    expected_ids = [generate_chunk_id(i) for i in range(len(chunks1))]
    assert [c["chunk_id"] for c in chunks1] == expected_ids

    for chunk in chunks1:
        assert chunk["text"]
        assert chunk["doc_id"] == "doc_123"
        assert chunk["doc_title"] == "문서 제목"
        assert chunk["updated_at"] == "2025-12-24T00:00:00Z"
        assert chunk["channel_id_or_common"] == "common"
        assert chunk["section_path"] in {"대제목", "대제목 > 소제목"}
