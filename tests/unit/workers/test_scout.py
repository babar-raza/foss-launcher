"""Tests for the Scout worker (Phase 2 — TC-4075/TC-4076).

Covers:
- ScoutWorker produces ScoutBundle with correct repo_info
- ScoutWorker sets context.repo_content (fresh run)
- ScoutWorker self_review passes on non-empty repo
- ScoutWorker self_review fails (high) on empty repo
- ScoutWorker writes scout_bundle.json artifact
- ScoutBundle has correct identity pass-through from IntakeBundle
- ScoutBundle round-trips (model_validate / model_dump)
- Resume path: UnderstandWorker re-reads files when context.repo_content is empty
- understand/scout.py re-export shim still works

TC: TC-4075, TC-4076
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from launcher.models.intake import IntakeBundle
from launcher.models.run_config import RunConfig
from launcher.models.scout import ScoutBundle
from launcher.models.understanding import RepoInfo
from launcher.orchestrator.worker_contract import WorkerContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_intake(repo_dir: str, *, launch_tier: str = "core") -> IntakeBundle:
    return IntakeBundle(
        family="cells",
        platform="python",
        repo_url="https://github.com/aspose/aspose-cells-foss-python",
        display_name="Aspose.Cells FOSS for Python",
        canonical_import="aspose_cells_foss",
        runtime_import="aspose.cells",
        launch_tier=launch_tier,  # type: ignore[arg-type]
        repo_dir=repo_dir,
        repo_sha="abc123",
    )


def _make_context(tmp_path: Path) -> WorkerContext:
    config = RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/aspose/aspose-cells-foss-python",
    )
    return WorkerContext(run_id="test-scout", run_dir=tmp_path, config=config)


def _fake_repo(tmp_path: Path) -> Path:
    """Create a minimal fake repo for Scout tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\nA test repo.\n")
    (repo / "pyproject.toml").write_text(
        "[project]\nname = \"test-pkg\"\nversion = \"1.0.0\"\n"
    )
    src = repo / "src" / "testpkg"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text('"""Test package."""\n')
    (src / "core.py").write_text(
        textwrap.dedent("""\
        class TestClass:
            \"\"\"A test class.\"\"\"
            def method(self) -> None:
                pass
        """)
    )
    return repo


# ---------------------------------------------------------------------------
# ScoutBundle model tests
# ---------------------------------------------------------------------------


class TestScoutBundleModel:
    def test_scout_bundle_instantiation(self):
        """ScoutBundle can be created with required fields."""
        bundle = ScoutBundle(
            family="cells",
            platform="python",
            repo_url="https://example.com/repo",
            display_name="Test Product",
            canonical_import="test_pkg",
            launch_tier="core",
            repo_dir="/tmp/repo",
        )
        assert bundle.family == "cells"
        assert bundle.platform == "python"
        assert bundle.canonical_import == "test_pkg"
        assert bundle.budget_log == []
        assert bundle.budget_log_overflow_count == 0
        assert isinstance(bundle.repo_info, RepoInfo)

    def test_scout_bundle_round_trips(self):
        """ScoutBundle serializes and deserializes correctly."""
        bundle = ScoutBundle(
            family="note",
            platform="java",
            repo_url="https://example.com/repo",
            display_name="Test Note",
            canonical_import="aspose.note",
            runtime_import="aspose.note",
            launch_tier="full",
            repo_dir="/tmp/repo",
            repo_sha="deadbeef",
            budget_log=[{"path": "file.py", "reason": "budget_exceeded"}],
            budget_log_overflow_count=5,
        )
        data = bundle.model_dump()
        restored = ScoutBundle.model_validate(data)
        assert restored.family == "note"
        assert restored.platform == "java"
        assert restored.budget_log_overflow_count == 5
        assert len(restored.budget_log) == 1

    def test_scout_bundle_identity_fields(self):
        """All IntakeBundle identity fields are present in ScoutBundle."""
        intake = IntakeBundle(
            family="words",
            platform="dotnet",
            repo_url="https://example.com/repo",
            display_name="Aspose.Words for .NET",
            canonical_import="Aspose.Words",
            runtime_import="Aspose.Words",
            launch_tier="minimal",
            repo_dir="/tmp/repo",
            repo_sha="cafebabe",
            discovered_at="2026-01-01T00:00:00Z",
        )
        # Simulate what ScoutWorker would produce
        bundle = ScoutBundle(
            family=intake.family,
            platform=intake.platform,
            repo_url=intake.repo_url,
            display_name=intake.display_name,
            canonical_import=intake.canonical_import,
            runtime_import=intake.runtime_import,
            launch_tier=intake.launch_tier,
            repo_sha=intake.repo_sha,
            repo_dir=intake.repo_dir,
            discovered_at=intake.discovered_at,
        )
        assert bundle.family == intake.family
        assert bundle.platform == intake.platform
        assert bundle.display_name == intake.display_name
        assert bundle.canonical_import == intake.canonical_import
        assert bundle.runtime_import == intake.runtime_import
        assert bundle.launch_tier == intake.launch_tier
        assert bundle.repo_sha == intake.repo_sha
        assert bundle.discovered_at == intake.discovered_at


