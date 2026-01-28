"""Tests for TC-560: Determinism and Reproducibility Harness.

Tests golden run capture, verification, and regression detection.

Binding spec: specs/10_determinism_and_caching.md (REQ-079)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import pytest

from launch.determinism import (
    ArtifactMismatch,
    GoldenRunMetadata,
    RegressionChecker,
    VerificationResult,
    capture_golden_run,
    delete_golden_run,
    list_golden_runs,
    verify_against_golden,
)
from launch.determinism.golden_run import (
    _collect_artifacts,
    _compute_file_hash,
    _compute_normalized_hash,
    _normalize_line_endings,
    _strip_trailing_whitespace,
)


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Path:
    """Create temporary run directory with artifacts."""
    run_dir = tmp_path / "runs" / "test-run-001"
    run_dir.mkdir(parents=True)

    # Create run_config.yaml
    config_path = run_dir / "run_config.yaml"
    config_path.write_text(
        "product_slug: test-product\n"
        "github_ref: main\n"
        "site_ref: main\n"
        "templates_version: 1.0.0\n",
        encoding="utf-8",
    )

    # Create artifacts directory
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir()

    # Create sample artifacts
    (artifacts_dir / "page_plan.json").write_text(
        json.dumps(
            {
                "pages": [
                    {"output_path": "test.md", "template_id": "basic"}
                ]
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    (artifacts_dir / "product_facts.json").write_text(
        json.dumps(
            {"product_name": "Test Product", "claims": []},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    # Create events.ndjson (should be excluded)
    (artifacts_dir / "events.ndjson").write_text(
        '{"event_id": "001", "ts": "2026-01-28T10:00:00Z"}\n'
        '{"event_id": "002", "ts": "2026-01-28T10:01:00Z"}\n',
        encoding="utf-8",
    )

    # Create drafts
    drafts_dir = run_dir / "drafts" / "getting-started"
    drafts_dir.mkdir(parents=True)

    (drafts_dir / "index.md").write_text(
        "# Getting Started\n\nWelcome to Test Product.\n",
        encoding="utf-8",
    )

    return run_dir


@pytest.fixture
def golden_runs_dir(tmp_path: Path) -> Path:
    """Create golden runs directory."""
    golden_dir = tmp_path / "artifacts" / "golden_runs"
    golden_dir.mkdir(parents=True)
    return golden_dir


class TestLineEndingNormalization:
    """Test line ending normalization."""

    def test_normalize_crlf_to_lf(self):
        """Test CRLF to LF normalization."""
        content = b"line1\r\nline2\r\nline3\r\n"
        normalized = _normalize_line_endings(content)
        assert normalized == b"line1\nline2\nline3\n"

    def test_normalize_already_lf(self):
        """Test content already with LF."""
        content = b"line1\nline2\nline3\n"
        normalized = _normalize_line_endings(content)
        assert normalized == content

    def test_normalize_mixed_endings(self):
        """Test mixed line endings."""
        content = b"line1\r\nline2\nline3\r\n"
        normalized = _normalize_line_endings(content)
        assert normalized == b"line1\nline2\nline3\n"


class TestTrailingWhitespace:
    """Test trailing whitespace stripping."""

    def test_strip_trailing_spaces(self):
        """Test stripping trailing spaces."""
        content = b"line1   \nline2\t\nline3\n"
        stripped = _strip_trailing_whitespace(content)
        assert stripped == b"line1\nline2\nline3\n"

    def test_strip_no_trailing_whitespace(self):
        """Test content without trailing whitespace."""
        content = b"line1\nline2\nline3\n"
        stripped = _strip_trailing_whitespace(content)
        assert stripped == content

    def test_strip_preserves_internal_whitespace(self):
        """Test that internal whitespace is preserved."""
        content = b"line 1  word\nline 2\ttab\n"
        stripped = _strip_trailing_whitespace(content)
        assert stripped == b"line 1  word\nline 2\ttab\n"


class TestHashComputation:
    """Test hash computation."""

    def test_compute_file_hash(self, tmp_path: Path):
        """Test computing file hash."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, world!", encoding="utf-8")

        hash_value = _compute_file_hash(file_path)
        assert len(hash_value) == 64  # SHA256 hex digest
        assert hash_value == "315f5bdb76d078c43b8ac0064e4a0164612b1fce77c869345bfc94c75894edd3"

    def test_compute_normalized_hash_with_crlf(self, tmp_path: Path):
        """Test normalized hash with CRLF line endings."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        # Same content, different line endings
        file1.write_bytes(b"line1\r\nline2\r\n")
        file2.write_bytes(b"line1\nline2\n")

        hash1 = _compute_normalized_hash(file1)
        hash2 = _compute_normalized_hash(file2)

        # Should produce same hash after normalization
        assert hash1 == hash2

    def test_compute_normalized_hash_with_trailing_whitespace(self, tmp_path: Path):
        """Test normalized hash with trailing whitespace."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        # Same content, different trailing whitespace
        file1.write_bytes(b"line1   \nline2\t\n")
        file2.write_bytes(b"line1\nline2\n")

        hash1 = _compute_normalized_hash(file1)
        hash2 = _compute_normalized_hash(file2)

        # Should produce same hash after normalization
        assert hash1 == hash2

    def test_hash_determinism_same_input(self, tmp_path: Path):
        """Test that same input produces same hash (determinism guarantee)."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Deterministic content", encoding="utf-8")

        hash1 = _compute_file_hash(file_path)
        hash2 = _compute_file_hash(file_path)
        hash3 = _compute_file_hash(file_path)

        assert hash1 == hash2 == hash3

    def test_hash_different_for_different_content(self, tmp_path: Path):
        """Test that different content produces different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A", encoding="utf-8")
        file2.write_text("Content B", encoding="utf-8")

        hash1 = _compute_file_hash(file1)
        hash2 = _compute_file_hash(file2)

        assert hash1 != hash2


