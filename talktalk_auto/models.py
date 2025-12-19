from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TalkTalkEvent:
    event: str
    user_id: str
    text: str | None
    raw: dict[str, Any] = field(default_factory=dict)
    has_image: bool = False
    has_composite: bool = False

    @property
    def has_text(self) -> bool:
        return bool(self.text)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TalkTalkEvent":
        event = str(payload.get("event", "")).lower()
        user_id = str(payload.get("user", ""))
        text_content = payload.get("textContent") or {}
        text = text_content.get("text") if isinstance(text_content, dict) else None
        has_image = bool(payload.get("imageContent"))
        has_composite = bool(payload.get("compositeContent"))
        return cls(
            event=event,
            user_id=user_id,
            text=text,
            raw=payload,
            has_image=has_image,
            has_composite=has_composite,
        )


@dataclass
class RagChunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    section: str
    updated_at: str
    text: str
    score: float


@dataclass
class RagResult:
    chunks: list[RagChunk]
    top1: float
    topk_avg: float


@dataclass
class LLMResult:
    draft_answer: str
    confidence: float
    send_to_user: bool
    needs_operator: bool
    reasons: list[str]
    citations: list[dict[str, Any]]
    followup_questions_for_operator: list[str]


@dataclass
class ChannelConfig:
    channel_id: str
    channel_name: str
    channel_mode: str
    docs_channel_ids: list[str]
    docs_common_ids: list[str]
    talktalk_auth_secret_arn: str
    sheet_id: str
    sheet_tab: str
    telegram_target: str
    index_s3_uri: str
    index_version: str

    @classmethod
    def from_item(cls, item: dict[str, Any]) -> "ChannelConfig":
        return cls(
            channel_id=item.get("channel_id", ""),
            channel_name=item.get("channel_name", ""),
            channel_mode=item.get("channel_mode", "TEST"),
            docs_channel_ids=item.get("docs_channel_ids") or [],
            docs_common_ids=item.get("docs_common_ids") or [],
            talktalk_auth_secret_arn=item.get("talktalk_auth_secret_arn", ""),
            sheet_id=item.get("sheet_id", ""),
            sheet_tab=item.get("sheet_tab", ""),
            telegram_target=item.get("telegram_target", ""),
            index_s3_uri=item.get("index_s3_uri", ""),
            index_version=item.get("index_version", ""),
        )


@dataclass
class Decision:
    send_to_user: bool
    needs_operator: bool
    reasons: list[str]
    blocked_by_mode: bool
    blocked_by_policy: bool
