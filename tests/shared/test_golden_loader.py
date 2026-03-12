"""Tests for GoldenIndex -- TC-3833, GL-01, GL-02."""
import pytest
from pathlib import Path
from unittest.mock import patch
from launcher.shared.golden_loader import (
    GoldenIndex, GoldenBlockSpec, GoldenSection, build_block_spec,
    _load_golden_for_role, _get_cached_index, _clear_golden_cache,
)


GOLDEN_DIR = Path("golden")


@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_load_indexes_files():
    index = GoldenIndex.load(GOLDEN_DIR)
    assert len(index) >= 1, "Expected at least one indexed golden file"


def test_load_missing_dir_returns_empty():
    index = GoldenIndex.load(Path("nonexistent_golden_dir_xyz"))
    assert len(index) == 0


def test_get_returns_none_for_unknown_role():
    index = GoldenIndex.load(Path("nonexistent_golden_dir_xyz"))
    assert index.get("workflow_page", "standard") is None


def test_get_section_no_match_returns_none():
    index = GoldenIndex.load(Path("nonexistent_golden_dir_xyz"))
    result = index.get_section("workflow_page", "standard", "Quick Start")
    assert result is None


def test_build_block_spec_with_code():
    gs = GoldenSection(
        heading="Usage Examples",
        raw_markdown="## Usage Examples\n```python\nfoo()\n```\n",
        word_count=50,
        has_code=True,
        has_list=False,
        has_table=False,
        excerpt="## Usage Examples\n```python\nfoo()\n```\n",
    )
    spec = build_block_spec(gs)
    assert "code" in spec.required_block_types
    assert "paragraph" in spec.required_block_types


def test_build_block_spec_tier_c_min_words():
    gs = GoldenSection(
        heading="Overview",
        raw_markdown="## Overview\nSome text here.\n",
        word_count=100,
        has_code=False, has_list=False, has_table=False,
        excerpt="## Overview\nSome text here.\n",
    )
    spec_c = build_block_spec(gs, richness_tier="C")
    spec_b = build_block_spec(gs, richness_tier="B")
    assert spec_c.min_words < spec_b.min_words


def test_select_for_tier_c_prefers_minimal():
    # Without actual files, verify logic: if minimal absent, returns None
    index = GoldenIndex()
    result = index.select_for_tier("workflow_page", "C")
    assert result is None


# ---------------------------------------------------------------------------
# TC-3842: _load_golden_for_role heal wrapper
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_load_golden_for_role_returns_text():
    from launcher.shared.golden_loader import _load_golden_for_role
    result = _load_golden_for_role("workflow_page", GOLDEN_DIR)
    # workflow_page is one of the 7 indexed pages
    assert result is not None
    assert len(result.split()) <= 501  # 500 words + ellipsis


def test_load_golden_for_role_missing_dir():
    from launcher.shared.golden_loader import _load_golden_for_role
    result = _load_golden_for_role("workflow_page", Path("nonexistent_golden_dir_xyz/"))
    assert result is None


def test_load_golden_for_role_unknown_role():
    from launcher.shared.golden_loader import _load_golden_for_role
    result = _load_golden_for_role("no_such_role_xyz", GOLDEN_DIR)
    assert result is None


def test_load_golden_for_role_truncates():
    result = _load_golden_for_role("workflow_page", GOLDEN_DIR, max_words=5)
    if result is not None:
        word_count = len(result.split())
        assert word_count <= 6  # 5 words + ellipsis


# ---------------------------------------------------------------------------
# GL-01: LRU cache tests
# ---------------------------------------------------------------------------

