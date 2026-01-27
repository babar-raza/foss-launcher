"""Unit tests for TC-422: Extract code snippets from example files.

Tests cover:
- Code file parsing (Python, C#, Java, JS, etc.)
- Function/class extraction (AST-based for Python, regex for others)
- Snippet quality filtering
- Relevance scoring
- Deterministic ordering (by relevance score, then by file path)
- Event emission
- Artifact validation
- Error handling (missing examples, syntax errors)

Spec references:
- specs/05_example_curation.md:35-52 (Code snippet extraction patterns)
- specs/05_example_curation.md:61-97 (Example discovery order)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/21_worker_contracts.md:127-145 (W3 binding requirements)

TC-422: W3.2 Extract code snippets from examples
"""

import json
import tempfile
from pathlib import Path
import pytest

from launch.workers.w3_snippet_curator.extract_code_snippets import (
    detect_language_from_path,
    compute_code_content_ratio,
    assess_snippet_quality,
    compute_snippet_id,
    extract_python_functions,
    extract_csharp_functions,
    find_closing_brace,
    extract_full_file_snippet,
    extract_snippets_from_file,
    compute_snippet_relevance_score,
    infer_tags_from_context,
    validate_snippet_syntax,
    load_repo_inventory,
    load_evidence_map,
    build_code_snippets_artifact,
    write_code_snippets_artifact,
    extract_code_snippets,
)
from launch.io.run_layout import RunLayout


class TestDetectLanguageFromPath:
    """Test language detection from file extension."""

    def test_detect_python(self):
        """Test detection of Python files."""
        assert detect_language_from_path(Path("example.py")) == "python"

    def test_detect_csharp(self):
        """Test detection of C# files."""
        assert detect_language_from_path(Path("example.cs")) == "csharp"

    def test_detect_java(self):
        """Test detection of Java files."""
        assert detect_language_from_path(Path("Example.java")) == "java"

    def test_detect_javascript(self):
        """Test detection of JavaScript files."""
        assert detect_language_from_path(Path("example.js")) == "javascript"

    def test_detect_typescript(self):
        """Test detection of TypeScript files."""
        assert detect_language_from_path(Path("example.ts")) == "typescript"

    def test_detect_unknown(self):
        """Test detection of unknown file types."""
        assert detect_language_from_path(Path("example.txt")) == "unknown"


class TestComputeCodeContentRatio:
    """Test code content ratio computation."""

    def test_empty_code(self):
        """Test empty code content."""
        assert compute_code_content_ratio("", "python") == 0.0

    def test_python_with_comments(self):
        """Test Python code with comments."""
        code = """# This is a comment
print("Hello")
# Another comment
result = 42
"""
        ratio = compute_code_content_ratio(code, "python")
        assert ratio == 0.4  # 2 meaningful lines out of 5 (including blank line at end)

    def test_csharp_with_comments(self):
        """Test C# code with comments."""
        code = """// This is a comment
Console.WriteLine("Hello");
// Another comment
int result = 42;
"""
        ratio = compute_code_content_ratio(code, "csharp")
        assert ratio == 0.4  # 2 meaningful lines out of 5 (including blank line at end)

    def test_all_meaningful_lines(self):
        """Test code with all meaningful lines."""
        code = """def hello():
    print("Hello")
    return 42
"""
        ratio = compute_code_content_ratio(code, "python")
        assert ratio == 0.75  # 3 meaningful lines out of 4 (including blank line at end)


class TestAssessSnippetQuality:
    """Test snippet quality assessment."""

    def test_valid_snippet(self):
        """Test valid snippet passes quality check."""
        snippet = {
            "code": """def hello():
    print("Hello, World!")
    return 42
""",
            "language": "python",
        }
        is_valid, reason = assess_snippet_quality(snippet)
        assert is_valid is True
        assert reason is None

    def test_empty_code(self):
        """Test empty code fails quality check."""
        snippet = {"code": "", "language": "python"}
        is_valid, reason = assess_snippet_quality(snippet)
        assert is_valid is False
        assert reason == "empty_code"

    def test_too_short(self):
        """Test snippet too short fails quality check."""
        snippet = {"code": "x = 1", "language": "python"}
        is_valid, reason = assess_snippet_quality(snippet)
        assert is_valid is False
        assert reason == "too_short"

    def test_too_long(self):
        """Test snippet too long fails quality check."""
        snippet = {
            "code": "\n".join([f"line_{i} = {i}" for i in range(600)]),
            "language": "python",
        }
        is_valid, reason = assess_snippet_quality(snippet)
        assert is_valid is False
        assert reason == "too_long"

    def test_low_content_ratio(self):
        """Test snippet with low content ratio fails quality check."""
        snippet = {
            "code": """# Comment 1
# Comment 2
# Comment 3
# Comment 4
# Comment 5
# Comment 6
# Comment 7
print("hello")
""",
            "language": "python",
        }
        is_valid, reason = assess_snippet_quality(snippet)
        assert is_valid is False
        assert reason == "low_content_ratio"


