"""Tests for finding_classifier buckets and sub-classification (TC-3852b / H4.2)."""
from __future__ import annotations

import pytest

from launcher.models.evaluation import Finding
from launcher.workers.evaluate.finding_classifier import (
    ENGINEERING_ONLY_CHECKS,
    LLM_FIXABLE_CHECKS,
    MIXED_CHECKS,
    DATA_FIXABLE_CHECKS,
    FixClass,
    classify_check,
    classify_mixed_check,
    classify_finding,
    is_healable,
)


class TestCheckBuckets:
    def test_engineering_only_checks_non_empty(self) -> None:
        assert len(ENGINEERING_ONLY_CHECKS) >= 2

    def test_llm_fixable_checks_non_empty(self) -> None:
        assert len(LLM_FIXABLE_CHECKS) >= 5

    def test_mixed_checks_non_empty(self) -> None:
        assert len(MIXED_CHECKS) >= 3

    def test_data_fixable_checks_non_empty(self) -> None:
        assert len(DATA_FIXABLE_CHECKS) >= 1

    def test_no_overlap_between_buckets(self) -> None:
        all_checks = [
            ENGINEERING_ONLY_CHECKS,
            MIXED_CHECKS,
            LLM_FIXABLE_CHECKS,
            DATA_FIXABLE_CHECKS,
        ]
        seen: set[str] = set()
        for bucket in all_checks:
            for check in bucket:
                assert check not in seen, f"'{check}' appears in multiple buckets"
                seen.add(check)


class TestClassifyCheck:
    def test_safety_is_engineering_only(self) -> None:
        assert classify_check("safety") == "engineering_only"

    def test_slug_safety_is_engineering_only(self) -> None:
        assert classify_check("slug_safety") == "engineering_only"

    def test_density_is_llm_fixable(self) -> None:
        assert classify_check("density") == "llm_fixable"

    def test_repetition_is_llm_fixable(self) -> None:
        assert classify_check("repetition") == "llm_fixable"

    def test_structure_is_llm_fixable(self) -> None:
        assert classify_check("structure") == "llm_fixable"

    def test_code_is_llm_fixable(self) -> None:
        assert classify_check("code") == "llm_fixable"

    def test_frontmatter_is_mixed(self) -> None:
        assert classify_check("frontmatter") == "mixed"

    def test_seo_is_mixed(self) -> None:
        assert classify_check("seo") == "mixed"

    def test_spec_leakage_is_mixed(self) -> None:
        assert classify_check("spec_leakage") == "mixed"

    def test_reference_completeness_is_data_fixable(self) -> None:
        assert classify_check("reference_completeness") == "data_fixable"

    def test_unknown_check_returns_unknown(self) -> None:
        assert classify_check("nonexistent_check_xyz") == "unknown"


class TestClassifyMixedCheck:
    def test_frontmatter_missing_is_engineering(self) -> None:
        result = classify_mixed_check("frontmatter", "required field missing")
        assert result == "engineering_only"

    def test_frontmatter_wrong_value_is_llm(self) -> None:
        result = classify_mixed_check("frontmatter", "title is too long")
        assert result == "llm_fixable"

    def test_seo_missing_field_is_engineering(self) -> None:
        result = classify_mixed_check("seo", "missing description field")
        assert result == "engineering_only"

    def test_seo_optimization_is_llm(self) -> None:
        result = classify_mixed_check("seo", "title keyword density low")
        assert result == "llm_fixable"

    def test_spec_leakage_in_code_is_engineering(self) -> None:
        result = classify_mixed_check("spec_leakage", "internal import found in code block")
        assert result == "engineering_only"

    def test_spec_leakage_in_prose_is_llm(self) -> None:
        result = classify_mixed_check("spec_leakage", "internal term in prose section")
        assert result == "llm_fixable"

    def test_non_mixed_check_delegates(self) -> None:
        result = classify_mixed_check("density", "word count too low")
        assert result == "llm_fixable"


class TestClassifyFinding:
    """Tests for the typed classify_finding(Finding) -> FixClass wrapper."""

    def _f(self, check: str, message: str = "", severity: str = "medium") -> Finding:
        return Finding(check=check, message=message, severity=severity, location="slug")  # type: ignore[arg-type]

    def test_llm_fixable_check_returns_llm_fixable(self) -> None:
        assert classify_finding(self._f("density", "too short")) == "llm_fixable"

    def test_engineering_only_check_returns_engineering_only(self) -> None:
        assert classify_finding(self._f("safety", "unsafe content")) == "engineering_only"

    def test_slug_safety_returns_engineering_only(self) -> None:
        assert classify_finding(self._f("slug_safety")) == "engineering_only"

    def test_data_fixable_check_returns_data_fixable(self) -> None:
        assert classify_finding(self._f("reference_completeness")) == "data_fixable"

    def test_mixed_engineering_branch(self) -> None:
        # "missing required field" triggers engineering_only sub-class
        result = classify_finding(self._f("frontmatter", "missing required field title"))
        assert result == "engineering_only"

    def test_mixed_llm_branch(self) -> None:
        # Value issue — LLM can fix
        result = classify_finding(self._f("frontmatter", "title is too long"))
        assert result == "llm_fixable"

    def test_mixed_seo_missing_is_engineering(self) -> None:
        result = classify_finding(self._f("seo", "missing description field"))
        assert result == "engineering_only"

    def test_unknown_check_returns_engineering_only(self) -> None:
        # Unknown check → fail-safe engineering_only (don't waste LLM tokens)
        result = classify_finding(self._f("nonexistent_xyz_check"))
        assert result == "engineering_only"

    def test_return_type_is_fix_class_literal(self) -> None:
        valid: set[str] = {"engineering_only", "llm_fixable", "data_fixable"}
        for check in ["density", "safety", "reference_completeness", "frontmatter",
                      "seo", "spec_leakage", "repetition", "unknown_check"]:
            result = classify_finding(self._f(check, "some message"))
            assert result in valid, f"check={check!r} returned unexpected {result!r}"

    def test_empty_check_name_returns_engineering_only(self) -> None:
        result = classify_finding(self._f("", "no check name"))
        assert result == "engineering_only"


class TestReadabilityClassification:
    """TC-3867: readability check registered as LLM_FIXABLE."""

    def test_readability_is_llm_fixable(self) -> None:
        assert classify_check("readability") == "llm_fixable"

    def test_readability_is_healable(self) -> None:
        assert is_healable("readability") is True

    def test_readability_finding_classify(self) -> None:
        f = Finding(check="readability", message="prose is too complex", severity="medium")
        assert classify_finding(f) == "llm_fixable"

    def test_readability_not_in_engineering_only(self) -> None:
        assert "readability" not in ENGINEERING_ONLY_CHECKS

    def test_readability_in_llm_fixable_set(self) -> None:
        assert "readability" in LLM_FIXABLE_CHECKS


class TestIsHealable:
    def test_safety_not_healable(self) -> None:
        assert is_healable("safety") is False

    def test_slug_safety_not_healable(self) -> None:
        assert is_healable("slug_safety") is False

    def test_density_healable(self) -> None:
        assert is_healable("density") is True

    def test_reference_completeness_healable(self) -> None:
        assert is_healable("reference_completeness") is True

    def test_frontmatter_missing_not_healable(self) -> None:
        assert is_healable("frontmatter", "missing required field") is False

    def test_frontmatter_title_healable(self) -> None:
        assert is_healable("frontmatter", "title is not descriptive") is True

    def test_unknown_check_healable(self) -> None:
        # Unknown checks default to healable (conservative: try LLM)
        assert is_healable("some_future_check") is True
