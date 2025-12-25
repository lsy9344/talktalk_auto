"""Prompts module for LLM interactions."""

from talktalk_shared.prompts.developer_prompt import (
    DEVELOPER_PROMPT,
    build_developer_message,
)
from talktalk_shared.prompts.system_prompt import SYSTEM_PROMPT, build_system_message

__all__ = [
    "SYSTEM_PROMPT",
    "build_system_message",
    "DEVELOPER_PROMPT",
    "build_developer_message",
]
