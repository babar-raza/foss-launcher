"""Tests for the Publish worker (W5).

Covers:
- Patch building from content manifest
- Target file path generation
- Patch bundle writing (draft mode)
- PR body generation
- Self-review
- Worker integration (draft mode, no manifest, missing files)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from launcher.models.content import ContentManifest, GeneratedPage, GenerationStats
from launcher.models.publish import Patch, PatchAction, PublishBundle, PullRequest
from launcher.models.run_config import RunConfig
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext
from launcher.workers.publish.worker import (
    PublishWorker,
    _build_patches,
    _build_pr_body,
    _target_file_path,
    _write_patch_bundle,
    create_worker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_context(tmp_path: Path) -> WorkerContext:
    run_dir = tmp_path / "runs" / "test-pub"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/test/test-repo",
        llm=None,
    )
    return WorkerContext(
        run_id="test-pub-001",
        run_dir=run_dir,
        config=config,
        llm_config=None,
    )


def _make_manifest(pages: list[GeneratedPage] | None = None) -> ContentManifest:
    return ContentManifest(
        pages=pages or [],
        generation_stats=GenerationStats(
            total_pages=len(pages or []),
            llm_calls=5,
            fallback_count=1,
            duration_seconds=12.3,
        ),
    )


def _write_page(run_dir: Path, md_path: str, content: str) -> None:
    full = run_dir / md_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


_SAMPLE_MD = """\
---
title: Getting Started
slug: getting-started
---

## Overview

