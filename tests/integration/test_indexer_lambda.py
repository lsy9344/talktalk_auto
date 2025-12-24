"""Integration tests for Indexer Lambda - Story 3.2 AC6"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_dynamodb, mock_s3

# Add indexer function to path
indexer_path = Path(__file__).parent.parent.parent / "src" / "functions" / "indexer"
sys.path.insert(0, str(indexer_path))


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials"""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "ap-northeast-2"


@pytest.fixture
def mock_env_vars():
    """Set up environment variables"""
    import os

    os.environ["CHANNEL_CONFIG_TABLE"] = "test-ChannelConfig"
    os.environ["GLOBAL_MODE_TABLE"] = "test-GlobalMode"
    os.environ["VECTOR_INDEX_METADATA_TABLE"] = "test-VectorIndexMetadata"
    os.environ["VECTOR_INDEX_BUCKET"] = "test-vectorindex-bucket"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["SERVICE_NAME"] = "test-talktalk"
    os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
    os.environ["TELEGRAM_CHAT_ID"] = "test-chat-id"


@pytest.fixture
def aws_mocks(aws_credentials, mock_env_vars):
    """Mock AWS services used in this test (DynamoDB + S3)."""
    with mock_dynamodb(), mock_s3():
        yield


@pytest.fixture
def indexer_app_module(aws_mocks):
    """Load indexer app module with a unique name (avoid collision with ingest's app.py)."""
    module_name = "indexer_app"
    if module_name in sys.modules:
        del sys.modules[module_name]

    app_path = indexer_path / "app.py"
    spec = importlib.util.spec_from_file_location(module_name, app_path)
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def dynamodb_setup(aws_mocks):
    """Set up mock DynamoDB tables"""
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")

    # Create ChannelConfig table
    channel_config_table = dynamodb.create_table(
        TableName="test-ChannelConfig",
        KeySchema=[{"AttributeName": "channel_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "channel_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Create GlobalMode table
    global_mode_table = dynamodb.create_table(
        TableName="test-GlobalMode",
        KeySchema=[{"AttributeName": "config_key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "config_key", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Create VectorIndexMetadata table
    metadata_table = dynamodb.create_table(
        TableName="test-VectorIndexMetadata",
        KeySchema=[{"AttributeName": "doc_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "doc_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    yield {
        "channel_config": channel_config_table,
        "global_mode": global_mode_table,
        "metadata": metadata_table,
    }


@pytest.fixture
def s3_setup(aws_mocks):
    """Set up mock S3 bucket"""
    s3 = boto3.client("s3", region_name="ap-northeast-2")
    s3.create_bucket(
        Bucket="test-vectorindex-bucket",
        CreateBucketConfiguration={"LocationConstraint": "ap-northeast-2"},
    )
    yield s3


@pytest.fixture
def mock_external_apis(indexer_app_module):
    """Mock external API clients"""
    with patch.object(indexer_app_module, "google_docs_client") as mock_google, \
         patch.object(indexer_app_module, "openai_client") as mock_openai, \
         patch.object(indexer_app_module, "telegram_client") as mock_telegram, \
         patch.object(indexer_app_module, "_build_faiss_index") as mock_build_index, \
         patch.object(indexer_app_module, "_upload_index_to_s3") as mock_upload_index:

        # Mock Google Docs client
        mock_google.get_revision_id.return_value = "rev_new_123"
        mock_google.get_document.return_value = {
            "documentId": "doc_test",
            "title": "Test Document",
            "revisionId": "rev_new_123",
            "modifiedTime": "2025-12-24T00:00:00Z",
        }
        mock_google.extract_sections_from_document.return_value = [
            {
                "section_path": "(문서 전체)",
                "text": "This is test document content.",
                "heading_level": 0,
            }
        ]

        # Mock OpenAI client
        mock_openai.create_embeddings.return_value = [[0.1] * 1536]
        mock_openai.EMBEDDING_MODEL = "text-embedding-3-small"
        mock_openai.EMBEDDING_DIMENSION = 1536

        # Mock Telegram client
        mock_telegram.send_message.return_value = None

        # Mock FAISS/S3 heavy parts (keep tests lightweight)
        mock_build_index.return_value = (MagicMock(), 1536)
        mock_upload_index.return_value = None

        yield {
            "app": indexer_app_module,
            "google": mock_google,
            "openai": mock_openai,
            "telegram": mock_telegram,
            "build_index": mock_build_index,
            "upload_index": mock_upload_index,
        }


def test_indexer_skips_unchanged_document(dynamodb_setup, s3_setup, mock_external_apis):
    """
    Test AC3: Unchanged documents are skipped (no re-indexing)

    Reference: Story 3.2 AC3, AC6
    """
    # Arrange: Set up channel with one document
    channel_config_table = dynamodb_setup["channel_config"]
    metadata_table = dynamodb_setup["metadata"]

    channel_config_table.put_item(
        Item={
            "channel_id": "test_channel",
            "enabled": True,
            "channel_mode": "TEST",
            "doc_ids": ["doc_test"],
            "common_doc_enabled": False,
        }
    )

    # Metadata with same revision ID (document unchanged)
    metadata_table.put_item(
        Item={
            "doc_id": "doc_test",
            "revision_id": "rev_new_123",  # Same as what Google API returns
            "last_modified_time": "2025-12-23T10:00:00Z",
            "embedding_model": "text-embedding-3-small",
        }
    )

    # Act: Invoke indexer
    event = {"source": "test"}
    context = MagicMock()

    result = mock_external_apis["app"].lambda_handler(event, context)

    # Assert: Document should be skipped (not re-indexed)
    assert result["statusCode"] == 200
    stats = result["body"]["stats"]
    assert stats["skipped"] == 1
    assert stats["updated"] == 0
    assert stats["failed"] == 0

    # Verify OpenAI embeddings NOT called (document was skipped)
    mock_external_apis["openai"].create_embeddings.assert_not_called()


def test_indexer_processes_changed_document(dynamodb_setup, s3_setup, mock_external_apis):
    """
    Test AC4: Changed documents are re-indexed

    Reference: Story 3.2 AC4, AC6
    """
    # Arrange: Set up channel with one document
    channel_config_table = dynamodb_setup["channel_config"]
    metadata_table = dynamodb_setup["metadata"]

    channel_config_table.put_item(
        Item={
            "channel_id": "test_channel",
            "enabled": True,
            "channel_mode": "TEST",
            "doc_ids": ["doc_test"],
            "common_doc_enabled": False,
        }
    )

    # Metadata with OLD revision ID (document changed)
    metadata_table.put_item(
        Item={
            "doc_id": "doc_test",
            "revision_id": "rev_old_999",  # Different from what Google API returns
            "last_modified_time": "2025-12-20T10:00:00Z",
            "embedding_model": "text-embedding-3-small",
        }
    )

    # Act: Invoke indexer
    event = {"source": "test"}
    context = MagicMock()

    result = mock_external_apis["app"].lambda_handler(event, context)

    # Assert: Document should be updated
    assert result["statusCode"] == 200
    stats = result["body"]["stats"]
    assert stats["updated"] == 1
    assert stats["skipped"] == 0
    assert stats["failed"] == 0

    # Verify OpenAI embeddings WERE called (document was re-indexed)
    mock_external_apis["openai"].create_embeddings.assert_called_once()

    # Verify metadata was updated with new revision
    updated_metadata = metadata_table.get_item(Key={"doc_id": "doc_test"})["Item"]
    assert updated_metadata["revision_id"] == "rev_new_123"

    # Verify chunks JSON uploaded (Story 3.3 AC4)
    obj = s3_setup.get_object(
        Bucket="test-vectorindex-bucket",
        Key="indices/doc_test.chunks.json",
    )
    assert obj["ContentType"].startswith("application/json")


def test_indexer_continues_on_document_failure(dynamodb_setup, s3_setup, mock_external_apis):
    """
    Test AC5: Individual document failures don't stop processing

    Reference: Story 3.2 AC5, AC6
    """
    # Arrange: Set up channel with multiple documents
    channel_config_table = dynamodb_setup["channel_config"]

    channel_config_table.put_item(
        Item={
            "channel_id": "test_channel",
            "enabled": True,
            "channel_mode": "TEST",
            "doc_ids": ["doc_1", "doc_2", "doc_3"],
            "common_doc_enabled": False,
        }
    )

    # Mock Google Docs to fail on second document (during processing)
    def mock_get_document(doc_id):
        if doc_id == "doc_2":
            raise Exception("Google Docs API error")
        return {
            "documentId": doc_id,
            "title": "Test Document",
            "revisionId": "rev_new_123",
        }

    mock_external_apis["google"].get_document.side_effect = mock_get_document

    # Act: Invoke indexer
    event = {"source": "test"}
    context = MagicMock()

    result = mock_external_apis["app"].lambda_handler(event, context)

    # Assert: Processing continues despite failure
    assert result["statusCode"] == 200
    stats = result["body"]["stats"]
    assert stats["failed"] == 1  # doc_2 failed
    assert stats["updated"] + stats["skipped"] == 2  # doc_1 and doc_3 processed
    assert len(result["body"]["failed_docs"]) == 1
    assert result["body"]["failed_docs"][0]["doc_id"] == "doc_2"
