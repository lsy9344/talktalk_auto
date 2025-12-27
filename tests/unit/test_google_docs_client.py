"""Unit tests for GoogleDocsClient"""
from unittest.mock import MagicMock, patch

import pytest

from talktalk_shared.clients.google_docs_client import GoogleDocsClient


@pytest.fixture
def mock_google_service():
    """Mock Google Docs API service"""
    with patch("talktalk_shared.clients.google_docs_client.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_secrets():
    """Mock config getter for Google SA JSON"""
    with patch("talktalk_shared.clients.google_docs_client.get_google_sa_json") as mock_get_sa:
        mock_get_sa.return_value = '{"type": "service_account", "project_id": "test"}'
        yield mock_get_sa


@pytest.fixture
def mock_credentials():
    """Mock Google service account credentials creation"""
    with patch(
        "talktalk_shared.clients.google_docs_client.service_account.Credentials.from_service_account_info"
    ) as mock_from_info:
        mock_from_info.return_value = MagicMock()
        yield mock_from_info


@pytest.fixture
def client(mock_google_service, mock_secrets, mock_credentials):
    """Create client instance with mocked dependencies"""
    return GoogleDocsClient()


def test_get_document(client, mock_google_service):
    """Test getting a document"""
    # Arrange
    doc_id = "test_doc_123"
    expected_doc = {
        "documentId": doc_id,
        "title": "Test Document",
        "revisionId": "rev_456",
        "body": {"content": []},
    }
    mock_google_service.documents().get().execute.return_value = expected_doc

    # Act
    result = client.get_document(doc_id)

    # Assert
    assert result == expected_doc
    mock_google_service.documents().get.assert_any_call(documentId=doc_id)


def test_get_revision_id(client, mock_google_service):
    """Test getting revision ID"""
    # Arrange
    doc_id = "test_doc_789"
    expected_revision = "rev_999"
    mock_google_service.documents().get().execute.return_value = {
        "documentId": doc_id,
        "revisionId": expected_revision,
    }

    # Act
    result = client.get_revision_id(doc_id)

    # Assert
    assert result == expected_revision


def test_get_document_text_simple(client, mock_google_service):
    """Test extracting text from simple document"""
    # Arrange
    doc_id = "test_doc_text"
    mock_doc = {
        "documentId": doc_id,
        "title": "Text Test",
        "revisionId": "rev_123",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Hello world\n"}},
                        ]
                    }
                },
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Second paragraph\n"}},
                        ]
                    }
                },
            ]
        },
    }
    mock_google_service.documents().get().execute.return_value = mock_doc

    # Act
    result = client.get_document_text(doc_id)

    # Assert
    assert "Hello world" in result
    assert "Second paragraph" in result


def test_get_document_text_empty(client, mock_google_service):
    """Test extracting text from empty document"""
    # Arrange
    doc_id = "empty_doc"
    mock_doc = {
        "documentId": doc_id,
        "title": "Empty",
        "revisionId": "rev_empty",
        "body": {"content": []},
    }
    mock_google_service.documents().get().execute.return_value = mock_doc

    # Act
    result = client.get_document_text(doc_id)

    # Assert
    assert result == ""


def test_get_modified_time(client, mock_google_service):
    """Test getting modifiedTime (Story 3.3 updated_at)"""
    # Arrange
    doc_id = "test_doc_modified"
    mock_google_service.documents().get().execute.return_value = {
        "documentId": doc_id,
        "modifiedTime": "2025-12-24T00:00:00Z",
    }

    # Act
    result = client.get_modified_time(doc_id)

    # Assert
    assert result == "2025-12-24T00:00:00Z"


def test_get_document_sections_extracts_heading_paths(client, mock_google_service):
    """Test extracting sections based on headings (Story 3.3 AC1)"""
    # Arrange
    doc_id = "test_doc_sections"
    mock_google_service.documents().get().execute.return_value = {
        "documentId": doc_id,
        "title": "Section Test",
        "revisionId": "rev_123",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        "elements": [{"textRun": {"content": "대제목\n"}}],
                    }
                },
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": "소개 문장\n"}}],
                    }
                },
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "HEADING_2"},
                        "elements": [{"textRun": {"content": "소제목\n"}}],
                    }
                },
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": "소제목 내용 1\n"}}],
                    }
                },
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": "소제목 내용 2\n"}}],
                    }
                },
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        "elements": [{"textRun": {"content": "다른 대제목\n"}}],
                    }
                },
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": "다른 대제목 내용\n"}}],
                    }
                },
            ]
        },
    }

    # Act
    sections = client.get_document_sections(doc_id)

    # Assert
    assert len(sections) == 3
    assert sections[0]["section_path"] == "대제목"
    assert "소개 문장" in sections[0]["text"]

    assert sections[1]["section_path"] == "대제목 > 소제목"
    assert "소제목 내용 1" in sections[1]["text"]
    assert "소제목 내용 2" in sections[1]["text"]

    assert sections[2]["section_path"] == "다른 대제목"
    assert "다른 대제목 내용" in sections[2]["text"]


def test_get_document_sections_fallback_when_only_headings(client, mock_google_service):
    """Test fallback to whole document when headings exist but no body text"""
    # Arrange
    doc_id = "test_doc_only_headings"
    mock_google_service.documents().get().execute.return_value = {
        "documentId": doc_id,
        "title": "Only Headings",
        "revisionId": "rev_123",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        "elements": [{"textRun": {"content": "대제목만 있음\n"}}],
                    }
                }
            ]
        },
    }

    # Act
    sections = client.get_document_sections(doc_id)

    # Assert
    assert len(sections) == 1
    assert sections[0]["section_path"] == "(문서 전체)"
    assert "대제목만 있음" in sections[0]["text"]