class TestGL01LRUCache:
    """GL-01: _load_golden_for_role must use LRU cache to avoid re-parsing files."""

    def setup_method(self):
        """Clear cache before each test for isolation."""
        _clear_golden_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        _clear_golden_cache()

    def test_load_golden_for_role_cached(self, tmp_path):
        """GoldenIndex.load called only once for repeated calls with same dir."""
        load_calls = []
        original_load = GoldenIndex.load

        def counting_load(golden_dir):
            load_calls.append(golden_dir)
            return original_load(golden_dir)

        _clear_golden_cache()
        with patch.object(GoldenIndex, "load", side_effect=counting_load):
            # Two calls with same dir — should only trigger one load
            _load_golden_for_role("workflow_page", tmp_path)
            _load_golden_for_role("workflow_page", tmp_path)
        assert len(load_calls) == 1, (
            f"Expected 1 GoldenIndex.load call, got {len(load_calls)}. "
            "LRU cache not working."
        )

    def test_different_dirs_get_separate_cache_entries(self, tmp_path):
        """Different golden_dir paths result in separate cache entries (2 loads)."""
        dir_a = tmp_path / "golden_a"
        dir_a.mkdir()
        dir_b = tmp_path / "golden_b"
        dir_b.mkdir()

        load_calls = []
        original_load = GoldenIndex.load

        def counting_load(golden_dir):
            load_calls.append(str(golden_dir))
            return original_load(golden_dir)

        _clear_golden_cache()
        with patch.object(GoldenIndex, "load", side_effect=counting_load):
            _load_golden_for_role("workflow_page", dir_a)
            _load_golden_for_role("workflow_page", dir_b)
        assert len(load_calls) == 2, "Different dirs must produce separate cache entries"

    def test_cache_clear_forces_reload(self, tmp_path):
        """After _clear_golden_cache(), next call triggers a fresh GoldenIndex.load."""
        load_calls = []
        original_load = GoldenIndex.load

        def counting_load(golden_dir):
            load_calls.append(golden_dir)
            return original_load(golden_dir)

        _clear_golden_cache()
        with patch.object(GoldenIndex, "load", side_effect=counting_load):
            _load_golden_for_role("workflow_page", tmp_path)
            _clear_golden_cache()
            _load_golden_for_role("workflow_page", tmp_path)
        assert len(load_calls) == 2, "Cache clear must force a reload on next access"

    def test_get_cached_index_is_lru_cached(self):
        """_get_cached_index must expose a cache_clear method (is lru_cache)."""
        assert hasattr(_get_cached_index, "cache_clear"), (
            "_get_cached_index must be decorated with functools.lru_cache"
        )
        assert hasattr(_get_cached_index, "cache_info"), (
            "_get_cached_index must expose cache_info"
        )


# ---------------------------------------------------------------------------
# GL-02: Jaccard threshold constant + grade parsing tests
# ---------------------------------------------------------------------------

