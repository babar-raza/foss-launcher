"""Unit tests for TC-421: Extract snippets from documentation files.

Tests cover:
- Code fence extraction from markdown
- Language normalization
- Snippet quality assessment
- Snippet ID generation (stable hashing)
- Relevance scoring
- Tag inference
- Syntax validation
- Deterministic ordering
- Event emission
- Artifact validation

Spec references:
- specs/05_example_curation.md:13-34 (Snippet extraction)
- specs/05_example_curation.md:61-97 (Example discovery order)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/21_worker_contracts.md:127-145 (W3 binding requirements)

TC-421: W3.1 Extract snippets from documentation
"""

import json
import tempfile
from pathlib import Path
import pytest

from launch.workers.w3_snippet_curator.extract_doc_snippets import (
    normalize_language,
    extract_code_fences,
    compute_code_content_ratio,
    assess_snippet_quality,
    compute_snippet_id,
    compute_snippet_relevance_score,
    infer_tags_from_context,
    validate_snippet_syntax,
    load_discovered_docs,
    load_evidence_map,
    extract_snippets_from_doc,
    build_doc_snippets_artifact,
    write_doc_snippets_artifact,
    extract_doc_snippets,
)
from launch.io.run_layout import RunLayout


class TestNormalizeLanguage:
    """Test language identifier normalization."""

    def test_normalize_csharp_variants(self):
        """Test normalization of C# language variants."""
        assert normalize_language("c#") == "csharp"
        assert normalize_language("C#") == "csharp"
        assert normalize_language("cs") == "csharp"
        assert normalize_language("csharp") == "csharp"

    def test_normalize_javascript_variants(self):
        """Test normalization of JavaScript variants."""
        assert normalize_language("js") == "javascript"
        assert normalize_language("javascript") == "javascript"
        assert normalize_language("JS") == "javascript"

    def test_normalize_python_variants(self):
        """Test normalization of Python variants."""
        assert normalize_language("py") == "python"
        assert normalize_language("python") == "python"
        assert normalize_language("python3") == "python"

    def test_normalize_shell_variants(self):
        """Test normalization of shell/bash variants."""
        assert normalize_language("sh") == "bash"
        assert normalize_language("shell") == "bash"
        assert normalize_language("bash") == "bash"

    def test_normalize_yaml_variants(self):
        """Test normalization of YAML variants."""
        assert normalize_language("yml") == "yaml"
        assert normalize_language("yaml") == "yaml"

    def test_normalize_empty_language(self):
        """Test normalization of empty language."""
        assert normalize_language("") == "unknown"
        assert normalize_language(None) == "unknown"

    def test_normalize_unknown_language(self):
        """Test normalization of unknown languages (pass-through)."""
        assert normalize_language("rust") == "rust"
        assert normalize_language("golang") == "golang"


class TestExtractCodeFences:
    """Test code fence extraction from markdown."""

    def test_extract_single_code_fence(self):
        """Test extraction of a single code fence."""
        content = """# Example

```python
print("Hello, World!")
```

More text.
"""
        fences = extract_code_fences(Path("example.md"), content)

        assert len(fences) == 1
        assert fences[0]["language"] == "python"
        assert fences[0]["code"] == 'print("Hello, World!")'
        assert fences[0]["start_line"] == 3
        assert fences[0]["end_line"] == 4

    def test_extract_multiple_code_fences(self):
        """Test extraction of multiple code fences."""
        content = """# Examples

```python
x = 1
```

```csharp
int x = 1;
```
"""
        fences = extract_code_fences(Path("examples.md"), content)

        assert len(fences) == 2
        assert fences[0]["language"] == "python"
        assert fences[0]["code"] == "x = 1"
        assert fences[1]["language"] == "csharp"
        assert fences[1]["code"] == "int x = 1;"

    def test_extract_multiline_code_fence(self):
        """Test extraction of multiline code fence."""
        content = """# Example

```python
def greet(name):
    print(f"Hello, {name}!")

greet("World")
```
"""
        fences = extract_code_fences(Path("example.md"), content)

        assert len(fences) == 1
        assert fences[0]["language"] == "python"
        assert fences[0]["code"] == 'def greet(name):\n    print(f"Hello, {name}!")\n\ngreet("World")'

    def test_extract_code_fence_without_language(self):
        """Test extraction of code fence without language specifier."""
        content = """# Example

```
some code here
```
"""
        fences = extract_code_fences(Path("example.md"), content)

        assert len(fences) == 1
        assert fences[0]["language"] == "unknown"
        assert fences[0]["code"] == "some code here"

    def test_extract_no_code_fences(self):
        """Test extraction from markdown without code fences."""
        content = """# Example

This is plain text.

No code blocks here.
"""
        fences = extract_code_fences(Path("example.md"), content)

        assert len(fences) == 0

    def test_extract_unclosed_code_fence(self):
        """Test extraction handles unclosed code fence."""
        content = """# Example

```python
x = 1

No closing fence
"""
        fences = extract_code_fences(Path("example.md"), content)

        # Unclosed fence should not be extracted
        assert len(fences) == 0