# ---------------------------------------------------------------------------
# ScoutWorker tests
# ---------------------------------------------------------------------------


class TestScoutWorker:
    @pytest.mark.asyncio
    async def test_scout_produces_bundle_with_repo_info(self, tmp_path: Path):
        """ScoutWorker produces ScoutBundle with non-empty repo_info."""
        from launcher.workers.scout.worker import ScoutWorker

        repo = _fake_repo(tmp_path)
        intake = _make_intake(str(repo))
        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        result = await worker.run(intake, ctx)

        assert isinstance(result, ScoutBundle)
        assert len(result.repo_info.file_tree) > 0
        assert result.repo_info.content_files_read > 0

    @pytest.mark.asyncio
    async def test_scout_sets_context_repo_content(self, tmp_path: Path):
        """After ScoutWorker.run(), context.repo_content is populated."""
        from launcher.workers.scout.worker import ScoutWorker

        repo = _fake_repo(tmp_path)
        intake = _make_intake(str(repo))
        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        await worker.run(intake, ctx)

        assert ctx.repo_content  # non-empty dict
        assert isinstance(ctx.repo_content, dict)
        # README.md should be in content
        assert any("README" in k for k in ctx.repo_content)

    @pytest.mark.asyncio
    async def test_scout_identity_pass_through(self, tmp_path: Path):
        """ScoutBundle contains identical identity fields from IntakeBundle."""
        from launcher.workers.scout.worker import ScoutWorker

        repo = _fake_repo(tmp_path)
        intake = _make_intake(str(repo))
        intake_dict = intake.model_dump()
        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        result = await worker.run(intake, ctx)

        assert result.family == intake_dict["family"]
        assert result.platform == intake_dict["platform"]
        assert result.canonical_import == intake_dict["canonical_import"]
        assert result.runtime_import == intake_dict["runtime_import"]
        assert result.launch_tier == intake_dict["launch_tier"]
        assert result.repo_sha == intake_dict["repo_sha"]
        assert result.repo_dir == intake_dict["repo_dir"]

    @pytest.mark.asyncio
    async def test_scout_artifact_written(self, tmp_path: Path):
        """Scout writes both summary and reviewable inventory artifacts."""
        from launcher.workers.scout.worker import ScoutWorker
        import json

        repo = _fake_repo(tmp_path)
        intake = _make_intake(str(repo))
        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        await worker.run(intake, ctx)

        artifact_path = tmp_path / "scout_bundle.json"
        assert artifact_path.exists(), "scout_bundle.json not written"
        data = json.loads(artifact_path.read_text())
        assert "files_enumerated" in data
        assert data["files_enumerated"] > 0
        inventory_path = tmp_path / "scout_inventory.json"
        assert inventory_path.exists(), "scout_inventory.json not written"
        inventory = json.loads(inventory_path.read_text())
        assert "doc_selection" in inventory
        assert "example_selection" in inventory

    @pytest.mark.asyncio
    async def test_scout_shared_facts_from_python_manifest(self, tmp_path: Path):
        """pyproject.toml present → shared_facts.package_name is set."""
        from launcher.workers.scout.worker import ScoutWorker

        repo = _fake_repo(tmp_path)
        intake = _make_intake(str(repo))
        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        result = await worker.run(intake, ctx)

        assert result.repo_info.shared_facts.package_name == "test-pkg"

    @pytest.mark.asyncio
    async def test_scout_shared_facts_infers_java_from_pom(self, tmp_path: Path):
        from launcher.workers.scout.worker import ScoutWorker

        repo = tmp_path / "java_repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Java Repo\n", encoding="utf-8")
        (repo / "pom.xml").write_text(
            "<project><groupId>org.example</groupId><artifactId>demo</artifactId><version>1.0.0</version></project>",
            encoding="utf-8",
        )
        src = repo / "src" / "main" / "java" / "org" / "example"
        src.mkdir(parents=True)
        (src / "App.java").write_text("package org.example; public class App {}\n", encoding="utf-8")

        intake = _make_intake(str(repo)).model_copy(update={"platform": "java", "runtime_import": ""})
        ctx = WorkerContext(
            run_id="test-scout-java",
            run_dir=tmp_path,
            config=RunConfig(
                family="cells",
                platform="java",
                repo_url="https://github.com/aspose/aspose-cells-foss-java",
            ),
        )
        worker = ScoutWorker()

        result = await worker.run(intake, ctx)

        assert result.repo_info.shared_facts.primary_language == "java"

    @pytest.mark.asyncio
    async def test_scout_raises_on_missing_repo_dir(self, tmp_path: Path):
        """ScoutWorker raises ValueError when repo_dir doesn't exist."""
        from launcher.workers.scout.worker import ScoutWorker

        intake = _make_intake(str(tmp_path / "nonexistent"))
        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        with pytest.raises(ValueError, match="repo_dir does not exist"):
            await worker.run(intake, ctx)

    @pytest.mark.asyncio
    async def test_scout_self_review_passes_on_good_repo(self, tmp_path: Path):
        """ScoutWorker.self_review passes on a non-empty repo."""
        from launcher.workers.scout.worker import ScoutWorker

        repo = _fake_repo(tmp_path)
        intake = _make_intake(str(repo))
        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        result = await worker.run(intake, ctx)
        review = await worker.self_review(result)

        assert review.passed
        assert not any(f.get("severity") == "high" for f in review.findings)

    @pytest.mark.asyncio
    async def test_scout_self_review_fails_on_empty_repo(self, tmp_path: Path):
        """ScoutWorker.self_review returns high-severity finding for empty repo."""
        from launcher.workers.scout.worker import ScoutWorker

        # Empty directory
        repo = tmp_path / "empty_repo"
        repo.mkdir()

        intake = _make_intake(str(repo))
        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        result = await worker.run(intake, ctx)
        review = await worker.self_review(result)

        # Should fail: no files enumerated AND no files read
        assert not review.passed
        high_findings = [f for f in review.findings if f.get("severity") == "high"]
        assert len(high_findings) >= 1

    @pytest.mark.asyncio
    async def test_scout_accepts_dict_proxy_input(self, tmp_path: Path):
        """ScoutWorker handles generic dict input (via model_validate fallback)."""
        from launcher.workers.scout.worker import ScoutWorker

        repo = _fake_repo(tmp_path)
        intake = _make_intake(str(repo))

        # Simulate what graph_builder does: pass a _DictProxy
        class _FakeProxy:
            def model_dump(self):
                return intake.model_dump()

        ctx = _make_context(tmp_path)
        worker = ScoutWorker()

        # Pass a DictProxy-like object (triggers the else branch)
        result = await worker.run(_FakeProxy(), ctx)  # type: ignore[arg-type]
        assert isinstance(result, ScoutBundle)


