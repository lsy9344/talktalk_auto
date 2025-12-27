"""AWS SSM Parameter Store utility for retrieving parameters.

Reference: docs/architecture.md#aws-components-summary
Reference: docs/stories/2.4.story.md AC 4, 6
"""

import logging
from typing import Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid repeated SSM calls
_parameter_cache: Dict[str, str] = {}


class ParameterStoreError(Exception):
    """Parameter Store 조회 실패 시 발생하는 예외."""

    pass


def get_parameter(
    parameter_name: str, use_cache: bool = True, client: Optional[boto3.client] = None
) -> str:
    """Retrieve parameter from AWS SSM Parameter Store.

    Args:
        parameter_name: Name or path of the parameter to retrieve
            (e.g., "/talktalk-auto/secrets/telegram-bot-token")
        use_cache: Whether to use in-memory cache (default: True)
        client: boto3 SSM client (creates default if None)

    Returns:
        Parameter value (decrypted if SecureString)

    Raises:
        ParameterStoreError: If parameter retrieval fails

    Reference: docs/architecture.md#aws-components-summary
    Reference: docs/stories/2.3.story.md AC 5
    """
    # Check cache first
    if use_cache and parameter_name in _parameter_cache:
        logger.debug(
            "Parameter retrieved from cache",
            extra={"parameter_name": _mask_parameter_name(parameter_name)},
        )
        return _parameter_cache[parameter_name]

    # Create client if not provided
    if client is None:
        client = boto3.client("ssm")

    try:
        response = client.get_parameter(Name=parameter_name, WithDecryption=True)

        # Extract parameter value
        parameter_value = response.get("Parameter", {}).get("Value")
        if parameter_value is None:
            raise ParameterStoreError(
                f"Parameter value is None: {_mask_parameter_name(parameter_name)}"
            )
        if not isinstance(parameter_value, str):
            raise ParameterStoreError(
                f"Parameter value is not a string: {_mask_parameter_name(parameter_name)}"
            )

        # Cache the parameter
        if use_cache:
            _parameter_cache[parameter_name] = parameter_value

        logger.info(
            "Parameter retrieved successfully from SSM Parameter Store",
            extra={"parameter_name": _mask_parameter_name(parameter_name)},
        )
        return parameter_value

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(
            "Failed to retrieve parameter from SSM Parameter Store",
            extra={
                "parameter_name": _mask_parameter_name(parameter_name),
                "error_code": error_code,
                "error_message": str(e),
            },
        )
        raise ParameterStoreError(
            f"Failed to retrieve parameter: {error_code}"
        ) from e

    except ParameterStoreError:
        # Re-raise ParameterStoreError as-is (already logged above)
        raise

    except BotoCoreError as e:
        logger.error(
            "BotoCore error retrieving parameter",
            extra={
                "parameter_name": _mask_parameter_name(parameter_name),
                "error": str(e),
            },
        )
        raise ParameterStoreError(f"BotoCore error: {str(e)}") from e

    except Exception as e:
        logger.error(
            "Unexpected error retrieving parameter",
            extra={
                "parameter_name": _mask_parameter_name(parameter_name),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise ParameterStoreError(f"Unexpected error: {str(e)}") from e


def clear_parameter_cache() -> None:
    """Clear the in-memory parameter cache.

    Useful for testing or when parameters are rotated.
    """
    global _parameter_cache
    _parameter_cache = {}
    logger.info("Parameter cache cleared")


def _mask_parameter_name(name: str) -> str:
    """Mask parameter name for logging (keep only last 8 characters).

    Args:
        name: Parameter name to mask

    Returns:
        Masked parameter name

    Example:
        /talktalk-auto/secrets/telegram-bot-token -> ***ot-token
    """
    if len(name) <= 8:
        return "***"
    return f"***{name[-8:]}"
