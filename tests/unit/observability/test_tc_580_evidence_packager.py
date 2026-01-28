"""
Test suite for TC-580: Evidence Packaging.

Tests evidence package creation, manifest generation, and file handling.
"""

import json
import zipfile
from pathlib import Path

import pytest

from src.launch.observability.evidence_packager import (
    PackageFile,
    PackageManifest,
    create_evidence_package,
)


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Path:
    """Create temporary run directory structure."""
    run_dir = tmp_path / "runs" / "test-run-123"
    run_dir.mkdir(parents=True)

    # Create artifacts directory
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir()

    # Create sample artifacts
    (artifacts_dir / "snapshot.json").write_text('{"run_id": "test-run-123"}', encoding="utf-8")
    (artifacts_dir / "product_facts.json").write_text('{"product_name": "Test"}', encoding="utf-8")

    # Create events file
    (run_dir / "events.ndjson").write_text('{"event_id": "1"}\n{"event_id": "2"}\n', encoding="utf-8")

    # Create snapshot
    (run_dir / "snapshot.json").write_text('{"run_id": "test-run-123"}', encoding="utf-8")

    return run_dir


def test_create_evidence_package_basic(temp_run_dir: Path):
    """Test basic evidence package creation."""
    output_path = temp_run_dir / "evidence.zip"

    manifest = create_evidence_package(temp_run_dir, output_path)

    assert output_path.exists()
    assert manifest.run_id == "test-run-123"
    assert manifest.total_files > 0
    assert manifest.total_size_bytes > 0
    assert len(manifest.files) > 0


def test_create_evidence_package_nonexistent_dir(tmp_path: Path):
    """Test creating package from nonexistent directory."""
    nonexistent = tmp_path / "does_not_exist"
    output_path = tmp_path / "evidence.zip"

    with pytest.raises(FileNotFoundError):
        create_evidence_package(nonexistent, output_path)


def test_create_evidence_package_file_list(temp_run_dir: Path):
    """Test that package contains expected files."""
    output_path = temp_run_dir / "evidence.zip"

    manifest = create_evidence_package(temp_run_dir, output_path)

    # Check expected files are in manifest
    file_paths = [f.relative_path for f in manifest.files]

    assert "snapshot.json" in file_paths
    assert "events.ndjson" in file_paths
    assert "artifacts/snapshot.json" in file_paths
    assert "artifacts/product_facts.json" in file_paths


def test_create_evidence_package_zip_content(temp_run_dir: Path):
    """Test that ZIP file contains expected content."""
    output_path = temp_run_dir / "evidence.zip"

    create_evidence_package(temp_run_dir, output_path)

    # Verify ZIP content
    with zipfile.ZipFile(output_path, "r") as zipf:
        namelist = zipf.namelist()

        assert "snapshot.json" in namelist
        assert "events.ndjson" in namelist
        assert "artifacts/snapshot.json" in namelist

        # Verify content integrity
        snapshot_content = zipf.read("snapshot.json").decode("utf-8")
        assert "test-run-123" in snapshot_content


def test_package_manifest_to_dict(temp_run_dir: Path):
    """Test PackageManifest serialization to dict."""
    output_path = temp_run_dir / "evidence.zip"

    manifest = create_evidence_package(temp_run_dir, output_path)
    result = manifest.to_dict()

    assert isinstance(result, dict)
    assert "package_created_at" in result
    assert result["run_id"] == "test-run-123"
    assert result["total_files"] == len(manifest.files)
    assert isinstance(result["files"], list)


def test_package_manifest_to_json(temp_run_dir: Path):
    """Test PackageManifest serialization to JSON."""
    output_path = temp_run_dir / "evidence.zip"

    manifest = create_evidence_package(temp_run_dir, output_path)
    json_str = manifest.to_json()

    # Verify valid JSON
    parsed = json.loads(json_str)
    assert parsed["run_id"] == "test-run-123"
    assert "files" in parsed


def test_package_file_metadata(temp_run_dir: Path):
    """Test that PackageFile metadata is correct."""
    output_path = temp_run_dir / "evidence.zip"

    manifest = create_evidence_package(temp_run_dir, output_path)

    # Find snapshot.json in manifest
    snapshot_file = next(f for f in manifest.files if f.relative_path == "snapshot.json")

    assert snapshot_file.size_bytes > 0
    assert len(snapshot_file.sha256) == 64  # SHA256 hex length
    assert snapshot_file.modified_at  # Should have timestamp