# ---------------------------------------------------------------------------
# ScoutWorker self_review unit tests (no disk I/O)
# ---------------------------------------------------------------------------


class TestScoutSelfReview:
    @pytest.mark.asyncio
    async def test_self_review_no_package_name_is_medium(self, tmp_path: Path):
        """Missing package_name → medium finding, not blocking."""
        from launcher.workers.scout.worker import ScoutWorker
        from launcher.models.understanding import SharedFacts

        worker = ScoutWorker()
        # Build a ScoutBundle with files but no package_name
        bundle = ScoutBundle(
            family="cells",
            platform="python",
            repo_url="https://example.com",
            display_name="Test",
            canonical_import="test",
            launch_tier="core",
            repo_dir=str(tmp_path),
            repo_info=RepoInfo(
                file_tree=["README.md"],
                content_files_read=1,
                shared_facts=SharedFacts(package_name=""),  # empty
            ),
        )
        review = await worker.self_review(bundle)

        assert review.passed  # medium finding doesn't block
        medium_findings = [f for f in review.findings if f.get("severity") == "medium"]
        assert any("package name" in f["message"].lower() for f in medium_findings)

    @pytest.mark.asyncio
    async def test_self_review_wrong_type_fails(self, tmp_path: Path):
        """Passing wrong output type to self_review returns passed=False."""
        from launcher.workers.scout.worker import ScoutWorker
        from launcher.models.base import LauncherBaseModel

        class _OtherBundle(LauncherBaseModel):
            name: str = "other"

        worker = ScoutWorker()
        result = await worker.self_review(_OtherBundle())
        assert not result.passed

    @pytest.mark.asyncio
    async def test_self_review_warns_on_important_files_skipped(self, tmp_path: Path):
        """TC-4236: important_files_skipped > 0 produces a medium self-review finding."""
        from launcher.workers.scout.worker import ScoutWorker
        from launcher.models.understanding import SharedFacts

        worker = ScoutWorker()
        bundle = ScoutBundle(
            family="cells",
            platform="python",
            repo_url="https://example.com",
            display_name="Test",
            canonical_import="test",
            launch_tier="core",
            repo_dir=str(tmp_path),
            repo_info=RepoInfo(
                file_tree=["README.md"],
                content_files_read=1,
                shared_facts=SharedFacts(package_name="my-lib"),
                important_files_skipped=3,  # TC-4236
            ),
        )
        review = await worker.self_review(bundle)

        # important_files_skipped is medium severity — doesn't block
        assert review.passed
        medium_findings = [f for f in review.findings if f.get("severity") == "medium"]
        assert any(
            "high-rank" in f["message"].lower() or "important" in f["message"].lower()
            for f in medium_findings
        ), f"Expected a medium finding about skipped files, got: {review.findings}"

    @pytest.mark.asyncio
    async def test_self_review_no_warning_when_no_important_skipped(self, tmp_path: Path):
        """TC-4236: important_files_skipped == 0 produces no skipped-files finding."""
        from launcher.workers.scout.worker import ScoutWorker
        from launcher.models.understanding import SharedFacts

        worker = ScoutWorker()
        bundle = ScoutBundle(
            family="cells",
            platform="python",
            repo_url="https://example.com",
            display_name="Test",
            canonical_import="test",
            launch_tier="core",
            repo_dir=str(tmp_path),
            repo_info=RepoInfo(
                file_tree=["README.md"],
                content_files_read=1,
                shared_facts=SharedFacts(package_name="my-lib"),
                important_files_skipped=0,  # no skips
            ),
        )
        review = await worker.self_review(bundle)
        skip_findings = [
            f for f in review.findings
            if "high-rank" in f.get("message", "").lower()
            or "important" in f.get("category", "").lower()
        ]
        assert len(skip_findings) == 0

    @pytest.mark.asyncio
    async def test_self_review_fails_on_meta_doc_selection(self, tmp_path: Path):
        """Scout must fail when operator/meta docs survive into selected doc_paths."""
        from launcher.workers.scout.worker import ScoutWorker
        from launcher.models.understanding import FileCategory, FileEntry, SharedFacts

        worker = ScoutWorker()
        bundle = ScoutBundle(
            family="cells",
            platform="python",
            repo_url="https://example.com",
            display_name="Test",
            canonical_import="test",
            launch_tier="core",
            repo_dir=str(tmp_path),
            repo_info=RepoInfo(
                file_tree=["README.md", "AGENTS.md"],
                file_index={
                    "README.md": FileEntry(category=FileCategory.doc, size_bytes=100, language=""),
                    "AGENTS.md": FileEntry(category=FileCategory.doc, size_bytes=100, language=""),
                },
                doc_paths=["README.md", "AGENTS.md"],
                content_files_read=2,
                shared_facts=SharedFacts(package_name="my-lib"),
            ),
        )
        review = await worker.self_review(bundle)

        assert not review.passed
        assert any(f.get("category") == "scout_meta_docs_selected" for f in review.findings)

    @pytest.mark.asyncio
    async def test_self_review_fails_on_example_starvation(self, tmp_path: Path):
        """Example-heavy repos must not pass Scout with near-zero retained examples."""
        from launcher.workers.scout.worker import ScoutWorker
        from launcher.models.understanding import FileCategory, FileEntry, SharedFacts

        worker = ScoutWorker()
        example_files = [f"examples/test_case_{i}.py" for i in range(6)]
        file_index = {
            path: FileEntry(category=FileCategory.test, size_bytes=200, language="python")
            for path in example_files
        }
        bundle = ScoutBundle(
            family="cells",
            platform="python",
            repo_url="https://example.com",
            display_name="Test",
            canonical_import="test",
            launch_tier="core",
            repo_dir=str(tmp_path),
            repo_info=RepoInfo(
                file_tree=example_files,
                file_index=file_index,
                example_paths=[],
                content_files_read=6,
                shared_facts=SharedFacts(package_name="my-lib", has_examples_folder=True),
            ),
        )
        review = await worker.self_review(bundle)

        assert not review.passed
        assert any(f.get("category") == "scout_example_starvation" for f in review.findings)


