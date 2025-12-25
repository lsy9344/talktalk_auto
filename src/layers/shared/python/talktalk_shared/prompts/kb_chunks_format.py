"""KB chunks formatter for RAG context injection

Formats RAG-retrieved KB chunks into a structured string for LLM prompt insertion.
Follows PRD Section 7.4 format specification.

Reference: Story 4.4 AC1, AC2
"""


def format_kb_chunks(chunks: list[dict[str, str]]) -> str:
    """Format KB chunks into PRD-specified string format

    Args:
        chunks: List of KB chunk dictionaries with required fields:
            - doc_id: Google Docs document ID
            - doc_title: Document title
            - section_path: Hierarchical section path
            - updated_at: ISO 8601 timestamp
            - chunk_id: Deterministic chunk identifier
            - text: Chunk text content

    Returns:
        Formatted KB chunks string enclosed in <KB> tags.
        Returns "<KB>\n</KB>" if chunks list is empty.

    Example:
        >>> chunks = [
        ...     {
        ...         "doc_id": "1ABC",
        ...         "doc_title": "가이드",
        ...         "section_path": "대제목 > 소제목",
        ...         "updated_at": "2025-12-25T10:00:00Z",
        ...         "chunk_id": "c_001",
        ...         "text": "이것은 청크 텍스트입니다."
        ...     }
        ... ]
        >>> print(format_kb_chunks(chunks))
        <KB>
        [1] doc_id=1ABC | title=가이드 | section=대제목 > 소제목 | \
updated_at=2025-12-25T10:00:00Z | chunk_id=c_001
        이것은 청크 텍스트입니다.
        </KB>

    Reference: PRD Section 7.4, Story 4.4 AC1
    """
    if not chunks:
        return "<KB>\n</KB>"

    lines = ["<KB>"]

    for idx, chunk in enumerate(chunks, start=1):
        # Extract required fields
        doc_id = chunk.get("doc_id", "")
        doc_title = chunk.get("doc_title", "")
        section_path = chunk.get("section_path", "")
        updated_at = chunk.get("updated_at", "")
        chunk_id = chunk.get("chunk_id", "")
        text = chunk.get("text", "")

        # Format header line with all metadata
        header = (
            f"[{idx}] "
            f"doc_id={doc_id} | "
            f"title={doc_title} | "
            f"section={section_path} | "
            f"updated_at={updated_at} | "
            f"chunk_id={chunk_id}"
        )

        lines.append(header)
        lines.append(text)

        # Add blank line between chunks (except after the last one)
        if idx < len(chunks):
            lines.append("")

    lines.append("</KB>")

    return "\n".join(lines)
