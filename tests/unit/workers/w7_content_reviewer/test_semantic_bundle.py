"""Tests for TC-3617 B1: Bundled semantic check (3-in-1 LLM call).

Verifies that check_semantic_bundle() batches all 3 semantic checks into
a single LLM call, and that check_all() correctly routes through the bundle
when an llm_client is present.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from launch.workers.w7_content_reviewer.checks.semantic_accuracy import (
    check_all,
    check_semantic_bundle,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def product_facts_foss():
    return {
        "product_name": "Aspose.Note FOSS Python",
        "license": "MIT",
        "api_surface_summary": {
            "classes": ["Scene", "Document"],
            "functions": ["load_file"],
            "class_details": [
                {"name": "Scene", "methods": ["save", "load"]},
            ],
        },
    }


@pytest.fixture
def product_facts_non_foss():
    return {
        "product_name": "Aspose.Note Enterprise",
        "license": "Commercial",
        "api_surface_summary": {
            "classes": ["Scene"],
            "functions": [],
            "class_details": [
                {"name": "Scene", "methods": ["save", "load"]},
            ],
        },
    }


def _make_bundle_response(
    api_hallucinations=None, licensing_issues=None, internal_details=None,
):
    """Helper: Build a valid bundle JSON response."""
    return {
        "content": json.dumps({
            "api_hallucinations": api_hallucinations or [],
            "licensing_issues": licensing_issues or [],
            "internal_details": internal_details or [],
        }),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSemanticBundle:
    """TC-3617 B1: Bundled semantic check tests."""

    def test_bundle_makes_one_llm_call(self, product_facts_foss):
        """One file should produce exactly 1 LLM call (not 3)."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response(
            api_hallucinations=[{"name": "Scene.fabricated", "line": 5}],
        )

        content = "# Test\n\n```python\nscene = Scene()\nscene.fabricated()\n```\n"
        issues = check_semantic_bundle(
            content, product_facts_foss, mock_llm, "test.md",
        )

        assert mock_llm.chat_completion.call_count == 1
        assert len(issues) == 1
        assert issues[0]["check"] == "semantic_accuracy.api_hallucination"

    def test_bundle_returns_all_three_check_types(self, product_facts_foss):
        """Bundle should return issues from all 3 check types."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response(
            api_hallucinations=[{"name": "Scene.fake", "line": 3}],
            licensing_issues=[{"term": "commercial license", "line": 10}],
            internal_details=[{"detail": "0xDEADBEEF", "line": 20}],
        )

        content = "# Features\n\n```python\nscene.fake()\n```\n## License\ncommercial\n"
        issues = check_semantic_bundle(
            content, product_facts_foss, mock_llm, "test.md",
        )

        check_types = {i["check"] for i in issues}
        assert "semantic_accuracy.api_hallucination" in check_types
        assert "semantic_accuracy.licensing_accuracy" in check_types
        assert "semantic_accuracy.content_relevance" in check_types
        assert len(issues) == 3

    def test_bundle_fallback_on_timeout(self, product_facts_foss, tmp_path):
        """Bundle timeout should trigger fallback to offline heuristics."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.side_effect = TimeoutError("timeout")

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()
        (drafts_dir / "test.md").write_text(
            "# Test\n\n```python\nscene = Scene()\nscene.nonexistent()\n```\n",
            encoding="utf-8",
        )

        # check_all should not raise — it falls back to offline
        issues = check_all(
            drafts_dir, product_facts_foss, llm_client=mock_llm,
        )
        # Offline heuristic should still find the hallucination
        api_issues = [i for i in issues if "api_hallucination" in i["check"]]
        assert len(api_issues) >= 1

    def test_bundle_fallback_on_parse_error(self, product_facts_foss, tmp_path):
        """Malformed JSON response should trigger fallback to offline."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {"content": "NOT VALID JSON {{{"}

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()
        (drafts_dir / "test.md").write_text(
            "# Test\n\n```python\nscene = Scene()\nscene.nonexistent()\n```\n",
            encoding="utf-8",
        )

        issues = check_all(
            drafts_dir, product_facts_foss, llm_client=mock_llm,
        )
        # Should not crash; offline fallback produces issues
        api_issues = [i for i in issues if "api_hallucination" in i["check"]]
        assert len(api_issues) >= 1

    def test_bundle_n_files_n_calls(self, product_facts_foss, tmp_path):
        """3 files should produce exactly 3 LLM calls (not 9)."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response()

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()
        for i in range(3):
            (drafts_dir / f"page_{i}.md").write_text(
                f"# Page {i}\n\nSome content.\n", encoding="utf-8",
            )

        check_all(
            drafts_dir, product_facts_foss, llm_client=mock_llm,
            max_parallel_files=1,  # Sequential for deterministic call count
        )

        assert mock_llm.chat_completion.call_count == 3

    def test_bundle_parallel_n_files_n_calls(self, product_facts_foss, tmp_path):
        """With max_parallel_files=5 (ThreadPoolExecutor path), N files → N calls (not 3N).

        TC-3617 SR-03: Validates B1 call-count reduction holds under the parallel
        executor path, not just the sequential path tested by test_bundle_n_files_n_calls.
        """
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response()

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()
        for i in range(5):
            (drafts_dir / f"page_{i}.md").write_text(
                f"# Page {i}\n\nSome content {i}.\n", encoding="utf-8",
            )

        check_all(
            drafts_dir, product_facts_foss,
            llm_client=mock_llm,
            max_parallel_files=5,  # explicit: force ThreadPoolExecutor path
        )

        assert mock_llm.chat_completion.call_count == 5, (
            f"Expected 5 LLM calls (N files, not 3N), "
            f"got {mock_llm.chat_completion.call_count}"
        )

    def test_bundle_skips_licensing_for_non_foss(self, product_facts_non_foss):
        """Non-FOSS product should omit licensing section from bundle prompt."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = _make_bundle_response()

        content = "# Test\n## License\ncommercial license terms\n"
        check_semantic_bundle(
            content, product_facts_non_foss, mock_llm, "test.md",
        )

        # Check the prompt sent to LLM contains "NOT APPLICABLE"
        call_args = mock_llm.chat_completion.call_args
        prompt = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][0][0]["content"]
        assert "NOT APPLICABLE" in prompt
