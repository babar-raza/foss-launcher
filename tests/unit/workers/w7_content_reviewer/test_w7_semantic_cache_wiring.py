"""Integration tests for SR-01: B2 cache wired into W7 worker.py.

TC-3617 SR-01: Verifies that when W7 worker passes run_dir to check_all(), the cache
is populated on first run and subsequent calls with identical content make zero LLM calls.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from launch.workers.w7_content_reviewer.checks.semantic_accuracy import check_all


def _make_product_facts():
    return {
        "product_name": "Aspose.Note FOSS Python",
        "license": "MIT",
        "api_surface_summary": {
            "classes": ["Document"],
            "functions": ["load"],
            "class_details": [],
        },
    }


def _make_bundle_response():
    return {
        "content": json.dumps({
            "api_hallucinations": [],
            "licensing_issues": [],
            "internal_details": [],
        })
    }


class TestCacheWiringEndToEnd:
    """TC-3617 SR-01: Proves B2 cache is populated and hit when run_dir is passed."""

    def test_first_call_populates_cache(self, tmp_path):
        """First call with run_dir=... creates semantic_cache.json in artifacts/."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response()

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()
        (drafts_dir / "page.md").write_text("# Test\n\nContent.\n", encoding="utf-8")

        check_all(
            drafts_dir, _make_product_facts(),
            llm_client=mock_llm, run_dir=tmp_path,
        )

        cache_path = tmp_path / "artifacts" / "semantic_cache.json"
        assert cache_path.exists(), "Cache file must be created after first run"
        cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
        assert isinstance(cache_data, dict), "Cache must be a JSON object"
        assert len(cache_data) == 1, "Cache must have 1 entry (1 file processed)"

    def test_second_call_hits_cache_zero_llm(self, tmp_path):
        """Second call with identical content makes zero LLM calls (cache hit)."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response()

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()
        (drafts_dir / "page.md").write_text("# Test\n\nContent.\n", encoding="utf-8")

        # First run — populates cache
        check_all(
            drafts_dir, _make_product_facts(),
            llm_client=mock_llm, run_dir=tmp_path,
        )
        assert mock_llm.chat_completion.call_count == 1

        # Reset mock to track second run independently
        mock_llm.reset_mock()

        # Second run — must hit cache
        check_all(
            drafts_dir, _make_product_facts(),
            llm_client=mock_llm, run_dir=tmp_path,
        )

        assert mock_llm.chat_completion.call_count == 0, (
            "Second run with identical content must make zero LLM calls (cache hit)"
        )

    def test_content_change_invalidates_cache(self, tmp_path):
        """Changing file content triggers a cache miss on next call."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response()

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()
        page = drafts_dir / "page.md"
        page.write_text("# Test\n\nOriginal content.\n", encoding="utf-8")

        # First run
        check_all(
            drafts_dir, _make_product_facts(),
            llm_client=mock_llm, run_dir=tmp_path,
        )
        mock_llm.reset_mock()

        # Modify content
        page.write_text("# Test\n\nModified content — entirely different.\n", encoding="utf-8")

        # Second run — must be a cache miss
        check_all(
            drafts_dir, _make_product_facts(),
            llm_client=mock_llm, run_dir=tmp_path,
        )

        assert mock_llm.chat_completion.call_count == 1, (
            "Modified content must trigger a cache miss and one new LLM call"
        )

    def test_no_run_dir_still_works(self, tmp_path):
        """Backward compat: check_all without run_dir still works (no cache, no crash)."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response()

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()
        (drafts_dir / "page.md").write_text("# Test\n\nContent.\n", encoding="utf-8")

        # Must not raise even without run_dir
        issues = check_all(
            drafts_dir, _make_product_facts(),
            llm_client=mock_llm,
            # run_dir intentionally omitted
        )

        assert isinstance(issues, list)
        assert mock_llm.chat_completion.call_count == 1
        # No cache file should be created
        assert not (tmp_path / "artifacts" / "semantic_cache.json").exists()
