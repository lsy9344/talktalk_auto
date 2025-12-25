"""Indexer Lambda - Google Docs KB document synchronization and indexing"""
import asyncio
import inspect
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Coroutine, Dict, List, Optional, Set, Tuple, cast

import boto3
from chunking import DocumentChunker  # type: ignore[import-not-found]

from talktalk_shared.clients import GoogleDocsClient, OpenAIClient, TelegramClient
from talktalk_shared.config import get_vector_index_bucket
from talktalk_shared.repositories import (
    ChannelConfigRepository,
    CommonDocIdsRepository,
    VectorIndexMetadataRepository,
)
from talktalk_shared.utils.doc_list import build_final_doc_list
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize clients and repositories
google_docs_client = GoogleDocsClient()
openai_client = OpenAIClient()
telegram_client = TelegramClient()
channel_config_repo = ChannelConfigRepository()
common_doc_ids_repo = CommonDocIdsRepository()
vector_metadata_repo = VectorIndexMetadataRepository()
s3_client = boto3.client("s3")
chunker = DocumentChunker()

# S3 bucket for vector indices
VECTOR_INDEX_BUCKET = get_vector_index_bucket()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Indexer Lambda handler - Weekly KB document sync with change detection

    Reference: Story 3.2 - Document synchronization with revision-based change detection
    """
    logger.info("Indexer Lambda started", extra={"event": event})

    try:
        # AC2: Get all active channels and build document list
        docs_to_process = _get_all_docs_to_process()
        logger.info(f"Found {len(docs_to_process)} unique documents to process")

        # Process each document
        stats = {"updated": 0, "skipped": 0, "failed": 0}
        failed_docs = []

        for doc_id, channel_id_or_common in docs_to_process:
            try:
                # AC3: Check if document changed using revisionId
                if _should_skip_document(doc_id):
                    stats["skipped"] += 1
                    logger.info(f"Skipped unchanged document: {doc_id}")
                    continue

                # AC4: Process changed document
                _process_document(doc_id, channel_id_or_common)
                stats["updated"] += 1
                logger.info(f"Successfully indexed document: {doc_id}")

            except Exception as e:
                # AC5: Continue processing other documents on failure
                stats["failed"] += 1
                failed_docs.append({"doc_id": doc_id, "error": str(e)})
                logger.error(
                    f"Failed to process document: {doc_id}",
                    extra={"error": str(e)},
                )

        # Send summary notification
        _send_summary_notification(stats, failed_docs)

        logger.info(
            "Indexer Lambda completed",
            extra={"stats": stats, "failed_count": len(failed_docs)},
        )

        return {
            "statusCode": 200,
            "body": {
                "message": "Indexing completed",
                "stats": stats,
                "failed_docs": failed_docs,
            },
        }

    except Exception as e:
        logger.error("Indexer Lambda failed", extra={"error": str(e)})
        _send_telegram_message(f"❌ Indexer Lambda failed: {str(e)}")
        raise


def _get_all_docs_to_process() -> List[Tuple[str, str]]:
    """
    Get all unique documents to process (doc_id + channel/common hint)

    Returns:
        List of (doc_id, channel_id_or_common)

    Reference: Story 3.2 AC2 - Build final document list from all channels
    Story 3.3 AC2 - channel_id/common metadata
    """
    # Get all active channels
    channels = channel_config_repo.get_all_active_channels()

    # Get common doc IDs
    common_doc_ids = common_doc_ids_repo.get_common_doc_ids()
    common_doc_id_set = set(common_doc_ids)

    # Collect all doc_ids with deduplication (+ doc_id -> channel_ids mapping)
    all_doc_ids: Set[str] = set()
    doc_id_to_channel_ids: Dict[str, Set[str]] = {}

    for channel in channels:
        channel_id_raw = channel.get("channel_id")
        channel_id = channel_id_raw if isinstance(channel_id_raw, str) else ""

        # Use build_final_doc_list utility (handles doc_ids/common_doc_enabled defaults safely)
        final_docs = build_final_doc_list(channel, common_doc_ids)
        all_doc_ids.update(final_docs)

        for doc_id in final_docs:
            if doc_id in common_doc_id_set:
                continue
            if channel_id:
                doc_id_to_channel_ids.setdefault(doc_id, set()).add(channel_id)

    docs_to_process: List[Tuple[str, str]] = []
    for doc_id in sorted(all_doc_ids):
        if doc_id in common_doc_id_set:
            docs_to_process.append((doc_id, "common"))
            continue

        channel_ids = sorted(doc_id_to_channel_ids.get(doc_id, set()))
        if not channel_ids:
            logger.warning(
                "No channel_id found for non-common doc_id; using 'unknown'",
                extra={"doc_id": doc_id},
            )
            docs_to_process.append((doc_id, "unknown"))
            continue

        if len(channel_ids) > 1:
            logger.warning(
                "Same doc_id found in multiple channels; picking the first channel_id",
                extra={"doc_id": doc_id, "channel_ids": channel_ids, "picked": channel_ids[0]},
            )

        docs_to_process.append((doc_id, channel_ids[0]))

    # Deterministic order helps debugging/tests
    return docs_to_process


def _should_skip_document(doc_id: str) -> bool:
    """
    Check if document should be skipped (no changes detected)

    Args:
        doc_id: Google Docs document ID

    Returns:
        True if document should be skipped (unchanged), False if should be processed

    Reference: Story 3.2 AC3 - Change detection using revisionId
    """
    try:
        # Get current revision ID from Google Docs
        current_revision_id = google_docs_client.get_revision_id(doc_id)

        # Get stored metadata
        metadata = vector_metadata_repo.get(doc_id)

        if metadata is None:
            # First time seeing this document
            logger.info(f"New document detected: {doc_id}")
            return False

        stored_revision_id = metadata.get("revision_id", "")

        if current_revision_id == stored_revision_id:
            # No change detected
            return True

        # Document has changed
        logger.info(
            "Document change detected",
            extra={
                "doc_id": doc_id,
                "old_revision": stored_revision_id,
                "new_revision": current_revision_id,
            },
        )
        return False

    except Exception as e:
        logger.error(
            "Failed to check document revision",
            extra={"doc_id": doc_id, "error": str(e)},
        )
        # On error, process the document to be safe
        return False


def _process_document(doc_id: str, channel_id_or_common: str) -> None:
    """
    Process a changed document: fetch → chunk → embed → index → upload → save metadata

    Args:
        doc_id: Google Docs document ID
        channel_id_or_common: Channel ID or "common"

    Reference: Story 3.2 AC4 - Full document processing pipeline
    Story 3.3 AC4 - Store chunk metadata for Worker
    """
    # 1. Fetch document metadata (single API call)
    document = google_docs_client.get_document(doc_id)
    revision_id = document.get("revisionId", "")
    doc_title = document.get("title", "Untitled")

    modified_time = document.get("modifiedTime")
    if isinstance(modified_time, str) and modified_time:
        updated_at = modified_time
    else:
        # Google Docs 응답에 modifiedTime이 없을 수도 있어서 안전한 fallback 사용
        updated_at = datetime.now(timezone.utc).isoformat()

    # 2. Extract sections + chunk into KBChunk objects
    sections = google_docs_client.extract_sections_from_document(document)
    chunks = chunker.chunk_sections(
        sections=sections,
        doc_id=doc_id,
        doc_title=doc_title,
        updated_at=updated_at,
        channel_id_or_common=channel_id_or_common,
    )

    if not chunks:
        logger.warning(f"No chunks generated for document: {doc_id}")
        _save_metadata(doc_id, revision_id, doc_title, 0)
        return

    # 3. Create embeddings
    chunk_texts = [c["text"] for c in chunks if c.get("text")]
    embeddings = openai_client.create_embeddings(chunk_texts)

    if not embeddings or len(embeddings) != len(chunk_texts):
        raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(chunk_texts)}")

    # 4. Build FAISS index
    index, dimension = _build_faiss_index(embeddings)

    logger.info(
        "Built FAISS index",
        extra={"doc_id": doc_id, "dimension": dimension, "vector_count": len(embeddings)},
    )

    # 5. Upload index to S3
    index_s3_key = f"indices/{doc_id}.faiss"
    _upload_index_to_s3(index, index_s3_key)

    # 6. Upload chunks (text + metadata) to S3 (Worker가 나중에 사용)
    chunks_s3_key = f"indices/{doc_id}.chunks.json"
    _upload_chunks_to_s3(chunks, chunks_s3_key)

    # 7. Save metadata
    _save_metadata(doc_id, revision_id, doc_title, len(chunks), index_s3_key)

    logger.info(
        "Uploaded chunk metadata to S3",
        extra={
            "doc_id": doc_id,
            "bucket": VECTOR_INDEX_BUCKET,
            "chunks_key": chunks_s3_key,
            "chunk_count": len(chunks),
        },
    )


def _build_faiss_index(embeddings: List[List[float]]) -> Tuple[Any, int]:
    """
    Build FAISS index from embeddings.

    Notes:
        - We import heavy deps (numpy/faiss) lazily to keep local tests light.
        - In AWS Lambda, these packages must be included in deployment package.
    """
    import faiss  # type: ignore[import-not-found,import-untyped]
    import numpy as np  # type: ignore[import-not-found]

    embedding_array = np.array(embeddings, dtype=np.float32)
    dimension = int(embedding_array.shape[1]) if embedding_array.ndim == 2 else 0

    index = faiss.IndexFlatL2(dimension)
    index.add(embedding_array)
    return index, dimension


def _write_faiss_index_to_file(index: Any, file_path: str) -> None:
    """Write FAISS index to a local file."""
    import faiss  # type: ignore[import-not-found,import-untyped]

    faiss.write_index(index, file_path)


def _upload_index_to_s3(index: Any, s3_key: str) -> None:
    """
    Upload FAISS index to S3

    Args:
        index: FAISS index object
        s3_key: S3 object key

    Reference: Story 3.2 AC4 - Upload vector index to S3
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        _write_faiss_index_to_file(index, tmp_path)

        with open(tmp_path, "rb") as f:
            s3_client.upload_fileobj(f, VECTOR_INDEX_BUCKET, s3_key)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    logger.info(
        "Uploaded FAISS index to S3",
        extra={"bucket": VECTOR_INDEX_BUCKET, "key": s3_key},
    )


