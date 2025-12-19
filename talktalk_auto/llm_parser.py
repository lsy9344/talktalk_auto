from __future__ import annotations

from .models import LLMResult


def _bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return default


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _list(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [str(value)]


def parse_llm_result(data: dict) -> LLMResult:
    return LLMResult(
        draft_answer=str(data.get("draft_answer", "") or ""),
        confidence=_float(data.get("confidence", 0.0), 0.0),
        send_to_user=_bool(data.get("send_to_user", False), False),
        needs_operator=_bool(data.get("needs_operator", False), False),
        reasons=[str(item) for item in _list(data.get("reasons"))],
        citations=_list(data.get("citations")),
        followup_questions_for_operator=[
            str(item) for item in _list(data.get("followup_questions_for_operator"))
        ],
    )
