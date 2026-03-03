"""Tests for SLUG_FILLER_PREFIX detection in gate_slug_safety (TC-3651).

Validates that gate_slug_safety detects slugs with 2+ consecutive leading
filler/stop-words as a safety net for slugs that bypass LLM refinement.
"""

from __future__ import annotations

import pytest

from src.launch.workers.w9_validator.gates.gate_slug_safety import _check_slug


class TestSlugFillerPrefix:
    """Gate detects 2+ leading filler words in a slug."""

    def test_two_leading_filler_words_flagged(self):
        """Slug 'you-can-create-rules' has 2 leading fillers → issue."""
        issues = []
        _check_slug("you-can-create-rules", "", "ci", issues)
        filler_issues = [i for i in issues if i["error_code"] == "SLUG_FILLER_PREFIX"]
        assert len(filler_issues) == 1
        assert filler_issues[0]["severity"] == "error"

    def test_one_leading_filler_word_ok(self):
        """Slug 'the-convert-tool' has 1 leading filler → no SLUG_FILLER_PREFIX."""
        issues = []
        _check_slug("the-convert-tool", "", "ci", issues)
        filler_issues = [i for i in issues if i["error_code"] == "SLUG_FILLER_PREFIX"]
        assert len(filler_issues) == 0

    def test_no_filler_words_ok(self):
        """Slug 'convert-3d-models' has 0 leading fillers → no issue."""
        issues = []
        _check_slug("convert-3d-models", "", "ci", issues)
        filler_issues = [i for i in issues if i["error_code"] == "SLUG_FILLER_PREFIX"]
        assert len(filler_issues) == 0

    def test_filler_prefix_severity_prod(self):
        """Profile 'prod' → severity 'blocker'."""
        issues = []
        _check_slug("you-can-create-rules", "", "prod", issues)
        filler_issues = [i for i in issues if i["error_code"] == "SLUG_FILLER_PREFIX"]
        assert filler_issues[0]["severity"] == "blocker"

    def test_filler_prefix_severity_local(self):
        """Profile 'local' → severity 'warn'."""
        issues = []
        _check_slug("you-can-create-rules", "", "local", issues)
        filler_issues = [i for i in issues if i["error_code"] == "SLUG_FILLER_PREFIX"]
        assert filler_issues[0]["severity"] == "warn"