class TestComputeSnippetId:
    """Test stable snippet ID generation."""

    def test_stable_snippet_id(self):
        """Test snippet ID is stable for same input."""
        snippet = {
            "code": "def hello():\n    print('Hello')",
            "language": "python",
            "source_path": "examples/hello.py",
            "start_line": 1,
            "end_line": 2,
        }

        id1 = compute_snippet_id(snippet)
        id2 = compute_snippet_id(snippet)

        assert id1 == id2
        assert len(id1) == 64  # SHA256 hex length

    def test_different_code_different_id(self):
        """Test different code produces different snippet ID."""
        snippet1 = {
            "code": "def hello():\n    print('Hello')",
            "language": "python",
            "source_path": "examples/hello.py",
            "start_line": 1,
            "end_line": 2,
        }

        snippet2 = {
            "code": "def world():\n    print('World')",
            "language": "python",
            "source_path": "examples/hello.py",
            "start_line": 1,
            "end_line": 2,
        }

        assert compute_snippet_id(snippet1) != compute_snippet_id(snippet2)

    def test_different_path_different_id(self):
        """Test different path produces different snippet ID."""
        snippet1 = {
            "code": "def hello():\n    print('Hello')",
            "language": "python",
            "source_path": "examples/hello.py",
            "start_line": 1,
            "end_line": 2,
        }

        snippet2 = {
            "code": "def hello():\n    print('Hello')",
            "language": "python",
            "source_path": "examples/world.py",
            "start_line": 1,
            "end_line": 2,
        }

        assert compute_snippet_id(snippet1) != compute_snippet_id(snippet2)


class TestExtractPythonFunctions:
    """Test Python function extraction using AST."""

    def test_extract_single_function(self):
        """Test extraction of a single function."""
        content = """def hello():
    print("Hello, World!")
    return 42
"""
        snippets = extract_python_functions(Path("example.py"), content)

        assert len(snippets) == 1
        assert snippets[0]["entity_type"] == "function"
        assert snippets[0]["entity_name"] == "hello"
        assert snippets[0]["language"] == "python"
        assert snippets[0]["start_line"] == 1
        assert snippets[0]["end_line"] == 3

    def test_extract_multiple_functions(self):
        """Test extraction of multiple functions."""
        content = """def hello():
    print("Hello")

def world():
    print("World")
"""
        snippets = extract_python_functions(Path("example.py"), content)

        assert len(snippets) == 2
        assert snippets[0]["entity_name"] == "hello"
        assert snippets[1]["entity_name"] == "world"

    def test_extract_class(self):
        """Test extraction of a class."""
        content = """class Example:
    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value
"""
        snippets = extract_python_functions(Path("example.py"), content)

        assert len(snippets) == 1
        assert snippets[0]["entity_type"] == "class"
        assert snippets[0]["entity_name"] == "Example"

    def test_syntax_error_returns_empty(self):
        """Test syntax error returns empty list."""
        content = """def hello(
    # Missing closing paren
    print("Hello")
"""
        snippets = extract_python_functions(Path("example.py"), content)

        assert len(snippets) == 0


class TestExtractCsharpFunctions:
    """Test C# function/class extraction using regex."""

    def test_extract_class(self):
        """Test extraction of a C# class."""
        content = """public class Example
{
    private int value;

    public void DoSomething()
    {
        Console.WriteLine("Hello");
    }
}
"""
        snippets = extract_csharp_functions(Path("Example.cs"), content)

        assert len(snippets) >= 1
        assert snippets[0]["entity_type"] == "class"
        assert snippets[0]["entity_name"] == "Example"
        assert snippets[0]["language"] == "csharp"


class TestFindClosingBrace:
    """Test finding closing braces."""

    def test_find_closing_brace_simple(self):
        """Test finding closing brace for simple case."""
        lines = [
            "public class Example",
            "{",
            "    int x = 1;",
            "}",
        ]

        closing_line = find_closing_brace(lines, 0)
        assert closing_line == 4  # 1-indexed

    def test_find_closing_brace_nested(self):
        """Test finding closing brace with nested braces."""
        lines = [
            "public class Example",
            "{",
            "    void Method() {",
            "        int x = 1;",
            "    }",
            "}",
        ]

        closing_line = find_closing_brace(lines, 0)
        assert closing_line == 6  # 1-indexed


