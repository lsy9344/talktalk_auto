"""
RAG (Retrieval-Augmented Generation) Module

Implements 2-stage retrieval strategy: Channel KB -> Common KB
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import boto3
import faiss  # type: ignore[import-not-found,import-untyped]
import numpy as np

from talktalk_shared.clients.openai_client import OpenAIClient
from talktalk_shared.config import get_aws_region, get_vector_index_bucket
from talktalk_shared.repositories.channel_config import ChannelConfigRepository
from talktalk_shared.repositories.common_doc_ids import CommonDocIdsRepository
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)

# Retrieval Configuration Constants
CHANNEL_KB_TOP_K = 6  # Default topK for channel KB
COMMON_KB_TOP_K = 4  # Default topK for common KB
MAX_TOTAL_CHUNKS = 10  # Maximum total chunks to return


@dataclass
class RetrievedChunk:
    """
    Data structure for a single retrieved chunk.

    Attributes:
        text: The chunk text content (for LLM input)
        doc_id: Document identifier
        doc_title: Document title
        section_path: Section path within document
        updated_at: Last update timestamp
        channel_id_or_common: Channel ID or "COMMON"
        chunk_id: Chunk identifier within document
        score: Optional similarity score/distance
    """

    text: str
    doc_id: str
    doc_title: str
    section_path: str
    updated_at: str
    channel_id_or_common: str
    chunk_id: str
    score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "text": self.text,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "section_path": self.section_path,
            "updated_at": self.updated_at,
            "channel_id_or_common": self.channel_id_or_common,
            "chunk_id": self.chunk_id,
            "score": self.score,
        }

    @classmethod
    def from_metadata(
        cls, text: str, metadata: Dict[str, Any], score: Optional[float] = None
    ) -> "RetrievedChunk":
        """Create RetrievedChunk from chunk metadata"""
        return cls(
            text=text,
            doc_id=metadata.get("doc_id", ""),
            doc_title=metadata.get("doc_title", ""),
            section_path=metadata.get("section_path", ""),
            updated_at=metadata.get("updated_at", ""),
            channel_id_or_common=metadata.get("channel_id_or_common", ""),
            chunk_id=metadata.get("chunk_id", ""),
            score=score,
        )


def deduplicate_chunks(chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
    """
    Remove duplicate chunks based on (doc_id, chunk_id).
    Keep the first occurrence (highest priority/score).

    Args:
        chunks: List of retrieved chunks

    Returns:
        Deduplicated list of chunks
    """
    seen_keys = set()
    deduplicated = []

    for chunk in chunks:
        key = (chunk.doc_id, chunk.chunk_id)
        if key not in seen_keys:
            seen_keys.add(key)
            deduplicated.append(chunk)

    return deduplicated


def get_document_lists(channel_id: str) -> tuple[List[str], List[str]]:
    """
    Get channel KB and common KB document lists.

    Args:
        channel_id: Channel ID to get configuration for

    Returns:
        Tuple of (channel_doc_ids, common_doc_ids)
        Returns ([], []) if channel not found or disabled

    Reference:
        Story 3.4 AC1, AC2: Channel KB and Common KB document retrieval
        docs/architecture.md#ChannelConfig
        docs/architecture.md#GlobalMode
    """
    channel_repo = ChannelConfigRepository()
    common_repo = CommonDocIdsRepository()

    # Get channel config
    channel_config = channel_repo.get(channel_id)
    if not channel_config:
        logger.warning(f"Channel config not found or disabled: {channel_id}")
        return ([], [])

    # Get channel-specific doc IDs
    channel_doc_ids = channel_config.get("doc_ids", [])
    if not isinstance(channel_doc_ids, list):
        logger.warning(
            f"Channel doc_ids is not a list for channel {channel_id}, using empty list"
        )
        channel_doc_ids = []

    # Get common KB doc IDs if enabled
    common_doc_ids: List[str] = []
    if channel_config.get("common_doc_enabled", False):
        common_doc_ids = common_repo.get_common_doc_ids()
    else:
        logger.info(f"Common KB disabled for channel: {channel_id}")

    # Deduplicate: ensure no doc_id appears in both lists
    # Priority: channel KB > common KB
    channel_set: Set[str] = set(channel_doc_ids)
    common_doc_ids = [doc_id for doc_id in common_doc_ids if doc_id not in channel_set]

    logger.info(
        f"Document lists retrieved for channel {channel_id}",
        extra={
            "channel_docs": len(channel_doc_ids),
            "common_docs": len(common_doc_ids),
        },
    )

    return (channel_doc_ids, common_doc_ids)


def load_index_and_chunks(
    doc_id: str, s3_client: Any, bucket: str
) -> Optional[tuple[Any, List[Dict[str, Any]]]]:
    """
    Load FAISS index and chunks for a document from S3.

    Args:
        doc_id: Document ID
        s3_client: Boto3 S3 client
        bucket: S3 bucket name

    Returns:
        Tuple of (faiss_index, chunks_list) if successful, None if failed

    Reference:
        Story 3.4 AC5: Partial failure handling
    """
    try:
        # Load FAISS index
        index_key = f"indices/{doc_id}.faiss"
        index_response = s3_client.get_object(Bucket=bucket, Key=index_key)
        index_bytes = index_response["Body"].read()
        index = faiss.deserialize_index(np.frombuffer(index_bytes, dtype=np.uint8))

        # Load chunks JSON
        chunks_key = f"indices/{doc_id}.chunks.json"
        chunks_response = s3_client.get_object(Bucket=bucket, Key=chunks_key)
        chunks = json.loads(chunks_response["Body"].read().decode("utf-8"))

        logger.info(
            f"Loaded index and chunks for doc_id: {doc_id}",
            extra={"chunk_count": len(chunks)},
        )
        return (index, chunks)

    except Exception as e:
        logger.warning(
            f"Failed to load index/chunks for doc_id: {doc_id}",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return None


def search_in_documents(
    doc_ids: List[str],
    question_embedding: List[float],
    top_k: int,
    s3_client: Any,
    bucket: str,
) -> List[RetrievedChunk]:
    """
    Search for similar chunks across multiple documents.

    Args:
        doc_ids: List of document IDs to search
        question_embedding: Question embedding vector
        top_k: Number of top results to return
        s3_client: Boto3 S3 client
        bucket: S3 bucket name

    Returns:
        List of top-K retrieved chunks sorted by similarity score

    Reference:
        Story 3.4 AC1, AC2: Channel KB and Common KB search
        Story 3.4 AC5: Partial failure handling
    """
    all_results: List[tuple[RetrievedChunk, float]] = []
    query_vector = np.array([question_embedding], dtype=np.float32)

    for doc_id in doc_ids:
        # Load index and chunks (skip if failed)
        result = load_index_and_chunks(doc_id, s3_client, bucket)
        if result is None:
            continue

        index, chunks = result

        # Search in this document's index
        try:
            distances, indices = index.search(query_vector, min(top_k, len(chunks)))

            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(chunks):
                    continue

                chunk_data = chunks[idx]
                chunk = RetrievedChunk.from_metadata(
                    text=chunk_data.get("text", ""),
                    metadata=chunk_data.get("metadata", {}),
                    score=float(dist),
                )
                all_results.append((chunk, float(dist)))

        except Exception as e:
            logger.warning(
                f"Search failed for doc_id: {doc_id}",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            continue

    # Sort by distance (lower is better for FAISS L2 distance)
    all_results.sort(key=lambda x: x[1])

    # Return top-K
    return [chunk for chunk, _ in all_results[:top_k]]


def retrieve_chunks(channel_id: str, question: str) -> List[RetrievedChunk]:
    """
    Retrieve relevant chunks using 2-stage strategy: Channel KB -> Common KB.

    Args:
        channel_id: Channel ID
        question: User question text

    Returns:
        List of retrieved chunks (max MAX_TOTAL_CHUNKS)

    Reference:
        Story 3.4 AC1-AC5: 2-stage retrieval implementation
    """
    # Create question embedding
    openai_client = OpenAIClient()
    try:
        embeddings = openai_client.create_embeddings([question])
        if not embeddings:
            logger.error("Failed to create question embedding")
            return []
        question_embedding = embeddings[0]
    except Exception as e:
        logger.error(
            "Error creating question embedding",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return []

    # Get document lists
    channel_doc_ids, common_doc_ids = get_document_lists(channel_id)
    if not channel_doc_ids and not common_doc_ids:
        logger.warning(f"No KB documents available for channel: {channel_id}")
        return []

    # Initialize S3 client
    s3_client = boto3.client("s3", region_name=get_aws_region())
    bucket = get_vector_index_bucket()

    # Stage 1: Search channel KB
    channel_chunks: List[RetrievedChunk] = []
    if channel_doc_ids:
        channel_chunks = search_in_documents(
            channel_doc_ids, question_embedding, CHANNEL_KB_TOP_K, s3_client, bucket
        )
        logger.info(f"Retrieved {len(channel_chunks)} chunks from channel KB")

    # Stage 2: Search common KB
    common_chunks: List[RetrievedChunk] = []
    if common_doc_ids:
        common_chunks = search_in_documents(
            common_doc_ids, question_embedding, COMMON_KB_TOP_K, s3_client, bucket
        )
        logger.info(f"Retrieved {len(common_chunks)} chunks from common KB")

    # Combine: channel KB first, then common KB
    combined_chunks = channel_chunks + common_chunks

    # Deduplicate
    deduplicated_chunks = deduplicate_chunks(combined_chunks)

    # Limit to MAX_TOTAL_CHUNKS
    final_chunks = deduplicated_chunks[:MAX_TOTAL_CHUNKS]

    logger.info(
        f"Final retrieval result for channel {channel_id}",
        extra={
            "total_chunks": len(final_chunks),
            "channel_kb": len(channel_chunks),
            "common_kb": len(common_chunks),
        },
    )

    return final_chunks