def test_create_evidence_package_with_custom_patterns(temp_run_dir: Path):
    """Test creating package with custom include patterns."""
    output_path = temp_run_dir / "evidence.zip"

    # Only include JSON files
    manifest = create_evidence_package(
        temp_run_dir,
        output_path,
        include_patterns=["*.json", "artifacts/*.json"],
    )

    # Should only have JSON files
    for file_info in manifest.files:
        assert file_info.relative_path.endswith(".json")


def test_create_evidence_package_nested_directories(tmp_path: Path):
    """Test packaging with nested directory structure."""
    run_dir = tmp_path / "runs" / "test-run"
    run_dir.mkdir(parents=True)

    # Create nested structure
    (run_dir / "artifacts" / "subfolder").mkdir(parents=True)
    (run_dir / "artifacts" / "subfolder" / "deep.json").write_text('{"test": true}', encoding="utf-8")

    (run_dir / "reports" / "gate1").mkdir(parents=True)
    (run_dir / "reports" / "gate1" / "report.md").write_text("# Report", encoding="utf-8")

    output_path = run_dir / "evidence.zip"
    manifest = create_evidence_package(run_dir, output_path)

    # Check nested paths preserved
    file_paths = [f.relative_path for f in manifest.files]
    assert "artifacts/subfolder/deep.json" in file_paths
    assert "reports/gate1/report.md" in file_paths


def test_create_evidence_package_deterministic_ordering(temp_run_dir: Path):
    """Test that files are ordered deterministically."""
    # Create multiple files in different directories
    (temp_run_dir / "a_first.json").write_text("{}", encoding="utf-8")
    (temp_run_dir / "z_last.json").write_text("{}", encoding="utf-8")

    output_path = temp_run_dir / "evidence.zip"

    # Generate package twice
    manifest1 = create_evidence_package(temp_run_dir, output_path)
    output_path.unlink()  # Delete ZIP
    manifest2 = create_evidence_package(temp_run_dir, output_path)

    # File order should be identical
    paths1 = [f.relative_path for f in manifest1.files]
    paths2 = [f.relative_path for f in manifest2.files]

    assert paths1 == paths2
    assert paths1 == sorted(paths1)  # Should be sorted


def test_create_evidence_package_empty_directory(tmp_path: Path):
    """Test creating package from empty directory."""
    run_dir = tmp_path / "runs" / "empty-run"
    run_dir.mkdir(parents=True)

    output_path = run_dir / "evidence.zip"
    manifest = create_evidence_package(run_dir, output_path)

    assert manifest.total_files == 0
    assert manifest.total_size_bytes == 0
    assert output_path.exists()  # ZIP created but empty


def test_create_evidence_package_large_files(tmp_path: Path):
    """Test handling of larger files."""
    run_dir = tmp_path / "runs" / "large-run"
    run_dir.mkdir(parents=True)

    # Create a larger file (1MB)
    large_content = "x" * (1024 * 1024)
    (run_dir / "large.txt").write_text(large_content, encoding="utf-8")

    output_path = run_dir / "evidence.zip"
    manifest = create_evidence_package(run_dir, output_path, include_patterns=["large.txt"])

    # Should handle large file
    large_file = next(f for f in manifest.files if f.relative_path == "large.txt")
    assert large_file.size_bytes == len(large_content.encode("utf-8"))
    assert large_file.sha256  # Should have hash


def test_package_file_sha256_correctness(temp_run_dir: Path):
    """Test that SHA256 hashes are computed correctly."""
    # Create file with known content
    test_file = temp_run_dir / "test.txt"
    test_content = "Hello, World!"
    test_file.write_text(test_content, encoding="utf-8")

    output_path = temp_run_dir / "evidence.zip"
    manifest = create_evidence_package(
        temp_run_dir,
        output_path,
        include_patterns=["test.txt"],
    )

    # Compute expected hash
    import hashlib
    expected_hash = hashlib.sha256(test_content.encode("utf-8")).hexdigest()

    # Verify hash matches
    test_file_info = manifest.files[0]
    assert test_file_info.sha256 == expected_hash


def test_create_evidence_package_forward_slashes(temp_run_dir: Path):
    """Test that paths use forward slashes in ZIP."""
    # Create nested structure
    (temp_run_dir / "nested" / "deep").mkdir(parents=True)
    (temp_run_dir / "nested" / "deep" / "file.json").write_text("{}", encoding="utf-8")

    output_path = temp_run_dir / "evidence.zip"
    manifest = create_evidence_package(temp_run_dir, output_path, include_patterns=["nested/**/*"])

    # Check that paths use forward slashes
    nested_file = next(f for f in manifest.files if "file.json" in f.relative_path)
    assert "/" in nested_file.relative_path
    assert "\\" not in nested_file.relative_path