class TestArtifactCollection:
    """Test artifact collection."""

    def test_collect_artifacts_excludes_events(self, temp_run_dir: Path):
        """Test that events.ndjson is excluded from collection."""
        artifacts = _collect_artifacts(temp_run_dir, exclude_events=True)

        # Should not include events.ndjson
        assert not any("events.ndjson" in path for path in artifacts.keys())

    def test_collect_artifacts_includes_json(self, temp_run_dir: Path):
        """Test that JSON artifacts are collected."""
        artifacts = _collect_artifacts(temp_run_dir, exclude_events=True)

        # Should include page_plan.json and product_facts.json
        assert any("page_plan.json" in path for path in artifacts.keys())
        assert any("product_facts.json" in path for path in artifacts.keys())

    def test_collect_artifacts_includes_drafts(self, temp_run_dir: Path):
        """Test that drafts are collected."""
        artifacts = _collect_artifacts(temp_run_dir, exclude_events=True)

        # Should include drafts
        assert any("drafts" in path and path.endswith(".md") for path in artifacts.keys())

    def test_collect_artifacts_empty_directory(self, tmp_path: Path):
        """Test collecting artifacts from empty directory."""
        run_dir = tmp_path / "empty-run"
        run_dir.mkdir()

        artifacts = _collect_artifacts(run_dir, exclude_events=True)
        assert len(artifacts) == 0

    def test_collect_artifacts_stable_ordering(self, temp_run_dir: Path):
        """Test that artifact collection has stable ordering."""
        artifacts1 = _collect_artifacts(temp_run_dir, exclude_events=True)
        artifacts2 = _collect_artifacts(temp_run_dir, exclude_events=True)

        # Keys should be in same order
        assert list(artifacts1.keys()) == list(artifacts2.keys())


