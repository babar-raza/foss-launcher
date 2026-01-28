"""Unit tests for TC-403: Documentation discovery in cloned product repo.

Tests cover:
- README detection
- Pattern-based filename detection
- Content-based keyword detection
- Doc relevance scoring
- Front matter extraction
- Doc root identification
- Deterministic ordering
- Event emission
- Artifact validation

Spec references:
- specs/02_repo_ingestion.md:78-142 (Doc discovery)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/21_worker_contracts.md (W1 binding requirements)

TC-403: W1.3 Discover docs in cloned product repo
"""

import json
import tempfile
from pathlib import Path
import pytest

from launch.workers.w1_repo_scout.discover_docs import (
    is_readme,
    matches_pattern_based_detection,
    check_content_based_detection,
    extract_front_matter,
    compute_doc_relevance_score,
    discover_documentation_files,
    identify_doc_roots,
    build_discovered_docs_artifact,
    write_discovered_docs_artifact,
    update_repo_inventory_with_docs,
    emit_discover_docs_events,
    discover_docs,
)
from launch.io.run_layout import RunLayout


class TestIsReadme:
    """Test README file detection."""

    def test_readme_uppercase(self):
        """Test detection of uppercase README."""
        assert is_readme(Path("README.md"))
        assert is_readme(Path("README.txt"))
        assert is_readme(Path("README"))

    def test_readme_lowercase(self):
        """Test detection of lowercase readme."""
        assert is_readme(Path("readme.md"))
        assert is_readme(Path("readme.txt"))

    def test_readme_mixed_case(self):
        """Test detection of mixed case README."""
        assert is_readme(Path("ReadMe.md"))
        assert is_readme(Path("Readme.txt"))

    def test_not_readme(self):
        """Test that non-README files are not detected."""
        assert not is_readme(Path("INSTALL.md"))
        assert not is_readme(Path("CONTRIBUTING.md"))
        assert not is_readme(Path("main.py"))


class TestPatternBasedDetection:
    """Test pattern-based filename detection."""

    def test_implementation_notes_pattern(self):
        """Test detection of implementation notes files."""
        matches, doc_type = matches_pattern_based_detection(Path("IMPLEMENTATION_NOTES.md"))
        assert matches
        assert doc_type == "implementation_notes"

        matches, doc_type = matches_pattern_based_detection(Path("MY_IMPLEMENTATION.md"))
        assert matches
        assert doc_type == "implementation_notes"

    def test_architecture_pattern(self):
        """Test detection of architecture documentation."""
        matches, doc_type = matches_pattern_based_detection(Path("ARCHITECTURE.md"))
        assert matches
        assert doc_type == "architecture"

        matches, doc_type = matches_pattern_based_detection(Path("DESIGN.md"))
        assert matches
        assert doc_type == "architecture"

        matches, doc_type = matches_pattern_based_detection(Path("SPEC.md"))
        assert matches
        assert doc_type == "architecture"

    def test_changelog_pattern(self):
        """Test detection of changelog files."""
        matches, doc_type = matches_pattern_based_detection(Path("CHANGELOG.md"))
        assert matches
        assert doc_type == "changelog"

        matches, doc_type = matches_pattern_based_detection(Path("CHANGELOG_2024.md"))
        assert matches
        assert doc_type == "changelog"

    def test_contributing_pattern(self):
        """Test detection of contributing files."""
        matches, doc_type = matches_pattern_based_detection(Path("CONTRIBUTING.md"))
        assert matches
        assert doc_type == "other"

    def test_notes_pattern(self):
        """Test detection of notes files."""
        matches, doc_type = matches_pattern_based_detection(Path("RELEASE_NOTES.md"))
        assert matches
        assert doc_type == "implementation_notes"

    def test_plan_pattern(self):
        """Test detection of plan files."""
        matches, doc_type = matches_pattern_based_detection(Path("PROJECT_PLAN.md"))
        assert matches
        assert doc_type == "other"

    def test_roadmap_pattern(self):
        """Test detection of roadmap files."""
        matches, doc_type = matches_pattern_based_detection(Path("ROADMAP.md"))
        assert matches
        assert doc_type == "other"

    def test_summary_pattern(self):
        """Test detection of summary files."""
        matches, doc_type = matches_pattern_based_detection(Path("PROJECT_SUMMARY.md"))
        assert matches
        assert doc_type == "other"

    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        matches, _ = matches_pattern_based_detection(Path("architecture.md"))
        assert matches

        matches, _ = matches_pattern_based_detection(Path("Architecture.MD"))
        assert matches

    def test_no_match(self):
        """Test that non-matching files return False."""
        matches, doc_type = matches_pattern_based_detection(Path("main.py"))
        assert not matches
        assert doc_type is None

        matches, doc_type = matches_pattern_based_detection(Path("setup.py"))
        assert not matches
        assert doc_type is None


