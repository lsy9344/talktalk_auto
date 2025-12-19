from __future__ import annotations

import json

from openai import OpenAI

from .llm_prompt import SYSTEM_PROMPT, build_user_prompt
from .settings import get_settings


_CLIENT: OpenAI | None = None


def _get_client() -> OpenAI:
    global _CLIENT
    if _CLIENT is None:
        settings = get_settings()
        _CLIENT = OpenAI(api_key=settings.openai_api_key)
    return _CLIENT


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    client = _get_client()
    resp = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in resp.data]


def generate_llm_json(question: str, context: str) -> dict:
    settings = get_settings()
    client = _get_client()
    user_prompt = build_user_prompt(question, context)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise
