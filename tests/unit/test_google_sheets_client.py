"""Unit tests for GoogleSheetsClient

Reference: Story 5.1 AC4 - Test configuration and client
Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
"""
import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from talktalk_shared.clients.google_sheets_client import (
    GoogleSheetsClient,
    GoogleSheetsError,
)
from talktalk_shared.config import GOOGLE_SHEETS_INBOX_LOG_TAB


@pytest.fixture
def mock_service() -> MagicMock:
    """Mock Google Sheets API service"""
    service = MagicMock()
    # Mock the chained API calls:
    # service.spreadsheets().values().append().execute()
    execute_return = service.spreadsheets.return_value.values.return_value
    execute_return.append.return_value.execute.return_value = {
        "spreadsheetId": "test_spreadsheet_id",
        "tableRange": "inbox_log!A1:Z10",
        "updates": {
            "updatedCells": 10,
            "updatedRows": 1,
        },
    }
    return service


@pytest.fixture
def mock_get_secret() -> Mock:
    """Mock get_secret function"""
    sa_json = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return Mock(return_value=json.dumps(sa_json))


def test_google_sheets_client_initialization() -> None:
    """Test GoogleSheetsClient initializes with circuit breaker"""
    # Arrange & Act
    client = GoogleSheetsClient()

    # Assert
    assert client.circuit_breaker is not None
    assert client._service is None


@patch("talktalk_shared.clients.google_sheets_client.service_account")
@patch("talktalk_shared.clients.google_sheets_client.get_google_sheets_spreadsheet_id")
@patch("talktalk_shared.clients.google_sheets_client.get_secret")
@patch("talktalk_shared.clients.google_sheets_client.build")
def test_append_row_success(
    mock_build: Mock,
    mock_get_secret: Mock,
    mock_get_spreadsheet_id: Mock,
    mock_service_account: Mock,
    mock_service: MagicMock,
) -> None:
    """Test successful row append to Google Sheets"""
    # Arrange
    mock_get_secret.return_value = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    mock_get_spreadsheet_id.return_value = "test_spreadsheet_id"
    mock_service_account.Credentials.from_service_account_info.return_value = MagicMock()
    mock_build.return_value = mock_service

    client = GoogleSheetsClient()
    test_values = [["value1", "value2", "value3"]]

    # Act
    result = client.append_row(test_values)

    # Assert
    assert result["spreadsheetId"] == "test_spreadsheet_id"
    assert result["updates"]["updatedCells"] == 10
    sheets_api = mock_service.spreadsheets.return_value.values.return_value
    sheets_api.append.assert_called_once()


@patch("talktalk_shared.clients.google_sheets_client.service_account")
@patch("talktalk_shared.clients.google_sheets_client.get_google_sheets_spreadsheet_id")
@patch("talktalk_shared.clients.google_sheets_client.get_secret")
@patch("talktalk_shared.clients.google_sheets_client.build")
def test_append_row_with_custom_sheet_name(
    mock_build: Mock,
    mock_get_secret: Mock,
    mock_get_spreadsheet_id: Mock,
    mock_service_account: Mock,
    mock_service: MagicMock,
) -> None:
    """Test append row with custom sheet name"""
    # Arrange
    mock_get_secret.return_value = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    mock_get_spreadsheet_id.return_value = "test_spreadsheet_id"
    mock_service_account.Credentials.from_service_account_info.return_value = MagicMock()
    mock_build.return_value = mock_service

    client = GoogleSheetsClient()
    test_values = [["value1", "value2"]]
    custom_sheet = "custom_log"

    # Act
    result = client.append_row(test_values, sheet_name=custom_sheet)

    # Assert
    assert result["spreadsheetId"] == "test_spreadsheet_id"
    call_kwargs = (
        mock_service.spreadsheets.return_value.values.return_value.append.call_args
    )
    assert custom_sheet in call_kwargs.kwargs["range"]


@patch("talktalk_shared.clients.google_sheets_client.service_account")
@patch("talktalk_shared.clients.google_sheets_client.get_google_sheets_spreadsheet_id")
@patch("talktalk_shared.clients.google_sheets_client.get_secret")
@patch("talktalk_shared.clients.google_sheets_client.build")
def test_append_row_retries_on_http_error(
    mock_build: Mock,
    mock_get_secret: Mock,
    mock_get_spreadsheet_id: Mock,
    mock_service_account: Mock,
) -> None:
    """Test append_row retries on HttpError (2 retries)"""
    # Arrange
    from googleapiclient.errors import HttpError

    mock_get_secret.return_value = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    mock_get_spreadsheet_id.return_value = "test_spreadsheet_id"

    # Mock service that fails with HttpError
    mock_service = MagicMock()
    mock_response = Mock()
    mock_response.status = 500
    http_error = HttpError(resp=mock_response, content=b"Internal Server Error")

    sheets_api = mock_service.spreadsheets.return_value.values.return_value
    sheets_api.append.return_value.execute.side_effect = http_error
    mock_service_account.Credentials.from_service_account_info.return_value = MagicMock()
    mock_build.return_value = mock_service

    client = GoogleSheetsClient()
    test_values = [["value1"]]

    # Act & Assert
    with pytest.raises(GoogleSheetsError) as exc_info:
        client.append_row(test_values)

    assert "Failed to append to Google Sheets after 3 attempts" in str(
        exc_info.value
    )
    # Verify retries: 3 attempts total (initial + 2 retries)
    assert sheets_api.append.return_value.execute.call_count == 3


@patch("talktalk_shared.clients.google_sheets_client.service_account")
@patch("talktalk_shared.clients.google_sheets_client.get_google_sheets_spreadsheet_id")
@patch("talktalk_shared.clients.google_sheets_client.get_secret")
@patch("talktalk_shared.clients.google_sheets_client.build")
def test_append_row_succeeds_on_second_attempt(
    mock_build: Mock,
    mock_get_secret: Mock,
    mock_get_spreadsheet_id: Mock,
    mock_service_account: Mock,
) -> None:
    """Test append_row succeeds on second attempt after initial failure"""
    # Arrange
    from googleapiclient.errors import HttpError

    mock_get_secret.return_value = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    mock_get_spreadsheet_id.return_value = "test_spreadsheet_id"

    # First call fails, second call succeeds
    mock_service = MagicMock()
    mock_response = Mock()
    mock_response.status = 500
    http_error = HttpError(resp=mock_response, content=b"Temporary error")

    success_response = {
        "spreadsheetId": "test_spreadsheet_id",
        "updates": {"updatedCells": 5},
    }

    sheets_api = mock_service.spreadsheets.return_value.values.return_value
    sheets_api.append.return_value.execute.side_effect = [
        http_error,
        success_response,
    ]
    mock_service_account.Credentials.from_service_account_info.return_value = MagicMock()
    mock_build.return_value = mock_service

    client = GoogleSheetsClient()
    test_values = [["retry_test"]]

    # Act
    result = client.append_row(test_values)

    # Assert
    assert result["spreadsheetId"] == "test_spreadsheet_id"
    assert result["updates"]["updatedCells"] == 5
    # Should have attempted twice
    assert sheets_api.append.return_value.execute.call_count == 2


def test_google_sheets_inbox_log_constant() -> None:
    """Test GOOGLE_SHEETS_INBOX_LOG_TAB constant is defined correctly"""
    # Assert
    assert GOOGLE_SHEETS_INBOX_LOG_TAB == "inbox_log"
