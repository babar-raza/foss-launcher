"""Tests for TC-2893: structured limitations prompt sanitization.

Validates that the structured (JSON) limitations path sanitizes claim text
before injecting into LLM prompts, matching the freeform path's pipeline.
"""

from __future__ import annotations

import pytest

from launch.workers.w5_section_writer.generators.content_generators import (
    _sanitize_claims_for_prompt,
)


def _claim(cid: str, text: str, enriched: str = "") -> dict:
    """Helper to build a minimal claim dict for testing."""
    d = {"claim_id": cid, "claim_text": text}
    if enriched:
        d["enriched_text"] = enriched
    return d


class TestSanitizeClaimsForPrompt:
    """TC-2893: _sanitize_claims_for_prompt replaces raw claim_text injection."""

    def test_prefers_enriched_text(self):
        """enriched_text is used when available, raw claim_text is ignored."""
        claims = [_claim("c1", "raw junk def foo()", "The library does not support feature X.")]
        result = _sanitize_claims_for_prompt(claims)
        assert "feature X" in result
        assert "def foo" not in result

    def test_skips_unsanitizable_claims(self):
        """Claims that fail sanitization are excluded from output."""
        claims = [
            _claim("c1", "```python\nimport os\nos.remove('all')\n```"),
            _claim("c2", "Maximum file size is limited to 500 MB for processing."),
        ]
        result = _sanitize_claims_for_prompt(claims)
        assert "500 MB" in result
        lines = [line for line in result.strip().split("\n") if line.strip()]
        assert len(lines) == 1  # only c2 survived

    def test_truncates_long_bullets(self):
        """Long claims are truncated to respect MAX_BULLET_LEN."""
        # Build a claim with multiple long sentences
        long_text = (
            "The library has a limitation where processing very large documents "
            "that contain thousands of embedded images and complex formatting "
            "may result in significantly increased memory consumption. "
            "This is especially true when working with documents that have "
            "deeply nested table structures and extensive use of custom styles. "
            "Users should consider splitting large documents into smaller chunks."
        )
        claims = [_claim("c1", long_text)]
        result = _sanitize_claims_for_prompt(claims)
        for line in result.strip().split("\n"):
            if line.startswith("- "):
                # MAX_BULLET_LEN = 170; body = 168; full line with "- " = 170
                assert len(line) <= 175  # small tolerance for sentence boundary

    def test_empty_claims_returns_empty(self):
        """Empty claims list returns empty string."""
        result = _sanitize_claims_for_prompt([])
        assert result == ""

    def test_all_claims_rejected_returns_empty(self):
        """Claims that are all too short or empty return empty string."""
        claims = [
            _claim("c1", "x"),   # too short
            _claim("c2", ""),    # empty
            _claim("c3", "ab"),  # too short
        ]
        result = _sanitize_claims_for_prompt(claims)
        assert result == ""

    def test_output_format_is_bullet_list(self):
        """All output lines start with '- ' prefix."""
        claims = [
            _claim("c1", "Maximum file size is limited to 500 MB for processing."),
            _claim("c2", "Thread safety is not guaranteed in all scenarios."),
        ]
        result = _sanitize_claims_for_prompt(claims)
        for line in result.strip().split("\n"):
            assert line.startswith("- ")

    def test_multiple_claims_preserved_order(self):
        """Claims maintain their input order in the output."""
        claims = [
            _claim("c1", "First limitation is about file size constraints."),
            _claim("c2", "Second limitation involves thread safety concerns."),
            _claim("c3", "Third limitation relates to memory consumption issues."),
        ]
        result = _sanitize_claims_for_prompt(claims)
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert "file size" in lines[0].lower() or "first" in lines[0].lower()
        assert "thread" in lines[1].lower() or "second" in lines[1].lower()
        assert "memory" in lines[2].lower() or "third" in lines[2].lower()

    def test_json_blob_claim_rejected(self):
        """Claims containing JSON blobs are sanitized or rejected."""
        claims = [
            _claim("c1", '{"key": "value", "nested": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6}}'),
            _claim("c2", "The API does not support batch operations for large datasets."),
        ]
        result = _sanitize_claims_for_prompt(claims)
        assert '"key"' not in result
        assert "batch operations" in result