class TestContentBasedDetection:
    """Test content-based keyword detection."""

    def test_features_heading(self):
        """Test detection of Features heading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Introduction\n\n## Features\n\nThis is a list of features.")

            assert check_content_based_detection(doc_file)

    def test_limitations_heading(self):
        """Test detection of Limitations heading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Overview\n\n## Limitations\n\nKnown limitations.")

            assert check_content_based_detection(doc_file)

    def test_implementation_heading(self):
        """Test detection of Implementation heading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Project\n\n## Implementation Details\n\nImplementation info.")

            assert check_content_based_detection(doc_file)

    def test_api_heading(self):
        """Test detection of API heading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Library\n\n## Public API\n\nAPI documentation.")

            assert check_content_based_detection(doc_file)

    def test_usage_heading(self):
        """Test detection of Usage heading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Tool\n\n## Usage\n\nHow to use this tool.")

            assert check_content_based_detection(doc_file)

    def test_quick_start_heading(self):
        """Test detection of Quick Start heading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Product\n\n## Quick Start\n\nGetting started guide.")

            assert check_content_based_detection(doc_file)

    def test_case_insensitive_keywords(self):
        """Test that keyword detection is case-insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Project\n\n## features\n\nLowercase features.")

            assert check_content_based_detection(doc_file)

    def test_no_matching_keywords(self):
        """Test that files without keywords return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Simple Doc\n\nJust some content without special headings.")

            assert not check_content_based_detection(doc_file)

    def test_scan_first_50_lines_only(self):
        """Test that only first 50 lines are scanned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"

            # Create file with keyword at line 60
            lines = ["# Line {}\n".format(i) for i in range(60)]
            lines[55] = "## Features\n"
            doc_file.write_text("".join(lines))

            # Should not detect (keyword is beyond line 50)
            assert not check_content_based_detection(doc_file)

    def test_unreadable_file(self):
        """Test graceful handling of unreadable files."""
        # Non-existent file
        assert not check_content_based_detection(Path("/nonexistent/file.md"))


class TestExtractFrontMatter:
    """Test YAML front matter extraction."""

    def test_extract_simple_front_matter(self):
        """Test extraction of simple YAML front matter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("---\ntitle: My Document\nauthor: John Doe\n---\n\n# Content")

            front_matter = extract_front_matter(doc_file)

            assert front_matter is not None
            assert front_matter["title"] == "My Document"
            assert front_matter["author"] == "John Doe"

    def test_no_front_matter(self):
        """Test that files without front matter return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("# Document\n\nContent without front matter.")

            front_matter = extract_front_matter(doc_file)
            assert front_matter is None

    def test_invalid_front_matter(self):
        """Test handling of invalid front matter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            # Missing closing ---
            doc_file.write_text("---\ntitle: Incomplete\n\n# Content")

            front_matter = extract_front_matter(doc_file)
            assert front_matter is None

    def test_empty_front_matter(self):
        """Test handling of empty front matter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.md"
            doc_file.write_text("---\n---\n\n# Content")

            front_matter = extract_front_matter(doc_file)
            assert front_matter is None


class TestComputeDocRelevanceScore:
    """Test documentation relevance scoring."""

    def test_root_readme_highest_score(self):
        """Test that root README gets highest score (100)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            readme_path = repo_dir / "README.md"
            readme_path.write_text("# Project")

            score = compute_doc_relevance_score(readme_path, repo_dir)
            assert score == 100

    def test_root_level_doc_high_score(self):
        """Test that root-level docs get score 90."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            doc_path = repo_dir / "CONTRIBUTING.md"
            doc_path.write_text("# Contributing")

            score = compute_doc_relevance_score(doc_path, repo_dir)
            assert score == 90

    def test_docs_directory_medium_score(self):
        """Test that docs/ files get score 80."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "docs").mkdir()
            doc_path = repo_dir / "docs" / "intro.md"
            doc_path.write_text("# Introduction")

            score = compute_doc_relevance_score(doc_path, repo_dir)
            assert score == 80

    def test_documentation_directory_medium_score(self):
        """Test that documentation/ files get score 80."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "documentation").mkdir()
            doc_path = repo_dir / "documentation" / "guide.md"
            doc_path.write_text("# Guide")

            score = compute_doc_relevance_score(doc_path, repo_dir)
            assert score == 80

    def test_nested_doc_low_score(self):
        """Test that nested docs get score 50."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "docs" / "api").mkdir(parents=True)
            doc_path = repo_dir / "docs" / "api" / "methods.md"
            doc_path.write_text("# Methods")

            score = compute_doc_relevance_score(doc_path, repo_dir)
            assert score == 50