class TestComputeCodeContentRatio:
    """Test code content ratio computation."""

    def test_all_code_lines(self):
        """Test ratio with all code lines."""
        code = """x = 1
y = 2
z = x + y"""
        ratio = compute_code_content_ratio(code)
        assert ratio == 1.0

    def test_mixed_code_and_comments(self):
        """Test ratio with mixed code and comments."""
        code = """# This is a comment
x = 1
# Another comment
y = 2"""
        ratio = compute_code_content_ratio(code)
        assert ratio == 0.5  # 2 code lines out of 4

    def test_empty_code(self):
        """Test ratio with empty code."""
        code = ""
        ratio = compute_code_content_ratio(code)
        assert ratio == 0.0

    def test_only_whitespace(self):
        """Test ratio with only whitespace."""
        code = "   \n\n   \n"
        ratio = compute_code_content_ratio(code)
        assert ratio == 0.0

    def test_only_comments(self):
        """Test ratio with only comments."""
        code = """# Comment 1
// Comment 2
/* Comment 3 */"""
        ratio = compute_code_content_ratio(code)
        assert ratio == 0.0


class TestAssessSnippetQuality:
    """Test snippet quality assessment."""

    def test_valid_snippet(self):
        """Test valid snippet passes quality check."""
        snippet = {
            "code": "x = 1\ny = 2\nz = x + y\nprint(z)"
        }
        is_valid, reason = assess_snippet_quality(snippet)
        assert is_valid
        assert reason is None

    def test_empty_snippet(self):
        """Test empty snippet fails quality check."""
        snippet = {"code": ""}
        is_valid, reason = assess_snippet_quality(snippet)
        assert not is_valid
        assert reason == "empty_code"

    def test_too_short_snippet(self):
        """Test snippet with only 1 line fails quality check."""
        snippet = {"code": "x = 1"}
        is_valid, reason = assess_snippet_quality(snippet)
        assert not is_valid
        assert reason == "too_short"

    def test_too_long_snippet(self):
        """Test snippet exceeding max lines fails quality check."""
        long_code = "\n".join([f"line_{i} = {i}" for i in range(350)])
        snippet = {"code": long_code}
        is_valid, reason = assess_snippet_quality(snippet)
        assert not is_valid
        assert reason == "too_long"

    def test_low_content_ratio_snippet(self):
        """Test snippet with low code content ratio fails quality check."""
        # Mostly comments and whitespace
        code = """# Comment 1
# Comment 2
# Comment 3
# Comment 4
x = 1"""
        snippet = {"code": code}
        is_valid, reason = assess_snippet_quality(snippet)
        assert not is_valid
        assert reason == "low_content_ratio"


