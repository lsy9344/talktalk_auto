"""Unit tests for Google Sheets configuration

Reference: Story 5.1 AC1 - Configuration validation
Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
"""
import os
from unittest.mock import patch

import pytest

from talktalk_shared.config import (
    GOOGLE_SHEETS_INBOX_LOG_TAB,
    get_google_sheets_spreadsheet_id,
)


def test_google_sheets_inbox_log_tab_constant() -> None:
    """Test GOOGLE_SHEETS_INBOX_LOG_TAB constant is 'inbox_log'"""
    # Assert
    assert GOOGLE_SHEETS_INBOX_LOG_TAB == "inbox_log"


def test_get_google_sheets_spreadsheet_id_success() -> None:
    """Test get_google_sheets_spreadsheet_id returns valid spreadsheet ID"""
    # Arrange
    test_spreadsheet_id = "1ABC123-test_spreadsheet_id"

    # Act
    with patch.dict(
        os.environ, {"GOOGLE_SHEETS_SPREADSHEET_ID": test_spreadsheet_id}
    ):
        result = get_google_sheets_spreadsheet_id()

    # Assert
    assert result == test_spreadsheet_id


def test_get_google_sheets_spreadsheet_id_missing() -> None:
    """Test get_google_sheets_spreadsheet_id raises error when missing"""
    # Arrange: Clear the environment variable
    with patch.dict(os.environ, {}, clear=True):
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            get_google_sheets_spreadsheet_id()

        assert "GOOGLE_SHEETS_SPREADSHEET_ID" in str(exc_info.value)
        assert "required" in str(exc_info.value)


def test_get_google_sheets_spreadsheet_id_empty() -> None:
    """Test get_google_sheets_spreadsheet_id raises error when empty"""
    # Arrange: Set empty string
    with patch.dict(os.environ, {"GOOGLE_SHEETS_SPREADSHEET_ID": ""}):
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            get_google_sheets_spreadsheet_id()

        assert "GOOGLE_SHEETS_SPREADSHEET_ID" in str(exc_info.value)
        assert "required" in str(exc_info.value)