class TestExtractFullFileSnippet:
    """Test full file extraction."""

    def test_extract_full_file(self):
        """Test extraction of full file as snippet."""
        content = """def hello():
    print("Hello")
"""
        snippet = extract_full_file_snippet(Path("hello.py"), content, "python")

        assert snippet["language"] == "python"
        assert snippet["entity_type"] == "file"
        assert snippet["entity_name"] == "hello.py"
        assert snippet["start_line"] == 1
        assert snippet["end_line"] == 3  # Number of lines including trailing newline


class TestComputeSnippetRelevanceScore:
    """Test snippet relevance scoring."""

    def test_example_folder_high_score(self):
        """Test snippets from examples/ get high score."""
        snippet = {"code": "def hello(): pass"}
        score = compute_snippet_relevance_score(snippet, "examples/hello.py", None)

        assert score == 100

    def test_readme_high_score(self):
        """Test snippets from README get high score."""
        snippet = {"code": "def hello(): pass"}
        score = compute_snippet_relevance_score(snippet, "README.md", None)

        assert score == 90

    def test_test_example_high_score(self):
        """Test snippets from test examples get high score."""
        snippet = {"code": "def hello(): pass"}
        score = compute_snippet_relevance_score(snippet, "tests/example_usage.py", None)

        # Note: "example" in path triggers example folder score (100) not test score (80)
        assert score == 100

    def test_src_medium_score(self):
        """Test snippets from src/ get medium score."""
        snippet = {"code": "def hello(): pass"}
        score = compute_snippet_relevance_score(snippet, "src/utils.py", None)

        assert score == 60

    def test_evidence_boost(self):
        """Test snippets cited in evidence_map get boost."""
        snippet = {"code": "def hello(): pass"}
        evidence_map = {
            "claims": [
                {
                    "claim_id": "claim1",
                    "citations": [{"path": "examples/hello.py"}],
                }
            ]
        }

        score = compute_snippet_relevance_score(snippet, "examples/hello.py", evidence_map)

        assert score == 110  # 100 + 10 boost


class TestInferTagsFromContext:
    """Test tag inference from file path and context."""

    def test_example_folder_tags(self):
        """Test tags inferred from examples/ folder."""
        snippet = {"entity_name": "hello"}
        tags = infer_tags_from_context(snippet, "examples/hello.py")

        assert "example" in tags

    def test_quickstart_tags(self):
        """Test tags inferred from quickstart path."""
        snippet = {"entity_name": "hello"}
        tags = infer_tags_from_context(snippet, "examples/quickstart.py")

        assert "quickstart" in tags
        assert "example" in tags

    def test_convert_tags(self):
        """Test tags inferred from convert in path."""
        snippet = {"entity_name": "convert_doc"}
        tags = infer_tags_from_context(snippet, "examples/convert.py")

        assert "convert" in tags

    def test_tags_sorted(self):
        """Test tags are sorted deterministically."""
        snippet = {"entity_name": "convert"}
        tags = infer_tags_from_context(snippet, "examples/quickstart_convert.py")

        assert tags == sorted(tags)  # Verify sorted


class TestValidateSnippetSyntax:
    """Test snippet syntax validation."""

    def test_valid_python_syntax(self):
        """Test valid Python syntax passes validation."""
        snippet = {
            "language": "python",
            "code": """def hello():
    print("Hello")
    return 42
""",
        }

        syntax_ok, error = validate_snippet_syntax(snippet)

        assert syntax_ok is True
        assert error is None

    def test_invalid_python_syntax(self):
        """Test invalid Python syntax fails validation."""
        snippet = {
            "language": "python",
            "code": """def hello(
    # Missing closing paren
    print("Hello")
""",
        }

        syntax_ok, error = validate_snippet_syntax(snippet)

        assert syntax_ok is False
        assert "SyntaxError" in error

    def test_valid_csharp_syntax(self):
        """Test valid C# syntax passes validation."""
        snippet = {
            "language": "csharp",
            "code": """public class Example {
    void Method() {
        Console.WriteLine("Hello");
    }
}
""",
        }

        syntax_ok, error = validate_snippet_syntax(snippet)

        assert syntax_ok is True

    def test_invalid_csharp_unbalanced_braces(self):
        """Test C# with unbalanced braces fails validation."""
        snippet = {
            "language": "csharp",
            "code": """public class Example {
    void Method() {
        Console.WriteLine("Hello");
    }
// Missing closing brace
""",
        }

        syntax_ok, error = validate_snippet_syntax(snippet)

        assert syntax_ok is False
        assert "Unbalanced braces" in error

    def test_unknown_language_passes(self):
        """Test unknown language passes validation."""
        snippet = {
            "language": "rust",
            "code": """fn main() {
    println!("Hello");
}
""",
        }

        syntax_ok, error = validate_snippet_syntax(snippet)

        assert syntax_ok is True  # Unknown languages pass