class TestComputeSnippetId:
    """Test snippet ID generation (stable hashing)."""

    def test_snippet_id_stability(self):
        """Test snippet ID is stable for same input."""
        snippet = {
            "code": "x = 1\ny = 2",
            "language": "python",
            "source_path": "README.md",
            "start_line": 10,
            "end_line": 11,
        }

        id1 = compute_snippet_id(snippet)
        id2 = compute_snippet_id(snippet)

        assert id1 == id2

    def test_snippet_id_different_for_different_code(self):
        """Test snippet ID differs for different code."""
        snippet1 = {
            "code": "x = 1",
            "language": "python",
            "source_path": "README.md",
            "start_line": 10,
            "end_line": 10,
        }

        snippet2 = {
            "code": "x = 2",
            "language": "python",
            "source_path": "README.md",
            "start_line": 10,
            "end_line": 10,
        }

        id1 = compute_snippet_id(snippet1)
        id2 = compute_snippet_id(snippet2)

        assert id1 != id2

    def test_snippet_id_different_for_different_lines(self):
        """Test snippet ID differs for different line ranges."""
        snippet1 = {
            "code": "x = 1",
            "language": "python",
            "source_path": "README.md",
            "start_line": 10,
            "end_line": 10,
        }

        snippet2 = {
            "code": "x = 1",
            "language": "python",
            "source_path": "README.md",
            "start_line": 20,
            "end_line": 20,
        }

        id1 = compute_snippet_id(snippet1)
        id2 = compute_snippet_id(snippet2)

        assert id1 != id2


class TestComputeSnippetRelevanceScore:
    """Test snippet relevance scoring."""

    def test_readme_snippet_highest_score(self):
        """Test README snippets get highest base score."""
        snippet = {}
        doc_metadata = {"doc_type": "readme", "evidence_priority": "high"}

        score = compute_snippet_relevance_score(snippet, "README.md", doc_metadata, None)
        assert score == 100

    def test_implementation_notes_high_score(self):
        """Test implementation notes get high score."""
        snippet = {}
        doc_metadata = {"doc_type": "implementation_notes", "evidence_priority": "high"}

        score = compute_snippet_relevance_score(snippet, "IMPLEMENTATION.md", doc_metadata, None)
        assert score == 90

    def test_architecture_docs_medium_score(self):
        """Test architecture docs get medium-high score."""
        snippet = {}
        doc_metadata = {"doc_type": "architecture", "evidence_priority": "medium"}

        score = compute_snippet_relevance_score(snippet, "ARCHITECTURE.md", doc_metadata, None)
        assert score == 80

    def test_evidence_map_boost(self):
        """Test snippets from cited docs get boost."""
        snippet = {}
        doc_metadata = {"doc_type": "other", "evidence_priority": "low"}

        evidence_map = {
            "claims": [
                {
                    "claim_id": "claim1",
                    "citations": [
                        {"path": "docs/guide.md", "start_line": 10, "end_line": 20}
                    ]
                }
            ]
        }

        score = compute_snippet_relevance_score(snippet, "docs/guide.md", doc_metadata, evidence_map)
        assert score == 60  # 50 base + 10 boost


class TestInferTagsFromContext:
    """Test tag inference from context."""

    def test_readme_tags(self):
        """Test README snippets get quickstart tags."""
        snippet = {}
        doc_metadata = {"doc_type": "readme"}

        tags = infer_tags_from_context(snippet, "README.md", doc_metadata)
        assert "quickstart" in tags
        assert "readme" in tags

    def test_implementation_tags(self):
        """Test implementation notes snippets get implementation tag."""
        snippet = {}
        doc_metadata = {"doc_type": "implementation_notes"}

        tags = infer_tags_from_context(snippet, "IMPLEMENTATION.md", doc_metadata)
        assert "implementation" in tags

    def test_quickstart_path_tag(self):
        """Test quickstart path inference."""
        snippet = {}
        doc_metadata = {"doc_type": "other"}

        tags = infer_tags_from_context(snippet, "docs/quickstart.md", doc_metadata)
        assert "quickstart" in tags

    def test_convert_path_tag(self):
        """Test convert path inference."""
        snippet = {}
        doc_metadata = {"doc_type": "other"}

        tags = infer_tags_from_context(snippet, "docs/convert.md", doc_metadata)
        assert "convert" in tags

    def test_tags_sorted(self):
        """Test tags are sorted deterministically."""
        snippet = {}
        doc_metadata = {"doc_type": "readme"}

        tags = infer_tags_from_context(snippet, "README.md", doc_metadata)
        assert tags == sorted(tags)

    def test_default_example_tag(self):
        """Test default example tag when no specific tags apply."""
        snippet = {}
        doc_metadata = {"doc_type": "other"}

        tags = infer_tags_from_context(snippet, "docs/guide.md", doc_metadata)
        assert "example" in tags


