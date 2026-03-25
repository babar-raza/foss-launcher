"""Tests for golden_conformance check (TC-2500).

Validates all 5 conformance dimensions, composite scoring,
finding thresholds, graceful degradation, and determinism.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from launcher.workers.evaluate.checks.golden_conformance import (
    _compute_code_ratio,
    _cosine_similarity,
    _dim_block_type_coverage,
    _dim_code_density_alignment,
    _dim_depth_proportionality,
    _dim_section_coverage,
    _dim_section_order,
    _match_sections,
    _prose_word_count,
    check_golden_conformance,
    clear_conformance_cache,
    get_conformance_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GOLDEN_FM = "---\ngrade: A\n---\n"


def _make_golden_file(
    tmp_path: Path,
    page_role: str = "howto_article",
    variant: str = "standard",
    sections: list[tuple[str, str]] | None = None,
) -> Path:
    """Create a golden .md file with known sections in the expected directory structure."""
    golden_dir = tmp_path / "golden"
    # Golden files are expected under subdomain/family/platform/ paths
    subdir = golden_dir / "kb.aspose.org" / "__FAMILY__" / "__PLATFORM__"
    subdir.mkdir(parents=True, exist_ok=True)

    if sections is None:
        sections = [
            ("Overview", "This section provides an overview of the feature.\n\nIt explains the key concepts and usage patterns."),
            ("Prerequisites", "Before starting, ensure you have the required dependencies installed."),
            ("Code Examples", "Here is how to use the feature:\n\n```python\nimport aspose.cells\nwb = aspose.cells.Workbook()\nprint(wb)\n```\n\nThis creates a new workbook instance."),
            ("Best Practices", "Follow these best practices:\n\n- Use context managers\n- Handle exceptions\n- Validate inputs"),
            ("Troubleshooting", "Common issues and solutions:\n\n| Issue | Solution |\n|-------|----------|\n| Import error | Reinstall package |"),
        ]

    content = _GOLDEN_FM
    for heading, body in sections:
        content += f"\n## {heading}\n\n{body}\n"

    fname = f"howto.variant-{variant}.md" if variant != "standard" else "howto.md"
    filepath = subdir / fname
    filepath.write_text(content, encoding="utf-8")
    return golden_dir


def _make_content(sections: list[tuple[str, str]]) -> str:
    """Build markdown content from (heading, body) pairs."""
    lines = ["---\ntitle: Test Page\npage_role: howto_article\n---\n"]
    for heading, body in sections:
        lines.append(f"\n## {heading}\n\n{body}\n")
    return "\n".join(lines)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear conformance cache before each test."""
    clear_conformance_cache()
    yield
    clear_conformance_cache()


# ---------------------------------------------------------------------------
# Graceful degradation tests
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    def test_golden_dir_none(self):
        findings = check_golden_conformance("# Test", "slug1", golden_dir=None)
        assert findings == []
        score, breakdown = get_conformance_result("slug1")
        assert score is None
        assert breakdown == {}

    def test_golden_dir_missing(self, tmp_path: Path):
        findings = check_golden_conformance(
            "# Test", "slug2", golden_dir=tmp_path / "nonexistent"
        )
        assert findings == []
        score, _ = get_conformance_result("slug2")
        assert score is None

    def test_no_golden_for_role(self, tmp_path: Path):
        golden_dir = tmp_path / "golden"
        golden_dir.mkdir()
        findings = check_golden_conformance(
            "# Test", "slug3",
            page_role="unknown_role", golden_dir=golden_dir,
        )
        assert findings == []
        score, _ = get_conformance_result("slug3")
        assert score is None

    def test_uncached_slug_returns_none(self):
        score, breakdown = get_conformance_result("never_evaluated")
        assert score is None
        assert breakdown == {}

    def test_empty_generated_content(self, tmp_path: Path):
        golden_dir = _make_golden_file(tmp_path)
        content = "---\ntitle: Empty\n---\n"
        findings = check_golden_conformance(
            content, "empty_slug",
            page_role="howto_article", golden_dir=golden_dir,
        )
        assert len(findings) == 1
        assert findings[0].severity == "high"
        score, _ = get_conformance_result("empty_slug")
        assert score == 0.0


