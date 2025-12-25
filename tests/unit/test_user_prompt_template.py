"""Unit tests for User Prompt Template module.

Tests verify:
1. USER_PROMPT_TEMPLATE constant matches PRD 7.3 text exactly
2. build_user_message() correctly replaces all template variables
3. build_user_message() returns correct dict structure
4. build_user_message() handles optional fields safely (None/empty values)
"""

from talktalk_shared.prompts.user_prompt_template import (
    USER_PROMPT_TEMPLATE,
    build_user_message,
)

# Expected text from PRD 7.3 - used as ground truth for comparison
EXPECTED_PRD_TEXT = """[채널 정보]
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


class TestUserPromptTemplateConstant:
    """Test USER_PROMPT_TEMPLATE constant."""

    def test_user_prompt_template_matches_prd_text(self):
        """USER_PROMPT_TEMPLATE must match PRD 7.3 text exactly (including newlines)."""
        assert USER_PROMPT_TEMPLATE == EXPECTED_PRD_TEXT, (
            "USER_PROMPT_TEMPLATE does not match PRD 7.3 text. "
            "DO NOT modify the prompt without coordination with architect."
        )

    def test_user_prompt_template_is_non_empty_string(self):
        """USER_PROMPT_TEMPLATE must be a non-empty string."""
        assert isinstance(USER_PROMPT_TEMPLATE, str)
        assert len(USER_PROMPT_TEMPLATE) > 0

    def test_user_prompt_template_contains_required_placeholders(self):
        """USER_PROMPT_TEMPLATE must contain all required placeholders."""
        # Required placeholders
        assert "{{channel_id}}" in USER_PROMPT_TEMPLATE
        assert "{{channel_name}}" in USER_PROMPT_TEMPLATE
        assert "{{global_mode}}" in USER_PROMPT_TEMPLATE
        assert "{{channel_mode}}" in USER_PROMPT_TEMPLATE
        assert "{{user_id}}" in USER_PROMPT_TEMPLATE
        assert "{{question_raw}}" in USER_PROMPT_TEMPLATE
        assert "{{kb_chunks}}" in USER_PROMPT_TEMPLATE

        # Optional placeholders
        assert "{{inflow}}" in USER_PROMPT_TEMPLATE
        assert "{{referer}}" in USER_PROMPT_TEMPLATE
        assert "{{from}}" in USER_PROMPT_TEMPLATE

    def test_user_prompt_template_contains_key_sections(self):
        """USER_PROMPT_TEMPLATE must contain critical section headers."""
        assert "[채널 정보]" in USER_PROMPT_TEMPLATE
        assert "[운영 모드]" in USER_PROMPT_TEMPLATE
        assert "[고객 메시지]" in USER_PROMPT_TEMPLATE
        assert "[추가 컨텍스트(있으면 제공)]" in USER_PROMPT_TEMPLATE
        assert "[지식베이스(KB) - 발췌]" in USER_PROMPT_TEMPLATE
        assert "send_to_user=false" in USER_PROMPT_TEMPLATE

    def test_user_prompt_template_has_no_trailing_whitespace(self):
        """USER_PROMPT_TEMPLATE should not have trailing whitespace at the end."""
        assert not USER_PROMPT_TEMPLATE.endswith(" ")
        assert not USER_PROMPT_TEMPLATE.endswith("\n")


class TestBuildUserMessage:
    """Test build_user_message() helper function."""

    def test_build_user_message_returns_dict(self):
        """build_user_message() must return a dict."""
        result = build_user_message(
            channel_id="test_channel",
            channel_name="Test Channel",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="테스트 질문입니다",
            kb_chunks="KB chunk 1\nKB chunk 2",
        )
        assert isinstance(result, dict)

    def test_build_user_message_has_correct_structure(self):
        """build_user_message() must return {"role": "user", "content": ...}."""
        result = build_user_message(
            channel_id="test_channel",
            channel_name="Test Channel",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="테스트 질문입니다",
            kb_chunks="KB chunk 1",
        )

        # Check keys
        assert "role" in result
        assert "content" in result
        assert len(result) == 2  # Only these two keys

        # Check role value
        assert result["role"] == "user"

        # Check content is a string
        assert isinstance(result["content"], str)

    def test_build_user_message_replaces_all_required_variables(self):
        """build_user_message() must replace all required {{...}} placeholders."""
        result = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="PROD",
            channel_mode="PROD",
            user_id="user999",
            question_raw="배송은 언제 되나요?",
            kb_chunks="배송은 2-3일 소요됩니다.",
        )

        content = result["content"]

        # No placeholders should remain for required fields
        assert "{{channel_id}}" not in content
        assert "{{channel_name}}" not in content
        assert "{{global_mode}}" not in content
        assert "{{channel_mode}}" not in content
        assert "{{user_id}}" not in content
        assert "{{question_raw}}" not in content
        assert "{{kb_chunks}}" not in content

        # Values should be present
        assert "ch001" in content
        assert "채널A" in content
        assert "PROD" in content
        assert "user999" in content
        assert "배송은 언제 되나요?" in content
        assert "배송은 2-3일 소요됩니다." in content

    def test_build_user_message_handles_optional_fields_with_values(self):
        """build_user_message() must replace optional fields when provided."""
        result = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="질문",
            kb_chunks="KB",
            inflow="mobile_app",
            referer="https://example.com",
            from_="search",
        )

        content = result["content"]

        # Optional placeholders should be replaced
        assert "{{inflow}}" not in content
        assert "{{referer}}" not in content
        assert "{{from}}" not in content

        # Values should be present
        assert "mobile_app" in content
        assert "https://example.com" in content
        assert "search" in content

    def test_build_user_message_handles_optional_fields_as_none(self):
        """build_user_message() must handle None for optional fields (no error)."""
        result = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="질문",
            kb_chunks="KB",
            inflow=None,
            referer=None,
            from_=None,
        )

        content = result["content"]

        # Should not raise error
        assert isinstance(content, str)

        # Placeholders should be replaced with empty string
        assert "{{inflow}}" not in content
        assert "{{referer}}" not in content
        assert "{{from}}" not in content

    def test_build_user_message_handles_optional_fields_omitted(self):
        """build_user_message() must work when optional fields are omitted entirely."""
        # Call without optional parameters
        result = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="질문",
            kb_chunks="KB",
        )

        content = result["content"]

        # Should not raise error
        assert isinstance(content, str)

        # Placeholders should be replaced with empty string
        assert "{{inflow}}" not in content
        assert "{{referer}}" not in content
        assert "{{from}}" not in content

    def test_build_user_message_does_not_replace_placeholders_inside_question_raw(self):
        """build_user_message() must not change question_raw even if it contains {{...}}."""
        question_raw = "질문에 {{from}} / {{kb_chunks}} 같은 글자가 있어도 그대로여야 합니다"
        result = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw=question_raw,
            kb_chunks="KB",
            from_="search",
        )

        content = result["content"]

        # message 라인은 question_raw 그대로 들어가야 합니다.
        assert f"- message: {question_raw}" in content

        # from 라인은 template 자리만 치환되어야 합니다.
        assert "- from: search" in content

    def test_build_user_message_returns_new_dict_each_time(self):
        """build_user_message() should return a new dict each call."""
        result1 = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="질문",
            kb_chunks="KB",
        )
        result2 = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="질문",
            kb_chunks="KB",
        )

        # They should be equal in value
        assert result1 == result2

        # But they should be different objects
        assert result1 is not result2

    def test_build_user_message_dict_is_valid_for_openai_api(self):
        """build_user_message() result should be valid for OpenAI Chat API."""
        result = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="질문",
            kb_chunks="KB",
        )

        # OpenAI expects: {"role": str, "content": str}
        assert isinstance(result.get("role"), str)
        assert isinstance(result.get("content"), str)
        assert result["role"] in ["system", "user", "assistant", "developer"]

    def test_build_user_message_preserves_template_structure(self):
        """build_user_message() should preserve section headers and structure."""
        result = build_user_message(
            channel_id="ch001",
            channel_name="채널A",
            global_mode="TEST",
            channel_mode="TEST",
            user_id="user123",
            question_raw="질문",
            kb_chunks="KB",
        )

        content = result["content"]

        # Section headers should still be present
        assert "[채널 정보]" in content
        assert "[운영 모드]" in content
        assert "[고객 메시지]" in content
        assert "[추가 컨텍스트(있으면 제공)]" in content
        assert "[지식베이스(KB) - 발췌]" in content