class TestScoutEvidenceSelection:
    def test_classify_file_prefers_example_dir_over_test_filename(self):
        from launcher.models.understanding import FileCategory
        from launcher.workers.understand.file_classifier import classify_file

        assert classify_file("examples/test_export.py") == FileCategory.example
        assert classify_file("samples/test_convert.py") == FileCategory.example
        assert classify_file("tests/examples/test_export.py") == FileCategory.test

    @pytest.mark.asyncio
    async def test_run_scout_excludes_meta_docs_and_keeps_example_test_files(self, tmp_path: Path):
        from launcher.workers.scout.scout import build_scout_inventory, run_scout

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Product\nActual usage docs.\n", encoding="utf-8")
        (repo / "AGENTS.md").write_text("# Operators\nDo not use.\n", encoding="utf-8")
        (repo / "llms.md").write_text("# Prompt notes\n", encoding="utf-8")
        examples_dir = repo / "examples"
        examples_dir.mkdir()
        (examples_dir / "__init__.py").write_text("", encoding="utf-8")
        (examples_dir / "test_export.py").write_text(
            "from pkg import Workbook\nwb = Workbook()\n",
            encoding="utf-8",
        )
        (repo / "pkg.py").write_text("class Workbook: pass\n", encoding="utf-8")

        repo_info, repo_content, budget_log, overflow = await run_scout(repo)
        inventory = build_scout_inventory(repo_info, repo_content, budget_log, overflow)

        assert repo_info.doc_paths == ["README.md"]
        assert "examples/test_export.py" in repo_info.example_paths
        assert "examples/__init__.py" not in repo_info.example_paths
        assert any(
            entry.get("path") == "AGENTS.md" and entry.get("reason") == "doc_ineligible_meta"
            for entry in budget_log
        )
        assert any(
            entry["path"] == "examples/test_export.py" and entry["decision"] == "kept"
            for entry in inventory["example_selection"]
        )
        assert any(
            entry["path"] == "AGENTS.md" and entry["reason"] == "doc_ineligible_meta"
            for entry in inventory["doc_selection"]
        )


