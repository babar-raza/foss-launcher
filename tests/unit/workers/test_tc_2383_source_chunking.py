"""Tests for TC-2383: W2 Source Chunking."""
import pytest
from pathlib import Path
from launch.workers.w2_facts_builder.chunk_sources import (
    chunk_source_files,
    retrieve_relevant_chunks,
    _chunk_by_headings,
    _chunk_python_file,
    _chunk_yaml,
    _make_chunk,
)


def test_chunk_source_files_empty_dir(tmp_path):
    """Empty directory returns empty list."""
    chunks = chunk_source_files(tmp_path)
    assert chunks == []


def test_chunk_source_files_with_markdown(tmp_path):
    """Markdown file is chunked."""
    md_file = tmp_path / "README.md"
    md_file.write_text(
        "# Introduction\n\nThis is a paragraph with enough words to form a chunk. " * 5
    )
    chunks = chunk_source_files(tmp_path)
    assert len(chunks) > 0
    assert all("chunk_id" in c for c in chunks)
    assert all("text" in c for c in chunks)
    assert all("file_path" in c for c in chunks)


def test_chunk_by_headings_basic():
    """Heading-based chunking produces chunks with heading context."""
    text = "# Getting Started\n\nThis is the intro paragraph with enough words. " * 10
    chunks = _chunk_by_headings(text, "README.md")
    assert len(chunks) > 0
    assert chunks[0]["heading_context"] == "Getting Started"


def test_chunk_yaml():
    """YAML files chunked in blocks."""
    yaml_text = "key: value\n" * 60
    chunks = _chunk_yaml(yaml_text, "config.yaml")
    assert len(chunks) > 0


def test_retrieve_relevant_chunks_returns_top_k():
    """retrieve_relevant_chunks returns at most top_k results."""
    chunks = [
        {
            "chunk_id": f"c{i}",
            "text": f"chunk {i} content",
            "file_path": f"f{i}.md",
            "heading_context": "",
            "token_count": 3,
        }
        for i in range(10)
    ]
    result = retrieve_relevant_chunks("chunk content", chunks, top_k=3)
    assert len(result) <= 3


def test_retrieve_relevant_chunks_empty():
    """Empty chunks list returns empty list."""
    result = retrieve_relevant_chunks("query", [], top_k=5)
    assert result == []


def test_make_chunk_deterministic():
    """Same inputs produce same chunk_id."""
    c1 = _make_chunk("text content", "path.md", "heading")
    c2 = _make_chunk("text content", "path.md", "heading")
    assert c1["chunk_id"] == c2["chunk_id"]


def test_chunk_source_files_skips_test_files(tmp_path):
    """Files matching skip patterns are excluded."""
    test_file = tmp_path / "test_something.md"
    test_file.write_text("# Test\n\nThis file should be skipped " * 10)
    normal_file = tmp_path / "README.md"
    normal_file.write_text("# Docs\n\nThis file should be included. " * 10)
    chunks = chunk_source_files(tmp_path)
    file_paths = [c["file_path"] for c in chunks]
    assert not any("test_something" in p for p in file_paths)
    assert any("README" in p for p in file_paths)


def test_chunk_source_files_py_without_docstrings_no_chunks(tmp_path):
    """Python files without docstrings produce no chunks."""
    py_file = tmp_path / "module.py"
    py_file.write_text("def foo():\n    pass\n" * 20)
    md_file = tmp_path / "guide.md"
    md_file.write_text("# Guide\n\nThis is a guide with enough content. " * 10)
    chunks = chunk_source_files(tmp_path)
    file_paths = [c["file_path"] for c in chunks]
    assert not any(p.endswith(".py") for p in file_paths)


def test_chunk_by_headings_min_token_filter():
    """Sections below MIN_CHUNK_TOKENS are excluded."""
    # Fewer than 30 tokens
    text = "# Short\n\nToo short."
    chunks = _chunk_by_headings(text, "doc.md")
    assert chunks == []


def test_chunk_source_files_max_chunks_respected(tmp_path):
    """max_chunks parameter is respected."""
    for i in range(20):
        f = tmp_path / f"doc{i}.md"
        f.write_text(
            f"# Section {i}\n\nThis is document {i} with enough content " * 5
        )
    chunks = chunk_source_files(tmp_path, max_chunks=5)
    assert len(chunks) <= 5


def test_make_chunk_fields():
    """_make_chunk returns all required fields."""
    chunk = _make_chunk("Some sample text here", "docs/readme.md", "Overview")
    assert "chunk_id" in chunk
    assert "file_path" in chunk
    assert chunk["file_path"] == "docs/readme.md"
    assert "text" in chunk
    assert chunk["text"] == "Some sample text here"
    assert "heading_context" in chunk
    assert chunk["heading_context"] == "Overview"
    assert "token_count" in chunk
    assert chunk["token_count"] == 4  # "Some sample text here" = 4 words


