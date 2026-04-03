"""Tests for check_extraction_quality — TC-5308."""
import pytest
from launcher.workers.evaluate.checks.extraction_quality import check_extraction_quality


def _make_ec(overall_completeness, api_class_count=5, api_method_count=20, missing_signals=None):
    class _EC:
        pass
    ec = _EC()
    ec.overall_completeness = overall_completeness
    ec.api_class_count = api_class_count
    ec.api_method_count = api_method_count
    ec.missing_signals = missing_signals or []
    return ec


class TestCheckExtractionQuality:
    def test_none_returns_no_findings(self):
        assert check_extraction_quality("s", "c", "s", extraction_completeness=None) == []

    def test_adequate_no_findings(self):
        assert check_extraction_quality("s", "c", "s", extraction_completeness=_make_ec(0.8)) == []

    def test_at_threshold_no_findings(self):
        # exactly at 0.35 should NOT fire
        assert check_extraction_quality("s", "c", "s", extraction_completeness=_make_ec(0.35)) == []

    def test_thin_fires_medium(self):
        findings = check_extraction_quality("s", "c", "s", extraction_completeness=_make_ec(0.20))
        assert len(findings) == 1
        assert findings[0].severity == "medium"
        assert findings[0].check == "extraction_quality"
        assert "0.20" in findings[0].message

    def test_just_below_threshold_fires_medium(self):
        findings = check_extraction_quality("s", "c", "s", extraction_completeness=_make_ec(0.34))
        assert len(findings) == 1
        assert findings[0].severity == "medium"

    def test_empty_score_fires_high(self):
        findings = check_extraction_quality("s", "c", "s", extraction_completeness=_make_ec(0.05, 0, 0))
        assert len(findings) == 1
        assert findings[0].severity == "high"

    def test_zero_classes_and_methods_fires_high(self):
        findings = check_extraction_quality("s", "c", "s", extraction_completeness=_make_ec(0.25, 0, 0))
        assert len(findings) == 1
        assert findings[0].severity == "high"

    def test_missing_signals_in_message(self):
        ec = _make_ec(0.15, missing_signals=["thin_api", "no_snippets"])
        findings = check_extraction_quality("s", "c", "s", extraction_completeness=ec)
        assert "thin_api" in findings[0].message

    def test_no_overall_completeness_attr_returns_empty(self):
        class _Bare:
            pass
        assert check_extraction_quality("s", "c", "s", extraction_completeness=_Bare()) == []