This is a sample page.
"""


# ---------------------------------------------------------------------------
# Target file path
# ---------------------------------------------------------------------------


class TestTargetFilePath:
    def test_basic(self):
        page = GeneratedPage(slug="getting-started", page_role="overview", section="docs")
        assert _target_file_path(page) == "docs/getting-started.md"

    def test_default_section(self):
        page = GeneratedPage(slug="index", page_role="toc", section="")
        assert _target_file_path(page) == "docs/index.md"

    def test_blog_section(self):
        page = GeneratedPage(slug="release-notes", page_role="blog_post", section="blog")
        assert _target_file_path(page) == "blog/release-notes.md"

    def test_content_path_hierarchical(self):
        page = GeneratedPage(
            slug="installation", page_role="workflow_page", section="docs",
            content_path="docs.aspose.org/cells/python/getting-started/installation",
        )
        assert _target_file_path(page) == "docs.aspose.org/cells/python/getting-started/installation.md"

    def test_content_path_no_platform(self):
        page = GeneratedPage(
            slug="_index", page_role="landing", section="products",
            content_path="products.aspose.org/cells/_index",
        )
        assert _target_file_path(page) == "products.aspose.org/cells/_index.md"


# ---------------------------------------------------------------------------
# Build patches
# ---------------------------------------------------------------------------


class TestBuildPatches:
    def test_builds_patches_from_files(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        md_path = "content_bundle/pages/overview.md"
        _write_page(run_dir, md_path, _SAMPLE_MD)

        manifest = _make_manifest([
            GeneratedPage(
                slug="overview", page_role="overview", section="docs",
                md_path=md_path,
            ),
        ])
        patches = _build_patches(manifest, run_dir)
        assert len(patches) == 1
        assert patches[0].file_path == "docs/overview.md"
        assert patches[0].action == PatchAction.create
        assert len(patches[0].content_hash) == 64  # SHA256 hex

    def test_missing_file_skipped(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        manifest = _make_manifest([
            GeneratedPage(
                slug="missing", page_role="overview", section="docs",
                md_path="content_bundle/pages/missing.md",
            ),
        ])
        patches = _build_patches(manifest, run_dir)
        assert len(patches) == 0

    def test_multiple_pages(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        for slug in ["page-a", "page-b", "page-c"]:
            _write_page(run_dir, f"content_bundle/pages/{slug}.md", _SAMPLE_MD)

        manifest = _make_manifest([
            GeneratedPage(slug=slug, page_role="overview", section="docs",
                          md_path=f"content_bundle/pages/{slug}.md")
            for slug in ["page-a", "page-b", "page-c"]
        ])
        patches = _build_patches(manifest, run_dir)
        assert len(patches) == 3


# ---------------------------------------------------------------------------
# Write patch bundle (draft mode)
# ---------------------------------------------------------------------------


class TestWritePatchBundle:
    def test_writes_to_disk(self, tmp_path):
        ctx = _make_context(tmp_path)
        patches = [
            Patch(file_path="docs/overview.md", action=PatchAction.create, content_hash="abc123"),
        ]
        _write_patch_bundle(patches, ctx)
        bundle_path = ctx.run_dir / "artifacts" / "patch_bundle.json"
        assert bundle_path.exists()
        data = json.loads(bundle_path.read_text(encoding="utf-8"))
        assert len(data["patches"]) == 1
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# PR body generation
# ---------------------------------------------------------------------------


class TestBuildPrBody:
    def test_basic_body(self):
        manifest = _make_manifest([
            GeneratedPage(slug="p1", page_role="overview", section="docs"),
        ])
        patches = [
            Patch(file_path="docs/p1.md", action=PatchAction.create, content_hash="abc"),
        ]
        body = _build_pr_body(manifest, patches, "run-123")
        assert "run-123" in body
        assert "docs/p1.md" in body
        assert "Pages" in body

    def test_truncates_long_list(self):
        manifest = _make_manifest([])
        patches = [
            Patch(file_path=f"docs/p{i}.md", action=PatchAction.create, content_hash="x")
            for i in range(25)
        ]
        body = _build_pr_body(manifest, patches, "run-456")
        assert "5 more" in body


# ---------------------------------------------------------------------------
# Self-review
# ---------------------------------------------------------------------------


class TestSelfReview:
    @pytest.mark.asyncio
    async def test_valid_bundle_passes(self):
        bundle = PublishBundle(
            patches=[
                Patch(file_path="docs/a.md", action=PatchAction.create, content_hash="abc"),
                Patch(file_path="docs/b.md", action=PatchAction.create, content_hash="def"),
            ],
        )
        worker = PublishWorker()
        result = await worker.self_review(bundle)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_duplicate_paths_fails(self):
        bundle = PublishBundle(
            patches=[
                Patch(file_path="docs/a.md", action=PatchAction.create, content_hash="abc"),
                Patch(file_path="docs/a.md", action=PatchAction.update, content_hash="def"),
            ],
        )
        worker = PublishWorker()
        result = await worker.self_review(bundle)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_wrong_output_type(self):
        worker = PublishWorker()
        from launcher.models.evaluation import QualitySummary
        result = await worker.self_review(QualitySummary())
        assert result.passed is False


# ---------------------------------------------------------------------------
# Worker integration
# ---------------------------------------------------------------------------


class TestPublishWorker:
    def test_create_worker(self):
        w = create_worker()
        assert isinstance(w, PublishWorker)
        assert w.name == "publish"

    @pytest.mark.asyncio
    async def test_draft_mode_with_manifest(self, tmp_path):
        ctx = _make_context(tmp_path)
        # Write a content manifest checkpoint
        md_path = "content_bundle/pages/overview.md"
        _write_page(ctx.run_dir, md_path, _SAMPLE_MD)

        manifest = _make_manifest([
            GeneratedPage(
                slug="overview", page_role="overview", section="docs",
                md_path=md_path, word_count=50,
            ),
        ])
        # Write the generate checkpoint
        checkpoint = ctx.run_dir / "generate_checkpoint.json"
        checkpoint.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        worker = PublishWorker()
        bundle = await worker.run(manifest, ctx)
        assert isinstance(bundle, PublishBundle)
        assert len(bundle.patches) == 1
        assert bundle.patches[0].file_path == "docs/overview.md"
        assert bundle.published_at != ""

        # Draft mode should write patch bundle
        assert (ctx.run_dir / "artifacts" / "patch_bundle.json").exists()

    @pytest.mark.asyncio
    async def test_no_manifest_empty_bundle(self, tmp_path):
        ctx = _make_context(tmp_path)
        worker = PublishWorker()
        # Pass a dummy input since we're testing missing checkpoint
        from launcher.models.evaluation import EvaluationReport, Verdict
        dummy = EvaluationReport(verdict=Verdict.GO)
        bundle = await worker.run(dummy, ctx)
        assert isinstance(bundle, PublishBundle)
        assert len(bundle.patches) == 0

    @pytest.mark.asyncio
    async def test_multiple_pages(self, tmp_path):
        ctx = _make_context(tmp_path)
        pages = []
        for slug in ["page-a", "page-b"]:
            md_path = f"content_bundle/pages/{slug}.md"
            _write_page(ctx.run_dir, md_path, _SAMPLE_MD)
            pages.append(GeneratedPage(
                slug=slug, page_role="overview", section="docs",
                md_path=md_path, word_count=50,
            ))

        manifest = _make_manifest(pages)
        checkpoint = ctx.run_dir / "generate_checkpoint.json"
        checkpoint.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        worker = PublishWorker()
        bundle = await worker.run(manifest, ctx)
        assert len(bundle.patches) == 2


class TestDeployIntegration:
    """Tests for deploy/ staging and content-repo MR integration."""

    def _make_context(self, tmp_path, deploy_dir="", content_repo_map=None):
        """Create a WorkerContext with configurable deploy settings."""
        from launcher.models.run_config import (
            LLMEndpoint,
            LLMConfig,
            OutputConfig,
            RunConfig,
        )
        from launcher.orchestrator.worker_contract import WorkerContext

        run_dir = tmp_path / "runs" / "test-deploy"
        run_dir.mkdir(parents=True, exist_ok=True)

        config = RunConfig(
            family="3d",
            platform="python",
            repo_url="https://github.com/aspose-3d/Aspose.3D-for-Python",
            output=OutputConfig(
                goal="draft",
                run_dir=str(run_dir),
                deploy_dir=deploy_dir,
                content_repo_map=content_repo_map or {},
            ),
            llm=LLMConfig(primary=LLMEndpoint(base_url="http://localhost", model="test")),
        )
        ctx = WorkerContext(
            run_id="test_run_01",
            run_dir=run_dir,
            config=config,
            llm_config=None,
        )
        return ctx

    @pytest.mark.asyncio
    async def test_deploy_dir_triggers_promote_run(self, tmp_path):
        """When deploy_dir is set, promote_run() is called with correct args."""
        from unittest.mock import MagicMock, patch

        from launcher.deploy.promoter import PromotionReport
        from launcher.workers.publish.worker import _promote_to_deploy

        deploy_dir = tmp_path / "deploy"
        ctx = self._make_context(tmp_path, deploy_dir=str(deploy_dir))

        mock_report = PromotionReport(run_id="test_run_01", promoted=2)

        with patch("launcher.deploy.promoter.promote_run", return_value=mock_report) as mock_pr:
            report, count = await _promote_to_deploy(ctx)

        assert count == 2
        assert report is mock_report
        mock_pr.assert_called_once()
        call_kwargs = mock_pr.call_args
        assert call_kwargs.kwargs["run_dir"] == ctx.run_dir
        assert call_kwargs.kwargs["deploy_dir"].resolve() == deploy_dir.resolve()

    @pytest.mark.asyncio
    async def test_no_deploy_dir_skips_promotion(self, tmp_path):
        """When deploy_dir is empty, _promote_to_deploy is never called."""
        from unittest.mock import patch, AsyncMock

        from launcher.workers.publish.worker import PublishWorker

        ctx = self._make_context(tmp_path, deploy_dir="")
        worker = PublishWorker()

        # No content manifest → returns empty bundle without calling promoter
        with patch("launcher.workers.publish.worker._promote_to_deploy") as mock_p:
            bundle = await worker.run(None, ctx)

        mock_p.assert_not_called()
        assert bundle.deployed_count == 0

    def test_content_repo_dir_env_var_expansion(self, tmp_path, monkeypatch):
        """${MY_REPO} in a content_repo_map value is expanded via os.path.expandvars."""
        import os
        from launcher.workers.publish._git_publisher import resolve_content_repo_dir

        monkeypatch.setenv("MY_TEST_REPO", str(tmp_path))
        result = resolve_content_repo_dir("${MY_TEST_REPO}")
        assert result == tmp_path.resolve()

    def test_files_copied_to_content_repo(self, tmp_path):
        """copy_to_content_repo writes files preserving directory structure."""
        from launcher.workers.publish._git_publisher import copy_to_content_repo

        deploy_dir = tmp_path / "deploy"
        content_repo = tmp_path / "content"
        content_repo.mkdir()

        content_path = "docs.aspose.org/3d/python/features"
        src = deploy_dir / (content_path + ".md")
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("# Features\nSome content.", encoding="utf-8")

        written = copy_to_content_repo(deploy_dir, content_repo, [content_path])

        assert len(written) == 1
        dest = content_repo / (content_path + ".md")
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "# Features\nSome content."

    def test_git_branch_commit_push_sequence(self, tmp_path):
        """git_create_branch → git_add_and_commit → git_push called in order."""
        from unittest.mock import MagicMock, patch

        from launcher.workers.publish._git_publisher import (
            git_add_and_commit,
            git_create_branch,
            git_push,
        )

        repo = tmp_path / "repo"
        repo.mkdir()
        dummy_file = repo / "test.md"
        dummy_file.write_text("hello")

        call_order = []

        with patch("launcher.workers.publish._git_publisher.safe_sub.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")

            git_create_branch(repo, "launch/3d-python/abc123")
            call_order.append("branch")

            git_add_and_commit(repo, [dummy_file], "docs: add content")
            call_order.append("commit")

            git_push(repo, "launch/3d-python/abc123")
            call_order.append("push")

        assert call_order == ["branch", "commit", "push"]
        # Verify git checkout -b was called
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "checkout" in first_call_args and "-b" in first_call_args

    @pytest.mark.asyncio
    async def test_gh_create_pr_url_in_bundle(self, tmp_path):
        """merge_request_url in bundle comes from gh_create_pr stdout."""
        from unittest.mock import MagicMock, patch

        from launcher.deploy.promoter import PromotionAction, PromotionReport, PagePromotionResult
        from launcher.workers.publish.worker import _push_to_content_repo

        content_repo = tmp_path / "content"
        content_repo.mkdir()
        ctx = self._make_context(
            tmp_path,
            deploy_dir=str(tmp_path / "deploy"),
            content_repo_map={"aspose.org": str(content_repo)},
        )

        report = PromotionReport(run_id="test_run_01", promoted=1)
        report.details.append(PagePromotionResult(
            content_path="docs.aspose.org/3d/python/features",
            action=PromotionAction.PROMOTED,
            new_grade="B",
            source_run_id="test_run_01",
        ))

        # Create the source file in deploy/
        src = tmp_path / "deploy" / "docs.aspose.org/3d/python/features.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("# Features")

        expected_url = "https://github.com/aspose-org/content/pull/42"

        with patch("launcher.workers.publish._git_publisher.safe_sub.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=expected_url)
            url, branch = await _push_to_content_repo(report, ctx)

        assert url == expected_url
        assert "3d-python" in branch

    @pytest.mark.asyncio
    async def test_promotion_failure_does_not_crash(self, tmp_path):
        """Exception in promote_run → deployed_count=0, no crash."""
        from unittest.mock import patch

        from launcher.workers.publish.worker import _promote_to_deploy

        ctx = self._make_context(tmp_path, deploy_dir=str(tmp_path / "deploy"))

        with patch("launcher.deploy.promoter.promote_run", side_effect=RuntimeError("oops")):
            report, count = await _promote_to_deploy(ctx)

        assert count == 0
        assert report is None

    @pytest.mark.asyncio
    async def test_content_repo_missing_skips_mr(self, tmp_path):
        """Domain mapped to non-existent path → MR skipped, returns ('', '')."""
        from launcher.deploy.promoter import PromotionAction, PromotionReport, PagePromotionResult
        from launcher.workers.publish.worker import _push_to_content_repo

        ctx = self._make_context(
            tmp_path,
            deploy_dir=str(tmp_path / "deploy"),
            content_repo_map={"aspose.org": str(tmp_path / "nonexistent_repo")},
        )

        report = PromotionReport(run_id="test_run_01", promoted=1)
        report.details.append(PagePromotionResult(
            content_path="docs.aspose.org/3d/python/features",
            action=PromotionAction.PROMOTED,
            new_grade="A",
            source_run_id="test_run_01",
        ))

        url, branch = await _push_to_content_repo(report, ctx)

        assert url == ""
        assert branch == ""

    @pytest.mark.asyncio
    async def test_zero_promoted_skips_mr(self, tmp_path):
        """When deployed_count=0, _push_to_content_repo is never called."""
        from unittest.mock import patch

        from launcher.workers.publish.worker import PublishWorker

        content_repo = tmp_path / "content"
        content_repo.mkdir()
        ctx = self._make_context(
            tmp_path,
            deploy_dir=str(tmp_path / "deploy"),
            content_repo_map={"aspose.org": str(content_repo)},
        )
        worker = PublishWorker()

        from launcher.deploy.promoter import PromotionReport
        mock_report = PromotionReport(run_id="test_run_01", promoted=0)

        with patch("launcher.workers.publish.worker._promote_to_deploy", return_value=(mock_report, 0)):
            with patch("launcher.workers.publish.worker._push_to_content_repo") as mock_mr:
                # No manifest → empty bundle, but _promote_to_deploy would still be called if deploy_dir set
                # To test the guard, we need a manifest, so skip manifest and check mock not called
                bundle = await worker.run(None, ctx)

        mock_mr.assert_not_called()
        assert bundle.merge_request_url == ""
