"""Tests for RepoInventory model.

Validates:
- RepoInventory serialization (to_dict/from_dict)
- Round-trip consistency
- Optional fields handling
- Validation logic
- Sub-component models (RepoFingerprint, RepoProfile, PhantomPath, DocEntrypointDetail)

TC-1030: Typed Artifact Models -- Foundation
"""

import pytest

from src.launch.models.repo_inventory import (
    DocEntrypointDetail,
    PhantomPath,
    PublicApiScope,
    RepoFingerprint,
    RepoInventory,
    RepoProfile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_repo_profile() -> RepoProfile:
    """Create a minimal RepoProfile for testing."""
    return RepoProfile(
        platform_family="python",
        primary_languages=["Python"],
        build_systems=["pip"],
        package_manifests=["setup.py"],
        recommended_test_commands=["pytest"],
        example_locator="standard_dirs",
        doc_locator="standard_dirs",
    )


def _minimal_inventory_data() -> dict:
    """Create minimal RepoInventory dict for testing."""
    return {
        "schema_version": "1.0",
        "repo_url": "https://github.com/test/repo",
        "repo_sha": "a" * 40,
        "fingerprint": {
            "primary_languages": ["Python"],
        },
        "repo_profile": {
            "platform_family": "python",
            "primary_languages": ["Python"],
            "build_systems": ["pip"],
            "package_manifests": ["setup.py"],
            "recommended_test_commands": ["pytest"],
            "example_locator": "standard_dirs",
            "doc_locator": "standard_dirs",
        },
        "paths": ["README.md", "src/main.py"],
        "doc_entrypoints": ["README.md"],
        "example_paths": ["examples/demo.py"],
    }


# ---------------------------------------------------------------------------
# RepoFingerprint tests
# ---------------------------------------------------------------------------

def test_repo_fingerprint_minimal():
    """Test RepoFingerprint with defaults."""
    fp = RepoFingerprint()
    data = fp.to_dict()
    assert data["primary_languages"] == []
    assert "default_branch" not in data
    assert "latest_release_tag" not in data
    assert "license_path" not in data


def test_repo_fingerprint_full():
    """Test RepoFingerprint with all fields."""
    fp = RepoFingerprint(
        default_branch="main",
        latest_release_tag="v1.0.0",
        license_path="LICENSE",
        primary_languages=["Python", "C#"],
    )
    data = fp.to_dict()
    assert data["default_branch"] == "main"
    assert data["latest_release_tag"] == "v1.0.0"
    assert data["license_path"] == "LICENSE"
    assert data["primary_languages"] == ["C#", "Python"]  # sorted


def test_repo_fingerprint_round_trip():
    """Test RepoFingerprint round-trip."""
    original = RepoFingerprint(
        default_branch="main",
        primary_languages=["Go", "Python"],
    )
    data = original.to_dict()
    restored = RepoFingerprint.from_dict(data)
    assert restored.default_branch == original.default_branch
    assert sorted(restored.primary_languages) == sorted(original.primary_languages)


# ---------------------------------------------------------------------------
# RepoProfile tests
# ---------------------------------------------------------------------------

def test_repo_profile_minimal():
    """Test RepoProfile with required fields only."""
    profile = _minimal_repo_profile()
    data = profile.to_dict()
    assert data["platform_family"] == "python"
    assert data["primary_languages"] == ["Python"]
    assert data["build_systems"] == ["pip"]
    assert "source_layout" not in data
    assert "public_api_scope" not in data


def test_repo_profile_with_optional():
    """Test RepoProfile with optional fields."""
    profile = RepoProfile(
        platform_family="dotnet",
        primary_languages=["C#"],
        build_systems=["msbuild", "dotnet"],
        package_manifests=["*.csproj"],
        recommended_test_commands=["dotnet test"],
        example_locator="standard_dirs",
        doc_locator="standard_dirs",
        source_layout="src",
        repo_archetype="sdk",
        public_api_scope=PublicApiScope(
            public_roots=["src/Public"],
            internal_prefixes=["_internal"],
            policy="explicit",
        ),
    )
    data = profile.to_dict()
    assert data["source_layout"] == "src"
    assert data["repo_archetype"] == "sdk"
    assert data["public_api_scope"]["policy"] == "explicit"
    assert data["build_systems"] == ["dotnet", "msbuild"]  # sorted


# ---------------------------------------------------------------------------
# PhantomPath tests
# ---------------------------------------------------------------------------

def test_phantom_path_minimal():
    """Test PhantomPath with required fields."""
    pp = PhantomPath(claimed_path="src/missing.py", source_file="README.md")
    data = pp.to_dict()
    assert data["claimed_path"] == "src/missing.py"
    assert data["source_file"] == "README.md"
    assert "source_line" not in data
    assert "claim_context" not in data


def test_phantom_path_full():
    """Test PhantomPath with all fields."""
    pp = PhantomPath(
        claimed_path="src/missing.py",
        source_file="README.md",
        source_line=42,
        claim_context="See src/missing.py for details",
    )
    data = pp.to_dict()
    assert data["source_line"] == 42
    assert data["claim_context"] == "See src/missing.py for details"


def test_phantom_path_round_trip():
    """Test PhantomPath round-trip."""
    original = PhantomPath(
        claimed_path="lib/util.py",
        source_file="docs/api.md",
        source_line=10,
    )
    data = original.to_dict()
    restored = PhantomPath.from_dict(data)
    assert restored.claimed_path == original.claimed_path
    assert restored.source_file == original.source_file
    assert restored.source_line == original.source_line


# ---------------------------------------------------------------------------
# DocEntrypointDetail tests
# ---------------------------------------------------------------------------

def test_doc_entrypoint_detail():
    """Test DocEntrypointDetail serialization."""
    detail = DocEntrypointDetail(
        path="README.md",
        doc_type="readme",
        evidence_priority="high",
    )
    data = detail.to_dict()
    assert data["path"] == "README.md"
    assert data["doc_type"] == "readme"
    assert data["evidence_priority"] == "high"


def test_doc_entrypoint_detail_round_trip():
    """Test DocEntrypointDetail round-trip."""
    original = DocEntrypointDetail(path="docs/api.md", doc_type="api_docs")
    data = original.to_dict()
    restored = DocEntrypointDetail.from_dict(data)
    assert restored.path == original.path
    assert restored.doc_type == original.doc_type
    assert restored.evidence_priority is None


# ---------------------------------------------------------------------------
# RepoInventory tests
# ---------------------------------------------------------------------------

def test_repo_inventory_minimal():
    """Test RepoInventory with minimal required fields."""
    inv = RepoInventory(
        schema_version="1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="a" * 40,
        fingerprint=RepoFingerprint(),
        repo_profile=_minimal_repo_profile(),
        paths=["README.md"],
        doc_entrypoints=["README.md"],
        example_paths=[],
    )
    data = inv.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["repo_url"] == "https://github.com/test/repo"
    assert data["repo_sha"] == "a" * 40
    assert data["paths"] == ["README.md"]
    assert data["doc_entrypoints"] == ["README.md"]
    assert data["example_paths"] == []
    # Optional fields should not be present
    assert "inferred_product_type" not in data
    assert "doc_entrypoint_details" not in data


def test_repo_inventory_with_optional():
    """Test RepoInventory with optional fields."""
    inv = RepoInventory(
        schema_version="1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="b" * 40,
        fingerprint=RepoFingerprint(default_branch="main"),
        repo_profile=_minimal_repo_profile(),
        paths=["README.md", "src/main.py"],
        doc_entrypoints=["README.md"],
        example_paths=["examples/demo.py"],
        source_roots=["src"],
        test_roots=["tests"],
        doc_roots=["docs"],
        example_roots=["examples"],
        binary_assets=["assets/logo.png"],
        phantom_paths=[
            PhantomPath(claimed_path="missing.py", source_file="README.md"),
        ],
        inferred_product_type="sdk",
        doc_entrypoint_details=[
            DocEntrypointDetail(path="README.md", doc_type="readme", evidence_priority="high"),
        ],
        repo_fingerprint="abcd1234" * 8,
        file_count=42,
        total_bytes=12345,
    )
    data = inv.to_dict()
    assert data["source_roots"] == ["src"]
    assert data["test_roots"] == ["tests"]
    assert data["inferred_product_type"] == "sdk"
    assert data["repo_fingerprint"] == "abcd1234" * 8
    assert data["file_count"] == 42
    assert data["total_bytes"] == 12345
    assert len(data["phantom_paths"]) == 1
    assert len(data["doc_entrypoint_details"]) == 1


def test_repo_inventory_from_dict():
    """Test RepoInventory.from_dict with minimal data."""
    data = _minimal_inventory_data()
    inv = RepoInventory.from_dict(data)
    assert inv.repo_url == "https://github.com/test/repo"
    assert inv.repo_sha == "a" * 40
    assert inv.fingerprint.primary_languages == ["Python"]
    assert inv.repo_profile.platform_family == "python"
    assert inv.paths == ["README.md", "src/main.py"]


def test_repo_inventory_round_trip():
    """Test RepoInventory serialization round-trip."""
    data = _minimal_inventory_data()
    data["phantom_paths"] = [
        {"claimed_path": "missing.py", "source_file": "README.md", "source_line": 5},
    ]
    data["inferred_product_type"] = "library"
    data["repo_fingerprint"] = "f" * 64
    data["file_count"] = 10
    data["total_bytes"] = 5000

    original = RepoInventory.from_dict(data)
    serialized = original.to_dict()
    restored = RepoInventory.from_dict(serialized)

    assert restored.repo_url == original.repo_url
    assert restored.repo_sha == original.repo_sha
    assert restored.inferred_product_type == original.inferred_product_type
    assert restored.repo_fingerprint == original.repo_fingerprint
    assert restored.file_count == original.file_count
    assert restored.total_bytes == original.total_bytes
    assert len(restored.phantom_paths) == 1
    assert restored.phantom_paths[0].claimed_path == "missing.py"


def test_repo_inventory_deterministic_sorting():
    """Test that paths and lists are sorted deterministically."""
    inv = RepoInventory(
        schema_version="1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="c" * 40,
        fingerprint=RepoFingerprint(primary_languages=["Go", "Python", "C"]),
        repo_profile=_minimal_repo_profile(),
        paths=["z.py", "a.py", "m.py"],
        doc_entrypoints=["docs/z.md", "docs/a.md"],
        example_paths=["examples/z.py", "examples/a.py"],
    )
    data = inv.to_dict()
    assert data["paths"] == ["a.py", "m.py", "z.py"]
    assert data["doc_entrypoints"] == ["docs/a.md", "docs/z.md"]
    assert data["example_paths"] == ["examples/a.py", "examples/z.py"]
    assert data["fingerprint"]["primary_languages"] == ["C", "Go", "Python"]


def test_repo_inventory_validate_valid():
    """Test validate() on valid inventory."""
    inv = RepoInventory(
        schema_version="1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="d" * 40,
        fingerprint=RepoFingerprint(),
        repo_profile=_minimal_repo_profile(),
        paths=[],
        doc_entrypoints=[],
        example_paths=[],
    )
    assert inv.validate() is True


def test_repo_inventory_validate_empty_url():
    """Test validate() rejects empty repo_url."""
    inv = RepoInventory(
        schema_version="1.0",
        repo_url="",
        repo_sha="e" * 40,
        fingerprint=RepoFingerprint(),
        repo_profile=_minimal_repo_profile(),
        paths=[],
        doc_entrypoints=[],
        example_paths=[],
    )
    with pytest.raises(ValueError, match="repo_url"):
        inv.validate()


def test_repo_inventory_validate_invalid_product_type():
    """Test validate() rejects invalid inferred_product_type."""
    inv = RepoInventory(
        schema_version="1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="f" * 40,
        fingerprint=RepoFingerprint(),
        repo_profile=_minimal_repo_profile(),
        paths=[],
        doc_entrypoints=[],
        example_paths=[],
        inferred_product_type="invalid_type",
    )
    with pytest.raises(ValueError, match="inferred_product_type"):
        inv.validate()


def test_repo_inventory_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    inv = RepoInventory(
        schema_version="1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="a" * 40,
        fingerprint=RepoFingerprint(default_branch="main"),
        repo_profile=_minimal_repo_profile(),
        paths=["README.md"],
        doc_entrypoints=[],
        example_paths=[],
    )
    json_str = inv.to_json()
    restored = RepoInventory.from_json(json_str)
    assert restored.repo_url == inv.repo_url
    assert restored.fingerprint.default_branch == "main"