class TestDiscoverDocumentationFiles:
    """Test documentation file discovery."""

    def test_discover_readme_only(self):
        """Test discovery in repo with only README."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "README.md").write_text("# Project")

            docs = discover_documentation_files(repo_dir)

            assert len(docs) == 1
            assert docs[0]["path"] == "README.md"
            assert docs[0]["doc_type"] == "readme"
            assert docs[0]["evidence_priority"] == "high"
            assert docs[0]["relevance_score"] == 100

    def test_discover_multiple_readmes(self):
        """Test discovery of multiple README files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "README.md").write_text("# Main README")
            (repo_dir / "docs").mkdir()
            (repo_dir / "docs" / "README.md").write_text("# Docs README")

            docs = discover_documentation_files(repo_dir)

            assert len(docs) == 2
            # Root README should be first (higher score)
            assert docs[0]["path"] == "README.md"
            assert docs[0]["relevance_score"] == 100
            assert docs[1]["path"] == "docs/README.md"
            assert docs[1]["relevance_score"] == 80

    def test_discover_pattern_based_files(self):
        """Test discovery of pattern-based documentation files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "ARCHITECTURE.md").write_text("# Architecture")
            (repo_dir / "IMPLEMENTATION_NOTES.md").write_text("# Implementation")

            docs = discover_documentation_files(repo_dir)

            # Find architecture doc
            arch_doc = next(d for d in docs if "ARCHITECTURE" in d["path"])
            assert arch_doc["doc_type"] == "architecture"
            assert arch_doc["evidence_priority"] == "medium"

            # Find implementation notes
            impl_doc = next(d for d in docs if "IMPLEMENTATION" in d["path"])
            assert impl_doc["doc_type"] == "implementation_notes"
            assert impl_doc["evidence_priority"] == "high"

    def test_discover_content_based_files(self):
        """Test discovery of content-based documentation files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # File with content-matching keywords
            doc_file = repo_dir / "guide.md"
            doc_file.write_text("# User Guide\n\n## Features\n\nList of features.")

            docs = discover_documentation_files(repo_dir)

            assert len(docs) == 1
            assert docs[0]["path"] == "guide.md"
            assert docs[0]["evidence_priority"] == "medium"

    def test_discover_docs_directory(self):
        """Test discovery of docs/ directory contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "docs").mkdir()
            (repo_dir / "docs" / "intro.md").write_text("# Introduction")
            (repo_dir / "docs" / "guide.md").write_text("# Guide")

            docs = discover_documentation_files(repo_dir)

            assert len(docs) == 2
            paths = {d["path"] for d in docs}
            assert "docs/intro.md" in paths
            assert "docs/guide.md" in paths

    def test_deterministic_ordering(self):
        """Test that discovery produces deterministic ordering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create files in non-deterministic order
            (repo_dir / "CONTRIBUTING.md").write_text("# Contributing")
            (repo_dir / "README.md").write_text("# README")
            (repo_dir / "CHANGELOG.md").write_text("# Changelog")

            # Run discovery multiple times
            docs1 = discover_documentation_files(repo_dir)
            docs2 = discover_documentation_files(repo_dir)

            # Results should be identical
            assert docs1 == docs2

            # README should be first (highest score)
            assert docs1[0]["path"] == "README.md"

    def test_skip_hidden_directories(self):
        """Test that hidden directories are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / ".git").mkdir()
            (repo_dir / ".git" / "config.md").write_text("# Git config")
            (repo_dir / "README.md").write_text("# Project")

            docs = discover_documentation_files(repo_dir)

            # Should only find README, not .git/config.md
            assert len(docs) == 1
            assert docs[0]["path"] == "README.md"

    def test_skip_non_doc_extensions(self):
        """Test that non-documentation files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "main.py").write_text("# Python file")
            (repo_dir / "README.md").write_text("# README")

            docs = discover_documentation_files(repo_dir)

            # Should only find README.md
            assert len(docs) == 1
            assert docs[0]["path"] == "README.md"

    def test_discover_empty_repo(self):
        """Test discovery in empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            docs = discover_documentation_files(repo_dir)

            assert docs == []


class TestIdentifyDocRoots:
    """Test documentation root directory identification."""

    def test_identify_docs_directory(self):
        """Test identification of docs/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "docs").mkdir()

            doc_roots = identify_doc_roots(repo_dir)

            assert "docs" in doc_roots

    def test_identify_documentation_directory(self):
        """Test identification of documentation/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "documentation").mkdir()

            doc_roots = identify_doc_roots(repo_dir)

            assert "documentation" in doc_roots

    def test_identify_site_directory(self):
        """Test identification of site/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "site").mkdir()

            doc_roots = identify_doc_roots(repo_dir)

            assert "site" in doc_roots

    def test_identify_multiple_doc_roots(self):
        """Test identification of multiple doc root directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "docs").mkdir()
            (repo_dir / "site").mkdir()

            doc_roots = identify_doc_roots(repo_dir)

            assert len(doc_roots) == 2
            assert "docs" in doc_roots
            assert "site" in doc_roots

    def test_no_doc_roots(self):
        """Test when no doc root directories exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            doc_roots = identify_doc_roots(repo_dir)

            assert doc_roots == []

    def test_deterministic_ordering(self):
        """Test that doc roots are returned in deterministic order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "site").mkdir()
            (repo_dir / "docs").mkdir()
            (repo_dir / "documentation").mkdir()

            doc_roots1 = identify_doc_roots(repo_dir)
            doc_roots2 = identify_doc_roots(repo_dir)

            # Should be sorted
            assert doc_roots1 == sorted(doc_roots1)
            # Should be deterministic
            assert doc_roots1 == doc_roots2


class TestArtifactBuilding:
    """Test artifact building and writing."""

    def test_build_discovered_docs_artifact(self):
        """Test building discovered_docs.json artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            doc_roots = ["docs"]
            doc_entrypoint_details = [
                {
                    "path": "README.md",
                    "doc_type": "readme",
                    "evidence_priority": "high",
                    "relevance_score": 100,
                },
                {
                    "path": "ARCHITECTURE.md",
                    "doc_type": "architecture",
                    "evidence_priority": "medium",
                    "relevance_score": 90,
                },
            ]

            artifact = build_discovered_docs_artifact(
                repo_dir, doc_roots, doc_entrypoint_details
            )

            assert artifact["doc_roots"] == ["docs"]
            assert len(artifact["doc_entrypoints"]) == 2
            assert "README.md" in artifact["doc_entrypoints"]
            assert artifact["discovery_summary"]["total_docs_found"] == 2
            assert artifact["discovery_summary"]["readme_count"] == 1
            assert artifact["discovery_summary"]["architecture_count"] == 1

    def test_write_discovered_docs_artifact(self):
        """Test writing discovered_docs.json artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "artifacts").mkdir()

            run_layout = RunLayout(run_dir=run_dir)

            artifact = {
                "doc_roots": ["docs"],
                "doc_entrypoints": ["README.md"],
                "doc_entrypoint_details": [],
                "discovery_summary": {"total_docs_found": 1},
            }

            write_discovered_docs_artifact(run_layout, artifact)

            artifact_path = run_layout.artifacts_dir / "discovered_docs.json"
            assert artifact_path.exists()

            # Verify JSON is valid
            content = json.loads(artifact_path.read_text())
            assert content["doc_roots"] == ["docs"]

    def test_write_artifact_deterministic(self):
        """Test that artifact writing is deterministic."""
        artifact = {
            "doc_roots": ["docs"],
            "doc_entrypoints": ["README.md", "ARCHITECTURE.md"],
            "doc_entrypoint_details": [],
            "discovery_summary": {"total_docs_found": 2},
        }

        outputs = []
        for _ in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                run_dir = Path(tmpdir)
                (run_dir / "artifacts").mkdir()
                run_layout = RunLayout(run_dir=run_dir)

                write_discovered_docs_artifact(run_layout, artifact)

                artifact_path = run_layout.artifacts_dir / "discovered_docs.json"
                outputs.append(artifact_path.read_bytes())

        # All outputs should be byte-identical
        assert outputs[0] == outputs[1] == outputs[2]


class TestRepoInventoryUpdate:
    """Test repo_inventory.json updates."""

    def test_update_repo_inventory_with_docs(self):
        """Test updating repo_inventory.json with doc discovery results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)
            run_layout.artifacts_dir.mkdir(parents=True)

            # Create initial repo_inventory.json
            initial_inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/test/repo.git",
                "repo_sha": "a" * 40,
                "fingerprint": {},
                "repo_profile": {
                    "platform_family": "python",
                    "primary_languages": ["Python"],
                    "build_systems": [],
                    "package_manifests": [],
                    "recommended_test_commands": [],
                    "example_locator": "standard",
                    "doc_locator": "standard",
                },
                "paths": [],
                "doc_entrypoints": [],
                "example_paths": [],
            }

            inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
            inventory_path.write_text(json.dumps(initial_inventory))

            # Update with doc discovery results
            doc_roots = ["docs"]
            doc_entrypoints = ["README.md", "docs/intro.md"]
            doc_entrypoint_details = [
                {"path": "README.md", "doc_type": "readme", "evidence_priority": "high"},
                {"path": "docs/intro.md", "doc_type": "other", "evidence_priority": "low"},
            ]

            update_repo_inventory_with_docs(
                run_layout, doc_roots, doc_entrypoints, doc_entrypoint_details
            )

            # Verify updates
            updated_inventory = json.loads(inventory_path.read_text())
            assert updated_inventory["doc_roots"] == ["docs"]
            assert updated_inventory["doc_entrypoints"] == doc_entrypoints
            assert updated_inventory["doc_entrypoint_details"] == doc_entrypoint_details
            assert updated_inventory["repo_profile"]["doc_locator"] == "pattern_and_content_based"

    def test_update_inventory_no_docs_found(self):
        """Test updating inventory when no docs are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)
            run_layout.artifacts_dir.mkdir(parents=True)

            # Create initial repo_inventory.json
            initial_inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/test/repo.git",
                "repo_sha": "b" * 40,
                "fingerprint": {},
                "repo_profile": {
                    "platform_family": "python",
                    "primary_languages": ["Python"],
                    "build_systems": [],
                    "package_manifests": [],
                    "recommended_test_commands": [],
                    "example_locator": "standard",
                    "doc_locator": "standard",
                },
                "paths": [],
                "doc_entrypoints": [],
                "example_paths": [],
            }

            inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
            inventory_path.write_text(json.dumps(initial_inventory))

            # Update with empty results
            update_repo_inventory_with_docs(run_layout, [], [], [])

            # Verify doc_locator is set to none_found
            updated_inventory = json.loads(inventory_path.read_text())
            assert updated_inventory["repo_profile"]["doc_locator"] == "none_found"


class TestEventEmission:
    """Test event emission."""

    def test_emit_discover_docs_events(self):
        """Test that discover_docs events are emitted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "artifacts").mkdir()
            events_file = run_dir / "events.ndjson"
            events_file.write_text("")

            run_layout = RunLayout(run_dir=run_dir)

            # Write artifacts first
            artifact = {
                "doc_roots": ["docs"],
                "doc_entrypoints": ["README.md"],
                "doc_entrypoint_details": [],
                "discovery_summary": {"total_docs_found": 1},
            }
            write_discovered_docs_artifact(run_layout, artifact)

            # Create repo_inventory.json
            inventory = {
                "schema_version": "1.0",
                "doc_roots": ["docs"],
                "doc_entrypoints": ["README.md"],
            }
            (run_layout.artifacts_dir / "repo_inventory.json").write_text(
                json.dumps(inventory)
            )

            emit_discover_docs_events(
                run_layout=run_layout,
                run_id="test-run-123",
                trace_id="trace-456",
                span_id="span-789",
                docs_found=1,
            )

            # Verify events were written
            events_content = events_file.read_text()
            assert events_content

            # Parse events
            events = [json.loads(line) for line in events_content.strip().split("\n")]

            # Verify event types
            event_types = [e["type"] for e in events]
            assert "WORK_ITEM_STARTED" in event_types
            assert "DOCS_DISCOVERY_COMPLETED" in event_types
            assert "ARTIFACT_WRITTEN" in event_types
            assert "WORK_ITEM_FINISHED" in event_types


