"""Tests for W9 Gate 15 upgrade: method signature validation (TC-2370).

TC-2370: Gate 15 now also checks method-level references against code_analysis.json.
When a known class is referenced with an unknown method, a G15-002 warn is emitted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from launch.workers.w9_validator.gates.gate_15_api_hallucination import execute_gate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_dir(tmp_path: Path, md_content: str, product_facts: dict, code_analysis: dict) -> Path:
    """Create a minimal run_dir with required artifacts and one markdown file."""
    run_dir = tmp_path / "run"
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True)

    (artifacts / "product_facts.json").write_text(
        json.dumps(product_facts), encoding="utf-8"
    )
    (artifacts / "code_analysis.json").write_text(
        json.dumps(code_analysis), encoding="utf-8"
    )

    site_dir = run_dir / "work" / "site"
    site_dir.mkdir(parents=True)
    (site_dir / "page.md").write_text(md_content, encoding="utf-8")

    return run_dir


_BASE_FACTS = {
    "api_surface_summary": {
        "classes": ["Scene"],
        "modules": [],
        "functions": [],
    }
}

_BASE_ANALYSIS = {
    "classes": [
        {"name": "Scene", "methods": ["load", "save", "render"]},
    ],
    "functions": [],
}


# ---------------------------------------------------------------------------
# Test 1: Unknown method on known class → G15-002 warn
# ---------------------------------------------------------------------------

def test_unknown_method_on_known_class_warns(tmp_path):
    """Scene.nonexistent is flagged as G15-002 (method not in class_methods).

    The regex captures `ClassName.method` without call parentheses — use
    the dotted form without `()` to exercise the method check.
    """
    run_dir = _make_run_dir(
        tmp_path,
        md_content="# Guide\n\nUse `Scene.nonexistent` to do things.\n",
        product_facts=_BASE_FACTS,
        code_analysis=_BASE_ANALYSIS,
    )

    gate_passed, issues = execute_gate(run_dir, "local")

    method_issues = [i for i in issues if i.get("error_code") == "GATE15_UNKNOWN_METHOD"]
    assert len(method_issues) >= 1
    assert method_issues[0]["severity"] == "warn"
    assert "Scene" in method_issues[0]["message"]
    assert "nonexistent" in method_issues[0]["message"]
    # Gate still passes — warn only
    assert gate_passed is True


# ---------------------------------------------------------------------------
# Test 2: Known method on known class → no G15-002 issue
# ---------------------------------------------------------------------------

def test_known_method_on_known_class_passes(tmp_path):
    """Scene.load() is a real method — no G15-002 issue emitted."""
    run_dir = _make_run_dir(
        tmp_path,
        md_content="# Guide\n\nUse `Scene.load()` to load files.\n",
        product_facts=_BASE_FACTS,
        code_analysis=_BASE_ANALYSIS,
    )

    gate_passed, issues = execute_gate(run_dir, "local")

    method_issues = [i for i in issues if i.get("error_code") == "GATE15_UNKNOWN_METHOD"]
    assert len(method_issues) == 0
    assert gate_passed is True


# ---------------------------------------------------------------------------
# Test 3: code_analysis has class but no methods list → no method check
# ---------------------------------------------------------------------------

def test_dotted_no_methods_data_skips(tmp_path):
    """When code_analysis has the class but no 'methods' field, skip the check."""
    analysis_no_methods = {
        "classes": [{"name": "Scene"}],  # no "methods" key
        "functions": [],
    }
    run_dir = _make_run_dir(
        tmp_path,
        md_content="# Guide\n\nUse `Scene.anything()` here.\n",
        product_facts=_BASE_FACTS,
        code_analysis=analysis_no_methods,
    )

    gate_passed, issues = execute_gate(run_dir, "local")

    method_issues = [i for i in issues if i.get("error_code") == "GATE15_UNKNOWN_METHOD"]
    # No method list → no method check → no G15-002 issues
    assert len(method_issues) == 0
    assert gate_passed is True


# ---------------------------------------------------------------------------
# Test 4: Single symbol (no dot) → unchanged top-level check behaviour
# ---------------------------------------------------------------------------

def test_single_symbol_no_dot_unchanged(tmp_path):
    """`Scene` (no dot) uses only the class-level check — no method check triggered."""
    run_dir = _make_run_dir(
        tmp_path,
        md_content="# Guide\n\nCreate a `Scene` instance.\n",
        product_facts=_BASE_FACTS,
        code_analysis=_BASE_ANALYSIS,
    )

    gate_passed, issues = execute_gate(run_dir, "local")

    # Scene is known → no GATE15_UNRECOGNIZED_API
    class_issues = [i for i in issues if i.get("error_code") == "GATE15_UNRECOGNIZED_API"]
    assert len(class_issues) == 0
    # No dot → no method check
    method_issues = [i for i in issues if i.get("error_code") == "GATE15_UNKNOWN_METHOD"]
    assert len(method_issues) == 0
    assert gate_passed is True
