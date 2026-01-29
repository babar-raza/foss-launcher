"""Unit tests for TC-404: Example discovery in cloned product repo.

Tests cover:
- Example directory pattern matching
- Example file pattern matching
- Language detection
- Complexity estimation
- Relevance scoring
- Metadata extraction
- Deterministic ordering
- Event emission
- Artifact validation

Spec references:
- specs/02_repo_ingestion.md:143-156 (Example discovery)
- specs/05_example_curation.md:61-97 (Example curation)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/21_worker_contracts.md (W1 binding requirements)

TC-404: W1.4 Discover examples in cloned product repo
"""

import json
import tempfile
from pathlib import Path
import pytest

from launch.workers.w1_repo_scout.discover_examples import (
    is_example_file,
    detect_language_from_extension,
    estimate_complexity,
    compute_example_relevance_score,
    identify_example_roots,
    discover_example_files,
    build_discovered_examples_artifact,
    write_discovered_examples_artifact,
    update_repo_inventory_with_examples,
    emit_discover_examples_events,
    discover_examples,
)
from launch.io.run_layout import RunLayout


class TestIsExampleFile:
    """Test example file pattern matching."""

    def test_example_prefix_underscore(self):
        """Test detection of example_ prefix."""
        assert is_example_file(Path("example_hello.py"))
        assert is_example_file(Path("Example_World.cs"))

    def test_example_prefix_hyphen(self):
        """Test detection of example- prefix."""
        assert is_example_file(Path("example-basic.py"))
        assert is_example_file(Path("Example-Advanced.cs"))

    def test_sample_prefix_underscore(self):
        """Test detection of sample_ prefix."""
        assert is_example_file(Path("sample_test.py"))
        assert is_example_file(Path("Sample_Demo.cs"))

    def test_sample_prefix_hyphen(self):
        """Test detection of sample- prefix."""
        assert is_example_file(Path("sample-app.py"))

    def test_demo_prefix_underscore(self):
        """Test detection of demo_ prefix."""
        assert is_example_file(Path("demo_script.py"))
        assert is_example_file(Path("Demo_Tool.cs"))

    def test_demo_prefix_hyphen(self):
        """Test detection of demo- prefix."""
        assert is_example_file(Path("demo-app.py"))

    def test_example_dot_py(self):
        """Test detection of example.py pattern."""
        assert is_example_file(Path("example.py"))
        assert is_example_file(Path("Example.py"))

    def test_sample_dot_py(self):
        """Test detection of sample.py pattern."""
        assert is_example_file(Path("sample.py"))
        assert is_example_file(Path("Sample.py"))

    def test_demo_dot_cs(self):
        """Test detection of demo.cs pattern."""
        assert is_example_file(Path("demo.cs"))
        assert is_example_file(Path("Demo.cs"))

    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        assert is_example_file(Path("EXAMPLE_TEST.py"))
        assert is_example_file(Path("sAmPlE_dEmO.cs"))

    def test_not_example_file(self):
        """Test that non-example files are not detected."""
        assert not is_example_file(Path("main.py"))
        assert not is_example_file(Path("test_unit.py"))
        assert not is_example_file(Path("README.md"))
        assert not is_example_file(Path("utils.py"))


