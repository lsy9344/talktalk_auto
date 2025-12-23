"""Naver TalkTalk Webhook Event Models"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TextContent(BaseModel):
    """Text content in webhook event"""

    text: Optional[str] = None
    code: Optional[str] = None
    inputType: Optional[str] = None


class Options(BaseModel):
    """User options in webhook event"""

    mobile: Optional[bool] = None
    under14: Optional[bool] = None
    under19: Optional[bool] = None


class WebhookEvent(BaseModel):
    """
    Naver TalkTalk Webhook Event Model

    Reference: docs/architecture.md#Naver TalkTalk Webhook API
    """

    event: str = Field(..., description="Event type: send, open, leave, echo")
    user: str = Field(..., description="User ID")
    textContent: Optional[TextContent] = None
    options: Optional[Options] = None
    imageContent: Optional[Dict[str, Any]] = None
    compositeContent: Optional[Dict[str, Any]] = None