class TestGL02JaccardAndGrade:
    """GL-02: _SECTION_JACCARD_THRESHOLD constant + grade parsed from frontmatter."""

    def test_jaccard_threshold_constant_exists(self):
        """_SECTION_JACCARD_THRESHOLD must be a module-level constant equal to 0.5."""
        import launcher.shared.golden_loader as gl_module
        assert hasattr(gl_module, "_SECTION_JACCARD_THRESHOLD"), (
            "_SECTION_JACCARD_THRESHOLD must be at module level"
        )
        assert gl_module._SECTION_JACCARD_THRESHOLD == 0.5

    def test_jaccard_used_in_get_section(self, tmp_path):
        """Patching _SECTION_JACCARD_THRESHOLD to 0.99 must block Jaccard-only matches.

        Uses "Install Python Library" vs "Install Python Package" — these share
        "install" and "python" but are not substrings of each other, so only
        Jaccard level-3 can match them.
        Jaccard = 2/4 = 0.5 (≥ 0.5 passes at default threshold; < 0.99 blocks).
        Both headings have 3 normalized tokens, satisfying _JACCARD_MIN_TOKENS=2.
        """
        import launcher.shared.golden_loader as gl_module
        # Golden section heading: "Install Python Library"
        section = GoldenSection(
            heading="Install Python Library",
            raw_markdown="## Install Python Library\nSome detailed installation text here.",
            word_count=9,
            has_code=False, has_list=False, has_table=False,
            excerpt="## Install Python Library\nSome detailed installation text here.",
        )
        from launcher.shared.golden_loader import GoldenPage
        page = GoldenPage(
            source_path=tmp_path / "test.md",
            page_role="workflow_page",
            variant="standard",
            subdomain="docs.aspose.org",
            grade="A",
            sections=[section],
            total_word_count=9,
        )
        index = GoldenIndex()
        index._pages[("workflow_page", "standard")] = page

        # "Install Python Package" vs "Install Python Library":
        # Level 1: normalized differ — no exact match
        # Level 2: neither is substring of the other — no substring match
        # Level 3: Jaccard on {"install","python","package"} vs {"install","python","library"}
        #   = 2/4 = 0.5
        #   At threshold 0.5: 0.5 ≥ 0.5 → match
        #   At threshold 0.99: 0.5 < 0.99 → no match
        result_low = index.get_section("workflow_page", "standard", "Install Python Package")
        # Verify it matched at the default threshold
        assert result_low is not None, (
            "'Install Python Package' vs 'Install Python Library' (Jaccard=0.5) "
            "must match at threshold=0.5"
        )

        # Now patch threshold to 0.99 — Jaccard match blocked
        with patch.object(gl_module, "_SECTION_JACCARD_THRESHOLD", 0.99):
            result_high = index.get_section("workflow_page", "standard", "Install Python Package")

        assert result_high is None, (
            "With threshold=0.99, Jaccard=0.5 must not match"
        )

    def test_grade_parsed_from_frontmatter_b(self, tmp_path):
        """Golden file with grade: B in frontmatter → page.grade == 'B'."""
        md_content = "---\ntitle: Test\ngrade: B\n---\n## Overview\nSome text here for testing.\n"
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        from launcher.shared.golden_loader import _parse_golden_file
        page = _parse_golden_file(md_file, tmp_path)
        assert page is not None
        assert page.grade == "B", f"Expected grade 'B', got '{page.grade}'"

    def test_grade_defaults_to_a_when_absent(self, tmp_path):
        """Golden file with no grade: field → page.grade == 'A'."""
        md_content = "---\ntitle: Test\n---\n## Overview\nSome text here for testing.\n"
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        from launcher.shared.golden_loader import _parse_golden_file
        page = _parse_golden_file(md_file, tmp_path)
        assert page is not None
        assert page.grade == "A", f"Expected default grade 'A', got '{page.grade}'"

    def test_grade_defaults_to_a_when_invalid(self, tmp_path):
        """Golden file with grade: X (invalid) → page.grade == 'A' (safe fallback)."""
        md_content = "---\ntitle: Test\ngrade: X\n---\n## Overview\nSome text here for testing.\n"
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        from launcher.shared.golden_loader import _parse_golden_file
        page = _parse_golden_file(md_file, tmp_path)
        assert page is not None
        assert page.grade == "A", f"Invalid grade 'X' must fall back to 'A', got '{page.grade}'"

    def test_grade_defaults_to_a_when_no_frontmatter(self, tmp_path):
        """Golden file with no frontmatter block → page.grade == 'A'."""
        md_content = "## Overview\nSome text here for testing purposes.\n"
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        from launcher.shared.golden_loader import _parse_golden_file
        page = _parse_golden_file(md_file, tmp_path)
        # File may have no sections (no frontmatter case), grade should default to A
        if page is not None:
            assert page.grade == "A"

    def test_grade_c_parsed_correctly(self, tmp_path):
        """Golden file with grade: C → page.grade == 'C'."""
        md_content = "---\ntitle: Test\ngrade: C\n---\n## Overview\nSome text here for testing.\n"
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        from launcher.shared.golden_loader import _parse_golden_file
        page = _parse_golden_file(md_file, tmp_path)
        assert page is not None
        assert page.grade == "C"


# ---------------------------------------------------------------------------
# TC-3876a: content field, grade_letter property, all_pages() iterator
# ---------------------------------------------------------------------------