class TestDetectLanguageFromExtension:
    """Test language detection from file extensions."""

    def test_python_extension(self):
        """Test Python file detection."""
        assert detect_language_from_extension(Path("example.py")) == "python"

    def test_csharp_extension(self):
        """Test C# file detection."""
        assert detect_language_from_extension(Path("Example.cs")) == "csharp"

    def test_java_extension(self):
        """Test Java file detection."""
        assert detect_language_from_extension(Path("Sample.java")) == "java"

    def test_javascript_extension(self):
        """Test JavaScript file detection."""
        assert detect_language_from_extension(Path("demo.js")) == "javascript"

    def test_typescript_extension(self):
        """Test TypeScript file detection."""
        assert detect_language_from_extension(Path("example.ts")) == "typescript"

    def test_go_extension(self):
        """Test Go file detection."""
        assert detect_language_from_extension(Path("main.go")) == "go"

    def test_rust_extension(self):
        """Test Rust file detection."""
        assert detect_language_from_extension(Path("lib.rs")) == "rust"

    def test_cpp_extension(self):
        """Test C++ file detection."""
        assert detect_language_from_extension(Path("example.cpp")) == "cpp"
        assert detect_language_from_extension(Path("header.hpp")) == "cpp"

    def test_c_extension(self):
        """Test C file detection."""
        assert detect_language_from_extension(Path("example.c")) == "c"
        assert detect_language_from_extension(Path("header.h")) == "c"

    def test_unknown_extension(self):
        """Test unknown file detection."""
        assert detect_language_from_extension(Path("README.md")) == "unknown"
        assert detect_language_from_extension(Path("data.json")) == "unknown"

    def test_case_insensitive_extension(self):
        """Test that extension detection is case-insensitive."""
        assert detect_language_from_extension(Path("Example.PY")) == "python"
        assert detect_language_from_extension(Path("Demo.CS")) == "csharp"


class TestEstimateComplexity:
    """Test code complexity estimation."""

    def test_simple_example(self):
        """Test detection of simple example (< 20 lines, <= 1 function)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            example_file = Path(tmpdir) / "simple.py"
            example_file.write_text(
                "import sys\n\n"
                "def hello():\n"
                "    print('Hello World')\n\n"
                "hello()\n"
            )

            assert estimate_complexity(example_file) == "simple"

    def test_medium_example(self):
        """Test detection of medium complexity example."""
        with tempfile.TemporaryDirectory() as tmpdir:
            example_file = Path(tmpdir) / "medium.py"
            lines = [
                "import sys\n",
                "import os\n\n",
                "def func1():\n",
                "    pass\n\n",
                "def func2():\n",
                "    pass\n\n",
                "def func3():\n",
                "    pass\n\n",
            ]
            # Add more lines to reach medium size
            lines.extend(["# comment line\n"] * 30)
            example_file.write_text("".join(lines))

            assert estimate_complexity(example_file) == "medium"

    def test_complex_example(self):
        """Test detection of complex example (> 100 lines or > 5 functions)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            example_file = Path(tmpdir) / "complex.py"
            lines = ["import sys\n\n"]

            # Add many functions
            for i in range(10):
                lines.append(f"def function_{i}():\n")
                lines.append("    pass\n\n")

            # Add many lines
            lines.extend(["# complex code\n"] * 100)
            example_file.write_text("".join(lines))

            assert estimate_complexity(example_file) == "complex"

    def test_class_based_complexity(self):
        """Test complexity detection with classes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            example_file = Path(tmpdir) / "classes.py"
            example_file.write_text(
                "class ClassA:\n"
                "    pass\n\n"
                "class ClassB:\n"
                "    pass\n\n"
                "class ClassC:\n"
                "    pass\n\n"
            )

            # 3 classes should trigger complex
            assert estimate_complexity(example_file) == "complex"

    def test_unreadable_file(self):
        """Test graceful handling of unreadable files."""
        # Non-existent file
        assert estimate_complexity(Path("/nonexistent/file.py")) == "unknown"


class TestComputeExampleRelevanceScore:
    """Test example relevance scoring."""

    def test_example_root_highest_score(self):
        """Test that files in example roots get highest score (100)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()
            example_path = repo_dir / "examples" / "demo.py"
            example_path.write_text("print('hello')")

            score = compute_example_relevance_score(
                example_path, repo_dir, is_in_example_root=True
            )
            assert score == 100

    def test_docs_examples_high_score(self):
        """Test that files in docs/examples get score 80."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "docs" / "examples").mkdir(parents=True)
            example_path = repo_dir / "docs" / "examples" / "demo.py"
            example_path.write_text("print('hello')")

            score = compute_example_relevance_score(
                example_path, repo_dir, is_in_example_root=False
            )
            assert score == 80

    def test_root_example_file_score(self):
        """Test that example files in root get score 70."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            example_path = repo_dir / "example_demo.py"
            example_path.write_text("print('hello')")

            score = compute_example_relevance_score(
                example_path, repo_dir, is_in_example_root=False
            )
            assert score == 70

    def test_test_examples_medium_score(self):
        """Test that test examples get score 50."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "tests").mkdir()
            example_path = repo_dir / "tests" / "example_test.py"
            example_path.write_text("print('hello')")

            score = compute_example_relevance_score(
                example_path, repo_dir, is_in_example_root=False
            )
            assert score == 50

    def test_nested_example_low_score(self):
        """Test that other nested examples get score 30."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "src" / "utils").mkdir(parents=True)
            example_path = repo_dir / "src" / "utils" / "example_helper.py"
            example_path.write_text("print('hello')")

            score = compute_example_relevance_score(
                example_path, repo_dir, is_in_example_root=False
            )
            assert score == 30


