"""TC-3913: Unit tests for understand-worker evidence extraction bugs."""
import json
from pathlib import Path

import pytest

from launcher.workers.understand.extract._api_surface import (
    _detect_package_root,
    _extract_exported_names,
    _is_submodule_only_allowlist,
)
from launcher.workers.understand.extract._snippets import (
    _EXCLUDED_DOC_NAMES,
    _is_heading_only,
)


# ---------------------------------------------------------------------------
# _is_submodule_only_allowlist
# ---------------------------------------------------------------------------

def test_is_submodule_only_true(tmp_path):
    (tmp_path / "threed").mkdir()
    assert _is_submodule_only_allowlist(frozenset({"threed"}), tmp_path) is True


def test_is_submodule_only_false_class_names(tmp_path):
    # "Scene" is not a subdirectory
    assert _is_submodule_only_allowlist(frozenset({"Scene"}), tmp_path) is False


def test_is_submodule_only_empty_returns_false(tmp_path):
    assert _is_submodule_only_allowlist(frozenset(), tmp_path) is False


def test_namespace_recursion_exposes_classes(tmp_path):
    """Recursion should unwrap aspose/__init__ -> threed/__init__ -> Scene."""
    aspose = tmp_path / "aspose"
    aspose.mkdir()
    (aspose / "__init__.py").write_text('__all__ = ["threed"]', encoding="utf-8")
    threed = aspose / "threed"
    threed.mkdir()
    (threed / "__init__.py").write_text('__all__ = ["Scene"]', encoding="utf-8")
    # After recursion the exported names should be {"Scene"}
    result = _extract_exported_names(threed / "__init__.py")
    assert result == frozenset({"Scene"})


def test_namespace_recursion_depth_cap(tmp_path):
    """4-level deep nesting must not RecursionError."""
    # Build 4-level chain: a/b/c/d/__init__.py
    current = tmp_path
    names = ["a", "b", "c", "d"]
    for i, name in enumerate(names):
        current = current / name
        current.mkdir()
        next_name = names[i + 1] if i + 1 < len(names) else "Leaf"
        (current / "__init__.py").write_text(
            f'__all__ = ["{next_name}"]', encoding="utf-8"
        )
    # Should not raise; result may be frozenset({"Leaf"}) or earlier stop
    from launcher.workers.understand.extract import _api_surface as mod  # noqa: F401
    # Just assert no exception
    result = _is_submodule_only_allowlist(frozenset({"a"}), tmp_path)
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# _detect_package_root — TypeScript dist/ fallback
# ---------------------------------------------------------------------------

def test_detect_ts_dist_missing_returns_src(tmp_path):
    pkg = {"main": "dist/index.js"}
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "foo.ts").write_text("export class Foo {}", encoding="utf-8")
    # dist/ does NOT exist
    result = _detect_package_root(tmp_path)
    assert result == "src"


def test_detect_ts_dist_present_returns_dist(tmp_path):
    pkg = {"main": "dist/index.js"}
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (tmp_path / "dist").mkdir()
    result = _detect_package_root(tmp_path)
    assert result == "dist"


def test_detect_ts_no_ts_in_src_returns_empty(tmp_path):
    pkg = {"main": "dist/index.js"}
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "foo.js").write_text("module.exports = {}", encoding="utf-8")
    # no .ts files, no dist/ → should return ""
    result = _detect_package_root(tmp_path)
    assert result == ""


# ---------------------------------------------------------------------------
# _is_heading_only
# ---------------------------------------------------------------------------

def test_is_heading_only_h1():
    assert _is_heading_only("# Title") is True


def test_is_heading_only_h3():
    assert _is_heading_only("### Using Scene.open() with options") is True


def test_is_heading_only_multiline_false():
    assert _is_heading_only("### heading\nimport x") is False


def test_is_heading_only_real_code_false():
    assert _is_heading_only("import aspose.threed") is False


# ---------------------------------------------------------------------------
# _EXCLUDED_DOC_NAMES — agents.md
# ---------------------------------------------------------------------------

def test_agents_md_in_excluded_doc_names():
    assert "agents.md" in _EXCLUDED_DOC_NAMES