# ---------------------------------------------------------------------------
# Dimension 1: Section Coverage
# ---------------------------------------------------------------------------

class TestSectionCoverage:
    def test_all_sections_present(self, tmp_path: Path):
        golden_dir = _make_golden_file(tmp_path, sections=[
            ("Overview", "Some overview text with enough words for parsing."),
            ("Code Examples", "Here is code:\n\n```python\nprint('hi')\n```\n\nExplanation here."),
        ])
        content = _make_content([
            ("Overview", "Our overview with content here to match section."),
            ("Code Examples", "Code goes here:\n\n```python\nprint('hi')\n```\n\nMore text."),
        ])
        findings = check_golden_conformance(
            content, "full_match",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score, breakdown = get_conformance_result("full_match")
        assert score is not None
        assert breakdown["section_coverage"] == 1.0

    def test_partial_sections(self, tmp_path: Path):
        golden_dir = _make_golden_file(tmp_path, sections=[
            ("Overview", "Overview text with enough words for parsing here."),
            ("Details", "Detail text with enough words for parsing here too."),
            ("Summary", "Summary text with enough words for parsing and display."),
        ])
        content = _make_content([
            ("Overview", "Our overview with matching content for the section."),
        ])
        findings = check_golden_conformance(
            content, "partial",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score, breakdown = get_conformance_result("partial")
        assert score is not None
        # Only 1 of 3 golden sections matched (no skeleton normalization)
        assert breakdown["section_coverage"] == pytest.approx(1 / 3, abs=0.01)

    def test_partial_sections_with_skeleton_normalization(self, tmp_path: Path):
        """TC-DFR-003: With skeleton_section_count, coverage denominator is normalized."""
        golden_dir = _make_golden_file(tmp_path, sections=[
            ("Overview", "Overview text with enough words for parsing here."),
            ("Details", "Detail text with enough words for parsing here too."),
            ("Summary", "Summary text with enough words for parsing and display."),
        ])
        content = _make_content([
            ("Overview", "Our overview with matching content for the section."),
        ])
        clear_conformance_cache()
        findings = check_golden_conformance(
            content, "partial_norm",
            page_role="howto_article", golden_dir=golden_dir,
            skeleton_section_count=1,
        )
        score, breakdown = get_conformance_result("partial_norm")
        assert score is not None
        # 1 matched / min(3 golden, 1 skeleton) = 1/1 = 1.0
        assert breakdown["section_coverage"] == pytest.approx(1.0, abs=0.01)

    def test_skeleton_larger_than_golden_uses_golden(self, tmp_path: Path):
        """TC-DFR-003: When skeleton > golden, denominator stays golden."""
        golden_dir = _make_golden_file(tmp_path, sections=[
            ("Overview", "Overview text with enough words for parsing here."),
            ("Details", "Detail text with enough words for parsing here too."),
        ])
        content = _make_content([
            ("Overview", "Our overview with matching content for the section."),
        ])
        clear_conformance_cache()
        findings = check_golden_conformance(
            content, "skel_larger",
            page_role="howto_article", golden_dir=golden_dir,
            skeleton_section_count=10,
        )
        score, breakdown = get_conformance_result("skel_larger")
        assert score is not None
        # 1 matched / min(2 golden, 10 skeleton) = 1/2 = 0.5
        assert breakdown["section_coverage"] == pytest.approx(0.5, abs=0.01)

    def test_zero_skeleton_falls_back_to_golden(self, tmp_path: Path):
        """TC-DFR-003: skeleton_section_count=0 uses golden (backward compat)."""
        golden_dir = _make_golden_file(tmp_path, sections=[
            ("Overview", "Overview text with enough words for parsing here."),
            ("Details", "Detail text with enough words for parsing here too."),
            ("Summary", "Summary text with enough words for parsing and display."),
        ])
        content = _make_content([
            ("Overview", "Our overview with matching content for the section."),
        ])
        clear_conformance_cache()
        findings = check_golden_conformance(
            content, "zero_skel",
            page_role="howto_article", golden_dir=golden_dir,
            skeleton_section_count=0,
        )
        score, breakdown = get_conformance_result("zero_skel")
        assert score is not None
        # Fallback: 1/3 = 0.33
        assert breakdown["section_coverage"] == pytest.approx(1 / 3, abs=0.01)


# ---------------------------------------------------------------------------
# Dimension 2: Section Order
# ---------------------------------------------------------------------------

class TestSectionOrder:
    def test_same_order(self):
        # Simulate matched pairs: golden order [0,1,2], gen order [0,1,2]
        pairs = [(0, 0, None, "A", ""), (1, 1, None, "B", ""), (2, 2, None, "C", "")]
        assert _dim_section_order(pairs) == 1.0

    def test_reversed_order(self):
        # golden order [0,1,2], gen order [2,1,0]
        pairs = [(0, 2, None, "A", ""), (1, 1, None, "B", ""), (2, 0, None, "C", "")]
        assert _dim_section_order(pairs) == 0.0

    def test_partial_reorder(self):
        # golden order [0,1,2], gen order [0,2,1] — 1 discordant pair
        pairs = [(0, 0, None, "A", ""), (1, 2, None, "B", ""), (2, 1, None, "C", "")]
        score = _dim_section_order(pairs)
        # concordant=2, discordant=1, tau=1/3, scaled=(1/3+1)/2 = 2/3
        assert score == pytest.approx(2 / 3, abs=0.01)

    def test_single_pair(self):
        pairs = [(0, 0, None, "A", "")]
        assert _dim_section_order(pairs) == 1.0

    def test_empty_pairs(self):
        assert _dim_section_order([]) == 1.0


# ---------------------------------------------------------------------------
# Dimension 3: Depth Proportionality
# ---------------------------------------------------------------------------

class TestDepthProportionality:
    def test_identical_distribution(self):
        assert _cosine_similarity([0.5, 0.5], [0.5, 0.5]) == pytest.approx(1.0, abs=0.001)

    def test_orthogonal_distribution(self):
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0, abs=0.001)

    def test_similar_distribution(self):
        score = _cosine_similarity([0.6, 0.4], [0.5, 0.5])
        assert 0.9 < score <= 1.0

    def test_zero_vector(self):
        assert _cosine_similarity([0.0, 0.0], [0.5, 0.5]) == 0.0


# ---------------------------------------------------------------------------
# Dimension 4: Block-Type Coverage
# ---------------------------------------------------------------------------

class TestBlockTypeCoverage:
    def test_empty_pairs(self):
        assert _dim_block_type_coverage([]) == 0.0


# ---------------------------------------------------------------------------
# Dimension 5: Code Density Alignment
# ---------------------------------------------------------------------------

class TestCodeDensityAlignment:
    def test_no_code_sections(self):
        assert _dim_code_density_alignment([]) == 1.0

    def test_compute_code_ratio_no_code(self):
        assert _compute_code_ratio("Just prose text here.") == 0.0

    def test_compute_code_ratio_with_code(self):
        text = "Some prose.\n\n```python\nprint('hello')\n```\n\nMore prose."
        ratio = _compute_code_ratio(text)
        assert 0.0 < ratio < 1.0

    def test_prose_word_count(self):
        text = "Hello world.\n\n```python\nprint('hi')\n```\n\nGoodbye world."
        count = _prose_word_count(text)
        # "Hello world." + "Goodbye world." = 4 words
        assert count == 4


# ---------------------------------------------------------------------------
# Finding threshold tests
# ---------------------------------------------------------------------------

class TestFindingThresholds:
    def test_high_score_no_findings(self, tmp_path: Path):
        """Score >= 0.75 should produce no findings."""
        golden_dir = _make_golden_file(tmp_path, sections=[
            ("Overview", "Overview text with enough words for parsing correctly."),
        ])
        content = _make_content([
            ("Overview", "Overview text with enough words for parsing correctly."),
        ])
        findings = check_golden_conformance(
            content, "high_score",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score, _ = get_conformance_result("high_score")
        if score is not None and score >= 0.75:
            assert len(findings) == 0

    def test_finding_severity_high(self, tmp_path: Path):
        """Score < 0.35 should produce HIGH finding."""
        golden_dir = _make_golden_file(tmp_path)
        # Very different content from golden
        content = _make_content([
            ("Unrelated Section", "Completely unrelated content that does not match any golden section at all."),
        ])
        findings = check_golden_conformance(
            content, "low_score",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score, _ = get_conformance_result("low_score")
        if score is not None and score < 0.35:
            assert any(f.severity == "high" for f in findings)

    def test_finding_check_name(self, tmp_path: Path):
        golden_dir = _make_golden_file(tmp_path)
        content = _make_content([
            ("Random", "Random content that has nothing to do with the golden template at all."),
        ])
        findings = check_golden_conformance(
            content, "check_name",
            page_role="howto_article", golden_dir=golden_dir,
        )
        for f in findings:
            assert f.check == "golden_conformance"


# ---------------------------------------------------------------------------
# Determinism test
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_same_output(self, tmp_path: Path):
        """Same inputs must produce identical scores across calls."""
        golden_dir = _make_golden_file(tmp_path)
        content = _make_content([
            ("Overview", "Overview text with enough words for parsing correctly."),
            ("Code Examples", "Here is code:\n\n```python\nimport aspose.cells\nprint('hello')\n```\n\nExplanation of the code."),
        ])

        check_golden_conformance(
            content, "det_1",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score1, breakdown1 = get_conformance_result("det_1")

        clear_conformance_cache()

        check_golden_conformance(
            content, "det_1",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score2, breakdown2 = get_conformance_result("det_1")

        assert score1 == score2
        assert breakdown1 == breakdown2


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

class TestCache:
    def test_cache_populated_after_check(self, tmp_path: Path):
        golden_dir = _make_golden_file(tmp_path)
        content = _make_content([
            ("Overview", "Overview text with enough words for parsing correctly."),
        ])
        check_golden_conformance(
            content, "cached_slug",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score, breakdown = get_conformance_result("cached_slug")
        assert score is not None
        assert "section_coverage" in breakdown

    def test_clear_cache(self, tmp_path: Path):
        golden_dir = _make_golden_file(tmp_path)
        content = _make_content([
            ("Overview", "Overview text with enough words for parsing correctly."),
        ])
        check_golden_conformance(
            content, "to_clear",
            page_role="howto_article", golden_dir=golden_dir,
        )
        clear_conformance_cache()
        score, _ = get_conformance_result("to_clear")
        assert score is None


# ---------------------------------------------------------------------------
# numeric_score computation tests
# ---------------------------------------------------------------------------

class TestNumericScore:
    """Tests for _compute_numeric_score in worker.py."""

    def test_no_findings_no_conformance(self):
        from launcher.workers.evaluate.worker import _compute_numeric_score
        # No findings, no conformance → base = 100, no blend
        score = _compute_numeric_score([], None)
        assert score == 100.0

    def test_no_findings_with_conformance(self):
        from launcher.workers.evaluate.worker import _compute_numeric_score
        # No findings, conformance=0.80 → 100*0.65 + 80*0.35 = 65 + 28 = 93
        score = _compute_numeric_score([], 0.80)
        assert score == 93.0

    def test_penalty_only(self):
        from launcher.workers.evaluate.worker import _compute_numeric_score
        from launcher.models.evaluation import Finding
        findings = [
            Finding(check="density", message="too short", severity="high"),
            Finding(check="repetition", message="repeated", severity="medium"),
        ]
        # non-safety high=1 (10pts), medium=1 (5pts) → penalty=15, base=85
        score = _compute_numeric_score(findings, None)
        assert score == 85.0

    def test_penalty_with_conformance(self):
        from launcher.workers.evaluate.worker import _compute_numeric_score
        from launcher.models.evaluation import Finding
        findings = [
            Finding(check="density", message="too short", severity="medium"),
        ]
        # medium=1 (5pts) → penalty=5, base=95
        # blend: 95*0.65 + 0.60*100*0.35 = 61.75 + 21 = 82.75
        score = _compute_numeric_score(findings, 0.60)
        assert score == 82.75

    def test_all_critical_findings(self):
        from launcher.workers.evaluate.worker import _compute_numeric_score
        from launcher.models.evaluation import Finding
        findings = [
            Finding(check="safety", message="xss", severity="critical"),
            Finding(check="safety", message="domain", severity="critical"),
            Finding(check="safety", message="script", severity="critical"),
            Finding(check="safety", message="inject", severity="critical"),
        ]
        # 4 critical × 25 = 100 → base = 0
        score = _compute_numeric_score(findings, 1.0)
        # 0*0.65 + 100*0.35 = 35
        assert score == 35.0

    def test_zero_conformance(self):
        from launcher.workers.evaluate.worker import _compute_numeric_score
        # No findings, conformance=0.0 → 100*0.65 + 0 = 65
        score = _compute_numeric_score([], 0.0)
        assert score == 65.0


# ---------------------------------------------------------------------------
# TC-GLD-015: Section matching tests (greedy bipartite matching)
# ---------------------------------------------------------------------------

class TestMatchSections:
    """Verify _match_sections uses greedy bipartite matching correctly."""

    def test_reordered_sections_all_match(self, tmp_path: Path):
        """Generated sections in different order should still all match.

        TC-GLD-015: The old forward-only algorithm could miss matches when
        sections appeared in a different order than the golden template.
        """
        golden_dir = _make_golden_file(tmp_path, sections=[
            ("Overview", "Overview text with enough words for parsing here."),
            ("Code Examples", "Code here:\n\n```python\nprint('hi')\n```\n\nDone."),
            ("Best Practices", "Follow these rules:\n\n- Rule one\n- Rule two"),
        ])
        # Generated content has same sections but in reversed order
        content = _make_content([
            ("Best Practices", "Follow these rules:\n\n- Rule one\n- Rule two"),
            ("Code Examples", "Code here:\n\n```python\nprint('hi')\n```\n\nDone."),
            ("Overview", "Overview text with enough words for parsing here."),
        ])
        findings = check_golden_conformance(
            content, "reorder_match",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score, breakdown = get_conformance_result("reorder_match")
        assert score is not None
        # All 3 golden sections should be matched
        assert breakdown["section_coverage"] == 1.0
        # Order is reversed, so order score should be low
        assert breakdown["section_order"] < 0.5

    def test_same_order_full_match(self, tmp_path: Path):
        """Sections in same order should produce perfect coverage and order."""
        golden_dir = _make_golden_file(tmp_path, sections=[
            ("Overview", "Overview text with enough words for parsing here."),
            ("Details", "Detail text with enough words for parsing as well."),
        ])
        content = _make_content([
            ("Overview", "Overview text with enough words for parsing here."),
            ("Details", "Detail text with enough words for parsing as well."),
        ])
        findings = check_golden_conformance(
            content, "same_order",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score, breakdown = get_conformance_result("same_order")
        assert score is not None
        assert breakdown["section_coverage"] == 1.0
        assert breakdown["section_order"] == 1.0

    def test_self_conformance_high_score(self, tmp_path: Path):
        """A golden page scored against itself should produce score >= 0.85.

        TC-GLD-015: This is the fundamental correctness invariant — the golden
        exemplar must conform highly to itself.
        """
        sections = [
            ("Overview", "This section provides an overview of the feature.\n\nIt explains the key concepts and usage patterns."),
            ("Code Examples", "Here is how to use the feature:\n\n```python\nimport aspose.cells\nwb = aspose.cells.Workbook()\nprint(wb)\n```\n\nThis creates a new workbook instance."),
            ("Best Practices", "Follow these best practices:\n\n- Use context managers\n- Handle exceptions properly\n- Validate all inputs carefully"),
        ]
        golden_dir = _make_golden_file(tmp_path, sections=sections)
        content = _make_content(sections)
        findings = check_golden_conformance(
            content, "self_conform",
            page_role="howto_article", golden_dir=golden_dir,
        )
        score, breakdown = get_conformance_result("self_conform")
        assert score is not None
        assert score >= 0.85, f"Self-conformance score {score} < 0.85: {breakdown}"
