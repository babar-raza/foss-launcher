"""Tests for claim citation and comment stripping in section_validator (P7A-01 G-01)."""

import pytest

from launcher.workers.generate.section_validator import (
    _strip_claim_citations,
    _strip_claim_comments,
)


class TestStripClaimCitations:
    """Tests for _strip_claim_citations() — removes [CLM-xxx] from prose."""

    def test_removes_single_citation(self):
        """Citation [CLM-12345] is removed from prose content."""
        result = _strip_claim_citations("This is some content [CLM-12345]")
        assert "CLM-12345" not in result
        assert "This is some content" in result

    def test_content_without_citations_unchanged(self):
        """Content with no citations is returned unchanged."""
        original = "Clean prose with no citations here."
        assert _strip_claim_citations(original) == original

    def test_citation_mid_line_preserves_surrounding_text(self):
        """Surrounding text is preserved when citation is mid-line."""
        result = _strip_claim_citations("line with [CLM-12345] more text")
        assert "line with" in result
        assert "more text" in result
        assert "CLM-12345" not in result

    def test_removes_multi_claim_citation(self):
        """Multi-claim citations like [CLM-001, CLM-002] are removed."""
        result = _strip_claim_citations("Feature [CLM-001, CLM-002] description")
        assert "CLM-001" not in result
        assert "CLM-002" not in result

    def test_removes_multiple_separate_citations(self):
        """Multiple separate citations on the same line are all removed."""
        result = _strip_claim_citations("A [CLM-001] and B [CLM-002]")
        assert "CLM-001" not in result
        assert "CLM-002" not in result


class TestStripClaimComments:
    """Tests for _strip_claim_comments() — removes # Claims: CLM-xxx from code."""

    def test_removes_claim_comment_line(self):
        """# Claims: CLM-xxx metadata line is removed from code."""
        code = "# Claims: CLM-12345\nprint('hello')"
        result = _strip_claim_comments(code)
        assert "CLM-12345" not in result
        assert "print('hello')" in result

    def test_code_without_comment_unchanged(self):
        """Code with no claim comments is returned unchanged."""
        code = "def foo():\n    return 1"
        assert _strip_claim_comments(code) == code

    def test_both_comment_and_citation_stripped_when_combined(self):
        """Applying both strip functions removes both markers."""
        code = "# Claims: CLM-001\nresult = compute() [CLM-001]"
        step1 = _strip_claim_comments(code)
        step2 = _strip_claim_citations(step1)
        assert "CLM-001" not in step2
        assert "compute()" in step2

    def test_indented_claim_comment_removed(self):
        """Indented # Claims: line is also stripped."""
        code = "    # Claims: CLM-999\n    x = 1"
        result = _strip_claim_comments(code)
        assert "CLM-999" not in result
        assert "x = 1" in result

    def test_code_block_with_no_citation_unchanged(self):
        """Code block with neither citation nor comment is unchanged."""
        code = "import os\npath = os.getcwd()\nprint(path)"
        assert _strip_claim_comments(code) == code
        assert _strip_claim_citations(code) == code
