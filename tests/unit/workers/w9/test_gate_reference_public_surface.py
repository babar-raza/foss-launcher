"""Phase 1: Tests for Gate — Reference Public Surface Boundary.

Covers:
- Graceful skip when artifacts missing
- Graceful skip when confidence is "unknown"
- Graceful skip when public_surface is empty
- All public references → pass
- Non-public class reference → profile-aware severity
- Non-public function reference → flagged
- Mixed public/private → only non-public flagged
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_reference_public_surface import (
    execute_gate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(run_dir: Path, rel_path: str, data: dict) -> None:
    """Write a JSON file relative to run_dir."""
    fp = run_dir / rel_path
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data), encoding="utf-8")


def _sample_inventory(
    classes=("Scene", "Mesh"),
    functions=("load_file",),
    confidence="high",
    source="__all__",
    use_import_paths=True,
) -> dict:
    # public_surface.classes stores import paths (e.g. "aspose.threed.Scene") by default
    if use_import_paths:
        ps_classes = [f"aspose.threed.{c}" for c in classes]
    else:
        ps_classes = list(classes)
    return {
        "package_name": "aspose-3d",
        "classes": [{"name": c, "import_path": f"aspose.threed.{c}", "methods": []} for c in classes],
        "functions": list(functions),
        "modules": ["aspose.threed"],
        "public_surface": {
            "classes": ps_classes,
            "functions": list(functions),
            "confidence": confidence,
            "source": source,
        },
    }


def _sample_page_plan(pages: list) -> dict:
    return {"pages": pages}


def _ref_page(object_name: str, object_kind: str = "class") -> dict:
    return {
        "slug": f"{object_name.lower()}-reference",
        "section": "reference",
        "page_role": "reference_object_page",
        "object_name": object_name,
        "object_kind": object_kind,
    }


# ---------------------------------------------------------------------------
# Graceful skips
# ---------------------------------------------------------------------------

class TestGracefulSkips:
    """Gate passes gracefully when artifacts are missing or confidence is low."""

    def test_no_api_inventory(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_no_page_plan(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_unknown_confidence(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/api_inventory.json",
                    _sample_inventory(confidence="unknown", source="none"))
        _write_json(tmp_path, "artifacts/page_plan.json",
                    _sample_page_plan([_ref_page("_Internal")]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_empty_public_surface(self, tmp_path: Path) -> None:
        inv = _sample_inventory()
        inv["public_surface"]["classes"] = []
        inv["public_surface"]["functions"] = []
        _write_json(tmp_path, "artifacts/api_inventory.json", inv)
        _write_json(tmp_path, "artifacts/page_plan.json",
                    _sample_page_plan([_ref_page("Scene")]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_corrupted_inventory(self, tmp_path: Path) -> None:
        arts = tmp_path / "artifacts"
        arts.mkdir(parents=True, exist_ok=True)
        (arts / "api_inventory.json").write_text("BROKEN", encoding="utf-8")
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True


# ---------------------------------------------------------------------------
# Public references → pass
# ---------------------------------------------------------------------------

class TestPublicReferences:
    """All reference pages for public symbols → gate passes."""

    def test_all_public_classes(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            _ref_page("Scene"),
            _ref_page("Mesh"),
        ]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_public_function(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            _ref_page("load_file", "function"),
        ]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_non_reference_pages_ignored(self, tmp_path: Path) -> None:
        """Pages with non-reference roles are not checked."""
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            {
                "slug": "intro",
                "section": "docs",
                "page_role": "landing_page",
                "object_name": "_Internal",
            },
        ]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []


# ---------------------------------------------------------------------------
# Non-public references → profile-aware severity
# ---------------------------------------------------------------------------

class TestNonPublicReferences:
    """Reference pages for non-public symbols produce profile-aware issues."""

    def test_private_class_warn_local(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            _ref_page("_InternalHelper"),
        ]))
        passed, issues = execute_gate(tmp_path, "local")
        assert passed is True  # warn doesn't fail
        assert len(issues) == 1
        assert issues[0]["severity"] == "warn"

    def test_private_class_error_ci(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            _ref_page("_InternalHelper"),
        ]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"

    def test_private_class_blocker_prod(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            _ref_page("_InternalHelper"),
        ]))
        passed, issues = execute_gate(tmp_path, "prod")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "blocker"

    def test_private_function_flagged(self, tmp_path: Path) -> None:
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            _ref_page("_private_func", "function"),
        ]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert issues[0]["error_code"] == "GATE_REF_PUBLIC_SURFACE_VIOLATION"

    def test_mixed_public_private(self, tmp_path: Path) -> None:
        """Only non-public references are flagged."""
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            _ref_page("Scene"),           # public — ok
            _ref_page("_InternalHelper"),  # not in public_surface — flagged
            _ref_page("Mesh"),            # public — ok
        ]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 1
        assert "_InternalHelper" in issues[0]["message"]

    def test_import_path_resolves_to_short_name(self, tmp_path: Path) -> None:
        """Gate resolves import paths in public_surface to match short object_name."""
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            _ref_page("Scene"),  # short name matches "aspose.threed.Scene" via rsplit
        ]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_page_without_object_name_ignored(self, tmp_path: Path) -> None:
        """Reference pages without object_name are skipped."""
        _write_json(tmp_path, "artifacts/api_inventory.json", _sample_inventory())
        _write_json(tmp_path, "artifacts/page_plan.json", _sample_page_plan([
            {
                "slug": "overview",
                "section": "reference",
                "page_role": "reference_object_page",
                # No object_name
            },
        ]))
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []
