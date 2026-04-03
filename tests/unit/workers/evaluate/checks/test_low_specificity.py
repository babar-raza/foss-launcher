"""Tests for low_specificity check (TC-PROSE-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.low_specificity import check_low_specificity


class TestLowSpecificity:
    def test_specific_prose_passes(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Loading\n\n"
            "Load OBJ files using `Scene.from_file()` with automatic format detection. "
            "The method returns a `Scene` object containing all nodes and meshes. "
            "Access the root node through `scene.root_node` to traverse the hierarchy.\n"
        )
        findings = check_low_specificity(content, "test-page", page_role="howto_article")
        assert len(findings) == 0

    def test_all_generic_verbs_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Features\n\n"
            "The library supports working with many different document types. "
            "It provides tools for handling various processing tasks efficiently. "
            "The system enables users to perform operations on their data easily. "
            "It also offers functionality for managing content in bulk.\n"
        )
        findings = check_low_specificity(content, "test-page", page_role="howto_article")
        assert len(findings) >= 1
        assert findings[0].check == "low_specificity"
        assert findings[0].severity == "low"

    def test_mixed_generic_and_specific_passes(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Features\n\n"
            "The library supports OBJ and STL file formats for 3D model processing. "
            "It provides the `Scene.from_file()` method for loading models from disk. "
            "The system enables batch conversion of .obj files to .stl output.\n"
        )
        findings = check_low_specificity(content, "test-page", page_role="howto_article")
        assert len(findings) == 0  # has backticked names and file extensions

    def test_reference_role_exempt(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "The class supports various operations on data elements. "
            "It provides methods for handling content processing tasks. "
            "The module enables interaction with internal structures.\n"
        )
        findings = check_low_specificity(content, "test-page", page_role="reference_object_page")
        assert len(findings) == 0

    def test_short_paragraph_not_flagged(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "The library supports various features. It provides many tools.\n"
        )
        # Only 2 sentences — below _MIN_SENTENCES threshold
        findings = check_low_specificity(content, "test-page", page_role="howto_article")
        assert len(findings) == 0

    def test_code_blocks_excluded(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Example\n\n"
            "```python\n# The library supports many formats\n"
            "# It provides tools for data handling\n"
            "# The system enables batch processing\n```\n"
        )
        findings = check_low_specificity(content, "test-page", page_role="howto_article")
        assert len(findings) == 0