class TestGoldenRunCapture:
    """Test golden run capture."""

    def test_capture_golden_run_success(self, temp_run_dir: Path, monkeypatch):
        """Test successful golden run capture."""
        # Change to temp directory
        monkeypatch.chdir(temp_run_dir.parent.parent)

        metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123def456",
        )

        assert metadata.run_id == "test-run-001"
        assert metadata.product_name == "test-product"
        assert metadata.git_ref == "main"
        assert metadata.git_sha == "abc123def456"
        assert metadata.total_artifacts > 0
        assert len(metadata.artifact_hashes) > 0

        # Verify metadata file created
        golden_dir = Path("artifacts/golden_runs/test-product/main/test-run-001")
        assert (golden_dir / "metadata.json").exists()

    def test_capture_golden_run_missing_directory(self, tmp_path: Path):
        """Test capture with missing run directory."""
        run_dir = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError, match="Run directory not found"):
            capture_golden_run(
                run_dir=run_dir,
                product_name="test-product",
                git_ref="main",
                git_sha="abc123",
            )

    def test_capture_golden_run_missing_config(self, tmp_path: Path):
        """Test capture with missing run_config."""
        run_dir = tmp_path / "run-no-config"
        run_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="No run_config found"):
            capture_golden_run(
                run_dir=run_dir,
                product_name="test-product",
                git_ref="main",
                git_sha="abc123",
            )

    def test_capture_golden_run_no_artifacts(self, tmp_path: Path):
        """Test capture with no artifacts."""
        run_dir = tmp_path / "run-no-artifacts"
        run_dir.mkdir()

        # Create only config
        (run_dir / "run_config.yaml").write_text("product_slug: test\n", encoding="utf-8")

        with pytest.raises(ValueError, match="No artifacts found"):
            capture_golden_run(
                run_dir=run_dir,
                product_name="test-product",
                git_ref="main",
                git_sha="abc123",
            )

    def test_capture_creates_copy_of_artifacts(self, temp_run_dir: Path, monkeypatch):
        """Test that capture creates copy of artifacts."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        golden_dir = Path("artifacts/golden_runs/test-product/main/test-run-001")

        # Verify artifacts copied
        for artifact_path in metadata.artifact_hashes.keys():
            assert (golden_dir / artifact_path).exists()

    def test_metadata_serialization_roundtrip(self, temp_run_dir: Path, monkeypatch):
        """Test metadata can be serialized and deserialized."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Convert to dict and back
        data = metadata.to_dict()
        restored = GoldenRunMetadata.from_dict(data)

        assert restored.run_id == metadata.run_id
        assert restored.product_name == metadata.product_name
        assert restored.git_ref == metadata.git_ref
        assert restored.git_sha == metadata.git_sha
        assert restored.artifact_hashes == metadata.artifact_hashes


