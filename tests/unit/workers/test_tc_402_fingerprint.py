"""Unit tests for TC-402: Deterministic repo fingerprinting and inventory.

Tests cover:
- Deterministic fingerprinting algorithm
- File tree walking and .gitignore respect
- Language detection
- Binary file detection
- Event emission
- Artifact validation
- Reproducibility guarantees

Spec references:
- specs/02_repo_ingestion.md:158-177 (Fingerprinting algorithm)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/21_worker_contracts.md (W1 binding requirements)

TC-402: W1.2 Deterministic repo fingerprinting and inventory
"""

import json
import tempfile
from pathlib import Path
import pytest

from launch.workers.w1_repo_scout.fingerprint import (
    compute_file_hash,
    detect_primary_language,
    is_binary_file,
    walk_repo_files,
    compute_repo_fingerprint,
    build_repo_inventory,
    write_repo_inventory_artifact,
    emit_fingerprint_events,
    fingerprint_repo,
)
from launch.io.run_layout import RunLayout


class TestComputeFileHash:
    """Test file hash computation."""

    def test_compute_file_hash_simple(self):
        """Test hash computation for simple text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            test_file = repo_dir / "test.txt"
            test_file.write_text("Hello, World!", encoding="utf-8")

            file_hash = compute_file_hash(test_file, "test.txt")

            # Hash should be 64-character hex string
            assert len(file_hash) == 64
            assert all(c in "0123456789abcdef" for c in file_hash)

    def test_compute_file_hash_deterministic(self):
        """Test hash is deterministic for same content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            test_file = repo_dir / "test.txt"
            test_file.write_text("Deterministic content", encoding="utf-8")

            hash1 = compute_file_hash(test_file, "test.txt")
            hash2 = compute_file_hash(test_file, "test.txt")

            assert hash1 == hash2

    def test_compute_file_hash_different_content(self):
        """Test different content produces different hashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            file1 = repo_dir / "file1.txt"
            file1.write_text("Content A", encoding="utf-8")

            file2 = repo_dir / "file2.txt"
            file2.write_text("Content B", encoding="utf-8")

            hash1 = compute_file_hash(file1, "file1.txt")
            hash2 = compute_file_hash(file2, "file2.txt")

            assert hash1 != hash2

    def test_compute_file_hash_path_sensitive(self):
        """Test hash includes file path (different paths = different hashes)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Same content, different paths
            file1 = repo_dir / "path1.txt"
            file1.write_text("Same content", encoding="utf-8")

            file2 = repo_dir / "path2.txt"
            file2.write_text("Same content", encoding="utf-8")

            hash1 = compute_file_hash(file1, "path1.txt")
            hash2 = compute_file_hash(file2, "path2.txt")

            # Should be different because paths differ
            assert hash1 != hash2

    def test_compute_file_hash_binary_content(self):
        """Test hash computation for binary file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            binary_file = repo_dir / "test.bin"
            binary_file.write_bytes(b"\x00\x01\x02\x03\xFF\xFE")

            file_hash = compute_file_hash(binary_file, "test.bin")

            assert len(file_hash) == 64
            assert all(c in "0123456789abcdef" for c in file_hash)

    def test_compute_file_hash_empty_file(self):
        """Test hash computation for empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            empty_file = repo_dir / "empty.txt"
            empty_file.write_text("", encoding="utf-8")

            file_hash = compute_file_hash(empty_file, "empty.txt")

            # Should still produce valid hash
            assert len(file_hash) == 64

    def test_compute_file_hash_unreadable_file(self):
        """Test hash computation for unreadable file (graceful failure)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            # Non-existent file
            fake_file = repo_dir / "nonexistent.txt"

            # Should handle gracefully with empty content
            file_hash = compute_file_hash(fake_file, "nonexistent.txt")
            assert len(file_hash) == 64


class TestDetectPrimaryLanguage:
    """Test programming language detection."""

    def test_detect_python_repository(self):
        """Test detection of Python as primary language."""
        file_paths = [
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "README.md",
            "setup.py",
        ]

        language = detect_primary_language(file_paths)
        assert language == "Python"

    def test_detect_csharp_repository(self):
        """Test detection of C# as primary language."""
        file_paths = [
            "src/Program.cs",
            "src/Utils.cs",
            "tests/ProgramTests.cs",
            "README.md",
        ]

        language = detect_primary_language(file_paths)
        assert language == "C#"

    def test_detect_java_repository(self):
        """Test detection of Java as primary language."""
        file_paths = [
            "src/main/java/Main.java",
            "src/main/java/Utils.java",
            "README.md",
        ]

        language = detect_primary_language(file_paths)
        assert language == "Java"

    def test_detect_javascript_repository(self):
        """Test detection of JavaScript as primary language."""
        file_paths = [
            "src/index.js",
            "src/utils.js",
            "package.json",
            "README.md",
        ]

        language = detect_primary_language(file_paths)
        assert language == "JavaScript"

    def test_detect_unknown_language(self):
        """Test unknown language for docs-only repos."""
        file_paths = [
            "README.md",
            "docs/intro.md",
            "LICENSE",
        ]

        language = detect_primary_language(file_paths)
        assert language == "unknown"

    def test_detect_mixed_language_preference(self):
        """Test that code files are weighted higher than config files."""
        file_paths = [
            "src/main.py",  # Python code (weight: 3)
            "config.json",  # JSON config (weight: 1)
            "config.yaml",  # YAML config (weight: 1)
            "data.json",  # JSON data (weight: 1)
            "settings.yaml",  # YAML settings (weight: 1)
        ]

        language = detect_primary_language(file_paths)
        # Python should win despite fewer files (due to higher weight)
        assert language == "Python"


