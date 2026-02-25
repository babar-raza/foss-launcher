"""Tests for template versioning (TC-2509 / TC-2510 / TC-2511).

Covers:
- Versioned template directory existence and content
- resolve_templates_root versioned-path resolution
- Strict mode enforcement
- Deprecation warning on legacy fallback
- Legacy fallback path correctness
- Subdomain completeness in versioned directory
"""
from __future__ import annotations

import logging
import warnings
from pathlib import Path

import pytest

from src.launch.content.template_registry import resolve_templates_root

# Repo root: three levels up from tests/unit/content/
REPO_ROOT = Path(__file__).parent.parent.parent.parent

# Expected subdomain directories inside templates.v1
_EXPECTED_SUBDOMAINS = frozenset({
    "docs.aspose.org",
    "kb.aspose.org",
    "products.aspose.org",
})


# ── TC-2509: Versioned directory exists ──────────────────────────────────────


def test_versioned_dir_exists():
    """specs/templates/templates.v1/ exists and contains files."""
    versioned = REPO_ROOT / "specs" / "templates" / "templates.v1"
    assert versioned.is_dir(), f"Expected versioned dir at {versioned}"
    files = list(versioned.rglob("*"))
    assert len(files) > 0, "Versioned template dir is empty"


def test_versioned_dir_has_all_subdomains():
    """templates.v1/ contains docs.aspose.org/, kb.aspose.org/, products.aspose.org/."""
    versioned = REPO_ROOT / "specs" / "templates" / "templates.v1"
    actual_dirs = {p.name for p in versioned.iterdir() if p.is_dir()}
    for subdomain in _EXPECTED_SUBDOMAINS:
        assert subdomain in actual_dirs, (
            f"Missing subdomain dir {subdomain} in {versioned}. "
            f"Found: {sorted(actual_dirs)}"
        )


def test_versioned_dir_excludes_disabled():
    """DISABLED directories must not be copied into templates.v1/."""
    versioned = REPO_ROOT / "specs" / "templates" / "templates.v1"
    for child in versioned.iterdir():
        assert "DISABLED" not in child.name, (
            f"Disabled dir leaked into versioned templates: {child.name}"
        )


# ── TC-2510: resolve_templates_root behavior ────────────────────────────────


def test_resolve_returns_versioned_path():
    """When versioned dir exists, resolve_templates_root() returns it."""
    result = resolve_templates_root(REPO_ROOT, "templates.v1")
    expected = REPO_ROOT / "specs" / "templates" / "templates.v1"
    assert result == expected


def test_resolve_versioned_logs_debug(caplog):
    """Versioned resolution emits a DEBUG log with versioned=True."""
    with caplog.at_level(logging.DEBUG, logger="src.launch.content.template_registry"):
        resolve_templates_root(REPO_ROOT, "templates.v1")
    assert "template_root_resolved" in caplog.text
    assert "versioned=True" in caplog.text


def test_strict_mode_raises_when_missing(tmp_path, monkeypatch):
    """LAUNCH_TEMPLATE_STRICT=1 raises FileNotFoundError when versioned dir absent."""
    monkeypatch.setenv("LAUNCH_TEMPLATE_STRICT", "1")
    templates = tmp_path / "specs" / "templates"
    templates.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="Versioned template dir not found"):
        resolve_templates_root(tmp_path, "templates.v99")


def test_legacy_fallback_emits_deprecation_warning(tmp_path, monkeypatch):
    """When versioned dir is missing, a DeprecationWarning is emitted."""
    monkeypatch.delenv("LAUNCH_TEMPLATE_STRICT", raising=False)
    templates = tmp_path / "specs" / "templates"
    templates.mkdir(parents=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolve_templates_root(tmp_path, "templates.v99")
    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert len(deprecation_warnings) == 1, (
        f"Expected exactly 1 DeprecationWarning, got {len(deprecation_warnings)}"
    )
    assert "Legacy template root fallback" in str(deprecation_warnings[0].message)


def test_legacy_fallback_returns_legacy_path(tmp_path, monkeypatch):
    """When versioned dir is missing, returns specs/templates/ as fallback."""
    monkeypatch.delenv("LAUNCH_TEMPLATE_STRICT", raising=False)
    templates = tmp_path / "specs" / "templates"
    templates.mkdir(parents=True)
    result = resolve_templates_root(tmp_path, "templates.v99")
    assert result == templates


def test_no_deprecation_warning_when_versioned_exists(monkeypatch):
    """No DeprecationWarning when versioned dir exists (happy path)."""
    monkeypatch.delenv("LAUNCH_TEMPLATE_STRICT", raising=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolve_templates_root(REPO_ROOT, "templates.v1")
    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert len(deprecation_warnings) == 0, (
        f"Unexpected DeprecationWarning on versioned path: {deprecation_warnings}"
    )
