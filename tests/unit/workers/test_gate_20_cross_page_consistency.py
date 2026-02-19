"""Tests for Gate 20: Cross-Page Consistency Check.

TC-2374 (RD-07) — Per specs/09_validation_gates.md §"Gate 20: Cross-Page Consistency".

Covers:
  - G20-001: duplicate prose block detection and clean path
  - G20-002: version contradiction detection and clean path
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
    run_gate_20,
    _find_duplicate_blocks,
    _find_version_contradictions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_pages(contents: list[str]) -> list[Path]:
    """Write markdown strings to temp files and return their Paths."""
    paths = []
    tmp = tempfile.mkdtemp()
    for i, content in enumerate(contents):
        p = Path(tmp) / f"page_{i}.md"
        p.write_text(content, encoding="utf-8")
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# G20-001: Duplicate block detection
# ---------------------------------------------------------------------------

class TestDuplicateBlockDetection:

    def test_duplicate_block_detected(self):
        """Two pages sharing a ≥ 100-char paragraph → G20-001 warn issued."""
        shared = (
            "Aspose.3D for Python provides a comprehensive API for creating, "
            "loading, and saving 3D scene files across many industry-standard formats."
        )
        assert len(shared) >= 100, "test fixture paragraph must be ≥ 100 chars"

        page_a = f"---\ntitle: Page A\n---\n\n{shared}\n\nSome unique content for A."
        page_b = f"---\ntitle: Page B\n---\n\n{shared}\n\nSome unique content for B."
        paths = _write_pages([page_a, page_b])

        gate_passed, issues = run_gate_20(paths)
        g20_001 = [i for i in issues if i["error_code"] == "G20-001"]
        assert len(g20_001) >= 1, f"Expected at least 1 G20-001 issue, got {issues}"
        # Duplicate warn must not fail the gate
        assert gate_passed is True, "Gate should PASS (warn-only) on duplicate block"

    def test_duplicate_block_clean(self):
        """Two pages with entirely unique paragraphs → no G20-001 issues."""
        page_a = (
            "---\ntitle: Page A\n---\n\n"
            "The Scene class manages all 3D objects and camera settings in the workspace.\n\n"
            "Use the load() method to import FBX or OBJ files from your local filesystem."
        )
        page_b = (
            "---\ntitle: Page B\n---\n\n"
            "The Mesh class represents a polygon mesh with vertices, edges, and faces.\n\n"
            "Call render() to produce a bitmap from the current scene viewpoint."
        )
        paths = _write_pages([page_a, page_b])

        gate_passed, issues = run_gate_20(paths)
        g20_001 = [i for i in issues if i["error_code"] == "G20-001"]
        assert len(g20_001) == 0, f"Expected no G20-001 issues, got {g20_001}"


# ---------------------------------------------------------------------------
# G20-002: Version contradiction
# ---------------------------------------------------------------------------

class TestVersionContradiction:

    def test_version_contradiction_detected(self):
        """Pages requiring Python 3.8 vs Python 3.11 → G20-002 error, gate FAILS."""
        page_a = (
            "---\ntitle: Install\n---\n\n"
            "Aspose.3D for Python requires Python 3.8 or later to be installed."
        )
        page_b = (
            "---\ntitle: Requirements\n---\n\n"
            "This library requires Python 3.11 or higher on your system."
        )
        paths = _write_pages([page_a, page_b])

        gate_passed, issues = run_gate_20(paths)
        g20_002 = [i for i in issues if i["error_code"] == "G20-002"]
        assert len(g20_002) >= 1, f"Expected at least 1 G20-002 issue, got {issues}"
        assert gate_passed is False, "Gate should FAIL when G20-002 error is raised"

    def test_version_no_contradiction(self):
        """Pages with consistent Python 3.9 requirement → no G20-002 issues, gate PASSES."""
        page_a = (
            "---\ntitle: Install\n---\n\n"
            "Aspose.3D for Python requires Python 3.9 or later."
        )
        page_b = (
            "---\ntitle: Quickstart\n---\n\n"
            "Ensure Python 3.9 is installed before running pip install."
        )
        paths = _write_pages([page_a, page_b])

        gate_passed, issues = run_gate_20(paths)
        g20_002 = [i for i in issues if i["error_code"] == "G20-002"]
        assert len(g20_002) == 0, f"Expected no G20-002 issues, got {g20_002}"
        assert gate_passed is True, "Gate should PASS when versions are consistent"