def _upload_chunks_to_s3(chunks: List[Dict[str, Any]], s3_key: str) -> None:
    """Upload chunk metadata(+text) JSON to S3.

    Reference: Story 3.3 AC4 - Save chunks JSON for Worker usage
    """
    body = json.dumps(chunks, ensure_ascii=False).encode("utf-8")
    s3_client.put_object(
        Bucket=VECTOR_INDEX_BUCKET,
        Key=s3_key,
        Body=body,
        ContentType="application/json; charset=utf-8",
    )


def _save_metadata(
    doc_id: str,
    revision_id: str,
    doc_title: str,
    chunk_count: int,
    s3_key: Optional[str] = None,
) -> None:
    """
    Save vector index metadata to DynamoDB

    Args:
        doc_id: Google Docs document ID
        revision_id: Document revision ID
        doc_title: Document title
        chunk_count: Number of chunks
        s3_key: S3 object key (optional)

    Reference: Story 3.2 AC4 - Update VectorIndexMetadata
    """
    metadata = {
        "doc_id": doc_id,
        "revision_id": revision_id,
        "last_modified_time": datetime.now(timezone.utc).isoformat(),
        "embedding_model": openai_client.EMBEDDING_MODEL,
        "doc_title": doc_title,
        "chunk_count": chunk_count,
        "vector_dimension": openai_client.EMBEDDING_DIMENSION,
    }

    if s3_key:
        metadata["index_s3_bucket"] = VECTOR_INDEX_BUCKET
        metadata["index_s3_key"] = s3_key

    vector_metadata_repo.put(metadata)

    logger.info(
        "Saved vector index metadata",
        extra={"doc_id": doc_id, "revision_id": revision_id, "chunk_count": chunk_count},
    )


