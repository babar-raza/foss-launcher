"""Tests for sentence_openings check (TC-PROSE-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.sentence_openings import check_sentence_openings


class TestSentenceOpenings:
    def test_varied_openings_pass(self):
        content = (
            "---\ntitle: Test\n---\n"
            "Load the file using Scene.from_file(). "
            "The method returns a Scene object. "
            "Each node in the scene represents a 3D entity. "
            "You can traverse nodes with child_nodes.\n"
        )
        findings = check_sentence_openings(content, "test-page")
        assert len(findings) == 0

    def test_three_consecutive_same_opening_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "The library supports OBJ format. "
            "The library supports STL format. "
            "The library supports glTF format. "
            "The library supports FBX format.\n"
        )
        findings = check_sentence_openings(content, "test-page")
        assert len(findings) >= 1
        assert findings[0].check == "sentence_openings"
        assert findings[0].severity == "medium"

    def test_you_can_repetition_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "You can load files from disk. "
            "You can save to multiple formats. "
            "You can traverse the scene graph. "
            "You can apply materials to nodes.\n"
        )
        findings = check_sentence_openings(content, "test-page")
        assert len(findings) >= 1

    def test_reference_role_exempt(self):
        content = (
            "---\ntitle: Test\n---\n"
            "The method loads data. "
            "The method saves data. "
            "The method returns a result.\n"
        )
        findings = check_sentence_openings(content, "test-page", page_role="api_reference")
        assert len(findings) == 0

    def test_short_content_passes(self):
        content = "---\ntitle: Test\n---\nJust one sentence here.\n"
        findings = check_sentence_openings(content, "test-page")
        assert len(findings) == 0

    def test_code_blocks_excluded(self):
        content = (
            "---\ntitle: Test\n---\n"
            "```python\nThe library loads data.\nThe library saves data.\n"
            "The library processes data.\n```\n"
            "This example shows basic usage.\n"
        )
        findings = check_sentence_openings(content, "test-page")
        assert len(findings) == 0