class TestIdentifyExampleRoots:
    """Test example root directory identification."""

    def test_identify_examples_directory(self):
        """Test identification of examples/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()

            example_roots = identify_example_roots(repo_dir)

            assert "examples" in example_roots

    def test_identify_samples_directory(self):
        """Test identification of samples/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "samples").mkdir()

            example_roots = identify_example_roots(repo_dir)

            assert "samples" in example_roots

    def test_identify_demo_directory(self):
        """Test identification of demo/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "demo").mkdir()

            example_roots = identify_example_roots(repo_dir)

            assert "demo" in example_roots

    def test_identify_multiple_example_roots(self):
        """Test identification of multiple example root directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()
            (repo_dir / "samples").mkdir()

            example_roots = identify_example_roots(repo_dir)

            assert len(example_roots) == 2
            assert "examples" in example_roots
            assert "samples" in example_roots

    def test_no_example_roots(self):
        """Test when no example root directories exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            example_roots = identify_example_roots(repo_dir)

            assert example_roots == []

    def test_deterministic_ordering(self):
        """Test that example roots are returned in deterministic order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "samples").mkdir()
            (repo_dir / "demo").mkdir()
            (repo_dir / "examples").mkdir()

            example_roots1 = identify_example_roots(repo_dir)
            example_roots2 = identify_example_roots(repo_dir)

            # Should be sorted
            assert example_roots1 == sorted(example_roots1)
            # Should be deterministic
            assert example_roots1 == example_roots2


