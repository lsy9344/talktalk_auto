"""Structured logging module"""
import json
import logging
from typing import Any, Dict, Optional


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Get structured logger instance

    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, level.upper()))

        # JSON formatter for CloudWatch
        formatter = logging.Formatter(
            json.dumps(
                {
                    "timestamp": "%(asctime)s",
                    "level": "%(levelname)s",
                    "logger": "%(name)s",
                    "message": "%(message)s",
                }
            )
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log message with additional context

    Args:
        logger: Logger instance
        level: Log level (info, warning, error, etc.)
        message: Log message
        extra: Additional context data (will be masked for PII)
    """
    log_func = getattr(logger, level.lower())
    if extra:
        log_func(message, extra=extra)
    else:
        log_func(message)
