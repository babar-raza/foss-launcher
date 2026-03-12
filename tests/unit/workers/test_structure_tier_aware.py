"""Tests for TC-HO-08C: tier-aware structure check (heading density)."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.structure import check_structure


def _make_page_with_words_and_h2s(word_count: int, h2_count: int) -> str:
    """Build a markdown page with the given word count and H2 section count."""
    filler_per_section = word_count // max(h2_count, 1) + 1
    parts = ["---\ntitle: Test\n---\n\n"]
    for i in range(h2_count):
        parts.append(f"## Section {i + 1}\n\n")
        parts.append(" ".join(["word"] * filler_per_section) + "\n\n")
    if h2_count == 0:
        # No sections — add content directly
        parts.append(" ".join(["word"] * word_count) + "\n\n## Only Heading\n\n")
        parts.append(" ".join(["word"] * 10) + "\n")
    return "".join(parts)


class TestTierAwareStructure:

    def test_tier_a_700_words_0_h2_produces_finding(self):
        # 700 words, only 1 H2 but that is already the structural section — build 0 extra
        # Use the "## Only Heading" trick and ensure word count is over 500
        content = (
            "---\ntitle: T\n---\n\n"
            + " ".join(["word"] * 700)
            + "\n\n## Only H2\n\nsome words\n"
        )
        findings = check_structure(content, "slug", richness_tier="A")
        structure_findings = [f for f in findings if "Insufficient structure" in f.message]
        assert len(structure_findings) >= 1

    def test_tier_c_700_words_1_h2_no_finding(self):
        # Tier C: threshold is 1000 words — 700 words should NOT trigger the check
        content = (
            "---\ntitle: T\n---\n\n"
            + " ".join(["word"] * 700)
            + "\n\n## Section One\n\nsome words\n"
        )
        findings = check_structure(content, "slug", richness_tier="C")
        structure_findings = [f for f in findings if "Insufficient structure" in f.message]
        assert len(structure_findings) == 0

    def test_tier_c_1100_words_0_h2_produces_finding(self):
        # Tier C: 1000+ words with 0 H2s should still trigger
        content = (
            "---\ntitle: T\n---\n\n"
            + " ".join(["word"] * 1100)
            + "\n\n## Only Section\n\none word\n"
        )
        findings = check_structure(content, "slug", richness_tier="C")
        # 1100 > 1000 and h2_count == 1 which satisfies >=1, so no finding
        # (Tier C requires >=1 H2; we have 1, so no finding)
        structure_findings = [f for f in findings if "Insufficient structure" in f.message]
        assert len(structure_findings) == 0

    def test_tier_c_1100_words_0_h2_produces_finding_when_no_sections(self):
        # Tier C: 1000+ words and 0 H2s → finding
        # Build a page with only an H3 (no H2)
        content = (
            "---\ntitle: T\n---\n\n"
            + " ".join(["word"] * 1100)
            + "\n\n### Not an H2\n\nsome words\n"
        )
        findings = check_structure(content, "slug", richness_tier="C")
        structure_findings = [f for f in findings if "Insufficient structure" in f.message]
        assert len(structure_findings) >= 1

    def test_tier_b_500_words_1_h2_no_finding(self):
        # Tier B: >= 500 words with 1 H2 → passes (requires >=1 H2)
        content = (
            "---\ntitle: T\n---\n\n"
            + " ".join(["word"] * 550)
            + "\n\n## Section One\n\nsome words\n"
        )
        findings = check_structure(content, "slug", richness_tier="B")
        structure_findings = [f for f in findings if "Insufficient structure" in f.message]
        assert len(structure_findings) == 0

    def test_tier_a_500_words_1_h2_produces_finding(self):
        # Tier A: >= 500 words with only 1 H2 → needs >=2
        content = (
            "---\ntitle: T\n---\n\n"
            + " ".join(["word"] * 550)
            + "\n\n## Only One\n\nsome words\n"
        )
        findings = check_structure(content, "slug", richness_tier="A")
        structure_findings = [f for f in findings if "Insufficient structure" in f.message]
        assert len(structure_findings) >= 1

    def test_default_tier_a_backward_compat(self):
        """Default richness_tier="A" preserves original threshold (500 words, 2 H2s)."""
        content = (
            "---\ntitle: T\n---\n\n"
            + " ".join(["word"] * 550)
            + "\n\n## Only One\n\nsome words\n"
        )
        findings_default = check_structure(content, "slug")
        findings_a = check_structure(content, "slug", richness_tier="A")
        default_msgs = sorted(f.message for f in findings_default)
        a_msgs = sorted(f.message for f in findings_a)
        assert default_msgs == a_msgs

    def test_unknown_tier_falls_back_to_tier_a(self):
        content = (
            "---\ntitle: T\n---\n\n"
            + " ".join(["word"] * 550)
            + "\n\n## Only One\n\nsome words\n"
        )
        findings_unknown = check_structure(content, "slug", richness_tier="X")
        findings_a = check_structure(content, "slug", richness_tier="A")
        unknown_msgs = sorted(f.message for f in findings_unknown)
        a_msgs = sorted(f.message for f in findings_a)
        assert unknown_msgs == a_msgs

    def test_other_checks_still_run_regardless_of_tier(self):
        """Template-label headings and H1 checks run for all tiers."""
        content = "---\ntitle: T\n---\n\n# Bad H1\n\n## [section title]\n\nwords\n"
        for tier in ("A", "B", "C"):
            findings = check_structure(content, "slug", richness_tier=tier)
            h1_findings = [f for f in findings if "H1" in f.message]
            label_findings = [f for f in findings if "Template-label" in f.message]
            assert len(h1_findings) >= 1, f"Tier {tier}: H1 check should run"
            assert len(label_findings) >= 1, f"Tier {tier}: template-label check should run"
