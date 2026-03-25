"""TC-5131: Claim authenticity check tests.

Verifies that check_claim_authenticity() detects claims marked as used
whose key terms are absent from page content.
"""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.hallucination_rate import (
    _top_tokens,
    check_claim_authenticity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _claim(cid: str, text: str, confidence: float = 1.0):
    """Create a minimal namespace claim object."""
    class _C:
        pass
    c = _C()
    c.claim_id = cid
    c.text = text
    c.confidence = confidence
    return c


# ---------------------------------------------------------------------------
# _top_tokens tests
# ---------------------------------------------------------------------------

class TestTopTokens:
    """Unit tests for _top_tokens() helper."""

    def test_extracts_longest_tokens(self):
        tokens = _top_tokens("Workbook supports saving to PDF format")
        assert "workbook" in tokens
        assert "supports" in tokens

    def test_excludes_stopwords(self):
        tokens = _top_tokens("the and or of to in for on with at by from")
        assert tokens == []

    def test_excludes_short_tokens(self):
        tokens = _top_tokens("CSV XLS PDF")
        assert tokens == [], "Tokens with len < 4 are excluded"

    def test_respects_n_parameter(self):
        tokens = _top_tokens("Workbook supports saving spreadsheets format", n=2)
        assert len(tokens) <= 2

    def test_deduplicates(self):
        tokens = _top_tokens("workbook workbook workbook format format")
        assert tokens.count("workbook") == 1

    def test_empty_input(self):
        assert _top_tokens("") == []


# ---------------------------------------------------------------------------
# check_claim_authenticity tests
# ---------------------------------------------------------------------------

class TestCheckClaimAuthenticity:
    """TC-5131: check_claim_authenticity() tests."""

    def test_claim_present_in_prose_no_finding(self):
        """Claim whose key terms appear in content produces no finding."""
        claims = {"C1": _claim("C1", "Workbook supports saving to PDF")}
        content = "## Saving\n\nThe Workbook class supports saving documents to PDF format."
        findings = check_claim_authenticity(["C1"], claims, content)
        assert len(findings) == 0

    def test_claim_absent_from_prose_produces_finding(self):
        """Claim whose key terms are missing from content → medium-severity finding."""
        claims = {"C1": _claim("C1", "Workbook supports saving to PDF")}
        content = "## Introduction\n\nThis page covers spreadsheet operations."
        findings = check_claim_authenticity(["C1"], claims, content)
        assert len(findings) == 1
        assert findings[0].check == "claim_authenticity"
        assert findings[0].severity == "medium"
        assert "C1" in findings[0].message

    def test_low_confidence_claim_skipped(self):
        """Claims with confidence < 0.75 are not checked."""
        claims = {"C1": _claim("C1", "Workbook supports saving", confidence=0.5)}
        content = "## Nothing related here."
        findings = check_claim_authenticity(["C1"], claims, content)
        assert len(findings) == 0

    def test_missing_claim_id_skipped(self):
        """Claim ID not in claims_by_id is silently skipped."""
        findings = check_claim_authenticity(["C_MISSING"], {}, "some content")
        assert len(findings) == 0

    def test_empty_content_returns_empty(self):
        """Empty content string returns no findings (guard clause)."""
        claims = {"C1": _claim("C1", "Workbook loading")}
        findings = check_claim_authenticity(["C1"], claims, "")
        assert len(findings) == 0

    def test_empty_claim_ids_returns_empty(self):
        """Empty claim_ids_used returns no findings."""
        findings = check_claim_authenticity([], {"C1": _claim("C1", "test")}, "content")
        assert len(findings) == 0

    def test_frontmatter_stripped_before_check(self):
        """Frontmatter is stripped — terms in frontmatter don't count as present."""
        claims = {"C1": _claim("C1", "Workbook supports spreadsheet operations")}
        content = "---\ntitle: Workbook spreadsheet operations\n---\n\nIntroduction only."
        findings = check_claim_authenticity(["C1"], claims, content)
        # Key terms are in frontmatter only, not body prose → finding expected
        assert len(findings) >= 1

    def test_code_blocks_stripped_before_check(self):
        """Code blocks are stripped — terms in code don't count as present."""
        claims = {"C1": _claim("C1", "Workbook supports spreadsheet loading")}
        content = "## Section\n\nSome text.\n\n```python\nworkbook = Workbook()\nworkbook.load_spreadsheet()\n```"
        findings = check_claim_authenticity(["C1"], claims, content)
        # "workbook" and "spreadsheet" appear in code block only
        # At least one finding expected if stripped properly
        assert len(findings) >= 1

    def test_slug_in_finding_location(self):
        """Finding location contains the slug passed to the function."""
        claims = {"C1": _claim("C1", "Workbook supports spreadsheet operations")}
        content = "## Nothing related."
        findings = check_claim_authenticity(["C1"], claims, content, slug="docs/overview")
        assert len(findings) == 1
        assert findings[0].location == "docs/overview"

    def test_multiple_claims_multiple_findings(self):
        """Multiple uncovered claims produce separate findings."""
        claims = {
            "C1": _claim("C1", "Workbook supports spreadsheet operations"),
            "C2": _claim("C2", "Worksheet provides formula calculation"),
        }
        content = "## Introduction\n\nGeneric paragraph."
        findings = check_claim_authenticity(["C1", "C2"], claims, content)
        assert len(findings) == 2
        checks = {f.message for f in findings}
        assert any("C1" in m for m in checks)
        assert any("C2" in m for m in checks)
