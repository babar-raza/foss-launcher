"""Tests for src/launch/content/template_registry.py

Covers:
- resolve_ruleset_path: real files, missing version, error message content
- resolve_templates_root: fallback to specs/templates/, versioned subdir, priority
- resolve_templates_root: strict mode raises, fallback debug logging
- _list_available_rulesets: sorted list with both known versions
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.launch.content.template_registry import (
    _list_available_rulesets,
    resolve_ruleset_path,
    resolve_templates_root,
)

# Repo root: two levels up from tests/unit/content/
REPO_ROOT = Path(__file__).parent.parent.parent.parent


# ── resolve_ruleset_path ──────────────────────────────────────────────────────


def test_resolve_ruleset_path_v1():
    """ruleset.v1.yaml is found in the real repository."""
    path = resolve_ruleset_path(REPO_ROOT, "ruleset.v1")
    assert path.exists()
    assert path.name == "ruleset.v1.yaml"


def test_resolve_ruleset_path_v1_1():
    """ruleset.v1_1.yaml is found in the real repository."""
    path = resolve_ruleset_path(REPO_ROOT, "ruleset.v1_1")
    assert path.exists()
    assert path.name == "ruleset.v1_1.yaml"


def test_resolve_ruleset_path_missing_raises():
    """FileNotFoundError is raised for an unknown ruleset version."""
    with pytest.raises(FileNotFoundError):
        resolve_ruleset_path(REPO_ROOT, "ruleset.nonexistent")


def test_resolve_ruleset_path_error_lists_available():
    """Error message includes available versions so the caller can diagnose."""
    with pytest.raises(FileNotFoundError, match="ruleset.v1"):
        resolve_ruleset_path(REPO_ROOT, "ruleset.nonexistent")


# ── resolve_templates_root ────────────────────────────────────────────────────


def test_resolve_templates_root_fallback(tmp_path):
    """Falls back to specs/templates/ when no versioned subfolder exists."""
    templates = tmp_path / "specs" / "templates"
    templates.mkdir(parents=True)
    result = resolve_templates_root(tmp_path, "templates.v1")
    assert result == templates


def test_resolve_templates_root_versioned(tmp_path):
    """Uses specs/templates/<version>/ when the versioned subfolder exists."""
    versioned = tmp_path / "specs" / "templates" / "templates.v1"
    versioned.mkdir(parents=True)
    result = resolve_templates_root(tmp_path, "templates.v1")
    assert result == versioned


def test_resolve_templates_root_v2_priority(tmp_path):
    """v2 versioned subdir takes priority; v1 (no subdir) falls back to base."""
    base = tmp_path / "specs" / "templates"
    base.mkdir(parents=True)
    v2 = base / "templates.v2"
    v2.mkdir()
    # v1: no versioned dir → fallback to base
    assert resolve_templates_root(tmp_path, "templates.v1") == base
    # v2: versioned dir present → use it
    assert resolve_templates_root(tmp_path, "templates.v2") == v2


def test_strict_mode_raises(tmp_path, monkeypatch):
    """LAUNCH_TEMPLATE_STRICT=1 raises when versioned dir is absent."""
    monkeypatch.setenv("LAUNCH_TEMPLATE_STRICT", "1")
    templates = tmp_path / "specs" / "templates"
    templates.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="Versioned template dir not found"):
        resolve_templates_root(tmp_path, "templates.v99")


def test_fallback_logs_debug(tmp_path, monkeypatch, caplog):
    """Fallback to specs/templates/ emits a DEBUG log message."""
    monkeypatch.delenv("LAUNCH_TEMPLATE_STRICT", raising=False)
    templates = tmp_path / "specs" / "templates"
    templates.mkdir(parents=True)
    with caplog.at_level(logging.DEBUG, logger="src.launch.content.template_registry"):
        result = resolve_templates_root(tmp_path, "templates.v99")
    assert result == templates
    assert "template_root_resolved" in caplog.text
    assert "versioned=False" in caplog.text


# ── _list_available_rulesets ──────────────────────────────────────────────────


def test_list_available_rulesets_sorted():
    """Returns a sorted list that includes at least the two known rulesets."""
    names = _list_available_rulesets(REPO_ROOT)
    assert "ruleset.v1" in names
    assert "ruleset.v1_1" in names
    assert names == sorted(names)
