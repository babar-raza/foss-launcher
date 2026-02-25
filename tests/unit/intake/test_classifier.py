"""Tests for the repository classifier.

Covers eligibility heuristics, deterministic classification, and
edge cases with realistic repo metadata.

TC: TC-2541, TC-2545
"""

from __future__ import annotations

import pytest

from launch.intake.repo_classifier import (
    ClassificationResult,
    ClassifierConfig,
    DEFAULT_ALLOWED_LICENSES,
    classify_repo,
    classify_repos,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_repo(
    full_name: str = "myorg/MyRepo",
    stars: int = 10,
    language: str = "Python",
    license_spdx: str | None = "MIT",
    is_template: bool = False,
    description: str = "A great repo",
    size: int = 500,
    has_readme: bool | None = None,
) -> dict:
    license_obj = {"spdx_id": license_spdx, "name": license_spdx} if license_spdx else None
    repo = {
        "full_name": full_name,
        "name": "MyRepo",
        "stargazers_count": stars,
        "language": language,
        "license": license_obj,
        "is_template": is_template,
        "description": description,
        "size": size,
    }
    if has_readme is not None:
        repo["has_readme"] = has_readme
    return repo


# ---------------------------------------------------------------------------
# Tests: classify_repo
# ---------------------------------------------------------------------------


class TestClassifyRepo:
    def test_eligible_repo(self):
        repo = _make_repo()
        result = classify_repo(repo)
        assert result.decision == "eligible"
        assert result.full_name == "myorg/MyRepo"

    def test_ineligible_no_license(self):
        repo = _make_repo(license_spdx=None)
        repo["license"] = None
        result = classify_repo(repo)
        assert result.decision == "ineligible"
        assert any("no license" in r for r in result.reasons)

    def test_ineligible_non_oss_license(self):
        repo = _make_repo(license_spdx="SSPL-1.0")
        result = classify_repo(repo)
        assert result.decision == "ineligible"
        assert any("SSPL-1.0" in r for r in result.reasons)

    def test_ineligible_low_stars(self):
        config = ClassifierConfig(min_stars=50)
        repo = _make_repo(stars=5)
        result = classify_repo(repo, config=config)
        assert result.decision == "ineligible"
        assert any("star count" in r for r in result.reasons)

    def test_needs_review_template(self):
        repo = _make_repo(is_template=True)
        result = classify_repo(repo)
        assert result.decision == "needs_review"
        assert any("template" in r for r in result.reasons)

    def test_needs_review_non_python_language(self):
        repo = _make_repo(language="JavaScript")
        result = classify_repo(repo)
        assert result.decision == "needs_review"
        assert any("JavaScript" in r for r in result.reasons)

    def test_needs_review_no_language(self):
        repo = _make_repo(language="")
        result = classify_repo(repo)
        assert result.decision == "needs_review"
        assert any("no primary language" in r for r in result.reasons)

    def test_needs_review_no_readme(self):
        repo = _make_repo(has_readme=False)
        result = classify_repo(repo)
        assert result.decision == "ineligible"
        assert any("README" in r for r in result.reasons)

    def test_needs_review_small_repo_no_desc(self):
        repo = _make_repo(description="", size=3)
        result = classify_repo(repo)
        assert result.decision == "needs_review"
        assert any("README" in r or "small" in r for r in result.reasons)

    def test_needs_review_unresolved_license(self):
        repo = _make_repo(license_spdx="NOASSERTION")
        result = classify_repo(repo)
        assert result.decision == "needs_review"
        assert any("NOASSERTION" in r for r in result.reasons)

    def test_eligible_mit(self):
        repo = _make_repo(license_spdx="MIT")
        result = classify_repo(repo)
        assert result.decision == "eligible"

    def test_eligible_apache(self):
        repo = _make_repo(license_spdx="Apache-2.0")
        result = classify_repo(repo)
        assert result.decision == "eligible"

    def test_deterministic_same_input(self):
        repo = _make_repo()
        r1 = classify_repo(repo)
        r2 = classify_repo(repo)
        assert r1.decision == r2.decision
        assert r1.reasons == r2.reasons

    def test_to_dict(self):
        repo = _make_repo()
        result = classify_repo(repo)
        d = result.to_dict()
        assert d["full_name"] == "myorg/MyRepo"
        assert d["decision"] == "eligible"
        assert isinstance(d["reasons"], list)

    def test_skip_python_check_when_disabled(self):
        config = ClassifierConfig(require_python=False)
        repo = _make_repo(language="Rust")
        result = classify_repo(repo, config=config)
        # Should not be marked needs_review for language
        assert not any("Rust" in r for r in result.reasons)

    def test_skip_license_check_when_disabled(self):
        config = ClassifierConfig(require_license=False)
        repo = _make_repo(license_spdx=None)
        repo["license"] = None
        result = classify_repo(repo, config=config)
        assert not any("license" in r.lower() for r in result.reasons)

    def test_require_language_java_eligible(self):
        config = ClassifierConfig(require_language="Java")
        repo = _make_repo(language="Java")
        result = classify_repo(repo, config=config)
        assert result.decision == "eligible"

    def test_require_language_java_mismatch(self):
        config = ClassifierConfig(require_language="Java")
        repo = _make_repo(language="Python")
        result = classify_repo(repo, config=config)
        assert result.decision == "needs_review"
        assert any("not Java" in r for r in result.reasons)

    def test_require_language_overrides_require_python(self):
        config = ClassifierConfig(require_python=True, require_language="Rust")
        repo = _make_repo(language="Rust")
        result = classify_repo(repo, config=config)
        # require_language takes precedence — Rust matches, no Python complaint
        assert not any("Python" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# Tests: classify_repos (batch)
# ---------------------------------------------------------------------------


class TestClassifyRepos:
    def test_batch_classification(self):
        repos = [
            _make_repo(full_name="org/A"),
            _make_repo(full_name="org/B", license_spdx=None),
        ]
        repos[1]["license"] = None
        results = classify_repos(repos)
        assert len(results) == 2
        assert results[0].decision == "eligible"
        assert results[1].decision == "ineligible"

    def test_empty_input(self):
        assert classify_repos([]) == []
