import logging

from .settings import get_settings


_LOGGER_READY = False


def setup_logging() -> None:
    global _LOGGER_READY
    if _LOGGER_READY:
        return
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    _LOGGER_READY = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
