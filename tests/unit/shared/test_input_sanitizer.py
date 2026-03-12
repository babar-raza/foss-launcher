"""Tests for input_sanitizer.sanitize_input() — TC-3825."""
from __future__ import annotations

import pytest

from launcher.shared.input_sanitizer import SanitizationResult, sanitize_input


# ---------------------------------------------------------------------------
# Clean passthrough (no changes)
# ---------------------------------------------------------------------------

class TestCleanContent:
    def test_plain_prose_unchanged(self) -> None:
        text = "Aspose.Cells for Python allows reading and writing Excel files."
        result = sanitize_input(text)
        assert result.text == text
        assert result.redaction_count == 0
        assert result.truncated is False
        assert result.redacted_kinds == []

    def test_empty_string(self) -> None:
        result = sanitize_input("")
        assert result.text == ""
        assert result.redaction_count == 0

    def test_normal_html_in_prose_unaffected(self) -> None:
        """HTML tags that are NOT injection vectors must not be removed."""
        text = "The <em>Workbook</em> class represents an Excel file."
        result = sanitize_input(text)
        # We only remove script/iframe/javascript/event handlers, not generic tags
        assert "<em>" in result.text


# ---------------------------------------------------------------------------
# XSS removal — prose context
# ---------------------------------------------------------------------------

class TestXSSRemoval:
    def test_script_tag_removed_from_prose(self) -> None:
        text = 'Use the API. <script>alert("xss")</script> Done.'
        result = sanitize_input(text)
        assert "<script" not in result.text
        assert "alert" not in result.text
        assert "xss" not in result.text
        assert result.redaction_count >= 1
        assert "xss" in result.redacted_kinds

    def test_script_tag_multiline_removed(self) -> None:
        text = "Use the API.\n<script type='text/javascript'>\nalert(1);\n</script>\nDone."
        result = sanitize_input(text)
        assert "<script" not in result.text
        assert "alert" not in result.text

    def test_iframe_removed(self) -> None:
        text = "See <iframe src='evil.com'></iframe> for details."
        result = sanitize_input(text)
        assert "<iframe" not in result.text
        assert "evil.com" not in result.text

    def test_javascript_url_removed(self) -> None:
        text = "Click [here](javascript:alert(1)) to proceed."
        result = sanitize_input(text)
        assert "javascript:" not in result.text

    def test_event_handler_double_quotes_removed(self) -> None:
        text = 'Button <div onclick="steal()">click</div>'
        result = sanitize_input(text)
        assert 'onclick=' not in result.text

    def test_event_handler_single_quotes_removed(self) -> None:
        text = "Button <div onmouseover='steal()'>hover</div>"
        result = sanitize_input(text)
        assert "onmouseover=" not in result.text


# ---------------------------------------------------------------------------
# Code block exemption
# ---------------------------------------------------------------------------

class TestCodeBlockExemption:
    def test_script_in_backtick_fence_preserved(self) -> None:
        """<script> inside a fenced code block must NOT be removed."""
        text = (
            "Here is a security example:\n"
            "```html\n"
            "<script>alert('xss demo')</script>\n"
            "```\n"
            "End of example."
        )
        result = sanitize_input(text)
        assert "<script>" in result.text
        assert "alert" in result.text

    def test_script_in_tilde_fence_preserved(self) -> None:
        """<script> inside a ~~~ fenced block must NOT be removed."""
        text = "Example:\n~~~\n<script>test</script>\n~~~\nDone."
        result = sanitize_input(text)
        assert "<script>" in result.text

    def test_script_outside_fence_removed_inside_preserved(self) -> None:
        """Mixed: prose XSS removed, code block XSS preserved."""
        text = (
            "<script>bad()</script>\n"
            "```\n"
            "<script>good_example()</script>\n"
            "```"
        )
        result = sanitize_input(text)
        # After the fence there's a script tag in prose: removed
        # Inside fence: preserved
        assert "good_example" in result.text
        # The prose script tag should be gone
        assert result.redaction_count >= 1

    def test_indented_code_block_script_preserved(self) -> None:
        """<script> in a 4-space indented block must NOT be removed."""
        text = "Example:\n    <script>alert(1)</script>\nEnd."
        result = sanitize_input(text)
        assert "<script>" in result.text


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------

class TestSecretRedaction:
    def test_sk_key_redacted(self) -> None:
        key = "sk-ABCDEFGHIJKLMNOPQRST"  # exactly 20 chars after prefix
        text = f"API key: {key}"
        result = sanitize_input(text)
        assert "[REDACTED]" in result.text
        assert key not in result.text
        assert result.redaction_count >= 1
        assert "secret" in result.redacted_kinds

    def test_pk_key_redacted(self) -> None:
        key = "pk-xxxxxxxxxxxxxxxxxxxxxxxxxxx"
        text = f"Publish key={key} here."
        result = sanitize_input(text)
        assert key not in result.text
        assert "[REDACTED]" in result.text

    def test_rk_key_redacted(self) -> None:
        text = "rk-abcdefghijklmnopqrstuvwxyz secret leaked"
        result = sanitize_input(text)
        assert "rk-abc" not in result.text

    def test_ak_key_redacted(self) -> None:
        text = "ak-11111111111111111111 token here"
        result = sanitize_input(text)
        assert "ak-111" not in result.text

    def test_short_key_not_redacted(self) -> None:
        """Keys shorter than 20 chars after the prefix must NOT be redacted."""
        text = "short-key sk-abc123 stays"
        result = sanitize_input(text)
        assert "sk-abc123" in result.text
        assert result.redaction_count == 0

    def test_mid_word_not_redacted(self) -> None:
        """sk- appearing mid-word (no word boundary) must not be redacted."""
        text = "mysk-ABCDEFGHIJKLMNOPQRST embedded"
        result = sanitize_input(text)
        # Negative lookbehind prevents match when preceded by alphanumeric
        assert "mysk-" in result.text

    def test_redacted_sentinel_is_idempotent(self) -> None:
        """[REDACTED] must not match the secret pattern (idempotency invariant)."""
        text = "[REDACTED] appeared in output"
        result = sanitize_input(text)
        assert result.text == text  # no further redaction
        assert result.redaction_count == 0


