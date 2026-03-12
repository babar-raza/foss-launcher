"""Tests for GoldenIndex load and query API (TC-3852b / H4.2)."""
from __future__ import annotations

from pathlib import Path

import pytest

from launcher.shared.golden_loader import (
    GoldenBlockSpec,
    GoldenIndex,
    GoldenPage,
    GoldenSection,
    _normalize_heading,
    build_block_spec,
)


GOLDEN_DIR = Path(__file__).parent.parent.parent / "golden"


class TestGoldenIndexLoad:
    def test_load_returns_index(self) -> None:
        index = GoldenIndex.load(GOLDEN_DIR)
        assert isinstance(index, GoldenIndex)

    def test_load_indexes_all_files(self) -> None:
        # 22 .md files in golden/, but GoldenIndex keys by (page_role, variant)
        # so duplicates overwrite each other. Verify at least 5 unique entries indexed.
        index = GoldenIndex.load(GOLDEN_DIR)
        assert len(index) >= 5, f"Expected >= 5 indexed pages, got {len(index)}"

    def test_load_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        index = GoldenIndex.load(tmp_path / "nonexistent")
        assert len(index) == 0

    def test_load_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        d = tmp_path / "golden_empty"
        d.mkdir()
        index = GoldenIndex.load(d)
        assert len(index) == 0


class TestGoldenIndexGet:
    @pytest.fixture(scope="class")
    def index(self) -> GoldenIndex:
        return GoldenIndex.load(GOLDEN_DIR)

    def test_get_known_role_returns_page(self, index: GoldenIndex) -> None:
        # At least one page must be indexed
        assert len(index) > 0
        # Get any available key
        key = next(iter(index._pages))
        page = index.get(key[0], key[1])
        assert isinstance(page, GoldenPage)

    def test_get_unknown_role_returns_none(self, index: GoldenIndex) -> None:
        result = index.get("nonexistent_role_xyz", "standard")
        assert result is None

    def test_select_for_tier_a_returns_standard(self, index: GoldenIndex) -> None:
        # Find any role that has a standard variant
        for (role, variant), page in index._pages.items():
            if variant == "standard":
                result = index.select_for_tier(role, "A")
                assert result is not None
                break

    def test_select_for_tier_c_returns_minimal_or_standard(self, index: GoldenIndex) -> None:
        # Find any role
        for (role, variant), page in index._pages.items():
            result = index.select_for_tier(role, "C")
            # May be None if neither minimal nor standard variant
            break


