"""Unit tests for RAG module (Worker Lambda)"""

import json
from io import BytesIO
from unittest.mock import Mock

import numpy as np
import pytest


@pytest.fixture
def mock_faiss_index():
    """Create a mock FAISS index"""
    mock_index = Mock()
    mock_index.search = Mock(
        return_value=(
            np.array([[0.1, 0.2, 0.3]]),  # distances
            np.array([[0, 1, 2]]),  # indices
        )
    )
    return mock_index


@pytest.fixture
def mock_chunks():
    """Create mock chunks data"""
    return [
        {
            "text": "Chunk 1 text content",
            "doc_id": "doc1",
            "doc_title": "Document 1",
            "section_path": "Section 1",
            "updated_at": "2024-01-01T00:00:00Z",
            "channel_id_or_common": "channel123",
            "chunk_id": "chunk1",
        },
        {
            "text": "Chunk 2 text content",
            "doc_id": "doc1",
            "doc_title": "Document 1",
            "section_path": "Section 2",
            "updated_at": "2024-01-01T00:00:00Z",
            "channel_id_or_common": "channel123",
            "chunk_id": "chunk2",
        },
        {
            "text": "Chunk 3 text content",
            "doc_id": "doc1",
            "doc_title": "Document 1",
            "section_path": "Section 3",
            "updated_at": "2024-01-01T00:00:00Z",
            "channel_id_or_common": "channel123",
            "chunk_id": "chunk3",
        },
    ]


def test_deduplicate_chunks():
    """Test chunk deduplication based on (doc_id, chunk_id)"""
    from src.functions.worker.rag import RetrievedChunk, deduplicate_chunks

    chunks = [
        RetrievedChunk(
            text="text1",
            doc_id="doc1",
            chunk_id="chunk1",
            doc_title="",
            section_path="",
            updated_at="",
            channel_id_or_common="",
        ),
        RetrievedChunk(
            text="text2",
            doc_id="doc1",
            chunk_id="chunk1",  # duplicate
            doc_title="",
            section_path="",
            updated_at="",
            channel_id_or_common="",
        ),
        RetrievedChunk(
            text="text3",
            doc_id="doc1",
            chunk_id="chunk2",
            doc_title="",
            section_path="",
            updated_at="",
            channel_id_or_common="",
        ),
    ]

    result = deduplicate_chunks(chunks)

    assert len(result) == 2
    assert result[0].text == "text1"  # First occurrence kept
    assert result[1].text == "text3"


def test_get_document_lists_channel_only(mocker):
    """Test getting document lists when common KB is disabled"""
    from src.functions.worker.rag import get_document_lists

    # Mock repositories
    mock_channel_repo = mocker.patch("src.functions.worker.rag.ChannelConfigRepository")
    mock_common_repo = mocker.patch("src.functions.worker.rag.CommonDocIdsRepository")

    mock_channel_repo.return_value.get.return_value = {
        "doc_ids": ["doc1", "doc2"],
        "common_doc_enabled": False,
    }

    channel_docs, common_docs = get_document_lists("channel123")

    assert channel_docs == ["doc1", "doc2"]
    assert common_docs == []
    mock_common_repo.return_value.get_common_doc_ids.assert_not_called()


def test_get_document_lists_with_common_kb(mocker):
    """Test getting document lists when common KB is enabled"""
    from src.functions.worker.rag import get_document_lists

    # Mock repositories
    mock_channel_repo = mocker.patch("src.functions.worker.rag.ChannelConfigRepository")
    mock_common_repo = mocker.patch("src.functions.worker.rag.CommonDocIdsRepository")

    mock_channel_repo.return_value.get.return_value = {
        "doc_ids": ["doc1", "doc2"],
        "common_doc_enabled": True,
    }
    mock_common_repo.return_value.get_common_doc_ids.return_value = ["doc3", "doc4"]

    channel_docs, common_docs = get_document_lists("channel123")

    assert channel_docs == ["doc1", "doc2"]
    assert common_docs == ["doc3", "doc4"]


def test_get_document_lists_deduplication(mocker):
    """Test that duplicate doc_ids are removed (channel KB takes priority)"""
    from src.functions.worker.rag import get_document_lists

    # Mock repositories
    mock_channel_repo = mocker.patch("src.functions.worker.rag.ChannelConfigRepository")
    mock_common_repo = mocker.patch("src.functions.worker.rag.CommonDocIdsRepository")

    mock_channel_repo.return_value.get.return_value = {
        "doc_ids": ["doc1", "doc2"],
        "common_doc_enabled": True,
    }
    mock_common_repo.return_value.get_common_doc_ids.return_value = [
        "doc2",
        "doc3",
    ]  # doc2 is duplicate

    channel_docs, common_docs = get_document_lists("channel123")

    assert channel_docs == ["doc1", "doc2"]
    assert common_docs == ["doc3"]  # doc2 removed from common