class TestGoldenRunVerification:
    """Test golden run verification."""

    def test_verify_matching_artifacts(self, temp_run_dir: Path, monkeypatch):
        """Test verification with matching artifacts (should pass)."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden run
        golden_metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Verify same run against itself
        result = verify_against_golden(
            run_dir=temp_run_dir,
            golden_run_id=golden_metadata.run_id,
            product_name="test-product",
            git_ref="main",
        )

        assert result.passed is True
        assert len(result.mismatches) == 0
        assert result.golden_run_id == golden_metadata.run_id

    def test_verify_mismatched_content(self, temp_run_dir: Path, tmp_path: Path, monkeypatch):
        """Test verification with mismatched content (should fail)."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden run
        golden_metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Create new run with modified content
        new_run_dir = temp_run_dir.parent / "test-run-002"
        new_run_dir.mkdir()

        # Copy structure
        (new_run_dir / "run_config.yaml").write_text(
            (temp_run_dir / "run_config.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        artifacts_dir = new_run_dir / "artifacts"
        artifacts_dir.mkdir()

        # Modified content
        (artifacts_dir / "page_plan.json").write_text(
            json.dumps({"pages": []}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        (artifacts_dir / "product_facts.json").write_text(
            json.dumps(
                {"product_name": "Modified Product", "claims": []},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        # Copy drafts unchanged
        drafts_dir = new_run_dir / "drafts" / "getting-started"
        drafts_dir.mkdir(parents=True)
        (drafts_dir / "index.md").write_text(
            (temp_run_dir / "drafts" / "getting-started" / "index.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        # Verify
        result = verify_against_golden(
            run_dir=new_run_dir,
            golden_run_id=golden_metadata.run_id,
            product_name="test-product",
            git_ref="main",
        )

        assert result.passed is False
        assert len(result.mismatches) > 0

        # Should detect mismatches in modified files
        mismatched_paths = [m.artifact_path for m in result.mismatches]
        assert any("page_plan.json" in path for path in mismatched_paths)
        assert any("product_facts.json" in path for path in mismatched_paths)

    def test_verify_missing_artifact(self, temp_run_dir: Path, tmp_path: Path, monkeypatch):
        """Test verification with missing artifact."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden run
        golden_metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Create new run missing an artifact
        new_run_dir = temp_run_dir.parent / "test-run-003"
        new_run_dir.mkdir()

        (new_run_dir / "run_config.yaml").write_text(
            (temp_run_dir / "run_config.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        artifacts_dir = new_run_dir / "artifacts"
        artifacts_dir.mkdir()

        # Only create one artifact (missing page_plan.json)
        (artifacts_dir / "product_facts.json").write_text(
            (temp_run_dir / "artifacts" / "product_facts.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        # Verify
        result = verify_against_golden(
            run_dir=new_run_dir,
            golden_run_id=golden_metadata.run_id,
            product_name="test-product",
            git_ref="main",
        )

        assert result.passed is False
        assert len(result.mismatches) > 0

        # Should detect missing artifacts
        missing = [m for m in result.mismatches if m.actual_hash == "MISSING"]
        assert len(missing) > 0

    def test_verify_unexpected_artifact(self, temp_run_dir: Path, tmp_path: Path, monkeypatch):
        """Test verification with unexpected artifact."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden run
        golden_metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Create new run with extra artifact
        new_run_dir = temp_run_dir.parent / "test-run-004"
        new_run_dir.mkdir()

        # Copy everything
        import shutil
        shutil.copy2(temp_run_dir / "run_config.yaml", new_run_dir / "run_config.yaml")
        shutil.copytree(temp_run_dir / "artifacts", new_run_dir / "artifacts")
        shutil.copytree(temp_run_dir / "drafts", new_run_dir / "drafts")

        # Add unexpected artifact
        (new_run_dir / "artifacts" / "unexpected.json").write_text(
            json.dumps({"unexpected": True}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        # Verify
        result = verify_against_golden(
            run_dir=new_run_dir,
            golden_run_id=golden_metadata.run_id,
            product_name="test-product",
            git_ref="main",
        )

        assert result.passed is False
        assert len(result.mismatches) > 0

        # Should detect unexpected artifacts
        unexpected = [m for m in result.mismatches if m.expected_hash == "NOT_IN_GOLDEN"]
        assert len(unexpected) > 0

    def test_verify_golden_run_not_found(self, temp_run_dir: Path, monkeypatch):
        """Test verification with non-existent golden run."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        with pytest.raises(FileNotFoundError, match="Golden run not found"):
            verify_against_golden(
                run_dir=temp_run_dir,
                golden_run_id="nonexistent-run",
            )

    def test_verify_run_dir_not_found(self, tmp_path: Path):
        """Test verification with non-existent run directory."""
        run_dir = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError, match="Run directory not found"):
            verify_against_golden(
                run_dir=run_dir,
                golden_run_id="test-run-001",
            )


class TestGoldenRunListing:
    """Test golden run listing."""

    def test_list_golden_runs_empty(self, tmp_path: Path, monkeypatch):
        """Test listing golden runs when none exist."""
        monkeypatch.chdir(tmp_path)

        runs = list_golden_runs()
        assert len(runs) == 0

    def test_list_golden_runs_single(self, temp_run_dir: Path, monkeypatch):
        """Test listing single golden run."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        runs = list_golden_runs()
        assert len(runs) == 1
        assert runs[0].product_name == "test-product"
        assert runs[0].git_ref == "main"

    def test_list_golden_runs_multiple(self, temp_run_dir: Path, tmp_path: Path, monkeypatch):
        """Test listing multiple golden runs."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture first run
        capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Create and capture second run
        run_dir_2 = temp_run_dir.parent / "test-run-005"
        run_dir_2.mkdir()

        import shutil
        shutil.copy2(temp_run_dir / "run_config.yaml", run_dir_2 / "run_config.yaml")
        shutil.copytree(temp_run_dir / "artifacts", run_dir_2 / "artifacts")
        shutil.copytree(temp_run_dir / "drafts", run_dir_2 / "drafts")

        capture_golden_run(
            run_dir=run_dir_2,
            product_name="test-product",
            git_ref="main",
            git_sha="def456",
        )

        runs = list_golden_runs()
        assert len(runs) == 2

    def test_list_golden_runs_filtered_by_product(self, temp_run_dir: Path, tmp_path: Path, monkeypatch):
        """Test listing golden runs filtered by product."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture run for test-product
        capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Create and capture run for other-product
        run_dir_2 = temp_run_dir.parent / "test-run-006"
        run_dir_2.mkdir()

        import shutil
        shutil.copy2(temp_run_dir / "run_config.yaml", run_dir_2 / "run_config.yaml")
        shutil.copytree(temp_run_dir / "artifacts", run_dir_2 / "artifacts")
        shutil.copytree(temp_run_dir / "drafts", run_dir_2 / "drafts")

        capture_golden_run(
            run_dir=run_dir_2,
            product_name="other-product",
            git_ref="main",
            git_sha="def456",
        )

        # List all
        all_runs = list_golden_runs()
        assert len(all_runs) == 2

        # List filtered
        test_product_runs = list_golden_runs(product_name="test-product")
        assert len(test_product_runs) == 1
        assert test_product_runs[0].product_name == "test-product"

        other_product_runs = list_golden_runs(product_name="other-product")
        assert len(other_product_runs) == 1
        assert other_product_runs[0].product_name == "other-product"

    def test_list_golden_runs_sorted_by_date(self, temp_run_dir: Path, tmp_path: Path, monkeypatch):
        """Test that golden runs are sorted by captured_at descending."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        import time

        # Capture first run
        capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        time.sleep(0.1)  # Ensure different timestamps

        # Create and capture second run
        run_dir_2 = temp_run_dir.parent / "test-run-007"
        run_dir_2.mkdir()

        import shutil
        shutil.copy2(temp_run_dir / "run_config.yaml", run_dir_2 / "run_config.yaml")
        shutil.copytree(temp_run_dir / "artifacts", run_dir_2 / "artifacts")
        shutil.copytree(temp_run_dir / "drafts", run_dir_2 / "drafts")

        capture_golden_run(
            run_dir=run_dir_2,
            product_name="test-product",
            git_ref="main",
            git_sha="def456",
        )

        runs = list_golden_runs()
        assert len(runs) == 2

        # Most recent should be first
        assert runs[0].run_id == "test-run-007"
        assert runs[1].run_id == "test-run-001"


class TestGoldenRunDeletion:
    """Test golden run deletion."""

    def test_delete_golden_run_exists(self, temp_run_dir: Path, monkeypatch):
        """Test deleting existing golden run."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Verify exists
        runs_before = list_golden_runs()
        assert len(runs_before) == 1

        # Delete
        result = delete_golden_run(
            golden_run_id=metadata.run_id,
            product_name="test-product",
            git_ref="main",
        )

        assert result is True

        # Verify deleted
        runs_after = list_golden_runs()
        assert len(runs_after) == 0

    def test_delete_golden_run_not_exists(self, tmp_path: Path, monkeypatch):
        """Test deleting non-existent golden run."""
        monkeypatch.chdir(tmp_path)

        result = delete_golden_run(
            golden_run_id="nonexistent",
            product_name="test-product",
            git_ref="main",
        )

        assert result is False

    def test_delete_golden_run_without_product_info(self, temp_run_dir: Path, monkeypatch):
        """Test deleting golden run without product/ref (search required)."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Delete without product/ref
        result = delete_golden_run(golden_run_id=metadata.run_id)

        assert result is True

        # Verify deleted
        runs_after = list_golden_runs()
        assert len(runs_after) == 0


class TestRegressionChecker:
    """Test regression checker."""

    def test_check_regression_no_changes(self, temp_run_dir: Path, monkeypatch):
        """Test regression check with no changes (should pass)."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden
        golden_metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Check regression
        checker = RegressionChecker()
        report = checker.check_regression(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            golden_run_id=golden_metadata.run_id,
        )

        assert report.passed is True
        assert report.total_artifacts > 0
        assert report.mismatched_artifacts == 0
        assert report.missing_artifacts == 0
        assert report.unexpected_artifacts == 0

    def test_check_regression_with_changes(self, temp_run_dir: Path, tmp_path: Path, monkeypatch):
        """Test regression check with changes (should fail)."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden
        golden_metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Create modified run
        new_run_dir = temp_run_dir.parent / "test-run-008"
        new_run_dir.mkdir()

        import shutil
        shutil.copy2(temp_run_dir / "run_config.yaml", new_run_dir / "run_config.yaml")

        artifacts_dir = new_run_dir / "artifacts"
        artifacts_dir.mkdir()

        # Modified content
        (artifacts_dir / "page_plan.json").write_text(
            json.dumps({"pages": []}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        # Copy other artifacts unchanged
        shutil.copy2(
            temp_run_dir / "artifacts" / "product_facts.json",
            artifacts_dir / "product_facts.json",
        )

        shutil.copytree(temp_run_dir / "drafts", new_run_dir / "drafts")

        # Check regression
        checker = RegressionChecker()
        report = checker.check_regression(
            run_dir=new_run_dir,
            product_name="test-product",
            git_ref="main",
            golden_run_id=golden_metadata.run_id,
        )

        assert report.passed is False
        assert report.mismatched_artifacts > 0

    def test_check_regression_auto_find_latest(self, temp_run_dir: Path, monkeypatch):
        """Test regression check auto-finding latest golden run."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden
        capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Check regression without specifying golden_run_id
        checker = RegressionChecker()
        report = checker.check_regression(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
        )

        assert report.passed is True

    def test_check_regression_no_golden_found(self, temp_run_dir: Path, monkeypatch):
        """Test regression check when no golden run exists."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        checker = RegressionChecker()

        with pytest.raises(FileNotFoundError, match="No golden run found"):
            checker.check_regression(
                run_dir=temp_run_dir,
                product_name="test-product",
                git_ref="main",
            )

    def test_save_regression_report(self, temp_run_dir: Path, tmp_path: Path, monkeypatch):
        """Test saving regression report to file."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden
        golden_metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Check regression
        checker = RegressionChecker()
        report = checker.check_regression(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            golden_run_id=golden_metadata.run_id,
        )

        # Save report
        output_path = tmp_path / "regression_report.json"
        checker.save_report(report, output_path)

        assert output_path.exists()

        # Verify content
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["passed"] is True
        assert data["run_id"] == "test-run-001"
        assert data["golden_run_id"] == golden_metadata.run_id

    def test_get_golden_metadata(self, temp_run_dir: Path, monkeypatch):
        """Test getting golden run metadata."""
        monkeypatch.chdir(temp_run_dir.parent.parent)

        # Capture golden
        golden_metadata = capture_golden_run(
            run_dir=temp_run_dir,
            product_name="test-product",
            git_ref="main",
            git_sha="abc123",
        )

        # Get metadata
        checker = RegressionChecker()
        metadata = checker.get_golden_metadata(
            product_name="test-product",
            git_ref="main",
            golden_run_id=golden_metadata.run_id,
        )

        assert metadata is not None
        assert metadata.run_id == golden_metadata.run_id
        assert metadata.product_name == "test-product"
        assert metadata.git_sha == "abc123"

    def test_get_golden_metadata_not_found(self, tmp_path: Path, monkeypatch):
        """Test getting metadata for non-existent golden run."""
        monkeypatch.chdir(tmp_path)

        checker = RegressionChecker()
        metadata = checker.get_golden_metadata(
            product_name="test-product",
            git_ref="main",
            golden_run_id="nonexistent",
        )

        assert metadata is None


class TestDeterminismGuarantees:
    """Test determinism guarantees."""

    def test_pythonhashseed_set(self):
        """Test that PYTHONHASHSEED is set to 0."""
        assert os.environ.get("PYTHONHASHSEED") == "0"

    def test_json_serialization_sorted_keys(self, tmp_path: Path):
        """Test that JSON serialization uses sorted keys."""
        data = {"z": 1, "a": 2, "m": 3}

        file_path = tmp_path / "test.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True)

        content = file_path.read_text(encoding="utf-8")

        # Keys should be in alphabetical order
        assert content.index('"a"') < content.index('"m"')
        assert content.index('"m"') < content.index('"z"')

    def test_artifact_collection_deterministic_order(self, temp_run_dir: Path):
        """Test that artifact collection maintains deterministic order."""
        # Collect multiple times
        artifacts_1 = _collect_artifacts(temp_run_dir, exclude_events=True)
        artifacts_2 = _collect_artifacts(temp_run_dir, exclude_events=True)
        artifacts_3 = _collect_artifacts(temp_run_dir, exclude_events=True)

        # Order should be identical
        keys_1 = list(artifacts_1.keys())
        keys_2 = list(artifacts_2.keys())
        keys_3 = list(artifacts_3.keys())

        assert keys_1 == keys_2 == keys_3

    def test_hash_computation_across_file_types(self, tmp_path: Path):
        """Test hash computation works across different file types."""
        # JSON file
        json_file = tmp_path / "test.json"
        json_file.write_text(
            json.dumps({"key": "value"}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        # Markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nContent here.\n", encoding="utf-8")

        # YAML file (as bytes to test binary-safe hashing)
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\n", encoding="utf-8")

        # All should produce valid SHA256 hashes
        json_hash = _compute_file_hash(json_file)
        md_hash = _compute_file_hash(md_file)
        yaml_hash = _compute_file_hash(yaml_file)

        assert len(json_hash) == 64
        assert len(md_hash) == 64
        assert len(yaml_hash) == 64

        # Different files should have different hashes
        assert json_hash != md_hash != yaml_hash