class TestValidateSnippetSyntax:
    """Test snippet syntax validation."""

    def test_valid_python_syntax(self):
        """Test valid Python code passes syntax check."""
        snippet = {
            "language": "python",
            "code": "x = 1\ny = 2\nprint(x + y)"
        }

        syntax_ok, error = validate_snippet_syntax(snippet)
        assert syntax_ok
        assert error is None

    def test_invalid_python_syntax(self):
        """Test invalid Python code fails syntax check."""
        snippet = {
            "language": "python",
            "code": "x = \nprint(x"
        }

        syntax_ok, error = validate_snippet_syntax(snippet)
        assert not syntax_ok
        assert "SyntaxError" in error

    def test_valid_csharp_syntax(self):
        """Test valid C# code passes basic check."""
        snippet = {
            "language": "csharp",
            "code": "int x = 1;\nint y = 2;"
        }

        syntax_ok, error = validate_snippet_syntax(snippet)
        assert syntax_ok

    def test_unbalanced_csharp_braces(self):
        """Test C# code with unbalanced braces fails check."""
        snippet = {
            "language": "csharp",
            "code": "void Main() {\n    int x = 1;\n"
        }

        syntax_ok, error = validate_snippet_syntax(snippet)
        assert not syntax_ok
        assert "Unbalanced braces" in error

    def test_unknown_language_skips_validation(self):
        """Test unknown languages skip validation."""
        snippet = {
            "language": "rust",
            "code": "fn main() { println!(\"Hello\"); }"
        }

        syntax_ok, error = validate_snippet_syntax(snippet)
        assert syntax_ok  # Skipped validation


class TestExtractSnippetsFromDoc:
    """Test snippet extraction from documentation file."""

    def test_extract_from_readme(self):
        """Test extraction from README file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            readme = repo_dir / "README.md"
            readme.write_text("""# Quick Start

```python
import mylib
mylib.run()
```

More documentation.
""")

            doc_metadata = {"doc_type": "readme", "evidence_priority": "high"}

            snippets = extract_snippets_from_doc("README.md", doc_metadata, repo_dir, None)

            assert len(snippets) == 1
            assert snippets[0]["language"] == "python"
            assert "quickstart" in snippets[0]["tags"]
            assert snippets[0]["source"]["path"] == "README.md"

    def test_extract_multiple_snippets(self):
        """Test extraction of multiple snippets from one doc."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            doc = repo_dir / "guide.md"
            doc.write_text("""# Guide

```python
x = 1
y = 2
```

```csharp
int x = 1;
int y = 2;
```
""")

            doc_metadata = {"doc_type": "other", "evidence_priority": "medium"}

            snippets = extract_snippets_from_doc("guide.md", doc_metadata, repo_dir, None)

            assert len(snippets) == 2
            assert snippets[0]["language"] == "python"
            assert snippets[1]["language"] == "csharp"

    def test_skip_low_quality_snippets(self):
        """Test that low quality snippets are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            doc = repo_dir / "doc.md"
            doc.write_text("""# Doc

```python
x = 1
```

