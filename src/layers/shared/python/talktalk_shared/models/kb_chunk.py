"""KB chunk models for RAG indexing with metadata

Reference: Story 3.3 AC2 - Chunk metadata structure
"""
from typing import TypedDict


class KBChunk(TypedDict, total=False):
    """Knowledge Base chunk with text and metadata

    Fields:
        text: The actual chunk text content
        doc_id: Google Docs document ID
        doc_title: Document title
        section_path: Hierarchical section path (e.g., "대제목 > 소제목")
        updated_at: ISO 8601 timestamp (from Google Docs modifiedTime)
        channel_id_or_common: Either a channel_id or "common" for shared KB
        chunk_id: Deterministic chunk identifier within document (e.g., "c_001")

    Reference: Story 3.3 AC2, AC3
    """

    text: str
    doc_id: str
    doc_title: str
    section_path: str
    updated_at: str
    channel_id_or_common: str
    chunk_id: str


class DocumentSection(TypedDict, total=False):
    """Document section extracted from Google Docs headings

    Fields:
        section_path: Hierarchical heading path (e.g., "Title > Subtitle")
        text: Section text content
        heading_level: Heading level (1-6, 0 for no heading)

    Reference: Story 3.3 AC1 - Section-based splitting
    """

    section_path: str
    text: str
    heading_level: int


def generate_chunk_id(index: int) -> str:
    """Generate deterministic chunk ID

    Args:
        index: Zero-based chunk index within document

    Returns:
        Chunk ID string (e.g., "c_001", "c_002")

    Reference: Story 3.3 AC3 - Deterministic chunk IDs
    """
    return f"c_{index + 1:03d}"
