"""Tests for TC-2386: W4 Pre-Generation Duplication Check."""
import pytest
from launch.workers._shared.jaccard import (
    compute_word_set,
    jaccard_similarity,
    SIMILARITY_THRESHOLD,
    STOPWORDS,
    _strip_frontmatter,
    _strip_code_blocks,
    _tokenize,
)
from launch.workers.w4_ia_planner.worker import check_pre_generation_redundancy


class TestJaccardModule:
    def test_identical_texts_similarity_one(self):
        s = compute_word_set("convert files format aspose python library")
        assert jaccard_similarity(s, s) == 1.0

    def test_disjoint_texts_similarity_zero(self):
        s1 = compute_word_set("python aspose convert files")
        s2 = compute_word_set("xml database schema query")
        assert jaccard_similarity(s1, s2) == 0.0

    def test_partial_overlap(self):
        s1 = compute_word_set("aspose python convert files format")
        s2 = compute_word_set("aspose python render images format")
        sim = jaccard_similarity(s1, s2)
        assert 0.0 < sim < 1.0

    def test_empty_set_returns_zero(self):
        assert jaccard_similarity(set(), {"word"}) == 0.0
        assert jaccard_similarity({"word"}, set()) == 0.0

    def test_strip_frontmatter(self):
        text = "---\ntitle: Test\n---\nActual content here"
        result = _strip_frontmatter(text)
        assert "Actual content here" in result
        assert "title: Test" not in result

    def test_strip_code_blocks(self):
        text = "Prose here\n```python\nsome_code()\n```\nMore prose"
        result = _strip_code_blocks(text)
        assert "some_code" not in result
        assert "Prose here" in result

    def test_tokenize_filters_stopwords(self):
        tokens = _tokenize("the quick brown fox and the lazy dog")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens

    def test_compute_word_set_returns_set(self):
        result = compute_word_set("convert documents aspose library")
        assert isinstance(result, set)
        assert len(result) > 0


class TestPreGenerationRedundancy:
    def _make_page(self, slug, title, purpose="", claims=None):
        return {
            "slug": slug,
            "title": title,
            "purpose": purpose,
            "claims": claims or [],
        }

    def test_no_pages_returns_empty(self):
        result = check_pre_generation_redundancy([])
        assert result == []

    def test_single_page_no_warnings(self):
        pages = [self._make_page("intro", "Introduction to Aspose", "Getting started guide")]
        result = check_pre_generation_redundancy(pages)
        assert result == []

    def test_similar_pages_detected(self):
        pages = [
            self._make_page(
                "intro-a", "Introduction to Aspose Convert",
                "convert documents python aspose library files format"
            ),
            self._make_page(
                "intro-b", "Introduction to Aspose Conversion",
                "convert documents python aspose library files format"
            ),
        ]
        result = check_pre_generation_redundancy(pages, threshold=0.3)
        assert len(result) >= 1
        assert result[0]["page_a"] == "intro-a"
        assert result[0]["page_b"] == "intro-b"
        assert "similarity" in result[0]

    def test_different_pages_no_warnings(self):
        pages = [
            self._make_page("tutorial", "Installation Tutorial", "install package python"),
            self._make_page("api-ref", "API Reference", "class methods parameters return"),
        ]
        result = check_pre_generation_redundancy(pages)
        assert result == []

    def test_similarity_below_threshold_not_flagged(self):
        pages = [
            self._make_page("p1", "Aspose Convert Files", "convert transform process"),
            self._make_page("p2", "Aspose Render Files", "render display visualize"),
        ]
        result = check_pre_generation_redundancy(pages, threshold=0.9)
        assert result == []

    def test_warning_has_required_fields(self):
        pages = [
            self._make_page(
                "dup-a", "Aspose Convert Format Files",
                "convert format files aspose python library transform"
            ),
            self._make_page(
                "dup-b", "Aspose Convert Format Files Similar",
                "convert format files aspose python library transform"
            ),
        ]
        result = check_pre_generation_redundancy(pages, threshold=0.1)
        if result:
            w = result[0]
            assert "page_a" in w
            assert "page_b" in w
            assert "similarity" in w
            assert "suggestion" in w