# ---------------------------------------------------------------------------
# Re-export shim tests
# ---------------------------------------------------------------------------


class TestUnderstandScoutShim:
    """Verify the understand/scout.py re-export shim still works (TC-4076)."""

    def test_run_scout_importable_from_understand_scout(self):
        """from launcher.workers.understand.scout import run_scout still works."""
        from launcher.workers.understand.scout import run_scout
        assert callable(run_scout)

    def test_walk_file_tree_importable_from_understand_scout(self):
        """_walk_file_tree still importable via old path."""
        from launcher.workers.understand.scout import _walk_file_tree
        assert callable(_walk_file_tree)

    def test_read_repo_content_importable_from_understand_scout(self):
        """_read_repo_content still importable via old path."""
        from launcher.workers.understand.scout import _read_repo_content
        assert callable(_read_repo_content)


# ---------------------------------------------------------------------------
# UnderstandWorker resume path test
# ---------------------------------------------------------------------------


class TestUnderstandWorkerResumePath:
    """TC-4076: UnderstandWorker re-reads files from disk when context.repo_content is empty."""

    @pytest.mark.asyncio
    async def test_understand_resumes_with_empty_repo_content(self, tmp_path: Path):
        """When context.repo_content is empty, Understand re-reads from file_index."""
        from unittest.mock import patch, AsyncMock
        from launcher.workers.understand.worker import UnderstandWorker

        repo = _fake_repo(tmp_path)

        # Build a realistic ScoutBundle (simulate what ScoutWorker would produce)
        from launcher.workers.scout.scout import run_scout
        repo_info, _, budget_log, overflow = await run_scout(repo)

        scout_bundle = ScoutBundle(
            family="cells",
            platform="python",
            repo_url="https://example.com/repo",
            display_name="Test",
            canonical_import="aspose_cells_foss",
            launch_tier="core",
            repo_dir=str(repo),
            repo_info=repo_info,
            budget_log=budget_log,
            budget_log_overflow_count=overflow,
        )

        config = RunConfig(
            family="cells", platform="python",
            repo_url="https://example.com/repo",
        )
        ctx = WorkerContext(run_id="test-resume", run_dir=tmp_path, config=config)
        # Deliberately leave context.repo_content empty (simulates resume from checkpoint)
        assert ctx.repo_content == {} or not ctx.repo_content

        worker = UnderstandWorker()

        # Mock run_extract to avoid LLM calls but verify repo_content was re-populated
        async def _mock_run_extract(product, repo_info, repo_dir, context):
            # This verifies that context.repo_content was populated by the resume path
            assert context.repo_content, (
                "context.repo_content was empty when run_extract was called — "
                "resume path did not re-read files from disk"
            )
            from launcher.models.claims import Claim, EvidenceAnchor
            from launcher.models.product import ApiSurface
            from launcher.models.understanding import ProductEvidence
            claim = Claim(
                claim_id="CLM-001",
                text="Test claim",
                kind="feature",
                evidence=[EvidenceAnchor(source_file="README.md", line_start=1, line_end=1, snippet="test")],
                visibility="public",
            )
            from launcher.models.understanding import ExtractionDatabase
            return [claim], [], ApiSurface(public_classes=[], import_allowlist=[], confidence="low"), ProductEvidence(), ExtractionDatabase()

        with patch("launcher.workers.understand.extract.run_extract", side_effect=_mock_run_extract):
            # Should not raise — resume path should re-read files
            result = await worker.run(scout_bundle, ctx)

        # context.repo_content should be populated after the resume read
        assert ctx.repo_content