def _send_summary_notification(stats: Dict[str, int], failed_docs: List[Dict[str, str]]) -> None:
    """
    Send indexing summary to Telegram

    Args:
        stats: Processing statistics dict
        failed_docs: List of failed documents

    Reference: Story 3.2 AC4 - Optional Telegram notification
    """
    try:
        message_lines = [
            "📊 KB Document Indexing Summary",
            f"✅ Updated: {stats['updated']}",
            f"⏭️ Skipped (unchanged): {stats['skipped']}",
            f"❌ Failed: {stats['failed']}",
        ]

        if failed_docs:
            message_lines.append("\nFailed documents:")
            for doc in failed_docs[:5]:  # Limit to first 5
                message_lines.append(f"- {doc['doc_id']}: {doc['error'][:50]}...")

        _send_telegram_message("\n".join(message_lines))

    except Exception as e:
        logger.error("Failed to send Telegram notification", extra={"error": str(e)})


def _send_telegram_message(text: str) -> None:
    """Send Telegram message from a sync Lambda handler safely."""
    try:
        result = telegram_client.send_message(text)
        if not inspect.isawaitable(result):
            return
        coro = cast(Coroutine[Any, Any, Any], result)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(coro)
        else:
            loop.create_task(coro)
    except Exception as e:
        logger.error("Failed to send Telegram message", extra={"error": str(e)})