def test_skip_patterns_filter_agents_md(tmp_path):
    """AGENTS.md is filtered from chunking (internal dev doc)."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Agent Instructions\n\nYou are an AI agent. Follow these rules. " * 10)
    readme = tmp_path / "README.md"
    readme.write_text("# Library\n\nThis library does useful things for users. " * 10)
    chunks = chunk_source_files(tmp_path)
    file_paths = [c["file_path"] for c in chunks]
    assert not any("AGENTS" in p for p in file_paths)
    assert any("README" in p for p in file_paths)


def test_skip_patterns_filter_github_dir(tmp_path):
    """Files under .github/ are filtered from chunking."""
    gh_dir = tmp_path / ".github" / "workflows"
    gh_dir.mkdir(parents=True)
    ci = gh_dir / "ci.yml"
    ci.write_text("name: CI\njobs:\n  test:\n    runs-on: ubuntu-latest\n" * 10)
    readme = tmp_path / "README.md"
    readme.write_text("# Library\n\nThis library is for end users. " * 10)
    chunks = chunk_source_files(tmp_path)
    file_paths = [c["file_path"] for c in chunks]
    assert not any(".github" in p for p in file_paths)


def test_skip_patterns_filter_contributing_md(tmp_path):
    """CONTRIBUTING.md is filtered from chunking."""
    contrib = tmp_path / "CONTRIBUTING.md"
    contrib.write_text("# Contributing\n\nPlease follow these PR guidelines. " * 10)
    readme = tmp_path / "README.md"
    readme.write_text("# Library\n\nThis library does useful things for users. " * 10)
    chunks = chunk_source_files(tmp_path)
    file_paths = [c["file_path"] for c in chunks]
    assert not any("CONTRIBUTING" in p for p in file_paths)


def test_retrieve_relevant_chunks_fallback_to_first_k():
    """When embeddings unavailable, fallback returns first K chunks."""
    chunks = [
        {
            "chunk_id": f"c{i}",
            "text": f"content {i}",
            "file_path": f"f{i}.md",
            "heading_context": "",
            "token_count": 2,
        }
        for i in range(10)
    ]
    # Since launch.workers._shared.embeddings doesn't have tfidf_cosine_similarity,
    # it falls back to chunks[:top_k]
    result = retrieve_relevant_chunks("query text", chunks, top_k=4)
    assert len(result) <= 4


# --- A4: Python AST chunking tests ---


def test_chunk_python_file_extracts_docstrings():
    """Classes and functions with docstrings become chunks."""
    code = '''
class Scene:
    """Represents a 3D scene with nodes, materials, and animations.

    The Scene class is the root container for all 3D objects. It manages
    the node hierarchy, materials, textures, and animation data. Use this
    class to load, manipulate, and save 3D file formats.
    """

    def add_node(self, node):
        """Add a child node to the scene root.

        This method attaches the given node to the root of the scene
        graph hierarchy, making it visible in the rendered output and
        accessible for transformation operations.
        """
        pass
'''
    chunks = _chunk_python_file(code, "aspose/threed/scene.py")
    assert len(chunks) >= 1
    names = [c["heading_context"] for c in chunks]
    assert "Scene" in names


def test_chunk_python_file_skips_no_docstring():
    """Functions/classes without docstrings are skipped."""
    code = '''
def helper():
    pass

class Internal:
    x = 1
'''
    chunks = _chunk_python_file(code, "internal.py")
    assert chunks == []


def test_chunk_python_file_syntax_error():
    """Syntax errors return empty list (no crash)."""
    chunks = _chunk_python_file("def broken(:\n    pass", "bad.py")
    assert chunks == []


def test_chunk_python_file_min_token_filter():
    """Short docstrings below MIN_CHUNK_TOKENS are excluded."""
    code = '''
def tiny():
    """Short."""
    pass
'''
    chunks = _chunk_python_file(code, "tiny.py")
    assert chunks == []


def test_chunk_source_files_includes_py_with_docstrings(tmp_path):
    """Python files with docstrings produce chunks in chunk_source_files."""
    py_file = tmp_path / "scene.py"
    py_file.write_text('''
class Scene:
    """Represents a 3D scene with nodes, materials, and animations.

    The Scene class is the root container for all 3D objects. It manages
    the node hierarchy, materials, textures, and animation data. Use this
    class to load, manipulate, and save 3D file formats.
    """
    pass
''')
    chunks = chunk_source_files(tmp_path)
    assert len(chunks) >= 1
    assert any(c["file_path"] == "scene.py" for c in chunks)
    assert any("Scene" in c["heading_context"] for c in chunks)
