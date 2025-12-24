"""Document chunking logic for RAG indexing"""
from typing import List, cast

try:
    # Prefer the lightweight split package (matches requirements.txt).
    from langchain_text_splitters import (  # type: ignore[import-not-found]
        RecursiveCharacterTextSplitter,
    )
except ImportError:  # pragma: no cover
    RecursiveCharacterTextSplitter = None  # type: ignore[assignment]

from talktalk_shared.models.kb_chunk import (  # type: ignore[import-not-found]
    DocumentSection,
    KBChunk,
    generate_chunk_id,
)
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)


def approximate_token_count(text: str) -> int:
    """
    Approximate token count for text

    We don't use a real tokenizer here, so we use a simple rule:

    - tokens ≈ characters / 4

    This is a common rough guess and is good enough for "400~800 tokens 근처" sizing.
    (Story 3.3 allows character-count approximation.)

    Args:
        text: Input text

    Returns:
        Approximate token count

    Reference: Story 3.3 AC1 - Token-based chunk sizing
    """
    if not text:
        return 0
    # Rough rule: 1 token ~= 4 characters
    return max(1, len(text) // 4)


class DocumentChunker:
    """Text chunking for document indexing"""

    def __init__(
        self,
        chunk_size_tokens: int = 600,
        chunk_overlap_tokens: int = 150,
    ) -> None:
        """
        Initialize document chunker

        Args:
            chunk_size_tokens: Target chunk size in tokens (default: 600, range 400-800)
            chunk_overlap_tokens: Overlap between chunks in tokens (default: 150)

        Reference: Story 3.3 AC1 - Token-based chunk sizing (400-800 tokens)
        """
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens

        # Convert tokens to approximate characters for fallback splitter
        # Rough approximation: 1 token ≈ 4 characters
        self._chunk_size_chars = int(chunk_size_tokens * 4)
        self._chunk_overlap_chars = int(chunk_overlap_tokens * 4)

        if RecursiveCharacterTextSplitter is not None:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size_tokens,
                chunk_overlap=chunk_overlap_tokens,
                length_function=approximate_token_count,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
        else:
            self.text_splitter = None
            logger.warning(
                "langchain_text_splitters not installed; using simple chunking fallback"
            )

        logger.info(
            "DocumentChunker initialized",
            extra={
                "chunk_size_tokens": chunk_size_tokens,
                "chunk_overlap_tokens": chunk_overlap_tokens,
            },
        )

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks

        Args:
            text: Full document text

        Returns:
            List of text chunks

        Reference: Story 3.2 AC4 - Split documents into chunks for embedding
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        if self.text_splitter is not None:
            chunks = cast(List[str], self.text_splitter.split_text(text))
        else:
            chunks = _simple_chunk_text(
                text,
                chunk_size=self._chunk_size_chars,
                chunk_overlap=self._chunk_overlap_chars,
            )

        logger.info(
            "Text chunked",
            extra={
                "original_length": len(text),
                "chunk_count": len(chunks),
                "avg_chunk_size": sum(len(c) for c in chunks) // len(chunks) if chunks else 0,
            },
        )

        return chunks

    def chunk_sections(
        self,
        sections: List[DocumentSection],
        doc_id: str,
        doc_title: str,
        updated_at: str,
        channel_id_or_common: str,
    ) -> List[KBChunk]:
        """
        Split document sections into chunks with metadata

        Args:
            sections: List of document sections with section_path and text
            doc_id: Document ID
            doc_title: Document title
            updated_at: Last modified time (ISO 8601)
            channel_id_or_common: Channel ID or "common" for shared KB

        Returns:
            List of KBChunk objects with text and metadata

        Reference: Story 3.3 AC1, AC2, AC3 - Section-based chunking with metadata
        """
        all_chunks: List[KBChunk] = []
        global_chunk_index = 0

        for section in sections:
            section_text = section.get("text", "").strip()
            if not section_text:
                continue

            section_path = section.get("section_path", "(문서 본문)")

            # Split section into chunks using text splitter
            if self.text_splitter is not None:
                text_chunks = cast(List[str], self.text_splitter.split_text(section_text))
            else:
                text_chunks = _simple_chunk_text(
                    section_text,
                    chunk_size=self._chunk_size_chars,
                    chunk_overlap=self._chunk_overlap_chars,
                )

            # Create KBChunk objects with metadata
            for text_chunk in text_chunks:
                chunk: KBChunk = {
                    "text": text_chunk,
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "section_path": section_path,
                    "updated_at": updated_at,
                    "channel_id_or_common": channel_id_or_common,
                    "chunk_id": generate_chunk_id(global_chunk_index),
                }
                all_chunks.append(chunk)
                global_chunk_index += 1

        logger.info(
            "Sections chunked with metadata",
            extra={
                "doc_id": doc_id,
                "section_count": len(sections),
                "chunk_count": len(all_chunks),
                "avg_tokens_per_chunk": (
                    sum(approximate_token_count(c["text"]) for c in all_chunks) // len(all_chunks)
                    if all_chunks
                    else 0
                ),
            },
        )

        return all_chunks


def _simple_chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Simple chunking fallback (character-based, with overlap)."""
    if chunk_size <= 0:
        return [text]

    overlap = max(chunk_overlap, 0)
    if overlap >= chunk_size:
        overlap = 0

    chunks: List[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(text_len, start + chunk_size)
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start = end - overlap

    return chunks
