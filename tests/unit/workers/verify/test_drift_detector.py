"""Unit tests for drift_detector.py — TC-5167."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from launcher.workers.verify.drift_detector import (
    _parse_formats_md,
    _read_from_clone_cache,
    compute_drift_status,
    compute_page_drift_actions,
    pass1_sha_check,
    pass2_claim_staleness,
    pass3_new_capabilities,
    write_drift_baseline,
)

try:
    import yaml as _yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def knowledge_dir(tmp_path: Path) -> Path:
    d = tmp_path / "knowledge" / "3d" / "python"
    d.mkdir(parents=True)
    return d


@pytest.fixture()
def clone_cache_dir(tmp_path: Path) -> Path:
    d = tmp_path / "clone_cache"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Pass 1: SHA check
# ---------------------------------------------------------------------------


def test_sha_unchanged_returns_clean(knowledge_dir: Path) -> None:
    """Pass1 returns (True, sha) when baseline SHA matches current SHA."""
    if not HAS_YAML:
        pytest.skip("pyyaml not installed")
    import yaml
    baseline = {"repo_sha_at_verify": "abc123def456", "family": "3d", "platform": "python"}
    (knowledge_dir / "drift_baseline.yaml").write_text(
        yaml.dump(baseline), encoding="utf-8"
    )
    is_clean, baseline_sha = pass1_sha_check(knowledge_dir, "abc123def456")
    assert is_clean is True
    assert baseline_sha == "abc123def456"


def test_sha_changed_returns_not_clean(knowledge_dir: Path) -> None:
    """Pass1 returns (False, old_sha) when SHA has changed."""
    if not HAS_YAML:
        pytest.skip("pyyaml not installed")
    import yaml
    baseline = {"repo_sha_at_verify": "oldsha", "family": "3d", "platform": "python"}
    (knowledge_dir / "drift_baseline.yaml").write_text(
        yaml.dump(baseline), encoding="utf-8"
    )
    is_clean, baseline_sha = pass1_sha_check(knowledge_dir, "newsha")
    assert is_clean is False
    assert baseline_sha == "oldsha"


def test_no_baseline_returns_not_clean(knowledge_dir: Path) -> None:
    """Pass1 returns (False, '') when no drift_baseline.yaml exists."""
    is_clean, baseline_sha = pass1_sha_check(knowledge_dir, "anysha")
    assert is_clean is False
    assert baseline_sha == ""


# ---------------------------------------------------------------------------
# Pass 2: Claim staleness
# ---------------------------------------------------------------------------


def test_deleted_source_file_marks_claim_stale(
    knowledge_dir: Path, clone_cache_dir: Path
) -> None:
    """Pass2 marks a claim stale when its evidence source_file is missing from file_tree."""
    claims = [
        {
            "claim_id": "CLM-001",
            "text": "Supports FBX export",
            "evidence": [{"source_file": "src/formats/fbx.py", "snippet": "def export_fbx"}],
        }
    ]
    (knowledge_dir / "claims.json").write_text(json.dumps(claims), encoding="utf-8")
    # File not in file_tree
    stale = pass2_claim_staleness(knowledge_dir, clone_cache_dir, [])
    assert len(stale) == 1
    assert stale[0]["claim_id"] == "CLM-001"
    assert stale[0]["reason"] == "source_deleted"


def test_evidence_anchor_changed_marks_claim_stale(
    knowledge_dir: Path, clone_cache_dir: Path
) -> None:
    """Pass2 marks a claim stale when anchor text is absent from the current file."""
    claims = [
        {
            "claim_id": "CLM-002",
            "text": "Can load OBJ files",
            "evidence": [
                {
                    "source_file": "src/formats/obj.py",
                    "snippet": "def load_obj(path):",
                }
            ],
        }
    ]
    (knowledge_dir / "claims.json").write_text(json.dumps(claims), encoding="utf-8")

    # Put a modified file in clone cache (anchor removed)
    repo_dir = clone_cache_dir / "aspose_3d_python"
    repo_dir.mkdir()
    src_dir = repo_dir / "src" / "formats"
    src_dir.mkdir(parents=True)
    (src_dir / "obj.py").write_text("def load_object(path):\n    pass\n", encoding="utf-8")

    stale = pass2_claim_staleness(
        knowledge_dir, clone_cache_dir, ["src/formats/obj.py"]
    )
    assert len(stale) == 1
    assert stale[0]["claim_id"] == "CLM-002"
    assert stale[0]["reason"] == "evidence_changed"


def test_no_changes_returns_empty_stale(
    knowledge_dir: Path, clone_cache_dir: Path
) -> None:
    """Pass2 returns empty list when all evidence anchors are still present."""
    claims = [
        {
            "claim_id": "CLM-003",
            "text": "Can load OBJ files",
            "evidence": [
                {
                    "source_file": "src/formats/obj.py",
                    "snippet": "def load_obj(path):",
                }
            ],
        }
    ]
    (knowledge_dir / "claims.json").write_text(json.dumps(claims), encoding="utf-8")

    repo_dir = clone_cache_dir / "aspose_3d_python"
    repo_dir.mkdir()
    src_dir = repo_dir / "src" / "formats"
    src_dir.mkdir(parents=True)
    (src_dir / "obj.py").write_text(
        "def load_obj(path):\n    pass\n", encoding="utf-8"
    )

    stale = pass2_claim_staleness(
        knowledge_dir, clone_cache_dir, ["src/formats/obj.py"]
    )
    assert stale == []


def test_no_claims_json_returns_empty(
    knowledge_dir: Path, clone_cache_dir: Path
) -> None:
    """Pass2 gracefully returns empty list when claims.json does not exist."""
    stale = pass2_claim_staleness(knowledge_dir, clone_cache_dir, ["any/file.py"])
    assert stale == []


# ---------------------------------------------------------------------------
# Pass 2 helper: _read_from_clone_cache
# ---------------------------------------------------------------------------


def test_read_from_clone_cache_finds_file(clone_cache_dir: Path) -> None:
    repo_dir = clone_cache_dir / "some_repo"
    repo_dir.mkdir()
    target = repo_dir / "src" / "module.py"
    target.parent.mkdir(parents=True)
    target.write_text("content here", encoding="utf-8")

    result = _read_from_clone_cache(clone_cache_dir, "src/module.py")
    assert result == "content here"


def test_read_from_clone_cache_missing(clone_cache_dir: Path) -> None:
    result = _read_from_clone_cache(clone_cache_dir, "nonexistent/path.py")
    assert result is None


# ---------------------------------------------------------------------------
# Pass 3: New capabilities
# ---------------------------------------------------------------------------


def test_new_api_identifier_detected(knowledge_dir: Path) -> None:
    """Pass3 detects a new import not in the baseline api_surface.json."""
    baseline_api = {
        "import_allowlist": ["aspose.threed", "aspose.threed.entities"],
        "public_classes": ["Scene", "Node"],
        "format_matrix": [],
    }
    (knowledge_dir / "api_surface.json").write_text(
        json.dumps(baseline_api), encoding="utf-8"
    )

    current_api = {
        "import_allowlist": ["aspose.threed", "aspose.threed.entities", "aspose.threed.animation"],
        "public_classes": ["Scene", "Node"],
        "api_identifiers": [],
    }
    new_caps = pass3_new_capabilities(knowledge_dir, current_api, [])
    identifiers = [c["identifier"] for c in new_caps]
    assert "aspose.threed.animation" in identifiers


def test_new_format_detected(knowledge_dir: Path) -> None:
    """Pass3 detects a new format not in knowledge/formats.md."""
    # Write a formats.md with only OBJ
    (knowledge_dir / "formats.md").write_text(
        "| Format | Import | Export |\n|--------|--------|--------|\n| OBJ | Yes | Yes |\n",
        encoding="utf-8",
    )

    current_api: dict = {"import_allowlist": [], "public_classes": [], "api_identifiers": []}
    current_fmt = [
        {"name": "OBJ", "can_import": True, "can_export": True},
        {"name": "GLTF", "can_import": True, "can_export": True},
    ]
    new_caps = pass3_new_capabilities(knowledge_dir, current_api, current_fmt)
    kinds = [c["kind"] for c in new_caps]
    identifiers = [c["identifier"] for c in new_caps]
    assert "format" in kinds
    assert "GLTF" in identifiers


def test_no_new_caps_returns_empty(knowledge_dir: Path) -> None:
    """Pass3 returns empty list when api_surface and formats are unchanged."""
    baseline_api = {
        "import_allowlist": ["aspose.threed"],
        "public_classes": ["Scene"],
        "format_matrix": [],
    }
    (knowledge_dir / "api_surface.json").write_text(
        json.dumps(baseline_api), encoding="utf-8"
    )
    (knowledge_dir / "formats.md").write_text(
        "| Format | Import | Export |\n|--------|--------|--------|\n| OBJ | Yes | No |\n",
        encoding="utf-8",
    )
    current_api = {
        "import_allowlist": ["aspose.threed"],
        "public_classes": ["Scene"],
        "api_identifiers": [],
    }
    current_fmt = [{"name": "OBJ", "can_import": True, "can_export": False}]
    new_caps = pass3_new_capabilities(knowledge_dir, current_api, current_fmt)
    assert new_caps == []


# ---------------------------------------------------------------------------
# _parse_formats_md
# ---------------------------------------------------------------------------


def test_parse_formats_md_extracts_names(knowledge_dir: Path) -> None:
    md = "| Format | Import | Export |\n|--------|--------|--------|\n| OBJ | Yes | No |\n| FBX | Yes | Yes |\n"
    (knowledge_dir / "formats.md").write_text(md, encoding="utf-8")
    result = _parse_formats_md(knowledge_dir / "formats.md")
    assert "OBJ" in result
    assert "FBX" in result


def test_parse_formats_md_missing_returns_empty(knowledge_dir: Path) -> None:
    result = _parse_formats_md(knowledge_dir / "formats.md")
    assert result == set()


# ---------------------------------------------------------------------------
# compute_drift_status
# ---------------------------------------------------------------------------


def test_no_baseline_returns_new_product() -> None:
    status = compute_drift_status(False, [], [], [])
    assert status == "new_product"


def test_stale_claims_returns_major() -> None:
    stale = [{"claim_id": "CLM-001", "reason": "source_deleted", "affected_pages": []}]
    status = compute_drift_status(True, stale, [], [])
    assert status == "major"


def test_outdated_code_returns_major() -> None:
    outdated = [{"content_path": "kb.aspose.org/3d/python/howto.md", "page_role": "howto_article", "issues": []}]
    status = compute_drift_status(True, [], [], outdated)
    assert status == "major"


def test_new_caps_only_returns_minor() -> None:
    caps = [{"kind": "format", "identifier": "GLTF", "source_file": "", "suggested_page_roles": []}]
    status = compute_drift_status(True, [], caps, [])
    assert status == "minor"


def test_no_changes_returns_clean() -> None:
    status = compute_drift_status(True, [], [], [])
    assert status == "clean"


# ---------------------------------------------------------------------------
# compute_page_drift_actions
# ---------------------------------------------------------------------------


def test_no_changes_returns_no_change_decision() -> None:
    content_index = {
        "pages": [
            {
                "content_path": "kb.aspose.org/3d/python/howto.md",
                "page_role": "howto_article",
                "status": "live",
            }
        ]
    }
    actions = compute_page_drift_actions(content_index, [], [], [])
    assert actions["kb.aspose.org/3d/python/howto.md"] == "no-change"


def test_outdated_code_returns_update_decision() -> None:
    content_index = {
        "pages": [
            {
                "content_path": "kb.aspose.org/3d/python/howto.md",
                "page_role": "howto_article",
                "status": "live",
            }
        ]
    }
    outdated = [{"content_path": "kb.aspose.org/3d/python/howto.md", "page_role": "howto_article", "issues": []}]
    actions = compute_page_drift_actions(content_index, [], [], outdated)
    assert actions["kb.aspose.org/3d/python/howto.md"] == "update"


def test_new_caps_returns_enhance_decision() -> None:
    content_index = {
        "pages": [
            {
                "content_path": "kb.aspose.org/3d/python/howto.md",
                "page_role": "howto_article",
                "status": "live",
            }
        ]
    }
    caps = [{"kind": "format", "identifier": "GLTF", "source_file": "", "suggested_page_roles": []}]
    actions = compute_page_drift_actions(content_index, [], caps, [])
    assert actions["kb.aspose.org/3d/python/howto.md"] == "enhance"


def test_missing_page_not_in_actions() -> None:
    """Pages not in content_index (status != live) are not in the actions dict."""
    content_index: dict = {"pages": []}
    actions = compute_page_drift_actions(content_index, [], [], [])
    assert actions == {}


# ---------------------------------------------------------------------------
# write_drift_baseline
# ---------------------------------------------------------------------------


def test_write_drift_baseline_creates_file(knowledge_dir: Path) -> None:
    if not HAS_YAML:
        pytest.skip("pyyaml not installed")

    claims = [
        {
            "claim_id": "CLM-001",
            "text": "Supports FBX",
            "evidence": [{"source_file": "src/fbx.py"}],
        }
    ]
    fmt_matrix = [{"name": "FBX", "can_import": True, "can_export": True}]
    write_drift_baseline(knowledge_dir, "3d", "python", "abc123", claims, fmt_matrix)

    baseline_path = knowledge_dir / "drift_baseline.yaml"
    assert baseline_path.exists()

    import yaml
    data = yaml.safe_load(baseline_path.read_text(encoding="utf-8"))
    assert data["family"] == "3d"
    assert data["platform"] == "python"
    assert data["repo_sha_at_verify"] == "abc123"
    assert "CLM-001" in data["claim_fingerprints"]
    assert "FBX" in data["format_fingerprints"]