# ---------------------------------------------------------------------------
# P1-A: README sanitization test (TC-4088)
# ---------------------------------------------------------------------------


class TestReadmeSanitization:
    """P1-A: readme_summary must use sanitized content from repo_content, not raw read."""

    @pytest.mark.asyncio
    async def test_readme_summary_is_sanitized(self, tmp_path: Path):
        """P1-A: readme_summary must not contain secrets from README."""
        import asyncio
        from launcher.workers.scout.scout import run_scout

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        # Plant a fake secret in README (sk- prefix + 40 alphanumeric chars)
        readme = repo_dir / "README.md"
        readme.write_text(
            "# My Lib\n\nAPI_KEY=sk-abc123defghijklmnopqrstuvwxyz1234567890\n\nUsage: import mylib\n"
        )
        # Need at least one source file to avoid empty tree
        (repo_dir / "module.py").write_text("class Foo: pass\n")

        repo_info, repo_content, budget_log, overflow = await run_scout(repo_dir)

        # readme_summary must not contain the raw secret — it comes from sanitized repo_content
        assert "sk-abc123defghijklmnopqrstuvwxyz1234567890" not in repo_info.readme_summary, (
            "readme_summary contains unsanitized secret — P1-A fix not applied correctly"
        )

    @pytest.mark.asyncio
    async def test_readme_summary_extracted_from_repo_content(self, tmp_path: Path):
        """P1-A: readme_summary content matches the sanitized version in repo_content."""
        from launcher.workers.scout.scout import run_scout

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        readme_text = "# My Library\n\nThis is the readme.\n"
        (repo_dir / "README.md").write_text(readme_text)
        (repo_dir / "module.py").write_text("class Bar: pass\n")

        repo_info, repo_content, budget_log, overflow = await run_scout(repo_dir)

        # readme_summary should be populated and match repo_content
        assert repo_info.readme_summary, "readme_summary should not be empty"
        assert "My Library" in repo_info.readme_summary
        # Should match what's in repo_content (modulo 4000-char truncation)
        readme_key = next((k for k in repo_content if k.lower() == "readme.md"), None)
        assert readme_key is not None, "README.md should be in repo_content"
        assert repo_info.readme_summary == repo_content[readme_key][:4000]


