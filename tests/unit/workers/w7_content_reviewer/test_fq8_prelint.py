"""Tests for W7 FQ-8 pre-lint detection via shared prelint_fq module.

TC-3500: Validates that W7 technical_accuracy surfaces FQ-8 adjacent-fence
issues using the shared detection function from _shared/prelint_fq.py.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from launch.workers._shared.prelint_fq import detect_adjacent_same_lang_fences


class TestSharedDetectAdjacentFences:
    """Shared detect_adjacent_same_lang_fences() function tests."""

    def test_adjacent_python_fences_detected(self):
        """Two adjacent python blocks produce a detection tuple."""
        content = "# Title\n\n```python\nx = 1\n```\n\n```python\ny = 2\n```\n"
        detections = detect_adjacent_same_lang_fences(content)
        assert len(detections) == 1
        close_line, open_line, lang = detections[0]
        assert lang == "python"
        assert open_line > close_line

    def test_different_languages_clean(self):
        """Python + bash fences produce no detections."""
        content = "```python\nx = 1\n```\n\n```bash\necho hi\n```\n"
        detections = detect_adjacent_same_lang_fences(content)
        assert len(detections) == 0

    def test_prose_between_is_clean(self):
        """Prose between same-language fences prevents detection."""
        content = "```python\nx = 1\n```\n\nSome explanation.\n\n```python\ny = 2\n```\n"
        detections = detect_adjacent_same_lang_fences(content)
        assert len(detections) == 0

    def test_empty_content(self):
        """Empty content produces no detections."""
        assert detect_adjacent_same_lang_fences("") == []


class TestW7FQ8Integration:
    """Verify W7 technical_accuracy._check_fq8_adjacent_fences works."""

    def test_fq8_detected_adjacent_python_fences(self):
        """Adjacent python fences produce a W7-format issue dict."""
        from launch.workers.w7_content_reviewer.checks.technical_accuracy import (
            _check_fq8_adjacent_fences,
        )
        content = "```python\nx = 1\n```\n\n```python\ny = 2\n```\n"
        issues = _check_fq8_adjacent_fences(content, "blog/tutorial.md", "tutorial")
        assert len(issues) == 1
        iss = issues[0]
        assert iss["check"] == "technical_accuracy.fq8_adjacent_fences"
        assert iss["severity"] == "warn"
        assert iss["auto_fixable"] is True
        assert "python" in iss["message"]

    def test_fq8_not_triggered_different_languages(self):
        """Different language fences produce no W7 FQ-8 issues."""
        from launch.workers.w7_content_reviewer.checks.technical_accuracy import (
            _check_fq8_adjacent_fences,
        )
        content = "```python\nx = 1\n```\n\n```bash\necho hi\n```\n"
        issues = _check_fq8_adjacent_fences(content, "docs/api.md", "api")
        assert len(issues) == 0

    def test_fq8_issue_id_uses_slug(self):
        """Issue ID should contain page_slug (not generic 'index')."""
        from launch.workers.w7_content_reviewer.checks.technical_accuracy import (
            _check_fq8_adjacent_fences,
        )
        content = "```python\nx = 1\n```\n\n```python\ny = 2\n```\n"
        issues = _check_fq8_adjacent_fences(content, "blog/python/index.md", "python")
        assert len(issues) == 1
        assert "python" in issues[0]["issue_id"]
        assert "index" not in issues[0]["issue_id"]
