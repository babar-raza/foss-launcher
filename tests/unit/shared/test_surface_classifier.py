"""Tests for surface classifier and repo profiling (capabilities #3)."""
from __future__ import annotations

import pytest

from launcher.models.product import RepoProfile, RichnessResult, RichnessTier
from launcher.models.understanding import RepoInfo, SharedFacts
from launcher.shared.surface_classifier import (
    build_repo_profile,
    classify_richness,
    classify_richness_with_surface,
)


def _make_repo_info(
    *,
    doc_count: int = 0,
    example_count: int = 0,
    readme: str = "",
    extra_files: list[str] | None = None,
    shared_facts: SharedFacts | None = None,
) -> RepoInfo:
    docs = [f"docs/page{i}.md" for i in range(doc_count)]
    examples = [f"examples/ex{i}.py" for i in range(example_count)]
    files = docs + examples + (extra_files or [])
    return RepoInfo(
        file_tree=files,
        doc_paths=docs,
        example_paths=examples,
        readme_summary=readme,
        shared_facts=shared_facts or SharedFacts(),
    )


class TestClassifyRichness:
    def test_tier_c_minimal(self) -> None:
        repo = _make_repo_info()
        result = classify_richness(repo)
        assert result.tier == RichnessTier.C
        assert result.score < 12

    def test_tier_b_moderate(self) -> None:
        repo = _make_repo_info(
            doc_count=5, example_count=3, readme="x" * 600,
            extra_files=["tests/test_main.py"],
        )
        result = classify_richness(repo)
        assert result.tier == RichnessTier.B
        assert result.score >= 12

    def test_tier_a_rich(self) -> None:
        repo = _make_repo_info(
            doc_count=10, example_count=10, readme="x" * 600,
            extra_files=["tests/test_main.py", ".github/workflows/ci.yml"],
        )
        result = classify_richness(repo)
        assert result.tier == RichnessTier.A
        assert result.score >= 25

    def test_uses_shared_facts_for_tests(self) -> None:
        facts = SharedFacts(has_tests=True, has_ci=True)
        repo = _make_repo_info(doc_count=5, shared_facts=facts)
        result = classify_richness(repo)
        assert "has_tests" in result.reason
        assert "has_ci" in result.reason

    def test_readme_threshold(self) -> None:
        short = _make_repo_info(readme="x" * 400)
        long = _make_repo_info(readme="x" * 600)
        assert classify_richness(long).score > classify_richness(short).score


class TestClassifyRichnessWithSurface:
    def test_api_confidence_boosts_score(self) -> None:
        repo = _make_repo_info(doc_count=5)
        base = classify_richness(repo)
        enhanced = classify_richness_with_surface(repo, api_confidence="high")
        assert enhanced.score == base.score + 10

    def test_public_classes_boost(self) -> None:
        repo = _make_repo_info(doc_count=5)
        result = classify_richness_with_surface(repo, public_class_count=25)
        assert "public_classes" in result.reason

    # TC-3871: extracted snippet count signal
    def test_extracted_snippets_boost_score(self) -> None:
        repo = _make_repo_info(doc_count=5)
        base = classify_richness_with_surface(repo)
        enhanced = classify_richness_with_surface(repo, extracted_snippet_count=10)
        assert enhanced.score == base.score + 3
        assert "extracted_snippets" in enhanced.reason

    def test_extracted_snippets_below_threshold_no_boost(self) -> None:
        repo = _make_repo_info(doc_count=5)
        base = classify_richness_with_surface(repo)
        no_boost = classify_richness_with_surface(repo, extracted_snippet_count=9)
        assert no_boost.score == base.score
        assert "extracted_snippets" not in no_boost.reason

    def test_extracted_snippets_composite_can_lift_tier(self) -> None:
        # Build a repo with score=11 (just below Tier B threshold of 12)
        # doc_count=6 (6pts) + example_count=5 (5pts) = 11 pts -> Tier C
        repo = _make_repo_info(doc_count=6, example_count=5)
        base = classify_richness(repo)
        assert base.tier.value == "C"
        assert base.score == 11
        # With 10 extracted snippets (+3) -> score=14 -> Tier B
        enhanced = classify_richness_with_surface(
            repo, extracted_snippet_count=10,
        )
        assert enhanced.tier.value == "B"
        assert enhanced.score == 14

    def test_all_signals_combined(self) -> None:
        repo = _make_repo_info(doc_count=5)
        result = classify_richness_with_surface(
            repo,
            api_confidence="high",
            public_class_count=25,
            extracted_snippet_count=10,
        )
        assert "api_confidence" in result.reason
        assert "public_classes" in result.reason
        assert "extracted_snippets" in result.reason


