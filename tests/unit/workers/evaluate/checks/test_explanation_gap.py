"""Tests for explanation_gap check (TC-PROSE-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.explanation_gap import check_explanation_gap


class TestExplanationGap:
    def test_well_explained_code_passes(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Loading Files\n\n"
            "Load a 3D model from disk using the Scene class. "
            "This method accepts OBJ, STL, and glTF file formats and returns a complete scene graph.\n\n"
            "```python\nfrom aspose_3d import Scene\nscene = Scene.from_file('model.obj')\n```\n\n"
            "The code above loads an OBJ file and creates a Scene object "
            "containing all nodes, meshes, and materials from the file.\n"
        )
        findings = check_explanation_gap(content, "test-page", page_role="howto_article")
        assert len(findings) == 0

    def test_naked_code_block_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Example\n\n"
            "```python\nfrom aspose_3d import Scene\nscene = Scene.from_file('model.obj')\n```\n\n"
        )
        findings = check_explanation_gap(content, "test-page", page_role="howto_article")
        assert len(findings) == 1
        assert findings[0].check == "explanation_gap"
        assert findings[0].severity == "medium"

    def test_reference_role_gets_low_severity(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Example\n\n"
            "```python\nscene = Scene()\n```\n\n"
        )
        findings = check_explanation_gap(content, "test-page", page_role="reference_object_page")
        assert len(findings) == 1
        assert findings[0].severity == "low"

    def test_code_with_only_before_context_passes(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Loading\n\n"
            "Load the model file from disk. This demonstrates the basic loading workflow "
            "with automatic format detection enabled.\n\n"
            "```python\nscene = Scene.from_file('model.obj')\n```\n"
        )
        findings = check_explanation_gap(content, "test-page", page_role="howto_article")
        assert len(findings) == 0

    def test_no_code_blocks_passes(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "This library provides 3D file processing capabilities.\n"
        )
        findings = check_explanation_gap(content, "test-page", page_role="howto_article")
        assert len(findings) == 0
