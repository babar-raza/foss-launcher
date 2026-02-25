"""Tests for the LLM Contract Module (TC-2519) and heading hierarchy (TC-2523).

Validates:
- OutputSchemaValidator: valid JSON, invalid JSON, markdown-fenced JSON, missing required field
- FailureClassifier: classify timeout, schema error, content error, unknown
- RetryStrategy: should retry on schema_error, should not retry on content_error, max retries
- RuleChecklist: format output, max rules limit
- validate_heading_hierarchy: valid H1->H2->H3, invalid H1->H3, H2->H4 skip
"""

from __future__ import annotations

import json

import pytest

from src.launch.workers._shared.llm_contract import (
    FailureClassifier,
    OutputSchemaValidator,
    RetryStrategy,
    RuleChecklist,
)
from src.launch.workers._shared.content_sanitizer import validate_heading_hierarchy


# ── OutputSchemaValidator ──────────────────────────────────────────────────────


class TestOutputSchemaValidator:
    """Tests for OutputSchemaValidator."""

    @pytest.fixture()
    def schema(self):
        return {
            "type": "object",
            "required": ["content"],
            "properties": {
                "content": {"type": "string"},
                "metadata": {"type": "object"},
            },
        }

    def test_valid_json(self, schema):
        """Valid JSON matching schema passes."""
        validator = OutputSchemaValidator(schema)
        ok, data, err = validator.validate('{"content": "hello world"}')
        assert ok is True
        assert data == {"content": "hello world"}
        assert err is None

    def test_valid_json_with_metadata(self, schema):
        """Valid JSON with optional metadata passes."""
        validator = OutputSchemaValidator(schema)
        raw = '{"content": "hello", "metadata": {"key": "value"}}'
        ok, data, err = validator.validate(raw)
        assert ok is True
        assert data["content"] == "hello"
        assert data["metadata"]["key"] == "value"

    def test_invalid_json(self, schema):
        """Invalid JSON string returns error."""
        validator = OutputSchemaValidator(schema)
        ok, data, err = validator.validate("this is not json")
        assert ok is False
        assert data is None
        assert "JSON parse error" in err

    def test_markdown_fenced_json(self, schema):
        """JSON inside markdown fence is extracted and validated."""
        validator = OutputSchemaValidator(schema)
        raw = '```json\n{"content": "fenced value"}\n```'
        ok, data, err = validator.validate(raw)
        assert ok is True
        assert data == {"content": "fenced value"}
        assert err is None

    def test_markdown_fenced_json_without_json_tag(self, schema):
        """JSON inside bare markdown fence (no json tag) is extracted."""
        validator = OutputSchemaValidator(schema)
        raw = '```\n{"content": "bare fence"}\n```'
        ok, data, err = validator.validate(raw)
        assert ok is True
        assert data["content"] == "bare fence"

    def test_missing_required_field(self, schema):
        """JSON missing required field returns schema error."""
        validator = OutputSchemaValidator(schema)
        ok, data, err = validator.validate('{"metadata": {"key": "val"}}')
        assert ok is False
        assert data is None
        assert "Schema validation error" in err

    def test_empty_string(self, schema):
        """Empty string returns parse error."""
        validator = OutputSchemaValidator(schema)
        ok, data, err = validator.validate("")
        assert ok is False
        assert data is None

    def test_non_object_json(self, schema):
        """JSON array (not object) returns parse error."""
        validator = OutputSchemaValidator(schema)
        ok, data, err = validator.validate('[1, 2, 3]')
        assert ok is False
        assert data is None

    def test_whitespace_padded_json(self, schema):
        """JSON with leading/trailing whitespace is parsed correctly."""
        validator = OutputSchemaValidator(schema)
        ok, data, err = validator.validate('  \n {"content": "padded"}  \n ')
        assert ok is True
        assert data["content"] == "padded"


# ── FailureClassifier ──────────────────────────────────────────────────────────