class TestDiscoverExampleFiles:
    """Test example file discovery."""

    def test_discover_examples_in_examples_dir(self):
        """Test discovery of files in examples/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()
            (repo_dir / "examples" / "demo.py").write_text("print('hello')")

            example_roots = identify_example_roots(repo_dir)
            examples = discover_example_files(repo_dir, example_roots)

            assert len(examples) == 1
            assert examples[0]["path"] == "examples/demo.py"
            assert examples[0]["language"] == "python"
            assert examples[0]["source_type"] == "repo_file"
            assert examples[0]["relevance_score"] == 100

    def test_discover_multiple_languages(self):
        """Test discovery of examples in multiple languages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()
            (repo_dir / "examples" / "demo.py").write_text("print('hello')")
            (repo_dir / "examples" / "demo.cs").write_text("Console.WriteLine();")
            (repo_dir / "examples" / "demo.java").write_text("System.out.println();")

            example_roots = identify_example_roots(repo_dir)
            examples = discover_example_files(repo_dir, example_roots)

            assert len(examples) == 3
            languages = {e["language"] for e in examples}
            assert languages == {"python", "csharp", "java"}

    def test_discover_example_files_outside_roots(self):
        """Test discovery of example files outside example roots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "example_main.py").write_text("print('hello')")
            (repo_dir / "sample_demo.cs").write_text("Console.WriteLine();")

            example_roots = identify_example_roots(repo_dir)
            examples = discover_example_files(repo_dir, example_roots)

            assert len(examples) == 2
            paths = {e["path"] for e in examples}
            assert "example_main.py" in paths
            assert "sample_demo.cs" in paths

    def test_discover_test_examples(self):
        """Test discovery and classification of test examples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "tests").mkdir()
            (repo_dir / "tests" / "example_test.py").write_text("def test(): pass")

            example_roots = identify_example_roots(repo_dir)
            examples = discover_example_files(repo_dir, example_roots)

            assert len(examples) == 1
            assert examples[0]["path"] == "tests/example_test.py"
            assert examples[0]["source_type"] == "test_example"
            assert examples[0]["relevance_score"] == 50

    def test_skip_non_code_files(self):
        """Test that non-code files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()
            (repo_dir / "examples" / "demo.py").write_text("print('hello')")
            (repo_dir / "examples" / "README.md").write_text("# Examples")
            (repo_dir / "examples" / "data.json").write_text("{}")

            example_roots = identify_example_roots(repo_dir)
            examples = discover_example_files(repo_dir, example_roots)

            # Should only find demo.py, not README.md or data.json
            assert len(examples) == 1
            assert examples[0]["path"] == "examples/demo.py"

    def test_skip_hidden_files(self):
        """Test that hidden files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()
            (repo_dir / "examples" / ".hidden.py").write_text("print('hidden')")
            (repo_dir / "examples" / "visible.py").write_text("print('visible')")

            example_roots = identify_example_roots(repo_dir)
            examples = discover_example_files(repo_dir, example_roots)

            # Should only find visible.py
            assert len(examples) == 1
            assert examples[0]["path"] == "examples/visible.py"

    def test_deterministic_ordering(self):
        """Test that discovery produces deterministic ordering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()

            # Create files in non-deterministic order
            (repo_dir / "examples" / "z_demo.py").write_text("print('z')")
            (repo_dir / "examples" / "a_demo.py").write_text("print('a')")
            (repo_dir / "examples" / "m_demo.py").write_text("print('m')")

            example_roots = identify_example_roots(repo_dir)

            # Run discovery multiple times
            examples1 = discover_example_files(repo_dir, example_roots)
            examples2 = discover_example_files(repo_dir, example_roots)

            # Results should be identical
            assert examples1 == examples2

            # Should be sorted by relevance (all 100), then by path (lexicographic)
            paths = [e["path"] for e in examples1]
            assert paths == sorted(paths)

    def test_discover_empty_repo(self):
        """Test discovery in empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            example_roots = identify_example_roots(repo_dir)
            examples = discover_example_files(repo_dir, example_roots)

            assert examples == []

    def test_complexity_metadata_extraction(self):
        """Test that complexity is extracted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            (repo_dir / "examples").mkdir()

            # Simple example
            simple_file = repo_dir / "examples" / "simple.py"
            simple_file.write_text("print('hello')\n")

            example_roots = identify_example_roots(repo_dir)
            examples = discover_example_files(repo_dir, example_roots)

            assert len(examples) == 1
            assert examples[0]["complexity"] == "simple"


class TestArtifactBuilding:
    """Test artifact building and writing."""

    def test_build_discovered_examples_artifact(self):
        """Test building discovered_examples.json artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            example_roots = ["examples"]
            example_file_details = [
                {
                    "path": "examples/demo.py",
                    "language": "python",
                    "complexity": "simple",
                    "relevance_score": 100,
                    "source_type": "repo_file",
                },
                {
                    "path": "examples/advanced.cs",
                    "language": "csharp",
                    "complexity": "complex",
                    "relevance_score": 100,
                    "source_type": "repo_file",
                },
            ]

            artifact = build_discovered_examples_artifact(
                repo_dir, example_roots, example_file_details
            )

            assert artifact["example_roots"] == ["examples"]
            assert len(artifact["example_paths"]) == 2
            assert "examples/demo.py" in artifact["example_paths"]
            assert artifact["discovery_summary"]["total_examples_found"] == 2
            assert artifact["discovery_summary"]["languages"]["python"] == 1
            assert artifact["discovery_summary"]["languages"]["csharp"] == 1
            assert artifact["discovery_summary"]["complexity"]["simple"] == 1
            assert artifact["discovery_summary"]["complexity"]["complex"] == 1

    def test_write_discovered_examples_artifact(self):
        """Test writing discovered_examples.json artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "artifacts").mkdir()

            run_layout = RunLayout(run_dir=run_dir)

            artifact = {
                "example_roots": ["examples"],
                "example_paths": ["examples/demo.py"],
                "example_file_details": [],
                "discovery_summary": {"total_examples_found": 1},
            }

            write_discovered_examples_artifact(run_layout, artifact)

            artifact_path = run_layout.artifacts_dir / "discovered_examples.json"
            assert artifact_path.exists()

            # Verify JSON is valid
            content = json.loads(artifact_path.read_text())
            assert content["example_roots"] == ["examples"]

    def test_write_artifact_deterministic(self):
        """Test that artifact writing is deterministic."""
        artifact = {
            "example_roots": ["examples", "samples"],
            "example_paths": ["examples/demo.py", "samples/test.cs"],
            "example_file_details": [],
            "discovery_summary": {"total_examples_found": 2},
        }

        outputs = []
        for _ in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                run_dir = Path(tmpdir)
                (run_dir / "artifacts").mkdir()
                run_layout = RunLayout(run_dir=run_dir)

                write_discovered_examples_artifact(run_layout, artifact)

                artifact_path = run_layout.artifacts_dir / "discovered_examples.json"
                outputs.append(artifact_path.read_bytes())

        # All outputs should be byte-identical
        assert outputs[0] == outputs[1] == outputs[2]


class TestRepoInventoryUpdate:
    """Test repo_inventory.json updates."""

    def test_update_repo_inventory_with_examples(self):
        """Test updating repo_inventory.json with example discovery results."""
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

            # Update with example discovery results
            example_roots = ["examples"]
            example_paths = ["examples/demo.py", "examples/test.cs"]
            example_file_details = [
                {
                    "path": "examples/demo.py",
                    "language": "python",
                    "complexity": "simple",
                    "relevance_score": 100,
                    "source_type": "repo_file",
                },
                {
                    "path": "examples/test.cs",
                    "language": "csharp",
                    "complexity": "medium",
                    "relevance_score": 100,
                    "source_type": "repo_file",
                },
            ]

            update_repo_inventory_with_examples(
                run_layout, example_roots, example_paths, example_file_details
            )

            # Verify updates
            updated_inventory = json.loads(inventory_path.read_text())
            assert updated_inventory["example_roots"] == ["examples"]
            assert updated_inventory["example_paths"] == example_paths
            assert updated_inventory["repo_profile"]["example_locator"] == "standard_dirs"

    def test_update_inventory_no_examples_found(self):
        """Test updating inventory when no examples are found."""
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
            update_repo_inventory_with_examples(run_layout, [], [], [])

            # Verify example_locator is set to none_found
            updated_inventory = json.loads(inventory_path.read_text())
            assert updated_inventory["repo_profile"]["example_locator"] == "none_found"

    def test_update_inventory_pattern_based(self):
        """Test updating inventory when examples found via pattern only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)
            run_layout.artifacts_dir.mkdir(parents=True)

            # Create initial repo_inventory.json
            initial_inventory = {
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

            inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
            inventory_path.write_text(json.dumps(initial_inventory))

            # Update with pattern-based examples (no example roots)
            example_roots = []
            example_paths = ["example_main.py"]
            example_file_details = [
                {
                    "path": "example_main.py",
                    "language": "python",
                    "complexity": "simple",
                    "relevance_score": 70,
                    "source_type": "repo_file",
                }
            ]

            update_repo_inventory_with_examples(
                run_layout, example_roots, example_paths, example_file_details
            )

            # Verify example_locator is set to pattern_based
            updated_inventory = json.loads(inventory_path.read_text())
            assert updated_inventory["repo_profile"]["example_locator"] == "pattern_based"


class TestEventEmission:
    """Test event emission."""

    def test_emit_discover_examples_events(self):
        """Test that discover_examples events are emitted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "artifacts").mkdir()
            events_file = run_dir / "events.ndjson"
            events_file.write_text("")

            run_layout = RunLayout(run_dir=run_dir)

            # Write artifacts first
            artifact = {
                "example_roots": ["examples"],
                "example_paths": ["examples/demo.py"],
                "example_file_details": [],
                "discovery_summary": {"total_examples_found": 1},
            }
            write_discovered_examples_artifact(run_layout, artifact)

            # Create repo_inventory.json
            inventory = {
                "schema_version": "1.0",
                "example_roots": ["examples"],
                "example_paths": ["examples/demo.py"],
            }
            (run_layout.artifacts_dir / "repo_inventory.json").write_text(
                json.dumps(inventory)
            )

            emit_discover_examples_events(
                run_layout=run_layout,
                run_id="test-run-123",
                trace_id="trace-456",
                span_id="span-789",
                examples_found=1,
                example_roots_count=1,
            )

            # Verify events were written
            events_content = events_file.read_text()
            assert events_content

            # Parse events
            events = [json.loads(line) for line in events_content.strip().split("\n")]

            # Verify event types
            event_types = [e["type"] for e in events]
            assert "WORK_ITEM_STARTED" in event_types
            assert "EXAMPLE_DISCOVERY_COMPLETED" in event_types
            assert "ARTIFACT_WRITTEN" in event_types
            assert "WORK_ITEM_FINISHED" in event_types


class TestIntegration:
    """Integration tests for full discover_examples workflow."""

    def test_discover_examples_integration(self):
        """Test full discover_examples workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Setup: Create repo directory with examples
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "examples").mkdir()
            (repo_dir / "examples" / "demo.py").write_text("print('hello')")
            (repo_dir / "examples" / "advanced.py").write_text("# complex\n" * 60)
            (repo_dir / "sample_main.py").write_text("def main(): pass")

            # Setup: Create repo_inventory.json (dependency from TC-402)
            run_layout.artifacts_dir.mkdir(parents=True)
            inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/test/repo.git",
                "repo_sha": "d" * 40,
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

            # Run discover_examples
            artifact = discover_examples(repo_dir, run_dir)

            # Verify artifact
            assert len(artifact["example_paths"]) == 3
            assert "examples/demo.py" in artifact["example_paths"]
            assert "examples/advanced.py" in artifact["example_paths"]
            assert "sample_main.py" in artifact["example_paths"]
            assert artifact["example_roots"] == ["examples"]

            # Verify discovered_examples.json was written
            artifact_path = run_layout.artifacts_dir / "discovered_examples.json"
            assert artifact_path.exists()

            # Verify repo_inventory.json was updated
            inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
            updated_inventory = json.loads(inventory_path.read_text())
            assert updated_inventory["example_roots"] == ["examples"]
            assert len(updated_inventory["example_paths"]) == 3

            # Verify events were emitted
            events_file = run_dir / "events.ndjson"
            assert events_file.exists()
            assert events_file.stat().st_size > 0

    def test_discover_examples_missing_dependency(self):
        """Test that discover_examples fails gracefully if TC-402 not run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            repo_dir = Path(tmpdir) / "work" / "repo"
            repo_dir.mkdir(parents=True)

            # No repo_inventory.json created
            (run_dir / "artifacts").mkdir()

            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError) as exc_info:
                discover_examples(repo_dir, run_dir)

            assert "repo_inventory.json" in str(exc_info.value)
            assert "TC-402" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