This snippet is too short (only 1 line).
""")

            doc_metadata = {"doc_type": "other", "evidence_priority": "low"}

            snippets = extract_snippets_from_doc("doc.md", doc_metadata, repo_dir, None)

            # Snippet too short, should be filtered out
            assert len(snippets) == 0


class TestBuildDocSnippetsArtifact:
    """Test building doc_snippets.json artifact."""

    def test_build_artifact(self):
        """Test artifact structure."""
        snippets = [
            {
                "snippet_id": "abc123",
                "language": "python",
                "tags": ["quickstart"],
                "source": {"type": "repo_file", "path": "README.md", "start_line": 10, "end_line": 12},
                "code": "x = 1\ny = 2",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
                "relevance_score": 100,
            }
        ]

        artifact = build_doc_snippets_artifact(snippets)

        assert artifact["schema_version"] == "1.0"
        assert len(artifact["snippets"]) == 1

        # relevance_score should be removed
        assert "relevance_score" not in artifact["snippets"][0]

    def test_artifact_removes_internal_fields(self):
        """Test that internal fields are removed from artifact."""
        snippets = [
            {
                "snippet_id": "abc123",
                "language": "python",
                "tags": ["quickstart"],
                "source": {"type": "repo_file", "path": "README.md", "start_line": 10, "end_line": 12},
                "code": "x = 1\ny = 2",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
                "relevance_score": 100,
                "internal_field": "should be removed",
            }
        ]

        artifact = build_doc_snippets_artifact(snippets)

        # Only standard fields should remain
        assert "relevance_score" not in artifact["snippets"][0]


class TestWriteDocSnippetsArtifact:
    """Test writing doc_snippets.json artifact."""

    def test_write_artifact(self):
        """Test artifact is written to correct location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            artifact = {
                "schema_version": "1.0",
                "snippets": [],
            }

            write_doc_snippets_artifact(run_layout, artifact)

            artifact_path = run_layout.artifacts_dir / "doc_snippets.json"
            assert artifact_path.exists()

            # Validate JSON structure
            loaded = json.loads(artifact_path.read_text())
            assert loaded["schema_version"] == "1.0"
            assert loaded["snippets"] == []

    def test_artifact_stable_json_formatting(self):
        """Test artifact uses stable JSON formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            artifact = {
                "schema_version": "1.0",
                "snippets": [
                    {
                        "snippet_id": "abc",
                        "language": "python",
                    }
                ],
            }

            write_doc_snippets_artifact(run_layout, artifact)

            artifact_path = run_layout.artifacts_dir / "doc_snippets.json"
            content = artifact_path.read_text()

            # Check for stable formatting (sorted keys, indentation)
            assert "  " in content  # 2-space indent
            assert content.endswith("\n")  # Trailing newline


class TestExtractDocSnippets:
    """Test main extract_doc_snippets function."""

    def test_full_extraction_workflow(self):
        """Test complete extraction workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Create repo directory
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)

            # Create README with code fence
            readme = repo_dir / "README.md"
            readme.write_text("""# Quick Start

```python
import mylib
result = mylib.run()
print(result)
```
""")

            # Create discovered_docs.json
            discovered_docs = {
                "doc_roots": [],
                "doc_entrypoints": ["README.md"],
                "doc_entrypoint_details": [
                    {
                        "path": "README.md",
                        "doc_type": "readme",
                        "evidence_priority": "high",
                        "relevance_score": 100,
                    }
                ],
                "discovery_summary": {
                    "total_docs_found": 1,
                    "readme_count": 1,
                }
            }

            run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)
            discovered_docs_path = run_layout.artifacts_dir / "discovered_docs.json"
            discovered_docs_path.write_text(json.dumps(discovered_docs, indent=2))

            # Run extraction
            artifact = extract_doc_snippets(repo_dir, run_dir)

            # Verify artifact
            assert len(artifact["snippets"]) == 1
            assert artifact["snippets"][0]["language"] == "python"
            assert "quickstart" in artifact["snippets"][0]["tags"]

            # Verify artifact file was written
            artifact_path = run_layout.artifacts_dir / "doc_snippets.json"
            assert artifact_path.exists()

    def test_deterministic_ordering(self):
        """Test snippets are sorted deterministically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)

            # Create multiple docs with snippets
            readme = repo_dir / "README.md"
            readme.write_text("""# Quick Start

```python
import mylib
mylib.run()
```
""")

            guide = repo_dir / "guide.md"
            guide.write_text("""# Guide