# ---------------------------------------------------------------------------
# Oversized truncation
# ---------------------------------------------------------------------------

class TestOversizedTruncation:
    def test_text_at_limit_not_truncated(self) -> None:
        text = "a" * 1000
        result = sanitize_input(text, max_chars=1000)
        assert result.truncated is False
        assert len(result.text) <= 1000

    def test_text_over_limit_truncated(self) -> None:
        text = "hello " * 10_000  # 60k chars
        result = sanitize_input(text, max_chars=1000)
        assert result.truncated is True
        assert "[TRUNCATED" in result.text
        assert "oversized" in result.redacted_kinds

    def test_truncation_at_word_boundary(self) -> None:
        text = "word " * 200  # clean word boundaries
        result = sanitize_input(text, max_chars=50)
        assert not result.text.startswith(" ")
        # Should not cut mid-word
        words = result.text.replace("[TRUNCATED: content exceeded limit]", "").split()
        for w in words:
            stripped = w.strip("[]:")
            if stripped:
                assert stripped == "word" or stripped == "TRUNCATED" or "content" in stripped or "exceeded" in stripped or "limit" in stripped


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    @pytest.mark.parametrize("text", [
        "Plain safe text.",
        "<script>alert(1)</script> after removal",
        "sk-ABCDEFGHIJKLMNOPQRST key present",
        "```\n<script>code demo</script>\n```",
        "Mixed: <iframe src='x'></iframe> and sk-ABCDEFGHIJKLMNOPQRST",
        "hello " * 200,  # near truncation boundary
        "",
        "No special content here at all.",
        "const x = 42; // normal code",
        "[REDACTED] in text already",
    ])
    def test_idempotent(self, text: str) -> None:
        """sanitize_input applied twice must equal applying it once."""
        first = sanitize_input(text, max_chars=500)
        second = sanitize_input(first.text, max_chars=500)
        assert first.text == second.text, (
            f"Idempotency violation: first={first.text!r}, second={second.text!r}"
        )


# ---------------------------------------------------------------------------
# Combined: multiple rules firing
# ---------------------------------------------------------------------------

class TestCombinedRules:
    def test_xss_and_secret_in_same_text(self) -> None:
        text = (
            "<script>steal()</script>\n"
            "API key: sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
            "Normal content."
        )
        result = sanitize_input(text)
        assert "<script" not in result.text
        assert "sk-ABCDEFGHIJKLM" not in result.text
        assert "[REDACTED]" in result.text
        assert "xss" in result.redacted_kinds
        assert "secret" in result.redacted_kinds
        assert result.redaction_count >= 2

    def test_claim_max_chars_limit(self) -> None:
        """Claims use max_chars=2000 — a 3000-char claim must be truncated."""
        text = "feature " * 400  # 3200 chars
        result = sanitize_input(text, max_chars=2_000)
        assert result.truncated is True
        assert len(result.text) <= 2_100  # truncation marker adds some chars


# ---------------------------------------------------------------------------
# SanitizationResult dataclass
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# SR-02: per-secret redaction observability
# ---------------------------------------------------------------------------


class TestSecretRedactionObservability:
    """SR-02: per-secret logging emits kind+pos, never the secret value."""

    def test_secret_redaction_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging
        key = "sk-ABCDEFGHIJKLMNOPQRST"
        text = f"API key: {key}"
        with caplog.at_level(logging.WARNING, logger="launcher.shared.input_sanitizer"):
            sanitize_input(text)
        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("[Sanitizer] secret redacted" in m for m in warning_messages), (
            f"Expected '[Sanitizer] secret redacted' warning; got: {warning_messages}"
        )
        assert any("kind=sk" in m for m in warning_messages), (
            "Warning must include kind=sk"
        )
        # The secret value must NEVER appear in any log message
        for msg in warning_messages:
            assert "ABCDEFGHIJKLMNOPQRST" not in msg, (
                f"Secret value leaked into log message: {msg!r}"
            )

    def test_secret_log_includes_position(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging
        text = "prefix text " + "sk-ABCDEFGHIJKLMNOPQRST"
        with caplog.at_level(logging.WARNING, logger="launcher.shared.input_sanitizer"):
            sanitize_input(text)
        messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        # pos= should be present (exact value varies but must be non-negative integer)
        assert any("pos=" in m for m in messages)

    def test_clean_input_no_warning_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging
        with caplog.at_level(logging.WARNING, logger="launcher.shared.input_sanitizer"):
            sanitize_input("Plain safe text without any secrets.")
        sanitizer_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING
            and "launcher.shared.input_sanitizer" in r.name
        ]
        assert not sanitizer_warnings


class TestSanitizationResult:
    def test_frozen_dataclass(self) -> None:
        result = SanitizationResult(text="x", redaction_count=0, truncated=False)
        with pytest.raises((AttributeError, TypeError)):
            result.text = "y"  # type: ignore[misc]

    def test_default_redacted_kinds(self) -> None:
        result = SanitizationResult(text="x", redaction_count=0, truncated=False)
        assert result.redacted_kinds == []
