"""Unit tests for telegram_client.py

Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
Reference: docs/stories/2.3.story.md AC 6
"""
from unittest.mock import AsyncMock, patch

import pytest
from telegram.error import TelegramError

from src.layers.shared.python.talktalk_shared.clients.telegram_client import (
    TelegramClient,
)


class TestTelegramClient:
    """Test TelegramClient class"""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Successful message send should return True"""
        # Arrange
        with patch(
            "src.layers.shared.python.talktalk_shared.clients.telegram_client.Bot"
        ) as MockBot:
            mock_bot = MockBot.return_value
            mock_bot.send_message = AsyncMock()

            client = TelegramClient(bot_token="test_token", chat_id="test_chat")

            # Act
            result = await client.send_message(text="Test message")

            # Assert
            assert result is True
            mock_bot.send_message.assert_called_once_with(
                chat_id="test_chat",
                text="Test message",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

    @pytest.mark.asyncio
    async def test_send_message_telegram_error_returns_false(self):
        """TelegramError should be caught and return False"""
        # Arrange
        with patch(
            "src.layers.shared.python.talktalk_shared.clients.telegram_client.Bot"
        ) as MockBot:
            mock_bot = MockBot.return_value
            mock_bot.send_message = AsyncMock(side_effect=TelegramError("Network error"))

            client = TelegramClient(bot_token="test_token", chat_id="test_chat")

            # Act
            result = await client.send_message(text="Test message")

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_generic_exception_returns_false(self):
        """Generic exception should be caught and return False"""
        # Arrange
        with patch(
            "src.layers.shared.python.talktalk_shared.clients.telegram_client.Bot"
        ) as MockBot:
            mock_bot = MockBot.return_value
            mock_bot.send_message = AsyncMock(side_effect=Exception("Unexpected error"))

            client = TelegramClient(bot_token="test_token", chat_id="test_chat")

            # Act
            result = await client.send_message(text="Test message")

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_custom_parse_mode(self):
        """Custom parse_mode should be passed correctly"""
        # Arrange
        with patch(
            "src.layers.shared.python.talktalk_shared.clients.telegram_client.Bot"
        ) as MockBot:
            mock_bot = MockBot.return_value
            mock_bot.send_message = AsyncMock()

            client = TelegramClient(bot_token="test_token", chat_id="test_chat")

            # Act
            await client.send_message(text="Test", parse_mode="HTML")

            # Assert
            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args[1]
            assert call_kwargs["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_send_message_disable_preview_false(self):
        """disable_web_page_preview can be set to False"""
        # Arrange
        with patch(
            "src.layers.shared.python.talktalk_shared.clients.telegram_client.Bot"
        ) as MockBot:
            mock_bot = MockBot.return_value
            mock_bot.send_message = AsyncMock()

            client = TelegramClient(bot_token="test_token", chat_id="test_chat")

            # Act
            await client.send_message(text="Test", disable_web_page_preview=False)

            # Assert
            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args[1]
            assert call_kwargs["disable_web_page_preview"] is False

    def test_client_initialization_with_params(self):
        """Client should initialize with provided token and chat_id"""
        # Arrange & Act
        with patch("src.layers.shared.python.talktalk_shared.clients.telegram_client.Bot"):
            client = TelegramClient(bot_token="my_token", chat_id="my_chat")

            # Assert
            assert client.bot_token == "my_token"
            assert client.chat_id == "my_chat"

    def test_client_initialization_from_env(self):
        """Client should read from environment if params not provided"""
        # Arrange & Act
        with patch(
            "src.layers.shared.python.talktalk_shared.clients.telegram_client.get_telegram_bot_token",
            return_value="env_token",
        ):
            with patch(
                "src.layers.shared.python.talktalk_shared.clients.telegram_client.get_telegram_chat_id",
                return_value="env_chat",
            ):
                with patch("src.layers.shared.python.talktalk_shared.clients.telegram_client.Bot"):
                    client = TelegramClient()

                    # Assert
                    assert client.bot_token == "env_token"
                    assert client.chat_id == "env_chat"