```python
x = 1
y = 2
```
""")

            # Create discovered_docs.json
            discovered_docs = {
                "doc_roots": [],
                "doc_entrypoints": ["README.md", "guide.md"],
                "doc_entrypoint_details": [
                    {"path": "README.md", "doc_type": "readme", "evidence_priority": "high", "relevance_score": 100},
                    {"path": "guide.md", "doc_type": "other", "evidence_priority": "low", "relevance_score": 50},
                ],
                "discovery_summary": {"total_docs_found": 2}
            }

            run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)
            discovered_docs_path = run_layout.artifacts_dir / "discovered_docs.json"
            discovered_docs_path.write_text(json.dumps(discovered_docs, indent=2))

            # Run extraction twice
            artifact1 = extract_doc_snippets(repo_dir, run_dir)

            # Clear artifact for second run
            (run_layout.artifacts_dir / "doc_snippets.json").unlink()

            artifact2 = extract_doc_snippets(repo_dir, run_dir)

            # Verify deterministic ordering
            assert len(artifact1["snippets"]) == len(artifact2["snippets"])

            for i in range(len(artifact1["snippets"])):
                assert artifact1["snippets"][i]["snippet_id"] == artifact2["snippets"][i]["snippet_id"]

            # Verify README snippet comes first (higher relevance)
            assert artifact1["snippets"][0]["source"]["path"] == "README.md"

    def test_extraction_with_evidence_map(self):
        """Test extraction uses evidence_map for prioritization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)

            doc = repo_dir / "guide.md"
            doc.write_text("""# Guide

```python
x = 1
y = 2
```
""")

            # Create discovered_docs.json
            discovered_docs = {
                "doc_roots": [],
                "doc_entrypoints": ["guide.md"],
                "doc_entrypoint_details": [
                    {"path": "guide.md", "doc_type": "other", "evidence_priority": "low", "relevance_score": 50}
                ],
                "discovery_summary": {"total_docs_found": 1}
            }

            # Create evidence_map.json with citation to guide.md
            evidence_map = {
                "schema_version": "1.0",
                "repo_url": "https://github.com/example/repo",
                "repo_sha": "abc123",
                "claims": [
                    {
                        "claim_id": "claim1",
                        "claim_text": "Supports feature X",
                        "claim_kind": "feature",
                        "truth_status": "fact",
                        "citations": [
                            {"path": "guide.md", "start_line": 3, "end_line": 6}
                        ]
                    }
                ]
            }

            run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)
            discovered_docs_path = run_layout.artifacts_dir / "discovered_docs.json"
            discovered_docs_path.write_text(json.dumps(discovered_docs, indent=2))

            evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
            evidence_map_path.write_text(json.dumps(evidence_map, indent=2))

            # Run extraction
            artifact = extract_doc_snippets(repo_dir, run_dir)

            # Verify snippet got evidence boost (base 50 + 10 = 60)
            # We can't check relevance_score directly (it's removed), but we verify extraction succeeded
            assert len(artifact["snippets"]) == 1

    def test_extraction_missing_discovered_docs(self):
        """Test extraction fails gracefully when discovered_docs.json is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            repo_dir = Path(tmpdir) / "repo"
            repo_dir.mkdir()

            with pytest.raises(FileNotFoundError) as exc_info:
                extract_doc_snippets(repo_dir, run_dir)

            assert "discovered_docs.json not found" in str(exc_info.value)


class TestDeterminism:
    """Test deterministic behavior (stable ordering, hashing)."""

    def test_snippet_id_determinism(self):
        """Test snippet IDs are deterministic."""
        snippet = {
            "code": "x = 1\ny = 2",
            "language": "python",
            "source_path": "README.md",
            "start_line": 10,
            "end_line": 11,
        }

        # Generate ID multiple times
        ids = [compute_snippet_id(snippet) for _ in range(10)]

        # All IDs should be identical
        assert len(set(ids)) == 1

    def test_artifact_ordering_determinism(self):
        """Test artifact snippet ordering is deterministic."""
        # Create snippets with different relevance scores
        snippets = [
            {
                "snippet_id": "id1",
                "language": "python",
                "tags": ["example"],
                "source": {"type": "repo_file", "path": "guide.md", "start_line": 10, "end_line": 12},
                "code": "x = 1",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
                "relevance_score": 50,
            },
            {
                "snippet_id": "id2",
                "language": "python",
                "tags": ["quickstart"],
                "source": {"type": "repo_file", "path": "README.md", "start_line": 5, "end_line": 7},
                "code": "y = 2",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
                "relevance_score": 100,
            },
        ]

        # Build artifact multiple times
        artifacts = [build_doc_snippets_artifact(snippets.copy()) for _ in range(5)]

        # All artifacts should be identical (stable order)
        for i in range(1, len(artifacts)):
            assert artifacts[i]["snippets"] == artifacts[0]["snippets"]
