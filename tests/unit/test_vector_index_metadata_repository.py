"""Unit tests for VectorIndexMetadataRepository"""
from unittest.mock import MagicMock, patch

import pytest

from talktalk_shared.repositories.vector_index_metadata import VectorIndexMetadataRepository


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource"""
    with patch("boto3.resource") as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table


@pytest.fixture
def repository(mock_dynamodb):
    """Create repository instance with mocked DynamoDB"""
    with patch(
        "talktalk_shared.repositories.vector_index_metadata.get_vector_index_metadata_table",
        return_value="test-table",
    ):
        repo = VectorIndexMetadataRepository()
        repo.table = mock_dynamodb
        return repo


def test_get_metadata_exists(repository, mock_dynamodb):
    """Test getting existing metadata"""
    # Arrange
    doc_id = "test_doc_123"
    expected_metadata = {
        "doc_id": doc_id,
        "revision_id": "rev_456",
        "last_modified_time": "2025-12-24T10:00:00Z",
        "embedding_model": "text-embedding-3-small",
        "index_s3_bucket": "test-bucket",
        "index_s3_key": "indices/test_doc_123.faiss",
    }
    mock_dynamodb.get_item.return_value = {"Item": expected_metadata}

    # Act
    result = repository.get(doc_id)

    # Assert
    assert result == expected_metadata
    mock_dynamodb.get_item.assert_called_once_with(Key={"doc_id": doc_id})


def test_get_metadata_not_found(repository, mock_dynamodb):
    """Test getting non-existent metadata"""
    # Arrange
    doc_id = "nonexistent_doc"
    mock_dynamodb.get_item.return_value = {}

    # Act
    result = repository.get(doc_id)

    # Assert
    assert result is None
    mock_dynamodb.get_item.assert_called_once_with(Key={"doc_id": doc_id})


def test_put_metadata(repository, mock_dynamodb):
    """Test saving metadata"""
    # Arrange
    metadata = {
        "doc_id": "test_doc_789",
        "revision_id": "rev_111",
        "last_modified_time": "2025-12-24T11:00:00Z",
        "embedding_model": "text-embedding-3-small",
        "index_s3_bucket": "test-bucket",
        "index_s3_key": "indices/test_doc_789.faiss",
        "chunk_count": 15,
    }

    # Act
    repository.put(metadata)

    # Assert
    mock_dynamodb.put_item.assert_called_once_with(Item=metadata)


def test_delete_metadata(repository, mock_dynamodb):
    """Test deleting metadata"""
    # Arrange
    doc_id = "test_doc_delete"

    # Act
    repository.delete(doc_id)

    # Assert
    mock_dynamodb.delete_item.assert_called_once_with(Key={"doc_id": doc_id})
