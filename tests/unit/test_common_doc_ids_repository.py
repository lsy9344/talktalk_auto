"""Unit tests for CommonDocIdsRepository"""
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from talktalk_shared.repositories.common_doc_ids import CommonDocIdsRepository


class TestCommonDocIdsRepository:
    """Tests for CommonDocIdsRepository"""

    @patch("talktalk_shared.repositories.common_doc_ids.boto3")
    def test_get_common_doc_ids_success(self, mock_boto3):
        """Test getting common doc IDs successfully"""
        # Arrange
        expected_doc_ids = ["doc1", "doc2", "doc3"]
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"config_key": "COMMON_DOC_IDS", "doc_ids": expected_doc_ids}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = CommonDocIdsRepository()

        # Act
        result = repo.get_common_doc_ids()

        # Assert
        assert result == expected_doc_ids
        mock_table.get_item.assert_called_once_with(Key={"config_key": "COMMON_DOC_IDS"})

    @patch("talktalk_shared.repositories.common_doc_ids.boto3")
    def test_get_common_doc_ids_not_found_returns_empty_list(self, mock_boto3):
        """Test getting common doc IDs when item doesn't exist returns empty list"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = CommonDocIdsRepository()

        # Act
        result = repo.get_common_doc_ids()

        # Assert
        assert result == []

    @patch("talktalk_shared.repositories.common_doc_ids.boto3")
    def test_get_common_doc_ids_empty_list(self, mock_boto3):
        """Test getting empty common doc IDs list"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"config_key": "COMMON_DOC_IDS", "doc_ids": []}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = CommonDocIdsRepository()

        # Act
        result = repo.get_common_doc_ids()

        # Assert
        assert result == []

    @patch("talktalk_shared.repositories.common_doc_ids.boto3")
    def test_get_common_doc_ids_invalid_type_returns_empty_list(self, mock_boto3):
        """Test getting common doc IDs when doc_ids is not a list returns empty list"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"config_key": "COMMON_DOC_IDS", "doc_ids": "not-a-list"}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = CommonDocIdsRepository()

        # Act
        result = repo.get_common_doc_ids()

        # Assert
        assert result == []

    @patch("talktalk_shared.repositories.common_doc_ids.boto3")
    def test_get_common_doc_ids_missing_doc_ids_attribute(self, mock_boto3):
        """Test getting common doc IDs when doc_ids attribute is missing returns empty list"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {"config_key": "COMMON_DOC_IDS"}}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = CommonDocIdsRepository()

        # Act
        result = repo.get_common_doc_ids()

        # Assert
        assert result == []

    @patch("talktalk_shared.repositories.common_doc_ids.boto3")
    def test_get_common_doc_ids_client_error_returns_empty_list(self, mock_boto3):
        """Test getting common doc IDs when DynamoDB error occurs returns empty list"""
        # Arrange
        mock_table = MagicMock()
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Internal error"}},
            "GetItem",
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table

        repo = CommonDocIdsRepository()

        # Act
        result = repo.get_common_doc_ids()

        # Assert
        assert result == []
