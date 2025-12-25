"""Unit tests for System Prompt module.

Tests verify:
1. SYSTEM_PROMPT constant matches PRD 7.1 text exactly
2. build_system_message() returns correct dict structure
"""

from talktalk_shared.prompts.system_prompt import SYSTEM_PROMPT, build_system_message

# Expected text from PRD 7.1 - used as ground truth for comparison
EXPECTED_PRD_TEXT = """당신은 네이버 톡톡에서 고객 문의에 답변 초안을 작성하는 담당자입니다.

목표:
- 제공된 지식베이스(KB) 내용에 근거해, 고객에게 보낼 수 있는 "답변 초안"을 생성합니다.
- 답변이 불확실하거나 리스크가 크면 고객에게 보내지 말고(무응답), \
운영자에게 알릴 수 있도록 구조화된 신호를 출력합니다.

말투/톤:
- 한국어
- 존댓말 + 친근한 말투
- 이모지는 0~2개 정도로 과하지 않게 사용

절대 금지(고객에게 나갈 문장 기준):
- "모르겠습니다 / 확실하지 않습니다 / 잘 모르겠어요 / 추측입니다" 등 무지/불확실을 직접 표현
- "상담원에게 연결해드릴게요 / 담당자 연결" 등 안내 문구
- KB에 없는 사실을 단정하거나, 정책/기간/금액을 임의로 생성

불확실/애매/리스크가 있으면:
- 고객에게는 보내지 않습니다(send_to_user=false)
- needs_operator=true로 표시하고, reasons에 왜 그런지 적습니다.
- 운영자가 바로 판단할 수 있도록 followup_questions_for_operator를 최대한 구체적으로 작성합니다.

출력은 반드시 JSON 형식만 반환합니다(설명 텍스트 금지)."""


class TestSystemPromptConstant:
    """Test SYSTEM_PROMPT constant."""

    def test_system_prompt_matches_prd_text(self):
        """SYSTEM_PROMPT must match PRD 7.1 text exactly (including newlines)."""
        assert SYSTEM_PROMPT == EXPECTED_PRD_TEXT, (
            "SYSTEM_PROMPT does not match PRD 7.1 text. "
            "DO NOT modify the prompt without coordination with architect."
        )

    def test_system_prompt_is_non_empty_string(self):
        """SYSTEM_PROMPT must be a non-empty string."""
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_contains_key_instructions(self):
        """SYSTEM_PROMPT must contain critical instructions."""
        # Check for key phrases (exact Korean text)
        assert "네이버 톡톡" in SYSTEM_PROMPT
        assert "지식베이스(KB)" in SYSTEM_PROMPT
        assert "send_to_user=false" in SYSTEM_PROMPT
        assert "needs_operator=true" in SYSTEM_PROMPT
        assert "JSON 형식만 반환" in SYSTEM_PROMPT

    def test_system_prompt_has_no_trailing_whitespace(self):
        """SYSTEM_PROMPT should not have trailing whitespace at the end."""
        assert not SYSTEM_PROMPT.endswith(" ")
        assert not SYSTEM_PROMPT.endswith("\n")


class TestBuildSystemMessage:
    """Test build_system_message() helper function."""

    def test_build_system_message_returns_dict(self):
        """build_system_message() must return a dict."""
        result = build_system_message()
        assert isinstance(result, dict)

    def test_build_system_message_has_correct_structure(self):
        """build_system_message() must return {"role": "system", "content": ...}."""
        result = build_system_message()

        # Check keys
        assert "role" in result
        assert "content" in result
        assert len(result) == 2  # Only these two keys

        # Check values
        assert result["role"] == "system"
        assert result["content"] == SYSTEM_PROMPT

    def test_build_system_message_content_matches_constant(self):
        """build_system_message()["content"] must exactly match SYSTEM_PROMPT."""
        result = build_system_message()
        assert result["content"] == SYSTEM_PROMPT

    def test_build_system_message_returns_new_dict_each_time(self):
        """build_system_message() should return a new dict each call (not a singleton)."""
        result1 = build_system_message()
        result2 = build_system_message()

        # They should be equal in value
        assert result1 == result2

        # But they should be different objects
        assert result1 is not result2

    def test_build_system_message_dict_is_valid_for_openai_api(self):
        """build_system_message() result should be valid for OpenAI Chat API."""
        result = build_system_message()

        # OpenAI expects: {"role": str, "content": str}
        assert isinstance(result.get("role"), str)
        assert isinstance(result.get("content"), str)
        assert result["role"] in ["system", "user", "assistant"]  # Valid roles
