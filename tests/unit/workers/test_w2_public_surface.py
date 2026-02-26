"""Phase 1: Tests for W2 public_surface confidence/source heuristics.

Covers:
- __all__ in root __init__.py → confidence="high", source="__all__"
- No __all__ but classes present → confidence="medium", source="underscore_convention"
- No classes at all → confidence="unknown", source="none"
- _build_export_reachability() unit tests
- Backward compatibility: medium confidence preserves existing filtering
"""

from __future__ import annotations

import ast
import json
import tempfile
import pytest
from pathlib import Path
from typing import Dict, List

from src.launch.workers.w2_facts_builder.code_analyzer import (
    build_api_inventory,
    _build_export_reachability,
)


# ---------------------------------------------------------------------------
# _build_export_reachability tests
# ---------------------------------------------------------------------------

class TestBuildExportReachability:
    """Tests for _build_export_reachability helper."""

    def test_empty_init_exports(self) -> None:
        symbols, source = _build_export_reachability({}, None, Path("/fake"), [])
        assert symbols == set()
        assert source == "none"

    def test_root_with_all(self, tmp_path: Path) -> None:
        """Root __init__.py with __all__ → high confidence, only __all__ symbols."""
        init = tmp_path / "pkg" / "__init__.py"
        init.parent.mkdir(parents=True, exist_ok=True)
        init.write_text('__all__ = ["Scene", "Mesh"]\n', encoding="utf-8")

        init_exports = {"pkg": ["Scene", "Mesh"]}
        symbols, source = _build_export_reachability(
            init_exports, [init], tmp_path, [""],
        )
        assert source == "__all__"
        assert symbols == {"Scene", "Mesh"}

    def test_root_without_all_unions_imports(self, tmp_path: Path) -> None:
        """Root __init__.py without __all__ → underscore_convention."""
        init = tmp_path / "pkg" / "__init__.py"
        init.parent.mkdir(parents=True, exist_ok=True)
        init.write_text("from .scene import Scene\n", encoding="utf-8")

        init_exports = {"pkg": ["scene"]}
        symbols, source = _build_export_reachability(
            init_exports, [init], tmp_path, [""],
        )
        assert source == "underscore_convention"
        assert symbols == {"scene"}

    def test_nested_init_exports(self, tmp_path: Path) -> None:
        """Multiple __init__.py files without root __all__ → unions all exports."""
        root_init = tmp_path / "pkg" / "__init__.py"
        sub_init = tmp_path / "pkg" / "sub" / "__init__.py"
        root_init.parent.mkdir(parents=True, exist_ok=True)
        sub_init.parent.mkdir(parents=True, exist_ok=True)
        root_init.write_text("from .sub import SubClass\n", encoding="utf-8")
        sub_init.write_text('__all__ = ["SubClass"]\n', encoding="utf-8")

        init_exports = {"pkg": ["sub"], "pkg.sub": ["SubClass"]}
        symbols, source = _build_export_reachability(
            init_exports, [root_init, sub_init], tmp_path, [""],
        )
        # Root has no __all__, so falls back to union
        assert source == "underscore_convention"
        assert "sub" in symbols
        assert "SubClass" in symbols


# ---------------------------------------------------------------------------
# build_api_inventory confidence/source tests
# ---------------------------------------------------------------------------

