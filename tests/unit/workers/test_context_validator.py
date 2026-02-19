"""Tests for TC-2352/TC-2353: Context sufficiency and page structure validation.

Tests the context_validator module which decides whether a page has enough
claims and snippets to generate quality content for its role, and validates
post-generation structural completeness.
"""

from __future__ import annotations

import pytest

from launch.workers.w5_section_writer.context_validator import (
    ROLE_THRESHOLDS,
    check_context_sufficiency,
    validate_page_structure,
)


def _make_claims(n: int, kind: str = "feature") -> list:
    """Create n dummy claims with given kind."""
    return [
        {"claim_id": f"c{i}", "claim_text": f"Claim {i}", "claim_kind": kind}
        for i in range(n)
    ]


def _make_snippets(n: int) -> list:
    """Create n dummy snippets."""
    return [{"snippet_id": f"s{i}", "code": f"print({i})"} for i in range(n)]


class TestTutorialSufficiency:
    """Tutorial pages require >=3 claims, >=1 snippet, >=1 workflow claim."""

    def test_tutorial_insufficient_no_workflow(self):
        claims = _make_claims(5, kind="feature")  # No workflow claims
        snippets = _make_snippets(2)
        page = {"page_role": "tutorial"}

        ok, reasons, downgrade = check_context_sufficiency(page, claims, snippets)

        assert ok is False
        assert any("workflow" in r for r in reasons)
        assert downgrade == "comprehensive_guide"

    def test_tutorial_sufficient(self):
        claims = _make_claims(2, kind="feature") + _make_claims(1, kind="workflow")
        snippets = _make_snippets(1)
        page = {"page_role": "tutorial"}

        ok, reasons, downgrade = check_context_sufficiency(page, claims, snippets)

        assert ok is True
        assert reasons == []
        assert downgrade is None

    def test_tutorial_insufficient_no_snippets(self):
        claims = _make_claims(2, kind="feature") + _make_claims(1, kind="workflow")
        snippets = []
        page = {"page_role": "tutorial"}

        ok, reasons, downgrade = check_context_sufficiency(page, claims, snippets)

        assert ok is False
        assert any("snippet" in r for r in reasons)


class TestFAQSufficiency:
    """FAQ pages require >=8 claims."""

    def test_faq_sufficient(self):
        claims = _make_claims(10)
        page = {"page_role": "faq"}

        ok, reasons, _ = check_context_sufficiency(page, claims, [])

        assert ok is True

    def test_faq_insufficient(self):
        claims = _make_claims(5)
        page = {"page_role": "faq"}

        ok, reasons, _ = check_context_sufficiency(page, claims, [])

        assert ok is False
        assert any("claims" in r for r in reasons)


class TestLandingSufficiency:
    """Landing pages require >=3 claims, no snippets."""

    def test_landing_sufficient(self):
        claims = _make_claims(3)
        page = {"page_role": "landing"}

        ok, reasons, _ = check_context_sufficiency(page, claims, [])

        assert ok is True

    def test_landing_insufficient(self):
        claims = _make_claims(2)
        page = {"page_role": "landing"}

        ok, reasons, _ = check_context_sufficiency(page, claims, [])

        assert ok is False


class TestDowngradeMapping:
    """Verify downgrade suggestions are correct."""

    def test_tutorial_downgrades_to_comprehensive_guide(self):
        page = {"page_role": "tutorial"}
        _, _, downgrade = check_context_sufficiency(page, [], [])
        assert downgrade == "comprehensive_guide"

    def test_feature_showcase_downgrades_to_landing(self):
        page = {"page_role": "feature_showcase"}
        _, _, downgrade = check_context_sufficiency(page, [], [])
        assert downgrade == "landing"

    def test_workflow_page_downgrades_to_landing(self):
        page = {"page_role": "workflow_page"}
        _, _, downgrade = check_context_sufficiency(page, [], [])
        assert downgrade == "landing"

    def test_comprehensive_guide_downgrades_to_landing(self):
        page = {"page_role": "comprehensive_guide"}
        _, _, downgrade = check_context_sufficiency(page, [], [])
        assert downgrade == "landing"

    def test_unknown_role_uses_defaults(self):
        """Unknown roles use the default threshold (2 claims, 0 snippets)."""
        claims = _make_claims(2)
        page = {"page_role": "some_unknown_role"}

        ok, reasons, _ = check_context_sufficiency(page, claims, [])

        assert ok is True

    def test_sufficient_page_has_no_downgrade(self):
        claims = _make_claims(10) + _make_claims(3, kind="workflow")
        snippets = _make_snippets(2)
        page = {"page_role": "tutorial"}

        ok, reasons, downgrade = check_context_sufficiency(page, claims, snippets)

        assert ok is True
        assert downgrade is None


# ---------------------------------------------------------------------------
# TC-2353: Post-generation page structure validation
# ---------------------------------------------------------------------------

class TestValidatePageStructure:
    """Tests for validate_page_structure()."""

    def test_tutorial_complete(self):
        content = (
            "## Prerequisites\n\nInstall Python.\n\n"
            "## Step-by-Step Guide\n\nDo this.\n\n"
            "```python\nprint('hello')\n```\n"
        )
        missing = validate_page_structure(content, "tutorial")
        assert missing == []

    def test_tutorial_missing_prerequisites(self):
        content = (
            "## Step-by-Step Guide\n\nDo this.\n\n"
            "```python\nprint('hello')\n```\n"
        )
        missing = validate_page_structure(content, "tutorial")
        assert any("Prerequisite" in m for m in missing)

    def test_tutorial_missing_steps(self):
        content = (
            "## Prerequisites\n\nInstall Python.\n\n"
            "```python\nprint('hello')\n```\n"
        )
        missing = validate_page_structure(content, "tutorial")
        assert any("Step" in m for m in missing)

    def test_tutorial_missing_code(self):
        content = (
            "## Prerequisites\n\nInstall Python.\n\n"
            "## Step-by-Step Guide\n\nDo this.\n"
        )
        missing = validate_page_structure(content, "tutorial")
        assert any("code" in m for m in missing)

    def test_faq_sufficient(self):
        qa_blocks = "\n\n".join(
            f"### Q: Question {i}?\n\nAnswer {i}." for i in range(5)
        )
        missing = validate_page_structure(qa_blocks, "faq")
        assert missing == []

    def test_faq_insufficient(self):
        qa_blocks = "\n\n".join(
            f"### Q: Question {i}?\n\nAnswer {i}." for i in range(3)
        )
        missing = validate_page_structure(qa_blocks, "faq")
        assert len(missing) > 0

    def test_comprehensive_guide_sufficient(self):
        content = "## Section 1\nA\n## Section 2\nB\n## Section 3\nC\n"
        missing = validate_page_structure(content, "comprehensive_guide")
        assert missing == []

    def test_comprehensive_guide_insufficient(self):
        content = "## Section 1\nA\n## Section 2\nB\n"
        missing = validate_page_structure(content, "comprehensive_guide")
        assert len(missing) > 0

    def test_unknown_role_always_passes(self):
        missing = validate_page_structure("anything", "some_role_xyz")
        assert missing == []

    def test_workflow_page_needs_code_and_heading(self):
        content = "## Setup\n\nDo this.\n\n```python\ncode()\n```\n"
        missing = validate_page_structure(content, "workflow_page")
        assert missing == []

    def test_workflow_page_missing_code(self):
        content = "## Setup\n\nDo this without code.\n"
        missing = validate_page_structure(content, "workflow_page")
        assert any("code" in m for m in missing)