class TestFailureClassifier:
    """Tests for FailureClassifier."""

    @pytest.fixture()
    def classifier(self):
        return FailureClassifier()

    def test_classify_timeout(self, classifier):
        """Timeout-related errors classified as timeout_error."""
        assert classifier.classify("Connection timed out after 30s") == "timeout_error"
        assert classifier.classify("deadline exceeded") == "timeout_error"
        assert classifier.classify("Request timeout") == "timeout_error"

    def test_classify_rate_limit(self, classifier):
        """Rate limit errors classified as rate_limit_error."""
        assert classifier.classify("429 Too Many Requests") == "rate_limit_error"
        assert classifier.classify("Rate limit exceeded") == "rate_limit_error"
        assert classifier.classify("Quota exhausted") == "rate_limit_error"

    def test_classify_schema_error(self, classifier):
        """Schema/JSON errors classified as schema_error."""
        assert classifier.classify("JSON decode error") == "schema_error"
        assert classifier.classify("Schema validation failed") == "schema_error"
        assert classifier.classify("missing required field 'content'") == "schema_error"
        assert classifier.classify("unexpected token at line 5") == "schema_error"

    def test_classify_content_error(self, classifier):
        """Content policy errors classified as content_error."""
        assert classifier.classify("content filter triggered") == "content_error"
        assert classifier.classify("Hallucination detected") == "content_error"
        assert classifier.classify("Policy violation: unsafe content") == "content_error"

    def test_classify_unknown(self, classifier):
        """Unrecognized errors classified as unknown_error."""
        assert classifier.classify("some random error") == "unknown_error"
        assert classifier.classify("") == "unknown_error"

    def test_classify_with_output(self, classifier):
        """Output text is also inspected for classification cues."""
        assert classifier.classify("generic error", "response has parse issues") == "schema_error"

    def test_priority_timeout_over_schema(self, classifier):
        """Timeout takes priority over schema keywords in same message."""
        assert classifier.classify("timeout during json parse") == "timeout_error"


# ── RetryStrategy ──────────────────────────────────────────────────────────────


class TestRetryStrategy:
    """Tests for RetryStrategy."""

    def test_should_retry_schema_error(self):
        """Schema errors should be retried."""
        strategy = RetryStrategy(max_retries=2)
        assert strategy.should_retry("schema_error", 0) is True
        assert strategy.should_retry("schema_error", 1) is True

    def test_should_not_retry_content_error(self):
        """Content errors should never be retried (escalated)."""
        strategy = RetryStrategy(max_retries=2)
        assert strategy.should_retry("content_error", 0) is False

    def test_max_retries_respected(self):
        """Should not retry when max retries reached."""
        strategy = RetryStrategy(max_retries=2)
        assert strategy.should_retry("schema_error", 2) is False
        assert strategy.should_retry("schema_error", 3) is False

    def test_should_retry_timeout(self):
        """Timeout errors should be retried."""
        strategy = RetryStrategy(max_retries=2)
        assert strategy.should_retry("timeout_error", 0) is True

    def test_should_retry_rate_limit(self):
        """Rate limit errors should be retried."""
        strategy = RetryStrategy(max_retries=2)
        assert strategy.should_retry("rate_limit_error", 0) is True

    def test_unknown_error_not_retried(self):
        """Unknown errors are not in retry_on set so should not retry."""
        strategy = RetryStrategy(max_retries=2)
        assert strategy.should_retry("unknown_error", 0) is False

    def test_zero_max_retries(self):
        """With max_retries=0, no retries at all."""
        strategy = RetryStrategy(max_retries=0)
        assert strategy.should_retry("schema_error", 0) is False

    def test_custom_retry_on(self):
        """Custom retry_on set respects user configuration."""
        strategy = RetryStrategy(
            max_retries=3,
            retry_on=frozenset({"unknown_error"}),
        )
        assert strategy.should_retry("unknown_error", 0) is True
        assert strategy.should_retry("schema_error", 0) is False

    def test_frozen_dataclass(self):
        """RetryStrategy is immutable (frozen dataclass)."""
        strategy = RetryStrategy(max_retries=2)
        with pytest.raises(AttributeError):
            strategy.max_retries = 5


# ── RuleChecklist ──────────────────────────────────────────────────────────────


