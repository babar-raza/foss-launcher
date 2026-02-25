"""Tests for gate_kb_howto_mandatory (TC-2481b: topic_category-based coverage).

Validates that the KB section of page_plan.json has sufficient how-to pages
covering all mandatory topic categories.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_kb_howto_mandatory import (
    execute_gate,
    _REQUIRED_TOPIC_CATEGORIES,
    _MIN_HOWTO_COUNT,
    _infer_category_from_slug,
)


@pytest.fixture
def tmp_run(tmp_path):
    (tmp_path / "artifacts").mkdir()
    return tmp_path


def _write_page_plan(run_dir: Path, pages: list) -> None:
    (run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps({"pages": pages}), encoding="utf-8"
    )


def _all_required_kb_pages_with_topics():
    """KB how-to pages covering all required topic categories."""
    slug_topic_pairs = [
        ("how-to-load-3d-models-python", "load_file"),
        ("how-to-save-3d-models-python", "save_file"),
        ("how-to-convert-fbx-to-obj", "convert_formats"),
        ("how-to-fix-common-3d-models-errors", "troubleshoot"),
        ("how-to-optimize-3d-models-performance", "optimize_performance"),
    ]
    return [
        {"section": "kb", "page_role": "howto_article", "slug": slug, "topic_category": tc}
        for slug, tc in slug_topic_pairs
    ]


def _all_required_kb_pages_legacy_slugs():
    """KB how-to pages with legacy slugs (no topic_category set)."""
    return [
        {"section": "kb", "page_role": "howto_article", "slug": "how-to-open-a-file"},
        {"section": "kb", "page_role": "howto_article", "slug": "how-to-save-a-file"},
        {"section": "kb", "page_role": "howto_article", "slug": "how-to-convert-formats"},
        {"section": "kb", "page_role": "howto_article", "slug": "how-to-fix-common-errors"},
        {"section": "kb", "page_role": "howto_article", "slug": "how-to-improve-performance"},
    ]


class TestGateKbHowtoSkips:
    def test_no_page_plan_skips(self, tmp_run):
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_invalid_json_fails(self, tmp_run):
        (tmp_run / "artifacts" / "page_plan.json").write_text("NOT JSON", encoding="utf-8")
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False


class TestGateKbHowtoPass:
    def test_all_topic_categories_present(self, tmp_run):
        _write_page_plan(tmp_run, _all_required_kb_pages_with_topics())
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_extra_kb_pages_allowed(self, tmp_run):
        pages = _all_required_kb_pages_with_topics() + [
            {"section": "kb", "page_role": "howto_article", "slug": "how-to-merge-documents"},
        ]
        _write_page_plan(tmp_run, pages)
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True

    def test_how_to_alias_role_accepted(self, tmp_run):
        """how_to and howto role aliases should count."""
        pages = [
            {"section": "kb", "page_role": "how_to", "slug": "how-to-load-files", "topic_category": "load_file"},
            {"section": "kb", "page_role": "howto", "slug": "how-to-convert-docs", "topic_category": "convert_formats"},
            {"section": "kb", "page_role": "howto_article", "slug": "how-to-save-files", "topic_category": "save_file"},
            {"section": "kb", "page_role": "how_to", "slug": "how-to-fix-errors", "topic_category": "troubleshoot"},
            {"section": "kb", "page_role": "howto_article", "slug": "how-to-optimize", "topic_category": "optimize_performance"},
        ]
        _write_page_plan(tmp_run, pages)
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True

    def test_legacy_slugs_inferred_categories(self, tmp_run):
        """Legacy page plans without topic_category should infer categories from slugs."""
        _write_page_plan(tmp_run, _all_required_kb_pages_legacy_slugs())
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True


class TestGateKbHowtoFail:
    def test_missing_topic_category_fails(self, tmp_run):
        pages = [
            {"section": "kb", "page_role": "howto_article", "slug": "how-to-load", "topic_category": "load_file"},
            {"section": "kb", "page_role": "howto_article", "slug": "how-to-save", "topic_category": "save_file"},
            # missing: convert_formats, troubleshoot, optimize_performance
        ]
        _write_page_plan(tmp_run, pages)
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False
        assert any("TOPIC_MISSING" in i["error_code"] for i in issues)

    def test_empty_plan_fails(self, tmp_run):
        _write_page_plan(tmp_run, [])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False

    def test_insufficient_count_fails(self, tmp_run):
        """Fewer than 5 how-to pages should fail count check."""
        pages = [
            {"section": "kb", "page_role": "howto_article", "slug": "how-to-load", "topic_category": "load_file"},
            {"section": "kb", "page_role": "howto_article", "slug": "how-to-save", "topic_category": "save_file"},
        ]
        _write_page_plan(tmp_run, pages)
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False
        assert any("COUNT" in i["error_code"] for i in issues)

    def test_wrong_section_not_counted(self, tmp_run):
        """KB slugs in the docs section don't satisfy the KB requirement."""
        pages = [
            {"section": "docs", "page_role": "howto_article", "slug": "how-to-load", "topic_category": "load_file"},
        ]
        _write_page_plan(tmp_run, pages)
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False


class TestInferCategoryFromSlug:
    def test_open_infers_load_file(self):
        assert _infer_category_from_slug("how-to-open-a-file") == "load_file"

    def test_load_infers_load_file(self):
        assert _infer_category_from_slug("how-to-load-3d-models-python") == "load_file"

    def test_save_infers_save_file(self):
        assert _infer_category_from_slug("how-to-save-a-file") == "save_file"

    def test_convert_infers_convert_formats(self):
        assert _infer_category_from_slug("how-to-convert-xlsx-to-csv") == "convert_formats"

    def test_fix_infers_troubleshoot(self):
        assert _infer_category_from_slug("how-to-fix-common-errors") == "troubleshoot"

    def test_performance_infers_optimize(self):
        assert _infer_category_from_slug("how-to-improve-performance") == "optimize_performance"

    def test_unknown_slug_returns_empty(self):
        assert _infer_category_from_slug("how-to-frobulate") == ""


class TestDeprecationWarning:
    """TC-2612: Verify deprecation warning for slug-based inference."""

    def test_legacy_slugs_emit_deprecation_warning(self, tmp_run):
        """Legacy page plans without topic_category emit DeprecationWarning."""
        import warnings
        _write_page_plan(tmp_run, _all_required_kb_pages_legacy_slugs())
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ok, issues = execute_gate(tmp_run, "local")
        # At least one DeprecationWarning should be emitted
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1
        assert "slug-based topic_category inference is deprecated" in str(dep_warnings[0].message).lower()

    def test_explicit_topic_category_no_deprecation(self, tmp_run):
        """Page plans with explicit topic_category do not emit DeprecationWarning."""
        import warnings
        _write_page_plan(tmp_run, _all_required_kb_pages_with_topics())
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ok, issues = execute_gate(tmp_run, "local")
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0


class TestConstants:
    def test_required_topic_categories_is_frozen_set(self):
        assert isinstance(_REQUIRED_TOPIC_CATEGORIES, frozenset)
        assert len(_REQUIRED_TOPIC_CATEGORIES) == 5

    def test_min_howto_count(self):
        assert _MIN_HOWTO_COUNT == 5
