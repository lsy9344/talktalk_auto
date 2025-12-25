"""Prompts module for LLM interactions."""

from talktalk_shared.prompts.developer_prompt import (
    DEVELOPER_PROMPT,
    build_developer_message,
)
from talktalk_shared.prompts.kb_chunks_format import format_kb_chunks
from talktalk_shared.prompts.system_prompt import SYSTEM_PROMPT, build_system_message
from talktalk_shared.prompts.user_prompt_template import (
    USER_PROMPT_TEMPLATE,
    build_user_message,
)

__all__ = [
    "SYSTEM_PROMPT",
    "build_system_message",
    "DEVELOPER_PROMPT",
    "build_developer_message",
    "USER_PROMPT_TEMPLATE",
    "build_user_message",
    "format_kb_chunks",
]