def test_get_document_lists_channel_not_found(mocker):
    """Test handling when channel config is not found"""
    from src.functions.worker.rag import get_document_lists

    # Mock repositories
    mock_channel_repo = mocker.patch("src.functions.worker.rag.ChannelConfigRepository")
    mock_channel_repo.return_value.get.return_value = None

    channel_docs, common_docs = get_document_lists("nonexistent")

    assert channel_docs == []
    assert common_docs == []


def test_load_index_and_chunks_success(mocker, mock_faiss_index, mock_chunks):
    """Test successful loading of index and chunks from S3"""
    from src.functions.worker.rag import load_index_and_chunks

    # Mock S3 client
    mock_s3_client = Mock()

    # Mock index response
    index_bytes = b"fake_faiss_index"
    mock_s3_client.get_object.side_effect = [
        {"Body": BytesIO(index_bytes)},  # index file
        {"Body": BytesIO(json.dumps(mock_chunks).encode())},  # chunks file
    ]

    # Mock faiss.deserialize_index
    mocker.patch(
        "src.functions.worker.rag.faiss.deserialize_index", return_value=mock_faiss_index
    )

    result = load_index_and_chunks("doc1", mock_s3_client, "test-bucket")

    assert result is not None
    index, chunks = result
    assert index == mock_faiss_index
    assert len(chunks) == 3


def test_load_index_and_chunks_failure(mocker):
    """Test handling of S3 load failure"""
    from src.functions.worker.rag import load_index_and_chunks

    # Mock S3 client that raises exception
    mock_s3_client = Mock()
    mock_s3_client.get_object.side_effect = Exception("S3 error")

    result = load_index_and_chunks("doc1", mock_s3_client, "test-bucket")

    assert result is None


def test_search_in_documents_success(mocker, mock_faiss_index, mock_chunks):
    """Test successful search in documents"""
    from src.functions.worker.rag import search_in_documents

    mock_s3_client = Mock()

    # Mock load_index_and_chunks
    mocker.patch(
        "src.functions.worker.rag.load_index_and_chunks",
        return_value=(mock_faiss_index, mock_chunks),
    )

    question_embedding = [0.1] * 1536
    chunks = search_in_documents(["doc1"], question_embedding, 3, mock_s3_client, "bucket")

    assert len(chunks) <= 3
    assert all(chunk.doc_id == "doc1" for chunk in chunks)


def test_search_in_documents_partial_failure(mocker, mock_faiss_index, mock_chunks):
    """Test that search continues when some documents fail to load"""
    from src.functions.worker.rag import search_in_documents

    mock_s3_client = Mock()

    # Mock: first doc fails, second succeeds
    mocker.patch(
        "src.functions.worker.rag.load_index_and_chunks",
        side_effect=[
            None,  # doc1 fails
            (mock_faiss_index, mock_chunks),  # doc2 succeeds
        ],
    )

    question_embedding = [0.1] * 1536
    chunks = search_in_documents(
        ["doc1", "doc2"], question_embedding, 3, mock_s3_client, "bucket"
    )

    # Should still return results from doc2
    assert len(chunks) > 0


def test_search_in_documents_empty_doc_list(mocker):
    """Test search with empty document list"""
    from src.functions.worker.rag import search_in_documents

    mock_s3_client = Mock()
    question_embedding = [0.1] * 1536

    chunks = search_in_documents([], question_embedding, 3, mock_s3_client, "bucket")

    assert chunks == []


