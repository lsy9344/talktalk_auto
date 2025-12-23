"""AWS Secrets Manager utility for retrieving secrets.

Reference: docs/architecture.md#aws-components-summary
Reference: docs/stories/2.4.story.md AC 4, 6
"""

import logging
from typing import Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid repeated Secrets Manager calls
_secrets_cache: Dict[str, str] = {}


class SecretsManagerError(Exception):
    """Secrets Manager 조회 실패 시 발생하는 예외."""

    pass


def get_secret_string(
    secret_arn: str, use_cache: bool = True, client: Optional[boto3.client] = None
) -> str:
    """Retrieve secret string from AWS Secrets Manager.

    Args:
        secret_arn: ARN of the secret to retrieve
        use_cache: Whether to use in-memory cache (default: True)
        client: boto3 Secrets Manager client (creates default if None)

    Returns:
        Secret string value

    Raises:
        SecretsManagerError: If secret retrieval fails

    Reference: docs/architecture.md#aws-components-summary
    """
    # Check cache first
    if use_cache and secret_arn in _secrets_cache:
        logger.debug(
            "Secret retrieved from cache",
            extra={"secret_arn": _mask_arn(secret_arn)},
        )
        return _secrets_cache[secret_arn]

    # Create client if not provided
    if client is None:
        client = boto3.client("secretsmanager")

    try:
        response = client.get_secret_value(SecretId=secret_arn)

        # Extract secret string
        secret_value = response.get("SecretString")
        if secret_value is None:
            # Binary secrets not supported (or missing SecretString)
            raise SecretsManagerError(
                f"Binary secret not supported: {_mask_arn(secret_arn)}"
            )
        if not isinstance(secret_value, str):
            raise SecretsManagerError(
                f"SecretString is not a string: {_mask_arn(secret_arn)}"
            )

        # Cache the secret
        if use_cache:
            _secrets_cache[secret_arn] = secret_value

        logger.info(
            "Secret retrieved successfully from Secrets Manager",
            extra={"secret_arn": _mask_arn(secret_arn)},
        )
        return secret_value

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(
            "Failed to retrieve secret from Secrets Manager",
            extra={
                "secret_arn": _mask_arn(secret_arn),
                "error_code": error_code,
                "error_message": str(e),
            },
        )
        raise SecretsManagerError(
            f"Failed to retrieve secret: {error_code}"
        ) from e

    except BotoCoreError as e:
        logger.error(
            "BotoCore error retrieving secret",
            extra={
                "secret_arn": _mask_arn(secret_arn),
                "error": str(e),
            },
        )
        raise SecretsManagerError(f"BotoCore error: {str(e)}") from e

    except Exception as e:
        logger.error(
            "Unexpected error retrieving secret",
            extra={
                "secret_arn": _mask_arn(secret_arn),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise SecretsManagerError(f"Unexpected error: {str(e)}") from e


def clear_secrets_cache() -> None:
    """Clear the in-memory secrets cache.

    Useful for testing or when secrets are rotated.
    """
    global _secrets_cache
    _secrets_cache = {}
    logger.info("Secrets cache cleared")


def _mask_arn(arn: str) -> str:
    """Mask ARN for logging (keep only last 8 characters).

    Args:
        arn: ARN string to mask

    Returns:
        Masked ARN string

    Example:
        arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:my-secret-AbCdEf
        -> ***AbCdEf
    """
    if len(arn) <= 8:
        return "***"
    return f"***{arn[-8:]}"
