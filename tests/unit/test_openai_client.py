"""Unit tests for OpenAIClient"""
from unittest.mock import MagicMock, patch

import pytest

from talktalk_shared.clients.openai_client import OpenAIClient


@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    with patch("talktalk_shared.clients.openai_client.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_secrets():
    """Mock config getter for OpenAI API key"""
    with patch("talktalk_shared.clients.openai_client.get_openai_api_key") as mock_get_key:
        mock_get_key.return_value = "test_api_key"
        yield mock_get_key


@pytest.fixture
def client(mock_openai, mock_secrets):
    """Create client instance with mocked dependencies"""
    return OpenAIClient()


def test_create_embeddings(client, mock_openai):
    """Test creating embeddings for text chunks"""
    # Arrange
    texts = ["First chunk", "Second chunk", "Third chunk"]

    # Mock embedding response
    mock_embedding_1 = MagicMock()
    mock_embedding_1.embedding = [0.1] * 1536
    mock_embedding_2 = MagicMock()
    mock_embedding_2.embedding = [0.2] * 1536
    mock_embedding_3 = MagicMock()
    mock_embedding_3.embedding = [0.3] * 1536

    mock_response = MagicMock()
    mock_response.data = [mock_embedding_1, mock_embedding_2, mock_embedding_3]

    mock_openai.embeddings.create.return_value = mock_response

    # Act
    result = client.create_embeddings(texts)

    # Assert
    assert len(result) == 3
    assert len(result[0]) == 1536
    assert len(result[1]) == 1536
    assert len(result[2]) == 1536
    mock_openai.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input=texts,
    )


def test_create_embeddings_empty_list(client, mock_openai):
    """Test creating embeddings with empty text list"""
    # Arrange
    texts = []

    # Act
    result = client.create_embeddings(texts)

    # Assert
    assert result == []
    mock_openai.embeddings.create.assert_not_called()


def test_create_embeddings_single_text(client, mock_openai):
    """Test creating embeddings for single text"""
    # Arrange
    texts = ["Single text chunk"]

    mock_embedding = MagicMock()
    mock_embedding.embedding = [0.5] * 1536

    mock_response = MagicMock()
    mock_response.data = [mock_embedding]

    mock_openai.embeddings.create.return_value = mock_response

    # Act
    result = client.create_embeddings(texts)

    # Assert
    assert len(result) == 1
    assert len(result[0]) == 1536
    assert result[0][0] == 0.5