# ---------------------------------------------------------------------------
# TC-4233: _extract_readme_summary section-aware extraction
# ---------------------------------------------------------------------------


class TestReadmeSectionExtraction:
    """TC-4233: Tests for _extract_readme_summary() section-aware extraction."""

    def test_short_readme_returned_unchanged(self):
        from launcher.workers.scout.scout import _extract_readme_summary
        short = "# Hello\nThis is a short README.\n"
        assert _extract_readme_summary(short) == short

    def test_budget_respected(self):
        from launcher.workers.scout.scout import _extract_readme_summary
        # Build a README that is 20K chars
        big_readme = "# Introduction\n" + "x" * 5000 + "\n\n# Installation\n" + "y" * 5000 + "\n\n# API\n" + "z" * 10000
        result = _extract_readme_summary(big_readme, max_chars=8000)
        assert len(result) <= 8000

    def test_high_priority_section_included(self):
        from launcher.workers.scout.scout import _extract_readme_summary
        # README with low-priority content first, Installation section late
        readme = (
            "# About\n" + "background content " * 200 + "\n\n"
            "# Installation\n"
            "Run `pip install mypackage` to get started.\n\n"
            "# License\n"
            "MIT License " * 100
        )
        result = _extract_readme_summary(readme, max_chars=500)
        assert "pip install mypackage" in result

    def test_empty_readme_returns_empty(self):
        from launcher.workers.scout.scout import _extract_readme_summary
        assert _extract_readme_summary("") == ""

    def test_intro_paragraph_included(self):
        from launcher.workers.scout.scout import _extract_readme_summary
        readme = "This is the intro before any headings.\n\n# Section 1\nContent here.\n"
        result = _extract_readme_summary(readme)
        assert "This is the intro before any headings." in result


# ---------------------------------------------------------------------------
# TC-4102: importance rank uses substring matching for compound names
# ---------------------------------------------------------------------------


