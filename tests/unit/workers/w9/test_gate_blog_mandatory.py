"""Tests for gate_blog_mandatory (Spec v1.1 J2).

Validates that the blog section of page_plan.json contains at least one
``blog`` (launch/announcement) and one ``feature_blog`` (feature highlight) page.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.launch.workers.w9_validator.gates.gate_blog_mandatory import execute_gate


@pytest.fixture
def tmp_run(tmp_path):
    """Create a minimal run directory with artifacts/."""
    (tmp_path / "artifacts").mkdir()
    return tmp_path


def _write_page_plan(run_dir: Path, pages: list) -> None:
    """Write a minimal page_plan.json."""
    (run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps({"pages": pages}), encoding="utf-8"
    )


class TestGateBlogMandatorySkips:
    def test_no_page_plan_returns_pass(self, tmp_run):
        """Gate skips gracefully when page_plan.json is absent."""
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_invalid_json_returns_fail(self, tmp_run):
        (tmp_run / "artifacts" / "page_plan.json").write_text("NOT JSON", encoding="utf-8")
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False
        assert any("Failed to load" in i["message"] for i in issues)


class TestGateBlogMandatoryPass:
    def test_both_roles_present_passes(self, tmp_run):
        """Gate passes when blog + feature_blog are both present."""
        _write_page_plan(tmp_run, [
            {"section": "blog", "page_role": "blog", "slug": "launch-post"},
            {"section": "blog", "page_role": "feature_blog", "slug": "feature-highlight"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_announcement_alias_passes(self, tmp_run):
        """``announcement`` role counts as the blog/launch role."""
        _write_page_plan(tmp_run, [
            {"section": "blog", "page_role": "announcement", "slug": "launch-post"},
            {"section": "blog", "page_role": "feature_blog", "slug": "feature"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True

    def test_extra_pages_still_pass(self, tmp_run):
        """Additional blog pages beyond the mandatory two do not cause failure."""
        _write_page_plan(tmp_run, [
            {"section": "blog", "page_role": "blog", "slug": "launch"},
            {"section": "blog", "page_role": "feature_blog", "slug": "features"},
            {"section": "blog", "page_role": "landing", "slug": "blog-home"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True


class TestGateBlogMandatoryFail:
    def test_missing_feature_blog_fails(self, tmp_run):
        """Gate fails when feature_blog is missing."""
        _write_page_plan(tmp_run, [
            {"section": "blog", "page_role": "blog", "slug": "launch"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False
        assert any("feature_blog" in i["message"] for i in issues)

    def test_missing_launch_blog_fails(self, tmp_run):
        """Gate fails when launch/blog post is missing."""
        _write_page_plan(tmp_run, [
            {"section": "blog", "page_role": "feature_blog", "slug": "features"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False
        assert any("blog" in i["message"].lower() for i in issues)

    def test_empty_blog_section_fails(self, tmp_run):
        """Gate fails when blog section is completely empty."""
        _write_page_plan(tmp_run, [
            {"section": "docs", "page_role": "workflow_page", "slug": "install"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False

    def test_non_blog_sections_ignored(self, tmp_run):
        """Roles from non-blog sections don't count toward blog mandatory requirement."""
        _write_page_plan(tmp_run, [
            {"section": "kb", "page_role": "blog", "slug": "some-kb-page"},
            {"section": "blog", "page_role": "feature_blog", "slug": "features"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        # blog role is in 'kb' section, not 'blog' — launch post missing
        assert ok is False