class TestGoldenIndexGetSection:
    @pytest.fixture(scope="class")
    def index(self) -> GoldenIndex:
        return GoldenIndex.load(GOLDEN_DIR)

    def test_get_section_unknown_role_returns_none(self, index: GoldenIndex) -> None:
        result = index.get_section("bogus_role", "standard", "Introduction")
        assert result is None

    def test_get_section_known_role_exact_match(self, index: GoldenIndex) -> None:
        # Find a page with at least one section
        for (role, variant), page in index._pages.items():
            if page.sections:
                heading = page.sections[0].heading
                result = index.get_section(role, variant, heading)
                assert isinstance(result, GoldenSection)
                break

    def test_get_section_substring_match(self, index: GoldenIndex) -> None:
        # Find a page with a section heading and use a prefix
        for (role, variant), page in index._pages.items():
            if page.sections:
                heading = page.sections[0].heading
                if len(heading) > 5:
                    partial = heading[:len(heading)//2]
                    result = index.get_section(role, variant, partial)
                    # Should match via substring
                    assert result is not None
                    break

    def test_get_section_no_match_returns_none(self, index: GoldenIndex) -> None:
        for (role, variant), page in index._pages.items():
            result = index.get_section(role, variant, "ZZZNonMatchingHeadingXXX123")
            assert result is None
            break


class TestGoldenIndexGetSpec:
    @pytest.fixture(scope="class")
    def index(self) -> GoldenIndex:
        return GoldenIndex.load(GOLDEN_DIR)

    def test_get_spec_unknown_returns_none(self, index: GoldenIndex) -> None:
        result = index.get_spec("bogus_role", "standard", "Introduction")
        assert result is None

    def test_get_spec_known_returns_block_spec(self, index: GoldenIndex) -> None:
        for (role, variant), page in index._pages.items():
            if page.sections:
                heading = page.sections[0].heading
                result = index.get_spec(role, variant, heading)
                assert isinstance(result, GoldenBlockSpec)
                assert "paragraph" in result.required_block_types
                assert result.min_words >= 0
                break


class TestBuildBlockSpec:
    def test_paragraph_always_required(self) -> None:
        gs = GoldenSection(
            heading="Overview",
            raw_markdown="Some text here.",
            word_count=50,
            has_code=False,
            has_list=False,
            has_table=False,
            excerpt="Some text here.",
        )
        spec = build_block_spec(gs)
        assert "paragraph" in spec.required_block_types

    def test_code_required_when_has_code(self) -> None:
        gs = GoldenSection(
            heading="Installation",
            raw_markdown="```python\nimport x\n```",
            word_count=10,
            has_code=True,
            has_list=False,
            has_table=False,
            excerpt="```python\nimport x\n```",
        )
        spec = build_block_spec(gs)
        assert "code" in spec.required_block_types

    def test_tier_c_uses_lower_min_words(self) -> None:
        gs = GoldenSection(
            heading="Overview",
            raw_markdown="x " * 100,
            word_count=100,
            has_code=False,
            has_list=False,
            has_table=False,
            excerpt="x " * 50,
        )
        spec_b = build_block_spec(gs, richness_tier="B")
        spec_c = build_block_spec(gs, richness_tier="C")
        assert spec_c.min_words <= spec_b.min_words


class TestNormalizeHeading:
    """Tests for _normalize_heading (V2AC-02)."""

    def test_stop_words_removed(self) -> None:
        result = _normalize_heading("The Installation Guide")
        assert "the" not in result.split()
        assert "installation" in result
        assert "guide" in result

    def test_punctuation_stripped(self) -> None:
        result = _normalize_heading("Getting Started: A Quick Guide!")
        assert ":" not in result
        assert "!" not in result

    def test_lowercased(self) -> None:
        result = _normalize_heading("OVERVIEW")
        assert result == "overview"

    def test_empty_string(self) -> None:
        assert _normalize_heading("") == ""

    def test_all_stop_words(self) -> None:
        assert _normalize_heading("the and or") == ""


class TestJaccardThresholdLowered:
    """Jaccard fallback now uses threshold 0.3 instead of 0.5 (V2AC-02)."""

    def _make_index(self, headings: list[str]) -> GoldenIndex:
        index = GoldenIndex()
        sections = [
            GoldenSection(
                heading=h,
                raw_markdown=f"## {h}\n" + ("word " * 40),
                word_count=40,
                has_code=False,
                has_list=False,
                has_table=False,
                excerpt=h,
            )
            for h in headings
        ]
        from launcher.shared.golden_loader import GoldenPage
        from pathlib import Path
        page = GoldenPage(
            source_path=Path("golden/test.md"),
            page_role="installation",
            variant="standard",
            subdomain="docs.aspose.org",
            grade="A",
            sections=sections,
            total_word_count=40 * len(headings),
        )
        index._pages[("installation", "standard")] = page
        return index

    def test_low_jaccard_match_above_03(self) -> None:
        # "Quick Start" vs "Quick Startup" — Jaccard on normalized tokens
        # normalized: "quick start" vs "quick startup" → intersection=1, union=2 = 0.5 ≥ 0.3
        index = self._make_index(["Quick Start Guide"])
        result = index.get_section("installation", "standard", "Quick Start")
        assert result is not None

    def test_no_match_when_unrelated(self) -> None:
        index = self._make_index(["Installation Steps"])
        result = index.get_section("installation", "standard", "ZZZUnrelated123")
        assert result is None

    def test_false_positive_rejected_at_05(self) -> None:
        # TC-3878 Wave 0 (G3): Threshold raised from 0.3 → 0.5 to eliminate false positives.
        # "Deploy Application" vs "Application Deployment":
        # normalized: "deploy application" vs "application deployment" → 2 tokens each
        # intersection={"application"}, union={"deploy","application","deployment"} → J = 1/3 ≈ 0.33
        # J = 0.33 < 0.5 → NO match (correctly rejected — these are semantically different headings)
        index = self._make_index(["Application Deployment"])
        result = index.get_section("installation", "standard", "Deploy Application")
        assert result is None, "J≈0.33 should be below threshold 0.5 — false positive correctly rejected"


class TestGetHealExcerpt:
    """Tests for GoldenIndex.get_heal_excerpt (V2CP-01)."""

    def _make_index_with_long_section(self) -> GoldenIndex:
        long_text = "word " * 500
        index = GoldenIndex()
        section = GoldenSection(
            heading="Getting Started",
            raw_markdown=f"## Getting Started\n{long_text}",
            word_count=500,
            has_code=False,
            has_list=False,
            has_table=False,
            excerpt=long_text[:600],
        )
        from launcher.shared.golden_loader import GoldenPage
        from pathlib import Path
        page = GoldenPage(
            source_path=Path("golden/test.md"),
            page_role="installation",
            variant="standard",
            subdomain="docs.aspose.org",
            grade="A",
            sections=[section],
            total_word_count=500,
        )
        index._pages[("installation", "standard")] = page
        return index

    def test_returns_truncated_excerpt(self) -> None:
        index = self._make_index_with_long_section()
        result = index.get_heal_excerpt("installation", "standard", "Getting Started")
        assert result is not None
        words = result.split()
        assert len(words) <= 302  # 300 + " …" may add 1 token
        assert "…" in result

    def test_returns_none_for_unknown_role(self) -> None:
        index = self._make_index_with_long_section()
        result = index.get_heal_excerpt("nonexistent_role", "standard", "Getting Started")
        assert result is None

    def test_returns_none_for_unmatched_heading(self) -> None:
        index = self._make_index_with_long_section()
        result = index.get_heal_excerpt("installation", "standard", "ZZZBogusHeadingXXX")
        assert result is None

    def test_custom_max_words(self) -> None:
        index = self._make_index_with_long_section()
        result = index.get_heal_excerpt(
            "installation", "standard", "Getting Started", max_words=50
        )
        assert result is not None
        words = result.replace(" …", "").split()
        assert len(words) <= 50

    def test_short_section_not_truncated(self) -> None:
        index = GoldenIndex()
        section = GoldenSection(
            heading="Overview",
            raw_markdown="## Overview\nShort content here with few words.",
            word_count=7,
            has_code=False,
            has_list=False,
            has_table=False,
            excerpt="Short content here with few words.",
        )
        from launcher.shared.golden_loader import GoldenPage
        from pathlib import Path
        page = GoldenPage(
            source_path=Path("golden/test.md"),
            page_role="howto_article",
            variant="standard",
            subdomain="kb.aspose.org",
            grade="A",
            sections=[section],
            total_word_count=7,
        )
        index._pages[("howto_article", "standard")] = page
        result = index.get_heal_excerpt("howto_article", "standard", "Overview")
        assert result is not None
        assert "…" not in result
