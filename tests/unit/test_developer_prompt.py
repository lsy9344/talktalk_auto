"""Unit tests for Developer Prompt module.

Tests verify:
1. DEVELOPER_PROMPT constant matches PRD 7.2 text exactly
2. build_developer_message() returns correct dict structure
"""

from talktalk_shared.prompts.developer_prompt import (
    DEVELOPER_PROMPT,
    build_developer_message,
)

# Expected text from PRD 7.2 - used as ground truth for comparison
EXPECTED_PRD_TEXT = """너는 반드시 아래 JSON 스키마를 준수해서만 출력한다.
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


class TestDeveloperPromptConstant:
    """Test DEVELOPER_PROMPT constant."""

    def test_developer_prompt_matches_prd_text(self):
        """DEVELOPER_PROMPT must match PRD 7.2 text exactly (including newlines)."""
        assert DEVELOPER_PROMPT == EXPECTED_PRD_TEXT, (
            "DEVELOPER_PROMPT does not match PRD 7.2 text. "
            "DO NOT modify the prompt without coordination with architect."
        )

    def test_developer_prompt_is_non_empty_string(self):
        """DEVELOPER_PROMPT must be a non-empty string."""
        assert isinstance(DEVELOPER_PROMPT, str)
        assert len(DEVELOPER_PROMPT) > 0

    def test_developer_prompt_contains_key_instructions(self):
        """DEVELOPER_PROMPT must contain critical instructions."""
        # Check for key phrases (exact Korean text)
        assert "JSON 스키마를 준수" in DEVELOPER_PROMPT
        assert "draft_answer" in DEVELOPER_PROMPT
        assert "confidence" in DEVELOPER_PROMPT
        assert "send_to_user" in DEVELOPER_PROMPT
        assert "needs_operator" in DEVELOPER_PROMPT
        assert "risk_level" in DEVELOPER_PROMPT
        assert "citations" in DEVELOPER_PROMPT
        assert "followup_questions_for_operator" in DEVELOPER_PROMPT
        assert "suggested_quick_reply" in DEVELOPER_PROMPT

    def test_developer_prompt_has_no_trailing_whitespace(self):
        """DEVELOPER_PROMPT should not have trailing whitespace at the end."""
        assert not DEVELOPER_PROMPT.endswith(" ")
        assert not DEVELOPER_PROMPT.endswith("\n")


class TestBuildDeveloperMessage:
    """Test build_developer_message() helper function."""

    def test_build_developer_message_returns_dict(self):
        """build_developer_message() must return a dict."""
        result = build_developer_message()
        assert isinstance(result, dict)

    def test_build_developer_message_has_correct_structure(self):
        """build_developer_message() must return {"role": "developer", "content": ...}."""
        result = build_developer_message()

        # Check keys
        assert "role" in result
        assert "content" in result
        assert len(result) == 2  # Only these two keys

        # Check values
        assert result["role"] == "developer"
        assert result["content"] == DEVELOPER_PROMPT

    def test_build_developer_message_content_matches_constant(self):
        """build_developer_message()["content"] must exactly match DEVELOPER_PROMPT."""
        result = build_developer_message()
        assert result["content"] == DEVELOPER_PROMPT

    def test_build_developer_message_returns_new_dict_each_time(self):
        """build_developer_message() should return a new dict each call (not a singleton)."""
        result1 = build_developer_message()
        result2 = build_developer_message()

        # They should be equal in value
        assert result1 == result2

        # But they should be different objects
        assert result1 is not result2

    def test_build_developer_message_dict_is_valid_for_openai_api(self):
        """build_developer_message() result should be valid for OpenAI Chat API."""
        result = build_developer_message()

        # OpenAI expects: {"role": str, "content": str}
        assert isinstance(result.get("role"), str)
        assert isinstance(result.get("content"), str)
        # OpenAI API supports "developer" role for schema enforcement
        assert result["role"] == "developer"