class TestIntegration:
    """Integration tests for full discover_docs workflow."""

    def test_discover_docs_integration(self):
        """Test full discover_docs workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Setup: Create repo directory with docs
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "README.md").write_text("# Test Project")
            (repo_dir / "ARCHITECTURE.md").write_text("# Architecture")
            (repo_dir / "docs").mkdir()
            (repo_dir / "docs" / "guide.md").write_text("# User Guide")

            # Setup: Create repo_inventory.json (dependency from TC-402)
            run_layout.artifacts_dir.mkdir(parents=True)
            inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/test/repo.git",
                "repo_sha": "c" * 40,
                "fingerprint": {},
                "repo_profile": {
                    "platform_family": "python",
                    "primary_languages": ["Python"],
                    "build_systems": [],
                    "package_manifests": [],
                    "recommended_test_commands": [],
                    "example_locator": "standard",
                    "doc_locator": "standard",
                },
                "paths": [],
                "doc_entrypoints": [],
                "example_paths": [],
            }
            (run_layout.artifacts_dir / "repo_inventory.json").write_text(
                json.dumps(inventory)
            )

            # Initialize events.ndjson
            (run_dir / "events.ndjson").write_text("")

            # Run discover_docs
            artifact = discover_docs(repo_dir, run_dir)

            # Verify artifact
            assert len(artifact["doc_entrypoints"]) == 3
            assert "README.md" in artifact["doc_entrypoints"]
            assert "ARCHITECTURE.md" in artifact["doc_entrypoints"]
            assert "docs/guide.md" in artifact["doc_entrypoints"]
            assert artifact["doc_roots"] == ["docs"]

            # Verify discovered_docs.json was written
            artifact_path = run_layout.artifacts_dir / "discovered_docs.json"
            assert artifact_path.exists()

            # Verify repo_inventory.json was updated
            inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
            updated_inventory = json.loads(inventory_path.read_text())
            assert updated_inventory["doc_roots"] == ["docs"]
            assert len(updated_inventory["doc_entrypoints"]) == 3

            # Verify events were emitted
            events_file = run_dir / "events.ndjson"
            assert events_file.exists()
            assert events_file.stat().st_size > 0

    def test_discover_docs_missing_dependency(self):
        """Test that discover_docs fails gracefully if TC-402 not run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            repo_dir = Path(tmpdir) / "work" / "repo"
            repo_dir.mkdir(parents=True)

            # No repo_inventory.json created
            (run_dir / "artifacts").mkdir()

            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError) as exc_info:
                discover_docs(repo_dir, run_dir)

            assert "repo_inventory.json" in str(exc_info.value)
            assert "TC-402" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