class TestIsBinaryFile:
    """Test binary file detection."""

    def test_text_file_not_binary(self):
        """Test that text files are not detected as binary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            text_file = Path(tmpdir) / "test.txt"
            text_file.write_text("This is text content", encoding="utf-8")

            assert not is_binary_file(text_file)

    def test_python_file_not_binary(self):
        """Test that Python files are not detected as binary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = Path(tmpdir) / "test.py"
            py_file.write_text("print('Hello')", encoding="utf-8")

            assert not is_binary_file(py_file)

    def test_pdf_file_is_binary(self):
        """Test that PDF files are detected as binary (extension)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "document.pdf"
            pdf_file.write_bytes(b"%PDF-1.4\x00\x00\x00")

            assert is_binary_file(pdf_file)

    def test_zip_file_is_binary(self):
        """Test that ZIP files are detected as binary (extension)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_file = Path(tmpdir) / "archive.zip"
            zip_file.write_bytes(b"PK\x03\x04")

            assert is_binary_file(zip_file)

    def test_image_file_is_binary(self):
        """Test that image files are detected as binary (extension)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = Path(tmpdir) / "image.png"
            png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

            assert is_binary_file(png_file)

    def test_null_bytes_detected_as_binary(self):
        """Test that files with null bytes are detected as binary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_file = Path(tmpdir) / "unknown.dat"
            # Text with null bytes
            binary_file.write_bytes(b"text\x00binary\x00data")

            assert is_binary_file(binary_file)

    def test_class_file_is_binary(self):
        """Test that Java .class files are detected as binary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            class_file = Path(tmpdir) / "Main.class"
            class_file.write_bytes(b"\xCA\xFE\xBA\xBE")

            assert is_binary_file(class_file)


class TestWalkRepoFiles:
    """Test repository file walking."""

    def test_walk_simple_repo(self):
        """Test walking a simple repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create simple structure
            (repo_dir / "README.md").write_text("# Readme")
            (repo_dir / "src").mkdir()
            (repo_dir / "src" / "main.py").write_text("print('hello')")
            (repo_dir / "src" / "utils.py").write_text("def util(): pass")

            file_paths = walk_repo_files(repo_dir)

            # Should find all files
            assert len(file_paths) == 3
            assert "README.md" in file_paths
            assert "src/main.py" in file_paths
            assert "src/utils.py" in file_paths

    def test_walk_ignores_git_directory(self):
        """Test that .git directory is ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "file.txt").write_text("content")
            (repo_dir / ".git").mkdir()
            (repo_dir / ".git" / "config").write_text("git config")

            file_paths = walk_repo_files(repo_dir)

            # Should not include .git files
            assert len(file_paths) == 1
            assert "file.txt" in file_paths
            assert not any(".git" in p for p in file_paths)

    def test_walk_ignores_pycache(self):
        """Test that __pycache__ directories are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "main.py").write_text("print('hello')")
            (repo_dir / "__pycache__").mkdir()
            (repo_dir / "__pycache__" / "main.cpython-39.pyc").write_bytes(b"\x00")

            file_paths = walk_repo_files(repo_dir)

            # Should not include __pycache__ files
            assert len(file_paths) == 1
            assert "main.py" in file_paths
            assert not any("__pycache__" in p for p in file_paths)

    def test_walk_ignores_node_modules(self):
        """Test that node_modules directories are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "index.js").write_text("console.log('hi')")
            (repo_dir / "node_modules").mkdir()
            (repo_dir / "node_modules" / "package").mkdir()
            (repo_dir / "node_modules" / "package" / "index.js").write_text("")

            file_paths = walk_repo_files(repo_dir)

            # Should not include node_modules files
            assert len(file_paths) == 1
            assert "index.js" in file_paths
            assert not any("node_modules" in p for p in file_paths)

    def test_walk_deterministic_ordering(self):
        """Test that file paths are returned in deterministic order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create files in non-alphabetical order
            (repo_dir / "zebra.txt").write_text("")
            (repo_dir / "alpha.txt").write_text("")
            (repo_dir / "beta.txt").write_text("")

            file_paths1 = walk_repo_files(repo_dir)
            file_paths2 = walk_repo_files(repo_dir)

            # Should be sorted
            assert file_paths1 == ["alpha.txt", "beta.txt", "zebra.txt"]
            # Should be deterministic
            assert file_paths1 == file_paths2

    def test_walk_empty_repo(self):
        """Test walking an empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            file_paths = walk_repo_files(repo_dir)

            assert file_paths == []

    def test_walk_nested_directories(self):
        """Test walking deeply nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "a" / "b" / "c").mkdir(parents=True)
            (repo_dir / "a" / "file1.txt").write_text("")
            (repo_dir / "a" / "b" / "file2.txt").write_text("")
            (repo_dir / "a" / "b" / "c" / "file3.txt").write_text("")

            file_paths = walk_repo_files(repo_dir)

            assert len(file_paths) == 3
            assert "a/file1.txt" in file_paths
            assert "a/b/file2.txt" in file_paths
            assert "a/b/c/file3.txt" in file_paths


