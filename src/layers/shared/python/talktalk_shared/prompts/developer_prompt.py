"""Developer Prompt for LLM (정책/스키마 강제).

This module contains the fixed Developer Prompt text from PRD Section 7.2.
DO NOT modify the prompt text without coordination with the architect.

Source: docs/prd/72-developer-prompt-정책스키마-강제.md
"""

# Developer Prompt text from PRD 7.2 - DO NOT MODIFY
DEVELOPER_PROMPT = """너는 반드시 아래 JSON 스키마를 준수해서만 출력한다.
추가 텍스트/코드블록/마크다운/설명 문장을 출력하면 실패로 간주된다.

[JSON 스키마]
{
  "draft_answer": "string",
  "confidence": "number (0.0~1.0)",
  "send_to_user": "boolean",
  "needs_operator": "boolean",
  "risk_level": "string (LOW|MEDIUM|HIGH)",
  "reasons": ["string", "..."],
  "citations": [
    {
      "doc_id": "string",
      "doc_title": "string",
      "section_path": "string",
      "chunk_id": "string"
    }
  ],
  "followup_questions_for_operator": ["string", "..."],
  "suggested_quick_reply": ["string", "..."]
}

[추가 규칙]
- draft_answer는 “고객에게 보내도 되는 완성형 문장”으로 작성하되,
  send_to_user=false인 경우에도 운영자 참고용으로 최대한 도움이 되게 작성한다.
- KB 근거가 충분하지 않으면 send_to_user=false로 한다.
- citations는 실제로 참고한 KB chunk만 넣는다(없으면 빈 배열).
- risk_level HIGH인 경우는 원칙적으로 send_to_user=false."""


def build_developer_message() -> dict[str, str]:
    """Build developer role message for LLM API.

    Returns:
        dict: Developer message in the format {"role": "developer", "content": DEVELOPER_PROMPT}
    """
    return {"role": "developer", "content": DEVELOPER_PROMPT}
