"""Unit tests for Secrets Manager utility.

Reference: docs/stories/2.4.story.md AC 7
"""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from talktalk_shared.utils.secrets import (
    SecretsManagerError,
    clear_secrets_cache,
    get_secret_string,
)


def test_get_secret_string_success() -> None:
    """Test successful secret retrieval."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": "my-secret-value-123"
    }

    # Act
    result = get_secret_string(
        secret_arn="arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:test",
        use_cache=False,  # Disable cache for testing
        client=mock_client,
    )

    # Assert
    assert result == "my-secret-value-123"
    mock_client.get_secret_value.assert_called_once_with(
        SecretId="arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:test"
    )


def test_get_secret_string_with_cache() -> None:
    """Test secret caching works."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": "cached-secret-value"
    }
    secret_arn = "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:cache-test"

    clear_secrets_cache()  # Clear before test

    # Act: First call should hit API
    result1 = get_secret_string(
        secret_arn=secret_arn,
        use_cache=True,
        client=mock_client,
    )

    # Second call should use cache
    result2 = get_secret_string(
        secret_arn=secret_arn,
        use_cache=True,
        client=mock_client,
    )

    # Assert
    assert result1 == "cached-secret-value"
    assert result2 == "cached-secret-value"
    # API should be called only once
    assert mock_client.get_secret_value.call_count == 1


def test_get_secret_string_client_error() -> None:
    """Test ClientError is handled properly."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_secret_value.side_effect = ClientError(
        error_response={
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": "Secret not found",
            }
        },
        operation_name="GetSecretValue",
    )

    # Act & Assert
    with pytest.raises(SecretsManagerError) as exc_info:
        get_secret_string(
            secret_arn="arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:notfound",
            use_cache=False,
            client=mock_client,
        )

    assert "ResourceNotFoundException" in str(exc_info.value)


def test_get_secret_string_binary_secret_not_supported() -> None:
    """Test binary secrets raise error."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretBinary": b"binary-data"
        # No SecretString
    }

    # Act & Assert
    with pytest.raises(SecretsManagerError) as exc_info:
        get_secret_string(
            secret_arn="arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:binary",
            use_cache=False,
            client=mock_client,
        )

    assert "Binary secret not supported" in str(exc_info.value)


def test_clear_secrets_cache() -> None:
    """Test cache clearing works."""
    # Arrange
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": "secret-value"
    }
    secret_arn = "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:clear-test"

    # Act: Cache a secret
    get_secret_string(
        secret_arn=secret_arn,
        use_cache=True,
        client=mock_client,
    )
    assert mock_client.get_secret_value.call_count == 1

    # Clear cache
    clear_secrets_cache()

    # Call again - should hit API again
    get_secret_string(
        secret_arn=secret_arn,
        use_cache=True,
        client=mock_client,
    )

    # Assert: API called twice (cache was cleared)
    assert mock_client.get_secret_value.call_count == 2


def test_mask_arn() -> None:
    """Test ARN masking for logging."""
    # Import the private function for testing
    from talktalk_shared.utils.secrets import _mask_arn

    # Act & Assert
    long_arn = (
        "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:my-secret-AbCdEf"
    )
    assert _mask_arn(long_arn) == "***t-AbCdEf"
    assert _mask_arn("short") == "***"
    assert _mask_arn("12345678") == "***"  # Exactly 8 chars -> masked
    assert _mask_arn("123456789") == "***23456789"  # More than 8 chars -> show last 8
