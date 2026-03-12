"""Tests for the claim_leakage evaluation check (CL-03)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.claim_leakage import check_claim_leakage


class TestCheckClaimLeakage:
    """Verify claim ID leakage detection in rendered markdown."""

    def test_bracket_citation_detected(self):
        """Bracket-format [CLM-xxx] in content triggers critical finding."""
        content = "---\ntitle: Test\n---\n\nSome text [CLM-cells-abc123].\n"
        findings = check_claim_leakage(content, "test-page")
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert findings[0].check == "claim_leakage"
        assert "CLM-cells-abc123" in findings[0].message

    def test_multiple_bracket_citations_detected(self):
        """Multiple bracket citations should each produce a finding."""
        content = "---\ntitle: Test\n---\n\nA [CLM-a]. B [CLM-b, CLM-c].\n"
        findings = check_claim_leakage(content, "test-page")
        assert len(findings) == 2

    def test_comment_claim_detected(self):
        """# Claims: CLM-xxx comment in code block triggers critical finding."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "```python\n"
            "# Claims: CLM-cells-abc, CLM-cells-def\n"
            "import foo\n"
            "```\n"
        )
        findings = check_claim_leakage(content, "test-page")
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert "Claims:" in findings[0].message

    def test_clean_content_passes(self):
        """Content without claim IDs should produce no findings."""
        content = "---\ntitle: Test\n---\n\nClean content with no leaked metadata.\n"
        findings = check_claim_leakage(content, "test-page")
        assert len(findings) == 0

    def test_frontmatter_not_scanned(self):
        """Claim-like patterns in frontmatter should not trigger findings."""
        content = "---\ntitle: CLM-test\nclaim_ids: [CLM-abc]\n---\n\nClean body.\n"
        findings = check_claim_leakage(content, "test-page")
        assert len(findings) == 0

    def test_finding_location_is_slug(self):
        """Finding location should be the page slug."""
        content = "---\ntitle: Test\n---\n\nText [CLM-x].\n"
        findings = check_claim_leakage(content, "my-page-slug")
        assert findings[0].location == "my-page-slug"
