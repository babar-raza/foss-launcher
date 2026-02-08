"""Tests for SnippetCatalog model.

Validates:
- SnippetCatalog serialization (to_dict/from_dict)
- Round-trip consistency
- Optional fields handling
- Validation logic
- Sub-component models (SnippetSource, SnippetValidation, SnippetRequirements, Snippet)

TC-1031: Typed Artifact Models -- Worker Models
"""

import pytest

from src.launch.models.snippet_catalog import (
    Snippet,
    SnippetCatalog,
    SnippetRequirements,
    SnippetSource,
    SnippetValidation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_snippet_data() -> dict:
    """Create minimal Snippet dict for testing."""
    return {
        "snippet_id": "snip_001",
        "language": "python",
        "tags": ["install", "setup"],
        "source": {"type": "repo_file", "path": "examples/demo.py", "start_line": 1, "end_line": 10},
        "code": "import aspose\nprint('hello')",
        "requirements": {"dependencies": ["aspose-3d"]},
        "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
    }


def _minimal_catalog_data() -> dict:
    """Create minimal SnippetCatalog dict for testing."""
    return {
        "schema_version": "1.0",
        "snippets": [_minimal_snippet_data()],
    }


# ---------------------------------------------------------------------------
# SnippetSource tests
# ---------------------------------------------------------------------------

def test_snippet_source_repo_file():
    """Test SnippetSource for repo_file type."""
    source = SnippetSource(
        source_type="repo_file",
        path="examples/demo.py",
        start_line=1,
        end_line=10,
    )
    data = source.to_dict()
    assert data["type"] == "repo_file"
    assert data["path"] == "examples/demo.py"
    assert data["start_line"] == 1
    assert data["end_line"] == 10
    assert "prompt_hash" not in data


def test_snippet_source_generated():
    """Test SnippetSource for generated type."""
    source = SnippetSource(
        source_type="generated",
        prompt_hash="abc123",
    )
    data = source.to_dict()
    assert data["type"] == "generated"
    assert data["prompt_hash"] == "abc123"
    assert "path" not in data


def test_snippet_source_round_trip():
    """Test SnippetSource round-trip."""
    original = SnippetSource(
        source_type="repo_file",
        path="src/main.py",
        start_line=5,
        end_line=20,
    )
    data = original.to_dict()
    restored = SnippetSource.from_dict(data)
    assert restored.source_type == original.source_type
    assert restored.path == original.path
    assert restored.start_line == original.start_line
    assert restored.end_line == original.end_line


# ---------------------------------------------------------------------------
# SnippetValidation tests
# ---------------------------------------------------------------------------

def test_snippet_validation_minimal():
    """Test SnippetValidation with defaults."""
    val = SnippetValidation(syntax_ok=True)
    data = val.to_dict()
    assert data["syntax_ok"] is True
    assert data["runnable_ok"] == "unknown"
    assert "log_path" not in data


def test_snippet_validation_full():
    """Test SnippetValidation with all fields."""
    val = SnippetValidation(
        syntax_ok=True,
        runnable_ok=True,
        log_path="logs/run.log",
    )
    data = val.to_dict()
    assert data["syntax_ok"] is True
    assert data["runnable_ok"] is True
    assert data["log_path"] == "logs/run.log"


def test_snippet_validation_round_trip():
    """Test SnippetValidation round-trip."""
    original = SnippetValidation(syntax_ok=False, runnable_ok=False)
    data = original.to_dict()
    restored = SnippetValidation.from_dict(data)
    assert restored.syntax_ok == original.syntax_ok
    assert restored.runnable_ok == original.runnable_ok


# ---------------------------------------------------------------------------
# SnippetRequirements tests
# ---------------------------------------------------------------------------

def test_snippet_requirements_minimal():
    """Test SnippetRequirements with defaults."""
    req = SnippetRequirements()
    data = req.to_dict()
    assert data["dependencies"] == []
    assert "runtime_notes" not in data


def test_snippet_requirements_full():
    """Test SnippetRequirements with all fields."""
    req = SnippetRequirements(
        dependencies=["numpy", "aspose-3d"],
        runtime_notes="Requires Python 3.8+",
    )
    data = req.to_dict()
    assert data["dependencies"] == ["aspose-3d", "numpy"]  # sorted
    assert data["runtime_notes"] == "Requires Python 3.8+"


def test_snippet_requirements_round_trip():
    """Test SnippetRequirements round-trip."""
    original = SnippetRequirements(dependencies=["pandas", "aspose"])
    data = original.to_dict()
    restored = SnippetRequirements.from_dict(data)
    assert sorted(restored.dependencies) == sorted(original.dependencies)


# ---------------------------------------------------------------------------
# Snippet tests
# ---------------------------------------------------------------------------

def test_snippet_from_dict():
    """Test Snippet.from_dict with full data."""
    data = _minimal_snippet_data()
    snippet = Snippet.from_dict(data)
    assert snippet.snippet_id == "snip_001"
    assert snippet.language == "python"
    assert snippet.tags == ["install", "setup"]
    assert snippet.source.source_type == "repo_file"
    assert snippet.code == "import aspose\nprint('hello')"


def test_snippet_to_dict():
    """Test Snippet.to_dict produces deterministic output."""
    data = _minimal_snippet_data()
    snippet = Snippet.from_dict(data)
    result = snippet.to_dict()
    assert result["snippet_id"] == "snip_001"
    assert result["language"] == "python"
    assert result["tags"] == ["install", "setup"]  # sorted
    assert result["source"]["type"] == "repo_file"


def test_snippet_round_trip():
    """Test Snippet round-trip."""
    data = _minimal_snippet_data()
    original = Snippet.from_dict(data)
    serialized = original.to_dict()
    restored = Snippet.from_dict(serialized)
    assert restored.snippet_id == original.snippet_id
    assert restored.language == original.language
    assert restored.code == original.code


def test_snippet_tags_sorted():
    """Test that snippet tags are sorted in to_dict."""
    snippet = Snippet(
        snippet_id="test",
        language="python",
        tags=["zebra", "alpha", "middle"],
        source=SnippetSource(source_type="generated", prompt_hash="abc"),
        code="pass",
        requirements=SnippetRequirements(),
        validation=SnippetValidation(syntax_ok=True),
    )
    data = snippet.to_dict()
    assert data["tags"] == ["alpha", "middle", "zebra"]


# ---------------------------------------------------------------------------
# SnippetCatalog tests
# ---------------------------------------------------------------------------

def test_snippet_catalog_minimal():
    """Test SnippetCatalog with empty snippets."""
    catalog = SnippetCatalog(schema_version="1.0")
    data = catalog.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["snippets"] == []


def test_snippet_catalog_from_dict():
    """Test SnippetCatalog.from_dict."""
    data = _minimal_catalog_data()
    catalog = SnippetCatalog.from_dict(data)
    assert catalog.schema_version == "1.0"
    assert len(catalog.snippets) == 1
    assert catalog.snippets[0].snippet_id == "snip_001"


def test_snippet_catalog_round_trip():
    """Test SnippetCatalog round-trip."""
    data = _minimal_catalog_data()
    original = SnippetCatalog.from_dict(data)
    serialized = original.to_dict()
    restored = SnippetCatalog.from_dict(serialized)
    assert restored.schema_version == original.schema_version
    assert len(restored.snippets) == len(original.snippets)
    assert restored.snippets[0].snippet_id == original.snippets[0].snippet_id


def test_snippet_catalog_validate_valid():
    """Test validate() on valid catalog."""
    data = _minimal_catalog_data()
    catalog = SnippetCatalog.from_dict(data)
    assert catalog.validate() is True


def test_snippet_catalog_validate_invalid_source_type():
    """Test validate() rejects invalid source type."""
    catalog = SnippetCatalog(
        schema_version="1.0",
        snippets=[
            Snippet(
                snippet_id="test",
                language="python",
                tags=[],
                source=SnippetSource(source_type="invalid_type"),
                code="pass",
                requirements=SnippetRequirements(),
                validation=SnippetValidation(syntax_ok=True),
            )
        ],
    )
    with pytest.raises(ValueError, match="source type"):
        catalog.validate()


def test_snippet_catalog_validate_empty_snippet_id():
    """Test validate() rejects empty snippet_id."""
    catalog = SnippetCatalog(
        schema_version="1.0",
        snippets=[
            Snippet(
                snippet_id="",
                language="python",
                tags=[],
                source=SnippetSource(source_type="generated", prompt_hash="abc"),
                code="pass",
                requirements=SnippetRequirements(),
                validation=SnippetValidation(syntax_ok=True),
            )
        ],
    )
    with pytest.raises(ValueError, match="snippet_id"):
        catalog.validate()


def test_snippet_catalog_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_catalog_data()
    catalog = SnippetCatalog.from_dict(data)
    json_str = catalog.to_json()
    restored = SnippetCatalog.from_json(json_str)
    assert restored.schema_version == catalog.schema_version
    assert len(restored.snippets) == len(catalog.snippets)