class TestFileImportanceRankSubstring:
    """TC-4102: importance rank uses substring matching for compound names."""

    def test_api_reference_ranks_high(self):
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.workers.understand.file_classifier import FileCategory
        # keyword 'api' (+3), nested (0), .md (+1) = 4
        assert _file_importance_rank("docs/api_reference.md", FileCategory.doc) >= 1

    def test_getting_started_ranks_high(self):
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.workers.understand.file_classifier import FileCategory
        # keyword 'gettingstarted' (+3), nested (0), .md (+1) = 4
        assert _file_importance_rank("docs/GETTING-STARTED.md", FileCategory.doc) >= 1

    def test_quickstart_ranks_high(self):
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.workers.understand.file_classifier import FileCategory
        # keyword 'quickstart' (+3), nested (0), .rst (+1) = 4
        assert _file_importance_rank("docs/quickstart.rst", FileCategory.doc) >= 1

    def test_readme_exact_still_ranks_high(self):
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.workers.understand.file_classifier import FileCategory
        # keyword 'readme' (+3), root (+2), .md (+1) = 6
        assert _file_importance_rank("README.md", FileCategory.doc) >= 1

    def test_random_file_ranks_zero(self):
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.workers.understand.file_classifier import FileCategory
        # no keyword (0), root (+2 — no slash), non-standard ext for doc (0) = 2
        # Adjusted: root-level files now get +2 from Factor 2.
        # This test verifies the file has no keyword-based rank contribution.
        assert _file_importance_rank("docs/some_utility_module.log", FileCategory.doc) == 0

    def test_root_level_doc_adds_2pts(self):
        """SUMMARY.md at root: no keyword (0), root (+2), .md ext (+1) = 3."""
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.models.understanding import FileCategory
        assert _file_importance_rank("SUMMARY.md", FileCategory.doc) == 3

    def test_nested_nonkeyword_doc_is_zero(self):
        """subdir/notes.log: no keyword, nested, non-standard ext = 0."""
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.models.understanding import FileCategory
        assert _file_importance_rank("subdir/notes.log", FileCategory.doc) == 0

    def test_nested_keyword_doc(self):
        """docs/api_reference.md: keyword (+3), nested (0), .md (+1) = 4."""
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.models.understanding import FileCategory
        assert _file_importance_rank("docs/api_reference.md", FileCategory.doc) == 4

    def test_root_readme_md_is_max_doc(self):
        """README.md: keyword 'readme' (+3), root (+2), .md (+1) = 6."""
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.models.understanding import FileCategory
        assert _file_importance_rank("README.md", FileCategory.doc) == 6

    def test_root_init_py_is_max_source(self):
        """__init__.py at root: keyword 'init' (+3), root (+2), .py (+1) = 6."""
        from launcher.workers.scout.scout import _file_importance_rank
        from launcher.models.understanding import FileCategory
        assert _file_importance_rank("__init__.py", FileCategory.source) == 6


# ---------------------------------------------------------------------------
# TC-4217: _parse_setup_py unit tests
# ---------------------------------------------------------------------------


class TestParseSetupPy:
    """TC-4217: Unit tests for the _parse_setup_py regex-based parser."""

    def test_parse_setup_py_name_version_license(self, tmp_path: Path):
        """Happy path: setup.py with name, version, license returns all six fields."""
        from launcher.workers.scout.scout import _parse_setup_py

        setup_py = tmp_path / "setup.py"
        setup_py.write_text(
            'from setuptools import setup\n'
            'setup(\n'
            '    name="mypkg",\n'
            '    version="1.0",\n'
            '    license="MIT",\n'
            ')\n'
        )
        result = _parse_setup_py(setup_py)
        # TC-4235: returns 6-tuple (name, ver, lic, desc, deps, entrypoints)
        assert result[:3] == ("mypkg", "1.0", "MIT")

    def test_parse_setup_py_missing_file(self, tmp_path: Path):
        """Non-existent setup.py returns ("", "", "", "", [], [])."""
        from launcher.workers.scout.scout import _parse_setup_py

        result = _parse_setup_py(tmp_path / "setup.py")
        assert result == ("", "", "", "", [], [])

    def test_parse_setup_py_no_setup_call(self, tmp_path: Path):
        """File with no name= pattern returns ("", "", "", "", [], [])."""
        from launcher.workers.scout.scout import _parse_setup_py

        setup_py = tmp_path / "setup.py"
        setup_py.write_text("# Just a comment\nprint('hello')\n")
        result = _parse_setup_py(setup_py)
        assert result == ("", "", "", "", [], [])