def test_retrieve_chunks_respects_topk_limits(mocker, mock_faiss_index, mock_chunks):
    """Test that retrieve_chunks respects topK limits (channel=6, common=4, max=10)"""
    from src.functions.worker.rag import MAX_TOTAL_CHUNKS, retrieve_chunks

    # Mock OpenAI client
    mock_openai = mocker.patch("src.functions.worker.rag.OpenAIClient")
    mock_openai.return_value.create_embeddings.return_value = [[0.1] * 1536]

    # Mock get_document_lists
    mocker.patch(
        "src.functions.worker.rag.get_document_lists",
        return_value=(["doc1", "doc2"], ["doc3"]),  # channel and common KB
    )

    # Mock S3 and boto3
    mock_s3_client = Mock()
    mocker.patch("src.functions.worker.rag.boto3.client", return_value=mock_s3_client)
    mocker.patch("src.functions.worker.rag.get_vector_index_bucket", return_value="test-bucket")

    # Create more chunks than limits
    many_chunks = [
        {
            "text": f"Chunk {i}",
            "metadata": {
                "doc_id": "doc1",
                "chunk_id": f"chunk{i}",
                "doc_title": "",
                "section_path": "",
                "updated_at": "",
                "channel_id_or_common": "channel",
            },
        }
        for i in range(20)
    ]

    mocker.patch(
        "src.functions.worker.rag.load_index_and_chunks",
        return_value=(mock_faiss_index, many_chunks),
    )

    # Override search to return 6 for channel, 4 for common
    def mock_search(doc_ids, embedding, top_k, s3, bucket):
        from src.functions.worker.rag import RetrievedChunk

        count = min(top_k, len(many_chunks))
        return [
            RetrievedChunk.from_metadata(
                text=many_chunks[i]["text"],
                metadata=many_chunks[i]["metadata"],
                score=0.1 * i,
            )
            for i in range(count)
        ]

    mocker.patch("src.functions.worker.rag.search_in_documents", side_effect=mock_search)

    chunks = retrieve_chunks("channel123", "test question")

    # Should respect MAX_TOTAL_CHUNKS
    assert len(chunks) <= MAX_TOTAL_CHUNKS


def test_retrieve_chunks_deduplication(mocker, mock_faiss_index):
    """Test that retrieve_chunks deduplicates chunks"""
    from src.functions.worker.rag import retrieve_chunks

    # Mock OpenAI client
    mock_openai = mocker.patch("src.functions.worker.rag.OpenAIClient")
    mock_openai.return_value.create_embeddings.return_value = [[0.1] * 1536]

    # Mock get_document_lists
    mocker.patch("src.functions.worker.rag.get_document_lists", return_value=(["doc1"], ["doc2"]))

    # Mock S3 and boto3
    mock_s3_client = Mock()
    mocker.patch("src.functions.worker.rag.boto3.client", return_value=mock_s3_client)
    mocker.patch("src.functions.worker.rag.get_vector_index_bucket", return_value="test-bucket")

    # Create duplicate chunks (same doc_id + chunk_id)
    duplicate_chunks = [
        {
            "text": "Duplicate chunk",
            "metadata": {
                "doc_id": "doc1",
                "chunk_id": "chunk1",  # Same
                "doc_title": "",
                "section_path": "",
                "updated_at": "",
                "channel_id_or_common": "channel",
            },
        }
    ]

    mocker.patch(
        "src.functions.worker.rag.load_index_and_chunks",
        return_value=(mock_faiss_index, duplicate_chunks),
    )

    def mock_search(doc_ids, embedding, top_k, s3, bucket):
        from src.functions.worker.rag import RetrievedChunk

        # Return same chunk from both searches
        return [
            RetrievedChunk.from_metadata(
                text=duplicate_chunks[0]["text"],
                metadata=duplicate_chunks[0]["metadata"],
                score=0.1,
            )
        ]

    mocker.patch("src.functions.worker.rag.search_in_documents", side_effect=mock_search)

    chunks = retrieve_chunks("channel123", "test question")

    # Should only have 1 chunk (deduplicated)
    assert len(chunks) == 1


def test_retrieve_chunks_no_kb_documents(mocker):
    """Test handling when no KB documents are available"""
    from src.functions.worker.rag import retrieve_chunks

    # Mock OpenAI client
    mock_openai = mocker.patch("src.functions.worker.rag.OpenAIClient")
    mock_openai.return_value.create_embeddings.return_value = [[0.1] * 1536]

    # Mock get_document_lists to return empty
    mocker.patch("src.functions.worker.rag.get_document_lists", return_value=([], []))

    chunks = retrieve_chunks("channel123", "test question")

    assert chunks == []


def test_retrieve_chunks_embedding_failure(mocker):
    """Test handling when embedding creation fails"""
    from src.functions.worker.rag import retrieve_chunks

    # Mock OpenAI client to raise exception
    mock_openai = mocker.patch("src.functions.worker.rag.OpenAIClient")
    mock_openai.return_value.create_embeddings.side_effect = Exception("API error")

    chunks = retrieve_chunks("channel123", "test question")

    assert chunks == []