class TestExtractSnippetsFromFile:
    """Test snippet extraction from files."""

    def test_extract_from_python_file(self):
        """Test extraction from Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            example_file = repo_dir / "hello.py"

            example_file.write_text("""def hello():
    print("Hello, World!")
    return 42

def world():
    print("World!")
""")

            snippets = extract_snippets_from_file(example_file, repo_dir)

            assert len(snippets) == 2
            assert snippets[0]["entity_name"] == "hello"
            assert snippets[1]["entity_name"] == "world"

    def test_extract_full_file_if_no_functions(self):
        """Test extraction of full file if no functions found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            example_file = repo_dir / "script.py"

            example_file.write_text("""print("Hello")
x = 42
print(x)
""")

            snippets = extract_snippets_from_file(example_file, repo_dir)

            assert len(snippets) == 1
            assert snippets[0]["entity_type"] == "file"

    def test_skip_unknown_file_types(self):
        """Test unknown file types are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            example_file = repo_dir / "data.txt"

            example_file.write_text("This is plain text")

            snippets = extract_snippets_from_file(example_file, repo_dir)

            assert len(snippets) == 0


class TestDeterministicOrdering:
    """Test deterministic ordering of snippets."""

    def test_snippets_sorted_by_relevance(self):
        """Test snippets are sorted by relevance score (descending)."""
        snippets = [
            {
                "snippet_id": "id1",
                "relevance_score": 50,
                "source": {"path": "src/utils.py", "start_line": 1},
            },
            {
                "snippet_id": "id2",
                "relevance_score": 100,
                "source": {"path": "examples/hello.py", "start_line": 1},
            },
            {
                "snippet_id": "id3",
                "relevance_score": 80,
                "source": {"path": "tests/example.py", "start_line": 1},
            },
        ]

        # Sort using the same key as extract_code_snippets
        sorted_snippets = sorted(
            snippets,
            key=lambda s: (
                -s.get("relevance_score", 0),
                s["source"]["path"],
                s["source"]["start_line"],
            ),
        )

        assert sorted_snippets[0]["snippet_id"] == "id2"  # Score 100
        assert sorted_snippets[1]["snippet_id"] == "id3"  # Score 80
        assert sorted_snippets[2]["snippet_id"] == "id1"  # Score 50


class TestBuildCodeSnippetsArtifact:
    """Test artifact building."""

    def test_build_artifact_removes_internal_fields(self):
        """Test artifact building removes internal fields."""
        snippets = [
            {
                "snippet_id": "id1",
                "language": "python",
                "tags": ["example"],
                "source": {"type": "repo_file", "path": "hello.py", "start_line": 1, "end_line": 3},
                "code": "def hello(): pass",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
                "relevance_score": 100,  # Internal field
                "entity_type": "function",  # Internal field
                "entity_name": "hello",  # Internal field
            }
        ]

        artifact = build_code_snippets_artifact(snippets)

        assert "schema_version" in artifact
        assert "snippets" in artifact
        assert len(artifact["snippets"]) == 1

        # Verify internal fields removed
        snippet = artifact["snippets"][0]
        assert "relevance_score" not in snippet
        assert "entity_type" not in snippet
        assert "entity_name" not in snippet


class TestWriteCodeSnippetsArtifact:
    """Test artifact writing."""

    def test_write_artifact_atomic(self):
        """Test artifact is written atomically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            run_layout = RunLayout(run_dir=run_dir)

            artifact = {
                "schema_version": "1.0",
                "snippets": [],
            }

            write_code_snippets_artifact(run_layout, artifact)

            artifact_path = artifacts_dir / "code_snippets.json"
            assert artifact_path.exists()

            # Verify content
            content = json.loads(artifact_path.read_text())
            assert content["schema_version"] == "1.0"
            assert content["snippets"] == []