class TestComputeRepoFingerprint:
    """Test repository fingerprint computation."""

    def test_fingerprint_simple_repo(self):
        """Test fingerprint for simple repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "README.md").write_text("# Project")
            (repo_dir / "main.py").write_text("print('hello')")

            result = compute_repo_fingerprint(repo_dir)

            assert "repo_fingerprint" in result
            assert len(result["repo_fingerprint"]) == 64
            assert result["file_count"] == 2
            assert result["total_bytes"] > 0

    def test_fingerprint_deterministic(self):
        """Test that fingerprint is deterministic (same repo = same hash)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "file1.txt").write_text("Content A")
            (repo_dir / "file2.txt").write_text("Content B")

            result1 = compute_repo_fingerprint(repo_dir)
            result2 = compute_repo_fingerprint(repo_dir)

            assert result1["repo_fingerprint"] == result2["repo_fingerprint"]
            assert result1["file_count"] == result2["file_count"]

    def test_fingerprint_changes_with_content(self):
        """Test that fingerprint changes when content changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # First fingerprint
            (repo_dir / "file.txt").write_text("Original")
            result1 = compute_repo_fingerprint(repo_dir)

            # Modify content
            (repo_dir / "file.txt").write_text("Modified")
            result2 = compute_repo_fingerprint(repo_dir)

            # Fingerprints should differ
            assert result1["repo_fingerprint"] != result2["repo_fingerprint"]

    def test_fingerprint_changes_with_new_file(self):
        """Test that fingerprint changes when files are added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # First fingerprint
            (repo_dir / "file1.txt").write_text("Content")
            result1 = compute_repo_fingerprint(repo_dir)

            # Add new file
            (repo_dir / "file2.txt").write_text("New content")
            result2 = compute_repo_fingerprint(repo_dir)

            # Fingerprints should differ
            assert result1["repo_fingerprint"] != result2["repo_fingerprint"]
            assert result2["file_count"] == result1["file_count"] + 1

    def test_fingerprint_empty_repo(self):
        """Test fingerprint for empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            result = compute_repo_fingerprint(repo_dir)

            # Should return zero fingerprint
            assert result["repo_fingerprint"] == "0" * 64
            assert result["file_count"] == 0
            assert result["total_bytes"] == 0

    def test_fingerprint_order_independence(self):
        """Test that fingerprint is independent of file creation order."""
        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            repo_dir1 = Path(tmpdir1)
            repo_dir2 = Path(tmpdir2)

            # Create files in different order
            (repo_dir1 / "a.txt").write_text("A")
            (repo_dir1 / "b.txt").write_text("B")

            (repo_dir2 / "b.txt").write_text("B")
            (repo_dir2 / "a.txt").write_text("A")

            result1 = compute_repo_fingerprint(repo_dir1)
            result2 = compute_repo_fingerprint(repo_dir2)

            # Should have same fingerprint (order doesn't matter)
            assert result1["repo_fingerprint"] == result2["repo_fingerprint"]


class TestBuildRepoInventory:
    """Test repository inventory building."""

    def test_build_minimal_inventory(self):
        """Test building inventory for minimal repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "README.md").write_text("# Project")
            (repo_dir / "main.py").write_text("print('hello')")

            inventory = build_repo_inventory(
                repo_dir=repo_dir,
                repo_url="https://github.com/test/repo.git",
                repo_sha="a" * 40,
            )

            assert inventory["schema_version"] == "1.0"
            assert inventory["repo_url"] == "https://github.com/test/repo.git"
            assert inventory["repo_sha"] == "a" * 40
            assert len(inventory["repo_fingerprint"]) == 64
            assert inventory["file_count"] == 2
            assert "README.md" in inventory["paths"]
            assert "main.py" in inventory["paths"]

    def test_build_inventory_detects_language(self):
        """Test that inventory detects primary language."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "src").mkdir()
            (repo_dir / "src" / "main.py").write_text("# Python")
            (repo_dir / "src" / "utils.py").write_text("# Utils")

            inventory = build_repo_inventory(
                repo_dir=repo_dir,
                repo_url="https://github.com/test/repo.git",
                repo_sha="b" * 40,
            )

            assert "Python" in inventory["fingerprint"]["primary_languages"]
            assert "Python" in inventory["repo_profile"]["primary_languages"]

    def test_build_inventory_identifies_binary_assets(self):
        """Test that inventory identifies binary assets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            (repo_dir / "doc.pdf").write_bytes(b"%PDF-1.4")
            (repo_dir / "image.png").write_bytes(b"\x89PNG")
            (repo_dir / "main.py").write_text("# Code")

            inventory = build_repo_inventory(
                repo_dir=repo_dir,
                repo_url="https://github.com/test/repo.git",
                repo_sha="c" * 40,
            )

            assert "doc.pdf" in inventory["binary_assets"]
            assert "image.png" in inventory["binary_assets"]
            assert "main.py" not in inventory["binary_assets"]

    def test_build_inventory_structure_matches_schema(self):
        """Test that inventory structure matches repo_inventory.schema.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "test.txt").write_text("test")

            inventory = build_repo_inventory(
                repo_dir=repo_dir,
                repo_url="https://github.com/test/repo.git",
                repo_sha="d" * 40,
            )

            # Required top-level fields
            assert "schema_version" in inventory
            assert "repo_url" in inventory
            assert "repo_sha" in inventory
            assert "fingerprint" in inventory
            assert "repo_profile" in inventory
            assert "paths" in inventory
            assert "doc_entrypoints" in inventory
            assert "example_paths" in inventory

            # Required fingerprint fields
            assert "primary_languages" in inventory["fingerprint"]

            # Required repo_profile fields
            assert "platform_family" in inventory["repo_profile"]
            assert "primary_languages" in inventory["repo_profile"]
            assert "build_systems" in inventory["repo_profile"]
            assert "package_manifests" in inventory["repo_profile"]
            assert "recommended_test_commands" in inventory["repo_profile"]
            assert "example_locator" in inventory["repo_profile"]
            assert "doc_locator" in inventory["repo_profile"]


class TestArtifactWriting:
    """Test artifact writing."""

    def test_write_repo_inventory_artifact(self):
        """Test writing repo_inventory.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "artifacts").mkdir()

            run_layout = RunLayout(run_dir=run_dir)

            inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/test/repo.git",
                "repo_sha": "e" * 40,
                "fingerprint": {"primary_languages": ["Python"]},
                "repo_profile": {
                    "platform_family": "python",
                    "primary_languages": ["Python"],
                    "build_systems": [],
                    "package_manifests": [],
                    "recommended_test_commands": [],
                    "example_locator": "standard",
                    "doc_locator": "standard",
                },
                "paths": ["main.py"],
                "doc_entrypoints": [],
                "example_paths": [],
                "repo_fingerprint": "f" * 64,
            }

            write_repo_inventory_artifact(run_layout, inventory)

            artifact_path = run_layout.artifacts_dir / "repo_inventory.json"
            assert artifact_path.exists()

            # Verify JSON is valid
            content = json.loads(artifact_path.read_text())
            assert content["repo_sha"] == "e" * 40
            assert content["repo_fingerprint"] == "f" * 64

    def test_write_artifact_deterministic(self):
        """Test that artifact writing is deterministic."""
        inventory = {
            "schema_version": "1.0",
            "repo_url": "https://github.com/test/repo.git",
            "repo_sha": "g" * 40,
            "fingerprint": {"primary_languages": ["Python"]},
            "repo_profile": {
                "platform_family": "python",
                "primary_languages": ["Python"],
                "build_systems": [],
                "package_manifests": [],
                "recommended_test_commands": [],
                "example_locator": "standard",
                "doc_locator": "standard",
            },
            "paths": ["a.py", "b.py"],
            "doc_entrypoints": [],
            "example_paths": [],
            "repo_fingerprint": "h" * 64,
        }

        outputs = []
        for _ in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                run_dir = Path(tmpdir)
                (run_dir / "artifacts").mkdir()
                run_layout = RunLayout(run_dir=run_dir)

                write_repo_inventory_artifact(run_layout, inventory)

                artifact_path = run_layout.artifacts_dir / "repo_inventory.json"
                outputs.append(artifact_path.read_bytes())

        # All outputs should be byte-identical
        assert outputs[0] == outputs[1] == outputs[2]


