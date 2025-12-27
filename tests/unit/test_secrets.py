"""Unit tests for SSM Parameter Store utility.

Reference: docs/stories/2.4.story.md AC 7
"""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from talktalk_shared.utils.secrets import (
    ParameterStoreError,
    clear_parameter_cache,
    get_parameter,
)


def test_get_parameter_success() -> None:
    """Test successful parameter retrieval from SSM."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {
        "Parameter": {"Value": "my-secret-value-123"}
    }

    # Act
    result = get_parameter(
        parameter_name="/talktalk-auto/secrets/telegram-bot-token",
        use_cache=False,  # Disable cache for testing
        client=mock_client,
    )

    # Assert
    assert result == "my-secret-value-123"
    mock_client.get_parameter.assert_called_once_with(
        Name="/talktalk-auto/secrets/telegram-bot-token", WithDecryption=True
    )




def test_get_parameter_with_cache() -> None:
    """Test parameter caching works."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {
        "Parameter": {"Value": "cached-secret-value"}
    }
    param_name = "/talktalk/test/cache-test"

    clear_parameter_cache()  # Clear before test

    # Act: First call should hit API
    result1 = get_parameter(
        parameter_name=param_name,
        use_cache=True,
        client=mock_client,
    )

    # Second call should use cache
    result2 = get_parameter(
        parameter_name=param_name,
        use_cache=True,
        client=mock_client,
    )

    # Assert
    assert result1 == "cached-secret-value"
    assert result2 == "cached-secret-value"
    # API should be called only once
    assert mock_client.get_parameter.call_count == 1




def test_get_parameter_client_error() -> None:
    """Test ClientError is handled properly."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_parameter.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "ParameterNotFound",
                "Message": "Parameter not found",
            }
        },
        operation_name="GetParameter",
    )

    # Act & Assert
    with pytest.raises(ParameterStoreError) as exc_info:
        get_parameter(
            parameter_name="/talktalk/notfound",
            use_cache=False,
            client=mock_client,
        )

    assert "ParameterNotFound" in str(exc_info.value)




def test_get_parameter_value_none() -> None:
    """Test parameter value None raises error."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {
        "Parameter": {}  # No Value key
    }

    # Act & Assert
    with pytest.raises(ParameterStoreError) as exc_info:
        get_parameter(
            parameter_name="/talktalk/empty",
            use_cache=False,
            client=mock_client,
        )

    assert "Parameter value is None" in str(exc_info.value)




def test_clear_parameter_cache() -> None:
    """Test cache clearing works."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {
        "Parameter": {"Value": "secret-value"}
    }
    param_name = "/talktalk/clear-test"

    # Act: Cache a parameter
    get_parameter(
        parameter_name=param_name,
        use_cache=True,
        client=mock_client,
    )
    assert mock_client.get_parameter.call_count == 1

    # Clear cache
    clear_parameter_cache()

    # Call again - should hit API again
    get_parameter(
        parameter_name=param_name,
        use_cache=True,
        client=mock_client,
    )

    # Assert: API called twice (cache was cleared)
    assert mock_client.get_parameter.call_count == 2


def test_mask_parameter_name() -> None:
    """Test parameter name masking for logging."""
    # Import the private function for testing
    from talktalk_shared.utils.secrets import _mask_parameter_name

    # Act & Assert
    long_param = "/talktalk-auto/secrets/telegram-bot-token"
    assert _mask_parameter_name(long_param) == "***ot-token"
    assert _mask_parameter_name("short") == "***"
    assert _mask_parameter_name("12345678") == "***"  # Exactly 8 chars -> masked
    assert _mask_parameter_name("123456789") == "***23456789"  # More than 8 chars -> show last 8