class TestBuildRepoProfile:
    def test_basic_profile(self) -> None:
        repo = _make_repo_info(
            doc_count=3, example_count=2, readme="Hello world",
            extra_files=["src/main.py", "tests/test_main.py"],
        )
        profile = build_repo_profile(repo)
        assert isinstance(profile, RepoProfile)
        assert profile.docs_depth == 5  # 3 docs + 2 examples
        assert profile.examples_count == 2
        assert profile.markdown_file_count == 3

    def test_has_readme_detection(self) -> None:
        repo = _make_repo_info(extra_files=["README.md"])
        profile = build_repo_profile(repo)
        assert profile.has_readme is True

    def test_no_readme_warning(self) -> None:
        repo = _make_repo_info(extra_files=["src/main.py"])
        profile = build_repo_profile(repo)
        assert profile.has_readme is False
        assert "no_readme" in profile.warnings

    def test_type_stubs_detection(self) -> None:
        repo = _make_repo_info(extra_files=["src/stubs/main.pyi"])
        profile = build_repo_profile(repo)
        assert profile.has_type_stubs is True

    def test_language_breakdown(self) -> None:
        repo = _make_repo_info(extra_files=[
            "src/a.py", "src/b.py", "src/c.py",
            "src/d.java", "src/e.java",
        ])
        profile = build_repo_profile(repo)
        assert profile.language_breakdown.get("py") == 3
        assert profile.language_breakdown.get("java") == 2

    def test_confidence_full_repo(self) -> None:
        repo = _make_repo_info(
            doc_count=5, example_count=2, readme="content",
            extra_files=["README.md"],
        )
        profile = build_repo_profile(repo)
        assert profile.confidence == 0.8

    def test_confidence_degrades_no_docs(self) -> None:
        repo = _make_repo_info(extra_files=["src/main.py"])
        profile = build_repo_profile(repo)
        assert profile.confidence < 0.8

    def test_empty_repo(self) -> None:
        repo = _make_repo_info()
        profile = build_repo_profile(repo)
        assert profile.confidence == 0.1
        assert "no_paths" in profile.warnings

    def test_api_surface_count(self) -> None:
        repo = _make_repo_info(extra_files=["src/main.py"])
        profile = build_repo_profile(repo, api_surface_count=42)
        assert profile.api_surface_count == 42

    def test_shared_facts_propagated(self) -> None:
        facts = SharedFacts(
            has_docs_folder=True,
            has_examples_folder=True,
            primary_language="python",
            build_systems=["pyproject"],
        )
        repo = _make_repo_info(shared_facts=facts, extra_files=["README.md"])
        profile = build_repo_profile(repo)
        assert profile.has_docs_folder is True
        assert profile.has_examples_folder is True
        assert profile.primary_language == "python"
        assert "pyproject" in profile.build_systems


# ---------------------------------------------------------------------------
# TC-3904: Regression tests for code_evidence_sparse (TC-3903 fix)
# Depends on: TC-3903 (code_evidence_sparse signal in RichnessResult)
# ---------------------------------------------------------------------------


class TestCodeEvidenceSparse:
    """TC-3904: code_evidence_sparse regression suite — ensures TC-3903 fix holds."""

    def test_sparse_true_for_zero_evidence(self) -> None:
        """Thin repo: 0 examples + 0 snippets → code_evidence_sparse=True."""
        repo = _make_repo_info(example_count=0)
        result = classify_richness_with_surface(repo, extracted_snippet_count=0)
        assert result.code_evidence_sparse is True

    def test_sparse_false_for_rich_repo(self) -> None:
        """Rich repo (Cells Python equivalent): 10 examples + 15 snippets → sparse=False."""
        repo = _make_repo_info(example_count=10, doc_count=5, readme="x" * 600)
        result = classify_richness_with_surface(repo, extracted_snippet_count=15)
        assert result.code_evidence_sparse is False

    def test_sparse_boundary_below(self) -> None:
        """2 examples + 0 snippets = 2 < 3 → code_evidence_sparse=True."""
        repo = _make_repo_info(example_count=2)
        result = classify_richness_with_surface(repo, extracted_snippet_count=0)
        assert result.code_evidence_sparse is True

    def test_sparse_boundary_at_threshold(self) -> None:
        """3 examples + 0 snippets = 3 == threshold → sparse=False (NOT < 3)."""
        repo = _make_repo_info(example_count=3)
        result = classify_richness_with_surface(repo, extracted_snippet_count=0)
        assert result.code_evidence_sparse is False

    def test_base_classify_richness_defaults_false(self) -> None:
        """classify_richness() base function: code_evidence_sparse defaults to False."""
        repo = _make_repo_info(example_count=0)
        result = classify_richness(repo)
        assert result.code_evidence_sparse is False

    def test_reason_string_includes_sparse_info(self) -> None:
        """classify_richness_with_surface reason includes code_evidence=X(sparse=Y)."""
        repo = _make_repo_info(example_count=0)
        result = classify_richness_with_surface(repo, extracted_snippet_count=0)
        assert "code_evidence=0" in result.reason
        assert "sparse=True" in result.reason

    def test_reason_string_sparse_false_for_rich_repo(self) -> None:
        """Rich repo reason string shows code_evidence=20 and sparse=False."""
        repo = _make_repo_info(example_count=10, doc_count=5, readme="x" * 600)
        result = classify_richness_with_surface(repo, extracted_snippet_count=15)
        # min(10,10) + min(15,10) = 20
        assert "code_evidence=20" in result.reason
        assert "sparse=False" in result.reason