class TestEventEmission:
    """Test event emission."""

    def test_emit_fingerprint_events(self):
        """Test that fingerprint events are emitted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "artifacts").mkdir()
            events_file = run_dir / "events.ndjson"
            events_file.write_text("")

            run_layout = RunLayout(run_dir=run_dir)

            # Write artifact first
            inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/test/repo.git",
                "repo_sha": "i" * 40,
                "fingerprint": {"primary_languages": []},
                "repo_profile": {
                    "platform_family": "unknown",
                    "primary_languages": [],
                    "build_systems": [],
                    "package_manifests": [],
                    "recommended_test_commands": [],
                    "example_locator": "standard",
                    "doc_locator": "standard",
                },
                "paths": [],
                "doc_entrypoints": [],
                "example_paths": [],
                "repo_fingerprint": "j" * 64,
            }
            write_repo_inventory_artifact(run_layout, inventory)

            emit_fingerprint_events(
                run_layout=run_layout,
                run_id="test-run-123",
                trace_id="trace-456",
                span_id="span-789",
                fingerprint="j" * 64,
                file_count=5,
            )

            # Verify events were written
            events_content = events_file.read_text()
            assert events_content

            # Parse events
            events = [json.loads(line) for line in events_content.strip().split("\n")]

            # Verify event types
            event_types = [e["type"] for e in events]
            assert "WORK_ITEM_STARTED" in event_types
            assert "REPO_FINGERPRINT_COMPUTED" in event_types
            assert "ARTIFACT_WRITTEN" in event_types
            assert "WORK_ITEM_FINISHED" in event_types

            # Verify fingerprint event payload
            fingerprint_event = next(
                e for e in events if e["type"] == "REPO_FINGERPRINT_COMPUTED"
            )
            assert fingerprint_event["payload"]["fingerprint"] == "j" * 64
            assert fingerprint_event["payload"]["file_count"] == 5


class TestIntegration:
    """Integration tests for full fingerprint workflow."""

    def test_fingerprint_repo_integration(self):
        """Test full fingerprint_repo workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Setup: Create repo directory
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "README.md").write_text("# Test Repo")
            (repo_dir / "main.py").write_text("print('test')")

            # Setup: Create resolved_refs.json (dependency from TC-401)
            run_layout.artifacts_dir.mkdir(parents=True)
            resolved_refs = {
                "repo": {
                    "repo_url": "https://github.com/test/repo.git",
                    "resolved_sha": "k" * 40,
                }
            }
            (run_layout.artifacts_dir / "resolved_refs.json").write_text(
                json.dumps(resolved_refs)
            )

            # Initialize events.ndjson
            (run_dir / "events.ndjson").write_text("")

            # Run fingerprint
            inventory = fingerprint_repo(repo_dir, run_dir)

            # Verify inventory
            assert inventory["repo_url"] == "https://github.com/test/repo.git"
            assert inventory["repo_sha"] == "k" * 40
            assert len(inventory["repo_fingerprint"]) == 64
            assert inventory["file_count"] == 2

            # Verify artifact was written
            artifact_path = run_layout.artifacts_dir / "repo_inventory.json"
            assert artifact_path.exists()

            # Verify events were emitted
            events_file = run_dir / "events.ndjson"
            assert events_file.exists()
            assert events_file.stat().st_size > 0

    def test_fingerprint_repo_missing_dependency(self):
        """Test that fingerprint_repo fails gracefully if TC-401 not run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            repo_dir = Path(tmpdir) / "work" / "repo"
            repo_dir.mkdir(parents=True)

            # No resolved_refs.json created
            (run_dir / "artifacts").mkdir()

            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError) as exc_info:
                fingerprint_repo(repo_dir, run_dir)

            assert "resolved_refs.json" in str(exc_info.value)
            assert "TC-401" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