class TestPublicSurfaceConfidence:
    """Tests for confidence and source fields in build_api_inventory output."""

    def test_all_export_high_confidence(self, tmp_path: Path) -> None:
        """__all__ in root __init__.py → confidence='high', source='__all__'."""
        init = tmp_path / "pkg" / "__init__.py"
        init.parent.mkdir(parents=True, exist_ok=True)
        init.write_text('__all__ = ["Scene", "Mesh"]\n', encoding="utf-8")

        code_analysis = {
            "api_surface": {
                "classes": [
                    {"name": "Scene", "module": "pkg.scene", "methods": [], "bases": []},
                    {"name": "Mesh", "module": "pkg.mesh", "methods": [], "bases": []},
                    {"name": "_Internal", "module": "pkg._internal", "methods": [], "bases": []},
                ],
                "functions": ["create_scene", "_helper"],
                "modules": ["pkg"],
            },
            "code_structure": {"package_names": ["test-pkg"]},
            "metadata": {},
        }
        result = build_api_inventory(
            code_analysis, tmp_path, [""], source_files=[init],
        )
        ps = result["public_surface"]
        assert ps["confidence"] == "high"
        assert ps["source"] == "__all__"
        # public_surface.classes now stores import paths (e.g. "pkg.Scene")
        assert any("Scene" in c for c in ps["classes"])
        assert any("Mesh" in c for c in ps["classes"])
        assert not any("_Internal" in c for c in ps["classes"])

    def test_no_all_medium_confidence(self, tmp_path: Path) -> None:
        """No __all__ but classes present → confidence='medium'."""
        init = tmp_path / "pkg" / "__init__.py"
        init.parent.mkdir(parents=True, exist_ok=True)
        init.write_text("from .scene import Scene\n", encoding="utf-8")

        code_analysis = {
            "api_surface": {
                "classes": [
                    {"name": "Scene", "module": "pkg.scene", "methods": [], "bases": []},
                    {"name": "_Private", "module": "pkg._priv", "methods": [], "bases": []},
                ],
                "functions": [],
                "modules": ["pkg"],
            },
            "code_structure": {"package_names": ["test-pkg"]},
            "metadata": {},
        }
        result = build_api_inventory(
            code_analysis, tmp_path, [""], source_files=[init],
        )
        ps = result["public_surface"]
        assert ps["confidence"] == "medium"
        assert ps["source"] == "underscore_convention"

    def test_no_classes_unknown_confidence(self, tmp_path: Path) -> None:
        """No classes at all → confidence='unknown'."""
        code_analysis = {
            "api_surface": {
                "classes": [],
                "functions": [],
                "modules": ["pkg"],
            },
            "code_structure": {"package_names": ["test-pkg"]},
            "metadata": {},
        }
        result = build_api_inventory(code_analysis, tmp_path, [""])
        ps = result["public_surface"]
        assert ps["confidence"] == "unknown"
        assert ps["source"] == "none"

    def test_no_init_files_unknown_confidence(self, tmp_path: Path) -> None:
        """No __init__.py files but classes exist → unknown (no export signal)."""
        code_analysis = {
            "api_surface": {
                "classes": [
                    {"name": "MyClass", "module": "pkg", "methods": [], "bases": []},
                ],
                "functions": [],
                "modules": ["pkg"],
            },
            "code_structure": {"package_names": ["test-pkg"]},
            "metadata": {},
        }
        result = build_api_inventory(code_analysis, tmp_path, [""])
        ps = result["public_surface"]
        assert ps["confidence"] == "unknown"
        assert ps["source"] == "none"  # no init exports
        # public_surface.classes stores import paths; short name still findable
        assert any("MyClass" in c for c in ps["classes"])

    def test_backward_compat_underscore_filtering(self, tmp_path: Path) -> None:
        """Underscore convention filtering applies even without init exports."""
        code_analysis = {
            "api_surface": {
                "classes": [
                    {"name": "Public", "module": "pkg", "methods": [], "bases": []},
                    {"name": "_Internal", "module": "pkg", "methods": [], "bases": []},
                ],
                "functions": ["public_func", "_private_func"],
                "modules": ["pkg"],
            },
            "code_structure": {"package_names": ["test-pkg"]},
            "metadata": {},
        }
        result = build_api_inventory(code_analysis, tmp_path, [""])
        ps = result["public_surface"]
        # public_surface.classes stores import paths; check by short name suffix
        assert any("Public" in c for c in ps["classes"])
        assert not any("_Internal" in c for c in ps["classes"])
        assert "public_func" in ps["functions"]
        assert "_private_func" not in ps["functions"]
