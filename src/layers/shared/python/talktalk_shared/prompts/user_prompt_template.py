"""User Prompt Template for LLM (런타임 구성).

This module contains the fixed User Prompt Template text from PRD Section 7.3.
DO NOT modify the prompt text without coordination with the architect.

Source: docs/prd/73-user-prompt-template-런타임-구성.md
"""

import re
from typing import Optional

# User Prompt Template text from PRD 7.3 - DO NOT MODIFY
USER_PROMPT_TEMPLATE = """[채널 정보]
- channel_id: {{channel_id}}
- channel_name: {{channel_name}}

[운영 모드]
- global_mode: {{global_mode}}   (TEST|PROD)
- channel_mode: {{channel_mode}} (TEST|PROD|DISABLED)

[고객 메시지]
- user_id: {{user_id}}
- message: {{question_raw}}

[추가 컨텍스트(있으면 제공)]
- inflow: {{inflow}}
- referer: {{referer}}
- from: {{from}}

[지식베이스(KB) - 발췌]
아래 KB 내용만 근거로 사용해 답변 초안을 작성하라.
KB에 없는 정보는 단정하지 말고, 운영자 확인이 필요하면 send_to_user=false로 하라.

{{kb_chunks}}"""

_PLACEHOLDER_RE = re.compile(r"{{([a-z_]+)}}")


def build_user_message(
    channel_id: str,
    channel_name: str,
    global_mode: str,
    channel_mode: str,
    user_id: str,
    question_raw: str,
    kb_chunks: str,
    inflow: Optional[str] = None,
    referer: Optional[str] = None,
    from_: Optional[str] = None,
) -> dict[str, str]:
    """Build user role message for LLM API.

    Args:
        channel_id: Channel ID
        channel_name: Channel name
        global_mode: Global mode (TEST|PROD)
        channel_mode: Channel mode (TEST|PROD|DISABLED)
        user_id: User ID from webhook event
        question_raw: Raw question text from user
        kb_chunks: Knowledge base chunks formatted as string
        inflow: Optional inflow context
        referer: Optional referer context
        from_: Optional from context (using from_ to avoid Python keyword)

    Returns:
        dict: User message in the format {"role": "user", "content": <filled template>}
    """
    values: dict[str, str] = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "global_mode": global_mode,
        "channel_mode": channel_mode,
        "user_id": user_id,
        "question_raw": question_raw,
        "kb_chunks": kb_chunks,
        "inflow": inflow or "",
        "referer": referer or "",
        "from": from_ or "",
    }

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return values.get(key, match.group(0))

    content = _PLACEHOLDER_RE.sub(replace, USER_PROMPT_TEMPLATE)

    return {"role": "user", "content": content}