class TestRuleChecklist:
    """Tests for RuleChecklist."""

    def test_format_for_prompt(self):
        """Rules are formatted as numbered checklist."""
        cl = RuleChecklist(rules=["Rule one.", "Rule two.", "Rule three."])
        output = cl.format_for_prompt()
        assert "RULES CHECKLIST (you MUST follow all):" in output
        assert "1. Rule one." in output
        assert "2. Rule two." in output
        assert "3. Rule three." in output

    def test_empty_checklist(self):
        """Empty rules return empty string."""
        cl = RuleChecklist(rules=[])
        assert cl.format_for_prompt() == ""

    def test_max_rules_limit(self):
        """Rules exceeding MAX_RULES are truncated."""
        many_rules = [f"Rule {i}" for i in range(15)]
        cl = RuleChecklist(rules=many_rules)
        assert len(cl.rules) == 10  # MAX_RULES default
        assert cl.rules[0] == "Rule 0"
        assert cl.rules[9] == "Rule 9"

    def test_single_rule(self):
        """Single rule formats correctly."""
        cl = RuleChecklist(rules=["Only rule."])
        output = cl.format_for_prompt()
        assert "1. Only rule." in output
        lines = output.strip().split("\n")
        assert len(lines) == 2  # header + 1 rule

    def test_max_rules_constant(self):
        """MAX_RULES class attribute is 10."""
        cl = RuleChecklist()
        assert cl.MAX_RULES == 10


# ── Heading Hierarchy Validator (TC-2523) ──────────────────────────────────────


class TestHeadingHierarchy:
    """Tests for validate_heading_hierarchy()."""

    def test_valid_h1_h2_h3(self):
        """H1 -> H2 -> H3 hierarchy is valid."""
        content = "# Title\n\n## Section\n\n### Subsection\n\nSome text.\n"
        errors = validate_heading_hierarchy(content)
        assert errors == []

    def test_valid_h1_h2_h2(self):
        """H1 -> H2 -> H2 (sibling headings) is valid."""
        content = "# Title\n\n## First\n\n## Second\n"
        errors = validate_heading_hierarchy(content)
        assert errors == []

    def test_valid_h2_h3_h2(self):
        """H2 -> H3 -> H2 (going up) is valid."""
        content = "## Section A\n\n### Sub A\n\n## Section B\n"
        errors = validate_heading_hierarchy(content)
        assert errors == []

    def test_invalid_h1_h3_skip(self):
        """H1 -> H3 skip is an error."""
        content = "# Title\n\n### Subsection\n\nSome text.\n"
        errors = validate_heading_hierarchy(content)
        assert len(errors) == 1
        assert "H1 -> H3" in errors[0]
        assert "line 3" in errors[0]

    def test_invalid_h2_h4_skip(self):
        """H2 -> H4 skip is an error."""
        content = "## Section\n\n#### Deep\n\nText.\n"
        errors = validate_heading_hierarchy(content)
        assert len(errors) == 1
        assert "H2 -> H4" in errors[0]

    def test_invalid_h1_h4_double_skip(self):
        """H1 -> H4 is a double skip (error)."""
        content = "# Title\n\n#### Way too deep\n"
        errors = validate_heading_hierarchy(content)
        assert len(errors) == 1
        assert "H1 -> H4" in errors[0]

    def test_multiple_skips(self):
        """Multiple heading skips produce multiple errors."""
        content = "# Title\n\n### Skip 1\n\n##### Skip 2\n"
        errors = validate_heading_hierarchy(content)
        assert len(errors) == 2

    def test_empty_content(self):
        """Empty content returns no errors."""
        assert validate_heading_hierarchy("") == []
        assert validate_heading_hierarchy("   \n  \n") == []

    def test_no_headings(self):
        """Content with no headings returns no errors."""
        content = "Just some text.\n\nMore text.\n"
        errors = validate_heading_hierarchy(content)
        assert errors == []

    def test_only_h1(self):
        """Single H1 is valid."""
        content = "# Title\n\nSome text.\n"
        errors = validate_heading_hierarchy(content)
        assert errors == []

    def test_headings_inside_code_fence_ignored(self):
        """Headings inside code fences should be ignored."""
        content = (
            "## Section\n\n"
            "```markdown\n"
            "#### This is in a code fence\n"
            "```\n\n"
            "### Valid subsection\n"
        )
        errors = validate_heading_hierarchy(content)
        assert errors == []

    def test_h1_to_h2_to_h1(self):
        """H1 -> H2 -> H1 (going back up) is valid."""
        content = "# First\n\n## Sub\n\n# Second\n"
        errors = validate_heading_hierarchy(content)
        assert errors == []

    def test_heading_text_in_error(self):
        """Error message includes heading text."""
        content = "# Title\n\n### My Subsection\n"
        errors = validate_heading_hierarchy(content)
        assert len(errors) == 1
        assert "My Subsection" in errors[0]