class TestTC3876aContentAndAllPages:
    """TC-3876a: GoldenPage.content field, grade_letter property, GoldenIndex.all_pages()."""

    def test_golden_page_has_content_field(self, tmp_path):
        """GoldenPage.content is a non-empty str populated from the file body."""
        md_content = "---\ntitle: Test\ngrade: B\n---\n## Overview\nSome text here.\n"
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        from launcher.shared.golden_loader import _parse_golden_file
        page = _parse_golden_file(md_file, tmp_path)
        assert page is not None
        assert isinstance(page.content, str)
        assert len(page.content) > 0

    def test_golden_page_content_strips_golden_comment(self, tmp_path):
        """GOLDEN REFERENCE comment is stripped from page.content; frontmatter is preserved."""
        md_content = (
            "<!-- GOLDEN REFERENCE | Source: test | Original-Grade: A- -->\n"
            "---\ntitle: Test\n---\n## Section\nSome text here.\n"
        )
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        from launcher.shared.golden_loader import _parse_golden_file
        page = _parse_golden_file(md_file, tmp_path)
        assert page is not None
        assert "GOLDEN REFERENCE" not in page.content
        assert "---" in page.content  # frontmatter still present

    def test_grade_letter_returns_single_letter(self, tmp_path):
        """grade_letter returns uppercase letter for bare grade."""
        from launcher.shared.golden_loader import GoldenPage
        page = GoldenPage(
            source_path=tmp_path / "test.md",
            page_role="installation",
            variant="standard",
            subdomain="docs.aspose.org",
            grade="B",
            sections=[],
            total_word_count=0,
        )
        assert page.grade_letter == "B"

    def test_grade_letter_strips_modifier(self, tmp_path):
        """grade_letter normalizes 'B+' → 'B' and 'A-' → 'A'."""
        md_b_plus = "---\ntitle: Test\ngrade: \"B+\"\n---\n## Section\nText here.\n"
        md_a_minus = "---\ntitle: Test\ngrade: \"A-\"\n---\n## Section\nText here.\n"

        from launcher.shared.golden_loader import _parse_golden_file
        for content, expected_grade, expected_letter in [
            (md_b_plus, "B+", "B"),
            (md_a_minus, "A-", "A"),
        ]:
            f = tmp_path / "test.md"
            f.write_text(content, encoding="utf-8")
            page = _parse_golden_file(f, tmp_path)
            assert page is not None, f"Failed to parse file with grade modifier"
            assert page.grade == expected_grade, f"Expected grade '{expected_grade}', got '{page.grade}'"
            assert page.grade_letter == expected_letter, f"Expected letter '{expected_letter}', got '{page.grade_letter}'"

    def test_all_pages_sorted_and_deterministic(self):
        """all_pages() returns sorted list; two calls return identical order."""
        index = GoldenIndex.load(GOLDEN_DIR)
        pages = index.all_pages()
        if not pages:
            return  # golden/ not present in this environment
        # All pages have content field populated
        assert all(isinstance(p.content, str) for p in pages)
        # Sorted by (subdomain, page_role, variant)
        keys = [(p.subdomain, p.page_role, p.variant) for p in pages]
        assert keys == sorted(keys), "all_pages() must return pages in sorted order"
        # Deterministic: same result on repeated call
        assert index.all_pages() == index.all_pages()


# ---------------------------------------------------------------------------
# TC-3878 (W2-S6): get_nearest_golden 3-level fallback
# ---------------------------------------------------------------------------

def test_get_nearest_golden_none_when_no_golden_dir():
    from launcher.shared.golden_loader import get_nearest_golden
    result = get_nearest_golden("landing", "Overview", None)
    assert result == ""


def test_get_nearest_golden_empty_when_dir_not_exist(tmp_path):
    from launcher.shared.golden_loader import get_nearest_golden
    missing = tmp_path / "nonexistent_golden"
    result = get_nearest_golden("landing", "Overview", missing)
    assert result == ""
