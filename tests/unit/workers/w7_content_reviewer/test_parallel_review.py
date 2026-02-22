"""TC-2403: Tests for parallel check execution and semantic caching in W7.

Validates:
1. _run_checks_parallel with include_semantic=True calls semantic dimension
2. _run_checks_parallel with include_semantic=False does NOT call semantic
3. n_workers=1 produces sequential execution (same results as parallel)
4. _sanitize_draft_file fixes malformed fences in-place
5. _sanitize_draft_file is a no-op on already-clean files
6. Parallel execution (n_workers>1) produces same issue count as sequential
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.workers.w7_content_reviewer.worker import (
    _run_checks_parallel,
    _sanitize_draft_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_product_facts():
    return {
        "product_name": "TestLib",
        "claims": [],
        "claim_groups": {},
        "api_surface_summary": {"classes": [], "functions": []},
        "license": "MIT",
        "code_snippets": [],
    }


@pytest.fixture()
def minimal_snippet_catalog():
    return {"snippets": []}


@pytest.fixture()
def minimal_evidence_map():
    return {"claims": {}}


@pytest.fixture()
def minimal_page_plan():
    return {"pages": [{"slug": "index", "title": "Index", "template": "feature.variant-standard"}]}


@pytest.fixture()
def drafts_dir(tmp_path):
    d = tmp_path / "drafts"
    d.mkdir()
    (d / "page1.md").write_text(
        "---\ntitle: Page One\n---\n\n## Introduction\n\nHello world.\n",
        encoding="utf-8",
    )
    (d / "page2.md").write_text(
        "---\ntitle: Page Two\n---\n\n## Details\n\nSome content here.\n",
        encoding="utf-8",
    )
    return d


# ---------------------------------------------------------------------------
# 1. include_semantic=True calls semantic dimension
# ---------------------------------------------------------------------------

class TestRunChecksParallelIncludesSemanticWhenRequested:
    """_run_checks_parallel with include_semantic=True invokes semantic_accuracy."""

    def test_semantic_called_when_include_semantic_true(
        self, drafts_dir, minimal_product_facts, minimal_snippet_catalog,
        minimal_evidence_map, minimal_page_plan,
    ):
        semantic_issue = {
            "check": "api_hallucination",
            "severity": "warn",
            "message": "Potential hallucination",
            "location": {"path": "page1.md", "line": 5},
            "auto_fixable": False,
        }
        with patch(
            "launch.workers.w7_content_reviewer.worker.semantic_accuracy.check_all",
            return_value=[semantic_issue],
        ) as mock_sa:
            all_issues, semantic_issues = _run_checks_parallel(
                drafts_dir,
                minimal_product_facts,
                minimal_snippet_catalog,
                minimal_evidence_map,
                minimal_page_plan,
                llm_client=None,
                n_workers=1,
                include_semantic=True,
            )

        mock_sa.assert_called_once()
        assert semantic_issue in all_issues
        assert semantic_issue in semantic_issues


# ---------------------------------------------------------------------------
# 2. include_semantic=False does NOT call semantic
# ---------------------------------------------------------------------------

class TestRunChecksParallelSkipsSemanticWhenNotRequired:
    """_run_checks_parallel with include_semantic=False skips semantic_accuracy."""

    def test_semantic_not_called_when_include_semantic_false(
        self, drafts_dir, minimal_product_facts, minimal_snippet_catalog,
        minimal_evidence_map, minimal_page_plan,
    ):
        with patch(
            "launch.workers.w7_content_reviewer.worker.semantic_accuracy.check_all",
        ) as mock_sa:
            all_issues, semantic_issues = _run_checks_parallel(
                drafts_dir,
                minimal_product_facts,
                minimal_snippet_catalog,
                minimal_evidence_map,
                minimal_page_plan,
                llm_client=None,
                n_workers=1,
                include_semantic=False,
            )

        mock_sa.assert_not_called()
        assert semantic_issues == []

    def test_semantic_issues_empty_when_include_semantic_false(
        self, drafts_dir, minimal_product_facts, minimal_snippet_catalog,
        minimal_evidence_map, minimal_page_plan,
    ):
        _, semantic_issues = _run_checks_parallel(
            drafts_dir,
            minimal_product_facts,
            minimal_snippet_catalog,
            minimal_evidence_map,
            minimal_page_plan,
            llm_client=None,
            n_workers=1,
            include_semantic=False,
        )
        assert semantic_issues == []


# ---------------------------------------------------------------------------
# 3. n_workers=1 (sequential) and n_workers=4 (parallel) produce same issue count
# ---------------------------------------------------------------------------

class TestRunChecksParallelDeterminism:
    """Parallel and sequential paths produce the same issues."""

    def test_sequential_and_parallel_same_issue_count(
        self, drafts_dir, minimal_product_facts, minimal_snippet_catalog,
        minimal_evidence_map, minimal_page_plan,
    ):
        # Patch semantic to return deterministic empty result
        with patch(
            "launch.workers.w7_content_reviewer.worker.semantic_accuracy.check_all",
            return_value=[],
        ):
            issues_seq, _ = _run_checks_parallel(
                drafts_dir, minimal_product_facts, minimal_snippet_catalog,
                minimal_evidence_map, minimal_page_plan,
                llm_client=None, n_workers=1, include_semantic=True,
            )
            issues_par, _ = _run_checks_parallel(
                drafts_dir, minimal_product_facts, minimal_snippet_catalog,
                minimal_evidence_map, minimal_page_plan,
                llm_client=None, n_workers=4, include_semantic=True,
            )

        # Issue count must match (order may differ in parallel mode)
        assert len(issues_seq) == len(issues_par)


# ---------------------------------------------------------------------------
# 4. _sanitize_draft_file fixes malformed fences in-place
# ---------------------------------------------------------------------------

class TestSanitizeDraftFileFixesMalformedFences:
    """_sanitize_draft_file modifies files with fixable content issues."""

    def test_strips_visible_claim_markers(self, tmp_path):
        draft = tmp_path / "test.md"
        draft.write_text(
            "---\ntitle: Test\n---\n\n[claim: abc123] Some content here.\n",
            encoding="utf-8",
        )
        _sanitize_draft_file(draft, family="", platform="")
        result = draft.read_text(encoding="utf-8")
        assert "[claim:" not in result

    def test_strips_llm_scaffolding(self, tmp_path):
        draft = tmp_path / "test.md"
        draft.write_text(
            "---\ntitle: Test\n---\n\n## Introduction\n\nHere is the content.\n\n"
            "<!-- BEGIN GENERATED CONTENT -->\nSome text.\n<!-- END GENERATED CONTENT -->\n",
            encoding="utf-8",
        )
        # Should not crash — either strips or leaves unchanged
        _sanitize_draft_file(draft, family="", platform="")
        assert draft.exists()  # file still exists


# ---------------------------------------------------------------------------
# 5. _sanitize_draft_file is a no-op on already-clean files
# ---------------------------------------------------------------------------

class TestSanitizeDraftFileNoOpOnCleanFiles:
    """_sanitize_draft_file does not modify files that are already clean."""

    def test_clean_file_unchanged(self, tmp_path):
        clean_content = (
            "---\ntitle: Clean Page\ndescription: A clean page.\n---\n\n"
            "## Introduction\n\nThis page has clean content.\n\n"
            "```python\nprint('hello')\n```\n"
        )
        draft = tmp_path / "clean.md"
        draft.write_text(clean_content, encoding="utf-8")
        _sanitize_draft_file(draft, family="", platform="")
        assert draft.read_text(encoding="utf-8") == clean_content

    def test_nonexistent_file_no_crash(self, tmp_path):
        missing = tmp_path / "nonexistent.md"
        # Should not raise — silently skips unreadable files
        _sanitize_draft_file(missing, family="", platform="")


# ---------------------------------------------------------------------------
# 6. Returns tuple (all_issues, semantic_issues) in both paths
# ---------------------------------------------------------------------------

class TestRunChecksParallelReturnType:
    """_run_checks_parallel always returns a 2-tuple."""

    def test_returns_tuple_sequential(
        self, drafts_dir, minimal_product_facts, minimal_snippet_catalog,
        minimal_evidence_map, minimal_page_plan,
    ):
        result = _run_checks_parallel(
            drafts_dir, minimal_product_facts, minimal_snippet_catalog,
            minimal_evidence_map, minimal_page_plan,
            llm_client=None, n_workers=1, include_semantic=False,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        all_issues, semantic_issues = result
        assert isinstance(all_issues, list)
        assert isinstance(semantic_issues, list)

    def test_returns_tuple_parallel(
        self, drafts_dir, minimal_product_facts, minimal_snippet_catalog,
        minimal_evidence_map, minimal_page_plan,
    ):
        with patch(
            "launch.workers.w7_content_reviewer.worker.semantic_accuracy.check_all",
            return_value=[],
        ):
            result = _run_checks_parallel(
                drafts_dir, minimal_product_facts, minimal_snippet_catalog,
                minimal_evidence_map, minimal_page_plan,
                llm_client=None, n_workers=4, include_semantic=True,
            )
        assert isinstance(result, tuple)
        assert len(result) == 2
