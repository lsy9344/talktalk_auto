"""Telegram Bot API client for operator alerts

Reference: docs/architecture.md#telegram-bot-api
Reference: docs/architecture/tech-stack.md
Reference: docs/stories/2.3.story.md AC 5
"""
import logging
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

from talktalk_shared.config import get_telegram_bot_token, get_telegram_chat_id

logger = logging.getLogger(__name__)


class TelegramClient:
    """
    Telegram Bot API client for sending alerts

    Uses python-telegram-bot library for message sending.
    Failures are logged but do not stop system operation.

    Reference: docs/architecture.md#telegram-bot-api
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram client

        Args:
            bot_token: Bot token (defaults to env TELEGRAM_BOT_TOKEN)
            chat_id: Chat ID (defaults to env TELEGRAM_CHAT_ID)
        """
        self.bot_token = bot_token or get_telegram_bot_token()
        self.chat_id = chat_id or get_telegram_chat_id()
        self.bot = Bot(token=self.bot_token)

    async def send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True,
    ) -> bool:
        """
        Send message to configured Telegram chat

        Failures are caught and logged only - system continues operation.

        Args:
            text: Message text to send
            parse_mode: Parse mode (Markdown or HTML)
            disable_web_page_preview: Whether to disable web page preview

        Returns:
            True if sent successfully, False otherwise

        Reference: docs/architecture.md#telegram-bot-api
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
            logger.info(
                "Telegram alert sent successfully",
                extra={"chat_id": self.chat_id, "message_length": len(text)},
            )
            return True

        except TelegramError as e:
            logger.error(
                "Failed to send Telegram alert",
                extra={
                    "error": str(e),
                    "chat_id": self.chat_id,
                    "error_type": type(e).__name__,
                },
            )
            return False

        except Exception as e:
            logger.error(
                "Unexpected error sending Telegram alert",
                extra={
                    "error": str(e),
                    "chat_id": self.chat_id,
                    "error_type": type(e).__name__,
                },
            )
            return False
