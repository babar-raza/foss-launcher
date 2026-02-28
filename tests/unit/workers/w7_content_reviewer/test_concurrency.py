"""Tests for W7 semantic concurrency fix (TC-3500).

Validates that n_workers is correctly forwarded to semantic_accuracy.check_all()
as the max_parallel_files parameter.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path

from launch.workers.w7_content_reviewer.worker import _run_checks_parallel


class TestSemanticConcurrency:
    """Verify max_parallel_files forwarding to semantic_accuracy.check_all()."""

    @patch("launch.workers.w7_content_reviewer.worker.semantic_accuracy")
    @patch("launch.workers.w7_content_reviewer.worker.content_quality")
    @patch("launch.workers.w7_content_reviewer.worker.technical_accuracy")
    @patch("launch.workers.w7_content_reviewer.worker.usability")
    def test_n_workers_propagates_to_semantic(
        self, mock_us, mock_ta, mock_cq, mock_sa, tmp_path,
    ):
        """n_workers=2 should pass max_parallel_files=2 to semantic check."""
        mock_cq.check_all.return_value = []
        mock_ta.check_all.return_value = []
        mock_us.check_all.return_value = []
        mock_sa.check_all.return_value = []

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        _run_checks_parallel(
            drafts_dir=drafts_dir,
            product_facts={},
            snippet_catalog={},
            evidence_map={},
            page_plan={"pages": []},
            llm_client=MagicMock(),
            n_workers=2,
            include_semantic=True,
        )

        # Verify semantic_accuracy.check_all was called with max_parallel_files=2
        mock_sa.check_all.assert_called_once()
        call_kwargs = mock_sa.check_all.call_args[1]
        assert call_kwargs["max_parallel_files"] == 2

    @patch("launch.workers.w7_content_reviewer.worker.semantic_accuracy")
    @patch("launch.workers.w7_content_reviewer.worker.content_quality")
    @patch("launch.workers.w7_content_reviewer.worker.technical_accuracy")
    @patch("launch.workers.w7_content_reviewer.worker.usability")
    def test_default_concurrency_without_config(
        self, mock_us, mock_ta, mock_cq, mock_sa, tmp_path,
    ):
        """Default n_workers=4 should pass max_parallel_files=4 to semantic."""
        mock_cq.check_all.return_value = []
        mock_ta.check_all.return_value = []
        mock_us.check_all.return_value = []
        mock_sa.check_all.return_value = []

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        _run_checks_parallel(
            drafts_dir=drafts_dir,
            product_facts={},
            snippet_catalog={},
            evidence_map={},
            page_plan={"pages": []},
            llm_client=MagicMock(),
            n_workers=4,
            include_semantic=True,
        )

        call_kwargs = mock_sa.check_all.call_args[1]
        assert call_kwargs["max_parallel_files"] == 4

    @patch("launch.workers.w7_content_reviewer.worker.semantic_accuracy")
    @patch("launch.workers.w7_content_reviewer.worker.content_quality")
    @patch("launch.workers.w7_content_reviewer.worker.technical_accuracy")
    @patch("launch.workers.w7_content_reviewer.worker.usability")
    def test_resolver_and_evidence_forwarded(
        self, mock_us, mock_ta, mock_cq, mock_sa, tmp_path,
    ):
        """resolver and evidence_bundles are forwarded to all check dimensions."""
        mock_cq.check_all.return_value = []
        mock_ta.check_all.return_value = []
        mock_us.check_all.return_value = []
        mock_sa.check_all.return_value = []

        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        sentinel_resolver = object()
        sentinel_bundles = {"page.md": [{"claim_id": "c1"}]}

        _run_checks_parallel(
            drafts_dir=drafts_dir,
            product_facts={},
            snippet_catalog={},
            evidence_map={},
            page_plan={"pages": []},
            llm_client=MagicMock(),
            n_workers=1,
            include_semantic=True,
            resolver=sentinel_resolver,
            evidence_bundles=sentinel_bundles,
        )

        # All dimensions should receive resolver
        assert mock_cq.check_all.call_args[1]["resolver"] is sentinel_resolver
        assert mock_ta.check_all.call_args[1]["resolver"] is sentinel_resolver
        assert mock_us.check_all.call_args[1]["resolver"] is sentinel_resolver
        assert mock_sa.check_all.call_args[1]["resolver"] is sentinel_resolver

        # Semantic should receive evidence_excerpts
        assert mock_sa.check_all.call_args[1]["evidence_excerpts"] == sentinel_bundles
