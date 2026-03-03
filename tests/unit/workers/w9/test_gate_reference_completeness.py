"""Unit tests for gate_reference_completeness (TC-3676).

Tests that reference pages are checked for code fences, API tables,
and object_name mentions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.workers.w9_validator.gates.gate_reference_completeness import (
    _extract_code_fences,
    _has_api_table,
    _is_placeholder,
    execute_gate,
)


# ── Helper: create a minimal run_dir structure ───────────────────────────


def _setup_run(tmp_path: Path, pages, files=None):
    """Create a run_dir with page_plan and optional markdown files.

    Args:
        tmp_path: pytest tmp_path fixture.
        pages: List of page dicts for page_plan.json.
        files: Dict of {relative_path: content} for markdown files.
    """
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    plan = {"pages": pages}
    (artifacts / "page_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    if files:
        site_dir = tmp_path / "work" / "site" / "content"
        site_dir.mkdir(parents=True)
        for rel_path, content in files.items():
            fpath = site_dir / rel_path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")


# ── _extract_code_fences tests ───────────────────────────────────────────


class TestExtractCodeFences:
    def test_single_fence(self):
        content = "text\n```python\nx = 1\n```\nmore"
        fences = _extract_code_fences(content)
        assert len(fences) == 1
        assert "x = 1" in fences[0]

    def test_multiple_fences(self):
        content = "```\nA\n```\n\n```\nB\n```"
        fences = _extract_code_fences(content)
        assert len(fences) == 2

    def test_no_fences(self):
        assert _extract_code_fences("Just text.") == []


# ── _is_placeholder tests ───────────────────────────────────────────────


class TestIsPlaceholder:
    def test_pass_only(self):
        assert _is_placeholder("pass") is True

    def test_todo_comment(self):
        assert _is_placeholder("# TODO: implement") is True

    def test_placeholder_comment(self):
        assert _is_placeholder("# No code example available for this section.\n# See the Getting Started guide for working examples.\npass") is True

    def test_real_code(self):
        assert _is_placeholder("from aspose.cells import Workbook\nwb = Workbook()") is False

    def test_empty(self):
        assert _is_placeholder("") is True


# ── _has_api_table tests ────────────────────────────────────────────────


class TestHasApiTable:
    def test_with_api_table(self):
        content = (
            "## API Summary\n\n"
            "| Method | Return Type | Description |\n"
            "|--------|-------------|-------------|\n"
            "| load() | Workbook | Load a file |\n"
        )
        assert _has_api_table(content) is True

    def test_without_table(self):
        assert _has_api_table("Just text, no tables.") is False

    def test_table_without_api_headers(self):
        content = (
            "| Name | Age |\n"
            "|------|-----|\n"
            "| Alice | 30 |\n"
        )
        assert _has_api_table(content) is False

    def test_table_inside_fence_ignored(self):
        content = (
            "```\n"
            "| Method | Description |\n"
            "|--------|-------------|\n"
            "```\n"
        )
        assert _has_api_table(content) is False


# ── execute_gate integration tests ──────────────────────────────────────


class TestExecuteGate:
    def test_no_page_plan_passes(self, tmp_path):
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_no_reference_pages_passes(self, tmp_path):
        _setup_run(tmp_path, [
            {"page_role": "landing", "slug": "index"},
        ])
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_valid_reference_page_passes(self, tmp_path):
        content = (
            "---\ntitle: API Reference\n---\n"
            "## Overview\n\nThe Workbook class.\n\n"
            "## API Summary\n\n"
            "| Method | Return Type | Description |\n"
            "|--------|-------------|-------------|\n"
            "| load() | Workbook | Load a file |\n\n"
            "## Example\n\n"
            "```python\nfrom aspose.cells import Workbook\nwb = Workbook()\n```\n"
        )
        _setup_run(tmp_path,
            [{"page_role": "api_reference", "slug": "api-ref", "object_name": "Workbook"}],
            {"api-ref.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True

    def test_missing_code_fence_fails(self, tmp_path):
        content = (
            "---\ntitle: API Reference\n---\n"
            "## Overview\n\nThe Workbook class.\n\n"
            "## API Summary\n\n"
            "| Method | Return Type | Description |\n"
            "|--------|-------------|-------------|\n"
            "| load() | Workbook | Load a file |\n"
        )
        _setup_run(tmp_path,
            [{"page_role": "api_reference", "slug": "api-ref"}],
            {"api-ref.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert any(i["error_code"] == "REF_MISSING_CODE_FENCE" for i in issues)

    def test_placeholder_code_fails(self, tmp_path):
        content = (
            "---\ntitle: API Reference\n---\n"
            "## Overview\n\nAPI docs.\n\n"
            "| Method | Description |\n|---|---|\n| load() | Load |\n\n"
            "```python\npass\n```\n"
        )
        _setup_run(tmp_path,
            [{"page_role": "api_reference", "slug": "api-ref"}],
            {"api-ref.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert any(i["error_code"] == "REF_PLACEHOLDER_CODE" for i in issues)

    def test_missing_api_table_fails(self, tmp_path):
        content = (
            "---\ntitle: API Reference\n---\n"
            "## Overview\n\nAPI docs.\n\n"
            "```python\nfrom aspose.cells import Workbook\n```\n"
        )
        _setup_run(tmp_path,
            [{"page_role": "api_reference", "slug": "api-ref"}],
            {"api-ref.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert any(i["error_code"] == "REF_MISSING_API_TABLE" for i in issues)

    def test_missing_object_name_warns(self, tmp_path):
        content = (
            "---\ntitle: API Reference\n---\n"
            "## Overview\n\nSome general API docs.\n\n"
            "| Method | Description |\n|---|---|\n| load() | Load |\n\n"
            "```python\nimport aspose\n```\n"
        )
        _setup_run(tmp_path,
            [{"page_role": "api_reference", "slug": "api-ref", "object_name": "Workbook"}],
            {"api-ref.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        # Object name is warn, not error — gate still passes
        warn_issues = [i for i in issues if i["error_code"] == "REF_MISSING_OBJECT_NAME"]
        assert len(warn_issues) == 1
        assert warn_issues[0]["severity"] == "warn"

    def test_reference_object_page_checked(self, tmp_path):
        content = "---\ntitle: Class Ref\n---\nNo code or tables here."
        _setup_run(tmp_path,
            [{"page_role": "reference_object_page", "slug": "class-ref"}],
            {"class-ref.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        codes = {i["error_code"] for i in issues}
        assert "REF_MISSING_CODE_FENCE" in codes
        assert "REF_MISSING_API_TABLE" in codes