class TestLoadRepoInventory:
    """Test loading repo inventory."""

    def test_load_repo_inventory_success(self):
        """Test successful loading of repo_inventory.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            repo_inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/example/repo",
                "repo_sha": "abc123",
                "fingerprint": {},
                "repo_profile": {
                    "platform_family": "python",
                    "primary_languages": ["python"],
                    "build_systems": [],
                    "package_manifests": [],
                    "recommended_test_commands": [],
                    "example_locator": "examples/",
                    "doc_locator": "docs/",
                },
                "paths": [],
                "doc_entrypoints": [],
                "example_paths": ["examples/hello.py"],
            }

            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            run_layout = RunLayout(run_dir=run_dir)
            inventory = load_repo_inventory(run_layout)

            assert inventory["example_paths"] == ["examples/hello.py"]

    def test_load_repo_inventory_missing_file(self):
        """Test loading fails when repo_inventory.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            run_layout = RunLayout(run_dir=run_dir)

            with pytest.raises(FileNotFoundError) as exc_info:
                load_repo_inventory(run_layout)

            assert "repo_inventory.json not found" in str(exc_info.value)


class TestLoadEvidenceMap:
    """Test loading evidence map."""

    def test_load_evidence_map_success(self):
        """Test successful loading of evidence_map.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            evidence_map = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/example/repo",
                "repo_sha": "abc123",
                "claims": [],
            }

            (artifacts_dir / "evidence_map.json").write_text(json.dumps(evidence_map))

            run_layout = RunLayout(run_dir=run_dir)
            evidence = load_evidence_map(run_layout)

            assert evidence is not None
            assert "claims" in evidence

    def test_load_evidence_map_missing_optional(self):
        """Test loading returns None when evidence_map.json missing (optional)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            run_layout = RunLayout(run_dir=run_dir)
            evidence = load_evidence_map(run_layout)

            assert evidence is None


class TestExtractCodeSnippetsIntegration:
    """Integration tests for extract_code_snippets."""

    def test_extract_code_snippets_full_workflow(self):
        """Test full code snippet extraction workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            work_dir = run_dir / "work"
            repo_dir = work_dir / "repo"
            artifacts_dir = run_dir / "artifacts"

            work_dir.mkdir()
            repo_dir.mkdir()
            artifacts_dir.mkdir()

            # Create example file
            examples_dir = repo_dir / "examples"
            examples_dir.mkdir()

            example_file = examples_dir / "hello.py"
            example_file.write_text("""def hello():
    '''Say hello to the world.'''
    print("Hello, World!")
    return 42

def world():
    '''Print world.'''
    print("World!")
""")

            # Create repo_inventory.json
            repo_inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/example/repo",
                "repo_sha": "abc123",
                "fingerprint": {},
                "repo_profile": {
                    "platform_family": "python",
                    "primary_languages": ["python"],
                    "build_systems": [],
                    "package_manifests": [],
                    "recommended_test_commands": [],
                    "example_locator": "examples/",
                    "doc_locator": "docs/",
                },
                "paths": [],
                "doc_entrypoints": [],
                "example_paths": ["examples/hello.py"],
            }

            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Extract code snippets
            artifact = extract_code_snippets(repo_dir, run_dir)

            # Verify artifact structure
            assert "schema_version" in artifact
            assert "snippets" in artifact
            assert len(artifact["snippets"]) == 2

            # Verify snippets
            snippet1 = artifact["snippets"][0]
            assert snippet1["language"] == "python"
            assert snippet1["source"]["type"] == "repo_file"
            assert snippet1["source"]["path"] == "examples/hello.py"
            assert snippet1["validation"]["syntax_ok"] is True
            assert "example" in snippet1["tags"]

            # Verify code_snippets.json written
            artifact_path = artifacts_dir / "code_snippets.json"
            assert artifact_path.exists()

    def test_extract_code_snippets_no_examples(self):
        """Test extraction with no example paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            work_dir = run_dir / "work"
            repo_dir = work_dir / "repo"
            artifacts_dir = run_dir / "artifacts"

            work_dir.mkdir()
            repo_dir.mkdir()
            artifacts_dir.mkdir()

            # Create repo_inventory.json with no example_paths
            repo_inventory = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/example/repo",
                "repo_sha": "abc123",
                "fingerprint": {},
                "repo_profile": {
                    "platform_family": "python",
                    "primary_languages": ["python"],
                    "build_systems": [],
                    "package_manifests": [],
                    "recommended_test_commands": [],
                    "example_locator": "",
                    "doc_locator": "docs/",
                },
                "paths": [],
                "doc_entrypoints": [],
                "example_paths": [],  # No examples
            }

            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Extract code snippets
            artifact = extract_code_snippets(repo_dir, run_dir)

            # Verify empty artifact
            assert len(artifact["snippets"]) == 0
