"""Tests for TC-HO-08B: tier-aware density check thresholds."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.density import check_density


def _make_page(total_words: int) -> str:
    """Build a minimal markdown page with approximately ``total_words`` prose words.

    All words placed in a single section to simplify total-word counting.
    """
    # Put all words inside a section (section prose contributes to total word count)
    section_filler = " ".join(["word"] * total_words)
    return (
        "---\ntitle: Test\n---\n\n"
        f"## Section One\n\n{section_filler}\n"
    )


def _make_sparse_section_page(section_words: int) -> str:
    """Build a page with many page-level words and a specific number of section words."""
    # First section: large enough to pass page-level check
    page_filler = " ".join(["word"] * 200)
    section_filler = " ".join(["word"] * section_words)
    return (
        "---\ntitle: Test\n---\n\n"
        f"## Large Section\n\n{page_filler}\n\n"
        f"## Short Section\n\n{section_filler}\n"
    )


class TestTierAwareDensity:

    def test_tier_a_60_words_produces_finding(self):
        # 60 total words < Tier A minimum (100) → finding expected
        content = _make_page(60)
        findings = check_density(content, "test-page", page_role="howto_article", richness_tier="A")
        density_findings = [f for f in findings if f.check == "density" and "minimum" in f.message.lower()]
        assert len(density_findings) >= 1

    def test_tier_c_60_words_no_page_finding(self):
        # 60 words >= Tier C minimum (50) → no page-level finding
        content = _make_page(60)
        findings = check_density(content, "test-page", page_role="howto_article", richness_tier="C")
        page_density = [
            f for f in findings
            if f.check == "density"
            and "minimum" in f.message.lower()
        ]
        assert len(page_density) == 0

    def test_tier_c_40_words_produces_finding(self):
        # 40 words < Tier C minimum (50) → finding expected
        content = _make_page(40)
        findings = check_density(content, "test-page", page_role="howto_article", richness_tier="C")
        page_density = [
            f for f in findings
            if f.check == "density"
            and "minimum" in f.message.lower()
        ]
        assert len(page_density) >= 1

    def test_tier_b_85_words_no_finding(self):
        # 85 words >= Tier B minimum (80) → no page-level finding
        content = _make_page(85)
        findings = check_density(content, "test-page", page_role="howto_article", richness_tier="B")
        page_density = [
            f for f in findings
            if f.check == "density"
            and "minimum" in f.message.lower()
        ]
        assert len(page_density) == 0

    def test_tier_a_section_12_words_produces_finding(self):
        # 12 section words < Tier A section minimum (20) → finding
        content = _make_sparse_section_page(12)
        findings = check_density(content, "test-page", richness_tier="A")
        section_findings = [f for f in findings if f.check == "density" and "Section" in f.message]
        assert len(section_findings) >= 1

    def test_tier_c_12_words_no_section_finding(self):
        # 12 section words >= Tier C section minimum (10) → no finding
        content = _make_sparse_section_page(12)
        findings = check_density(content, "test-page", richness_tier="C")
        section_findings = [f for f in findings if f.check == "density" and "Section" in f.message]
        assert len(section_findings) == 0

    def test_default_tier_a_backward_compat(self):
        """Default richness_tier="A" preserves original behaviour."""
        content = _make_page(60)
        findings_default = check_density(content, "test-page")
        findings_explicit_a = check_density(content, "test-page", richness_tier="A")
        # Both should produce the same set of density findings
        default_msgs = sorted(f.message for f in findings_default if f.check == "density")
        explicit_msgs = sorted(f.message for f in findings_explicit_a if f.check == "density")
        assert default_msgs == explicit_msgs

    def test_unknown_tier_falls_back_to_tier_a(self):
        """Unknown tier string falls back to Tier A thresholds."""
        content = _make_page(60)
        findings_unknown = check_density(content, "test-page", richness_tier="Z")
        findings_a = check_density(content, "test-page", richness_tier="A")
        unknown_msgs = sorted(f.message for f in findings_unknown if f.check == "density")
        a_msgs = sorted(f.message for f in findings_a if f.check == "density")
        assert unknown_msgs == a_msgs

    def test_placeholder_detection_always_runs(self):
        """Placeholder detection is not skipped for any tier."""
        content = "---\ntitle: T\n---\n\n## Section\n\n[todo] some content here\n"
        for tier in ("A", "B", "C"):
            findings = check_density(content, "slug", richness_tier=tier)
            ph = [f for f in findings if "placeholder" in f.message.lower() or "[todo]" in f.message.lower()]
            assert len(ph) >= 1, f"Tier {tier}: placeholder should always be detected"
