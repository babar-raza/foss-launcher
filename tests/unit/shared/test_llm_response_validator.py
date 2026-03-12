"""Tests for llm_response_validator — TC-3843, TC-3870."""
import pytest
from src.launcher.shared.llm_response_validator import validate_llm_response, enhance_prompt_for_retry, ValidationResult


class TestValidateLlmResponse:
    def test_valid_json_array_with_type_keys(self):
        result = validate_llm_response('[{"type": "paragraph", "content": "Hello"}]')
        assert result.is_valid is True
        assert result.issues == []

    def test_empty_array_is_valid(self):
        result = validate_llm_response('[]')
        assert result.is_valid is True

    def test_non_json_string(self):
        result = validate_llm_response('not json at all')
        assert result.is_valid is False
        assert any("Not valid JSON" in issue for issue in result.issues)

    def test_json_object_not_array(self):
        result = validate_llm_response('{"type": "paragraph"}')
        assert result.is_valid is False
        assert any("Expected JSON array" in issue for issue in result.issues)

    def test_array_element_missing_type(self):
        result = validate_llm_response('[{"content": "Hello"}]')
        assert result.is_valid is False
        assert any("missing 'type' key" in issue for issue in result.issues)

    def test_enhance_prompt_with_issues(self):
        enhanced = enhance_prompt_for_retry("original prompt", ["issue 1"])
        assert "PREVIOUS RESPONSE FAILED VALIDATION" in enhanced
        assert "issue 1" in enhanced

    def test_enhance_prompt_no_issues(self):
        result = enhance_prompt_for_retry("original", [])
        assert result == "original"

    def test_enhance_prompt_prepends_notice(self):
        """Notice must come BEFORE the original prompt body — TC-4223."""
        enhanced = enhance_prompt_for_retry("original prompt", ["Element 0 missing 'type' key"])
        # Notice is first; original prompt is at the end
        assert enhanced.startswith("CRITICAL")
        assert enhanced.endswith("original prompt")

    def test_enhance_prompt_contains_type_hint(self):
        """Retry hint must list valid type values — TC-4223."""
        enhanced = enhance_prompt_for_retry("base", ["Element 0 missing 'type' key"])
        assert "paragraph" in enhanced  # valid type values hint present

    def test_enhance_prompt_with_validation_result_object(self):
        """Backward compat: ValidationResult object accepted — TC-4223."""
        vr = ValidationResult(is_valid=False, issues=["Element 0 missing 'type' key"])
        enhanced = enhance_prompt_for_retry("base prompt", vr)
        assert enhanced.startswith("CRITICAL")
        assert "base prompt" in enhanced


class TestContentTypeRouting:
    """TC-3870: validate_llm_response respects content_type kwarg."""

    # --- markdown ---
    def test_markdown_always_valid(self):
        result = validate_llm_response("Some prose content.", content_type="markdown")
        assert result.is_valid is True

    def test_markdown_empty_string_valid(self):
        result = validate_llm_response("", content_type="markdown")
        assert result.is_valid is True

    def test_markdown_invalid_json_still_valid(self):
        result = validate_llm_response("not json {broken", content_type="markdown")
        assert result.is_valid is True

    # --- json_object ---
    def test_json_object_valid_dict(self):
        result = validate_llm_response(
            '{"grade": "B", "findings": []}', content_type="json_object"
        )
        assert result.is_valid is True
        assert result.issues == []

    def test_json_object_invalid_json(self):
        result = validate_llm_response("not json", content_type="json_object")
        assert result.is_valid is False
        assert any("Not valid JSON" in issue for issue in result.issues)

    def test_json_object_array_rejected(self):
        result = validate_llm_response('[{"type": "x"}]', content_type="json_object")
        assert result.is_valid is False
        assert any("Expected JSON object" in issue for issue in result.issues)

    def test_json_object_review_response_format(self):
        """Simulate real review LLM response — should pass."""
        payload = '{"grade": "C", "findings": [{"check": "density", "message": "too thin", "severity": "high"}]}'
        result = validate_llm_response(payload, content_type="json_object")
        assert result.is_valid is True

    # --- json_array (default) ---
    def test_json_array_default_explicit(self):
        result = validate_llm_response('[{"type": "p"}]', content_type="json_array")
        assert result.is_valid is True

    def test_json_array_default_no_kwarg(self):
        """No content_type kwarg → defaults to json_array (backward compat)."""
        result = validate_llm_response('[{"type": "p"}]')
        assert result.is_valid is True

    def test_json_array_dict_rejected_by_default(self):
        result = validate_llm_response('{"grade": "B"}')
        assert result.is_valid is False
        assert any("Expected JSON array" in issue for issue in result.issues)