def test_package_manifest_total_size(temp_run_dir: Path):
    """Test that total_size_bytes is accurate."""
    # Create files with known sizes
    (temp_run_dir / "file1.txt").write_text("a" * 100, encoding="utf-8")
    (temp_run_dir / "file2.txt").write_text("b" * 200, encoding="utf-8")

    output_path = temp_run_dir / "evidence.zip"
    manifest = create_evidence_package(
        temp_run_dir,
        output_path,
        include_patterns=["file*.txt"],
    )

    # Verify total size
    expected_size = sum(f.size_bytes for f in manifest.files)
    assert manifest.total_size_bytes == expected_size
    assert manifest.total_size_bytes == 300  # 100 + 200


def test_create_evidence_package_iso8601_timestamps(temp_run_dir: Path):
    """Test that timestamps are in ISO 8601 format."""
    output_path = temp_run_dir / "evidence.zip"
    manifest = create_evidence_package(temp_run_dir, output_path)

    # Check package timestamp
    assert "T" in manifest.package_created_at
    assert manifest.package_created_at.endswith(("Z", "+00:00"))

    # Check file timestamps
    for file_info in manifest.files:
        assert "T" in file_info.modified_at


def test_create_evidence_package_excludes_directories(temp_run_dir: Path):
    """Test that directories themselves are not included."""
    (temp_run_dir / "empty_dir").mkdir()
    (temp_run_dir / "dir_with_file").mkdir()
    (temp_run_dir / "dir_with_file" / "file.txt").write_text("content", encoding="utf-8")

    output_path = temp_run_dir / "evidence.zip"
    manifest = create_evidence_package(temp_run_dir, output_path, include_patterns=["**/*"])

    # Only files should be in manifest, not directories
    for file_info in manifest.files:
        assert not file_info.relative_path.endswith("/")

    # File in directory should be included
    assert any("dir_with_file/file.txt" in f.relative_path for f in manifest.files)


def test_package_file_to_dict(temp_run_dir: Path):
    """Test PackageFile serialization to dict."""
    package_file = PackageFile(
        relative_path="test/file.json",
        size_bytes=1024,
        sha256="a" * 64,
        modified_at="2024-01-01T00:00:00Z",
    )

    result = package_file.to_dict()

    assert isinstance(result, dict)
    assert result["relative_path"] == "test/file.json"
    assert result["size_bytes"] == 1024
    assert result["sha256"] == "a" * 64
    assert result["modified_at"] == "2024-01-01T00:00:00Z"


def test_create_evidence_package_run_id_extraction(tmp_path: Path):
    """Test that run_id is extracted from directory name."""
    run_dir = tmp_path / "runs" / "custom-run-id-456"
    run_dir.mkdir(parents=True)
    (run_dir / "snapshot.json").write_text("{}", encoding="utf-8")

    output_path = run_dir / "evidence.zip"
    manifest = create_evidence_package(run_dir, output_path)

    assert manifest.run_id == "custom-run-id-456"


def test_create_evidence_package_zip_compression(temp_run_dir: Path):
    """Test that ZIP uses compression."""
    # Create compressible content
    compressible = "a" * 10000
    (temp_run_dir / "compressible.txt").write_text(compressible, encoding="utf-8")

    output_path = temp_run_dir / "evidence.zip"
    create_evidence_package(
        temp_run_dir,
        output_path,
        include_patterns=["compressible.txt"],
    )

    # Verify compression
    zip_size = output_path.stat().st_size
    original_size = len(compressible.encode("utf-8"))

    # Compressed size should be significantly smaller
    assert zip_size < original_size


def test_create_evidence_package_with_run_config(temp_run_dir: Path):
    """Test packaging with run_config files."""
    (temp_run_dir / "run_config.yaml").write_text("product_name: Test", encoding="utf-8")
    (temp_run_dir / "run_config.json").write_text('{"product_name": "Test"}', encoding="utf-8")

    output_path = temp_run_dir / "evidence.zip"
    manifest = create_evidence_package(temp_run_dir, output_path)

    file_paths = [f.relative_path for f in manifest.files]
    assert "run_config.yaml" in file_paths
    assert "run_config.json" in file_paths


def test_create_evidence_package_manifest_count(temp_run_dir: Path):
    """Test that total_files matches actual file count."""
    output_path = temp_run_dir / "evidence.zip"
    manifest = create_evidence_package(temp_run_dir, output_path)

    assert manifest.total_files == len(manifest.files)
    assert manifest.total_files > 0
