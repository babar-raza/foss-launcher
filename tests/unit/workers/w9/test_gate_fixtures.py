"""Integration tests using checked-in lean and advanced validation run fixtures.

Exercises gates 29–33 against both fixture profiles to verify end-to-end
Spec v1.1 enforcement on realistic artifact trees.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_blog_mandatory import (
    execute_gate as gate_blog_mandatory,
)
from src.launch.workers.w9_validator.gates.gate_kb_howto_mandatory import (
    execute_gate as gate_kb_howto_mandatory,
)
from src.launch.workers.w9_validator.gates.gate_reference_objects import (
    execute_gate as gate_reference_objects,
)
from src.launch.workers.w9_validator.gates.gate_kb_howto_structure import (
    execute_gate as gate_kb_howto_structure,
)
from src.launch.workers.w9_validator.gates.gate_kb_howto_evidence import (
    execute_gate as gate_kb_howto_evidence,
)


_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
_LEAN = _FIXTURES / "lean_validation_run"
_ADVANCED = _FIXTURES / "advanced_validation_run"


# ---------------------------------------------------------------------------
# Precondition: fixtures exist
# ---------------------------------------------------------------------------


class TestFixturesExist:
    """Sanity check that checked-in fixture dirs are present."""

    def test_lean_fixture_exists(self):
        assert _LEAN.is_dir(), f"Missing fixture: {_LEAN}"
        assert (_LEAN / "artifacts" / "page_plan.json").is_file()
        assert (_LEAN / "artifacts" / "product_facts.json").is_file()

    def test_advanced_fixture_exists(self):
        assert _ADVANCED.is_dir(), f"Missing fixture: {_ADVANCED}"
        assert (_ADVANCED / "artifacts" / "page_plan.json").is_file()
        assert (_ADVANCED / "artifacts" / "product_facts.json").is_file()

    def test_lean_has_kb_drafts(self):
        kb_dir = _LEAN / "drafts" / "kb"
        assert kb_dir.is_dir()
        assert len(list(kb_dir.glob("*.md"))) == 5

    def test_advanced_has_kb_drafts(self):
        kb_dir = _ADVANCED / "drafts" / "kb"
        assert kb_dir.is_dir()
        assert len(list(kb_dir.glob("*.md"))) == 5


# ---------------------------------------------------------------------------
# Lean fixture tests (sparse evidence, not-evidenced drafts)
# ---------------------------------------------------------------------------


class TestLeanFixture:
    """Lean fixture: sparse evidence, all how-to pages use not-evidenced fallback."""

    def test_kb_howto_mandatory_passes(self):
        """gate_30: KB section has all 5 mandatory how-to slugs."""
        ok, issues = gate_kb_howto_mandatory(_LEAN, "local")
        assert ok is True
        error_issues = [i for i in issues if i.get("severity") == "error"]
        assert len(error_issues) == 0

    def test_blog_mandatory_passes(self):
        """gate_29: Blog section has both blog + feature_blog roles."""
        ok, issues = gate_blog_mandatory(_LEAN, "local")
        assert ok is True

    def test_kb_howto_structure_passes(self):
        """gate_32: All drafts exist with correct heading order, no FQ-1."""
        ok, issues = gate_kb_howto_structure(_LEAN, "local")
        assert ok is True
        error_issues = [i for i in issues if i.get("severity") == "error"]
        assert len(error_issues) == 0

    def test_kb_howto_evidence_passes(self):
        """gate_33: No format hallucinations (empty supported_formats)."""
        ok, issues = gate_kb_howto_evidence(_LEAN, "local")
        assert ok is True
        # With empty supported_formats in product_facts, nothing to compare
        warn_issues = [i for i in issues if i.get("severity") == "warn"]
        assert len(warn_issues) == 0

    def test_not_evidenced_content_present(self):
        """Lean drafts use not-evidenced fallback with all required headings."""
        draft = (_LEAN / "drafts" / "kb" / "how-to-open-a-file.md").read_text(
            encoding="utf-8"
        )
        assert "## Goal" in draft
        assert "## See Also" in draft
        assert "## Steps" in draft
        # Not-evidenced marker: pseudo-code comment
        assert "No working example was found" in draft


# ---------------------------------------------------------------------------
# Advanced fixture tests (rich evidence, real format drafts)
# ---------------------------------------------------------------------------


class TestAdvancedFixture:
    """Advanced fixture: rich claims, 3 supported formats, real code examples."""

    def test_kb_howto_mandatory_passes(self):
        """gate_30: KB section has all 5 mandatory how-to slugs."""
        ok, issues = gate_kb_howto_mandatory(_ADVANCED, "local")
        assert ok is True

    def test_kb_howto_structure_passes(self):
        """gate_32: All drafts exist with correct heading order."""
        ok, issues = gate_kb_howto_structure(_ADVANCED, "local")
        assert ok is True
        error_issues = [i for i in issues if i.get("severity") == "error"]
        assert len(error_issues) == 0

    def test_kb_howto_evidence_no_hallucinations(self):
        """gate_33: Conversion draft mentions only FBX, OBJ, STL — all evidenced."""
        ok, issues = gate_kb_howto_evidence(_ADVANCED, "local")
        assert ok is True
        # All formats mentioned in drafts are evidenced in product_facts
        warn_issues = [i for i in issues if i.get("severity") == "warn"]
        assert len(warn_issues) == 0

    def test_conversion_draft_has_evidenced_formats(self):
        """Conversion how-to draft mentions FBX, OBJ, STL — all from product_facts."""
        draft = (_ADVANCED / "drafts" / "kb" / "how-to-convert-formats.md").read_text(
            encoding="utf-8"
        )
        assert "FBX" in draft
        assert "OBJ" in draft
        assert "STL" in draft

    def test_conversion_draft_has_code_fence(self):
        """Conversion how-to has a python code block with real API calls."""
        draft = (_ADVANCED / "drafts" / "kb" / "how-to-convert-formats.md").read_text(
            encoding="utf-8"
        )
        assert "```python" in draft
        assert "scene.save(" in draft or "scene.open(" in draft

    def test_advanced_product_facts_has_formats(self):
        """Product facts include 3 supported formats with directions."""
        pf = json.loads(
            (_ADVANCED / "artifacts" / "product_facts.json").read_text(encoding="utf-8")
        )
        formats = pf.get("supported_formats", [])
        assert len(formats) == 3
        format_names = sorted(f["format"] for f in formats)
        assert format_names == ["FBX", "OBJ", "STL"]

    def test_advanced_page_plan_has_conversion_page(self):
        """Page plan has a conversion how-to with is_conversion_howto flag."""
        pp = json.loads(
            (_ADVANCED / "artifacts" / "page_plan.json").read_text(encoding="utf-8")
        )
        conversion_pages = [
            p for p in pp["pages"]
            if p.get("content_strategy", {}).get("is_conversion_howto")
        ]
        assert len(conversion_pages) == 1
        assert conversion_pages[0]["slug"] == "how-to-convert-formats"

    def test_reference_objects_graceful_skip(self):
        """gate_31: Graceful skip when no reference pages in fixture page_plan."""
        ok, issues = gate_reference_objects(_ADVANCED, "local")
        # Advanced fixture has no reference section pages — graceful skip
        assert ok is True
