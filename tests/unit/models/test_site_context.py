"""Tests for SiteContext model.

Validates:
- SiteContext serialization (to_dict/from_dict)
- Round-trip consistency
- Sub-component models (RepoRef, HugoConfigFile, BuildMatrixEntry, HugoConfig)
- Validation logic

TC-1030: Typed Artifact Models -- Foundation
"""

import pytest

from src.launch.models.site_context import (
    BuildMatrixEntry,
    HugoConfig,
    HugoConfigFile,
    RepoRef,
    SiteContext,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_site_context_data() -> dict:
    """Create minimal SiteContext dict for testing."""
    return {
        "schema_version": "1.0",
        "site": {
            "repo_url": "https://github.com/test/site",
            "requested_ref": "main",
            "resolved_sha": "a" * 40,
        },
        "workflows": {
            "repo_url": "https://github.com/test/workflows",
            "requested_ref": "main",
            "resolved_sha": "b" * 40,
        },
        "hugo": {
            "config_root": "config",
            "config_files": [],
            "build_matrix": [],
        },
    }


# ---------------------------------------------------------------------------
# RepoRef tests
# ---------------------------------------------------------------------------

def test_repo_ref_minimal():
    """Test RepoRef with required fields."""
    ref = RepoRef(
        repo_url="https://github.com/test/repo",
        requested_ref="main",
        resolved_sha="abc1234" * 6,
    )
    data = ref.to_dict()
    assert data["repo_url"] == "https://github.com/test/repo"
    assert data["requested_ref"] == "main"
    assert data["resolved_sha"] == "abc1234" * 6
    assert "clone_path" not in data


def test_repo_ref_with_clone_path():
    """Test RepoRef with clone_path."""
    ref = RepoRef(
        repo_url="https://github.com/test/repo",
        requested_ref="v1.0",
        resolved_sha="d" * 40,
        clone_path="/tmp/work/site",
    )
    data = ref.to_dict()
    assert data["clone_path"] == "/tmp/work/site"


def test_repo_ref_round_trip():
    """Test RepoRef round-trip."""
    original = RepoRef(
        repo_url="https://github.com/test/repo",
        requested_ref="main",
        resolved_sha="e" * 40,
        clone_path="/tmp/work/repo",
    )
    data = original.to_dict()
    restored = RepoRef.from_dict(data)
    assert restored.repo_url == original.repo_url
    assert restored.requested_ref == original.requested_ref
    assert restored.resolved_sha == original.resolved_sha
    assert restored.clone_path == original.clone_path


# ---------------------------------------------------------------------------
# HugoConfigFile tests
# ---------------------------------------------------------------------------

def test_hugo_config_file():
    """Test HugoConfigFile serialization."""
    config_file = HugoConfigFile(
        path="config/_default/config.toml",
        sha256="a" * 64,
        bytes_=1024,
        ext=".toml",
    )
    data = config_file.to_dict()
    assert data["path"] == "config/_default/config.toml"
    assert data["sha256"] == "a" * 64
    assert data["bytes"] == 1024
    assert data["ext"] == ".toml"


def test_hugo_config_file_round_trip():
    """Test HugoConfigFile round-trip."""
    original = HugoConfigFile(
        path="config.yaml",
        sha256="b" * 64,
        bytes_=512,
        ext=".yaml",
    )
    data = original.to_dict()
    restored = HugoConfigFile.from_dict(data)
    assert restored.path == original.path
    assert restored.sha256 == original.sha256
    assert restored.bytes == original.bytes
    assert restored.ext == original.ext


# ---------------------------------------------------------------------------
# BuildMatrixEntry tests
# ---------------------------------------------------------------------------

def test_build_matrix_entry():
    """Test BuildMatrixEntry serialization."""
    entry = BuildMatrixEntry(
        subdomain="docs.aspose.org",
        family="3d",
        config_path="config/docs/3d",
    )
    data = entry.to_dict()
    assert data["subdomain"] == "docs.aspose.org"
    assert data["family"] == "3d"
    assert data["config_path"] == "config/docs/3d"


def test_build_matrix_entry_round_trip():
    """Test BuildMatrixEntry round-trip."""
    original = BuildMatrixEntry(
        subdomain="products.aspose.org",
        family="cells",
        config_path="config/products/cells",
    )
    data = original.to_dict()
    restored = BuildMatrixEntry.from_dict(data)
    assert restored.subdomain == original.subdomain
    assert restored.family == original.family
    assert restored.config_path == original.config_path


# ---------------------------------------------------------------------------
# HugoConfig tests
# ---------------------------------------------------------------------------

def test_hugo_config_empty():
    """Test HugoConfig with no files or matrix."""
    config = HugoConfig(
        config_root="config",
        config_files=[],
        build_matrix=[],
    )
    data = config.to_dict()
    assert data["config_root"] == "config"
    assert data["config_files"] == []
    assert data["build_matrix"] == []


def test_hugo_config_with_entries():
    """Test HugoConfig with files and matrix entries."""
    config = HugoConfig(
        config_root="config",
        config_files=[
            HugoConfigFile(path="config.toml", sha256="a" * 64, bytes_=100, ext=".toml"),
        ],
        build_matrix=[
            BuildMatrixEntry(subdomain="docs", family="3d", config_path="config/docs"),
        ],
    )
    data = config.to_dict()
    assert len(data["config_files"]) == 1
    assert len(data["build_matrix"]) == 1


# ---------------------------------------------------------------------------
# SiteContext tests
# ---------------------------------------------------------------------------

def test_site_context_minimal():
    """Test SiteContext from minimal data."""
    data = _minimal_site_context_data()
    ctx = SiteContext.from_dict(data)
    assert ctx.schema_version == "1.0"
    assert ctx.site.repo_url == "https://github.com/test/site"
    assert ctx.workflows.repo_url == "https://github.com/test/workflows"
    assert ctx.hugo.config_root == "config"


def test_site_context_round_trip():
    """Test SiteContext serialization round-trip."""
    data = _minimal_site_context_data()
    data["hugo"]["config_files"] = [
        {"path": "config.toml", "sha256": "c" * 64, "bytes": 256, "ext": ".toml"},
    ]
    data["hugo"]["build_matrix"] = [
        {"subdomain": "docs.aspose.org", "family": "3d", "config_path": "config/docs/3d"},
    ]

    original = SiteContext.from_dict(data)
    serialized = original.to_dict()
    restored = SiteContext.from_dict(serialized)

    assert restored.site.repo_url == original.site.repo_url
    assert restored.site.resolved_sha == original.site.resolved_sha
    assert restored.workflows.repo_url == original.workflows.repo_url
    assert restored.hugo.config_root == original.hugo.config_root
    assert len(restored.hugo.config_files) == 1
    assert len(restored.hugo.build_matrix) == 1


def test_site_context_validate_valid():
    """Test validate() on valid SiteContext."""
    data = _minimal_site_context_data()
    ctx = SiteContext.from_dict(data)
    assert ctx.validate() is True


def test_site_context_validate_empty_site_url():
    """Test validate() rejects empty site.repo_url."""
    ctx = SiteContext(
        schema_version="1.0",
        site=RepoRef(repo_url="", requested_ref="main", resolved_sha="a" * 40),
        workflows=RepoRef(
            repo_url="https://github.com/test/wf",
            requested_ref="main",
            resolved_sha="b" * 40,
        ),
        hugo=HugoConfig(config_root="config", config_files=[], build_matrix=[]),
    )
    with pytest.raises(ValueError, match="site.repo_url"):
        ctx.validate()


def test_site_context_validate_short_sha():
    """Test validate() rejects resolved_sha shorter than 7 chars."""
    ctx = SiteContext(
        schema_version="1.0",
        site=RepoRef(
            repo_url="https://github.com/test/site",
            requested_ref="main",
            resolved_sha="abc",  # Too short
        ),
        workflows=RepoRef(
            repo_url="https://github.com/test/wf",
            requested_ref="main",
            resolved_sha="b" * 40,
        ),
        hugo=HugoConfig(config_root="config", config_files=[], build_matrix=[]),
    )
    with pytest.raises(ValueError, match="resolved_sha"):
        ctx.validate()


def test_site_context_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_site_context_data()
    ctx = SiteContext.from_dict(data)
    json_str = ctx.to_json()
    restored = SiteContext.from_json(json_str)
    assert restored.site.repo_url == ctx.site.repo_url
    assert restored.workflows.repo_url == ctx.workflows.repo_url
