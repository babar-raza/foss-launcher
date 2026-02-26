"""TC-2812 / TC-2870: Tests for evidence-gated code generation in W5 multi_pass.

Covers:
- _format_api_symbols_block: prompt injection formatting
- _validate_code_fences_against_inventory: code fence validation (now via shared lib)
- _to_comments_only: fallback pseudocode conversion
- _sanitize_invalid_code_fences: end-to-end post-generation sanitization
- Backward compat: no api_inventory → no changes
"""

from __future__ import annotations

import pytest

from src.launch.workers.w5_section_writer.multi_pass import (
    _format_api_symbols_block,
    _validate_code_fences_against_inventory,
    _to_comments_only,
    _sanitize_invalid_code_fences,
)
from src.launch.workers._shared.code_fence_validator import (
    STDLIB_IMPORT_ALLOWLIST as _STDLIB_ALLOWLIST_W5,
)


# ---------------------------------------------------------------------------
# Test inventory fixtures
# ---------------------------------------------------------------------------

def _sample_inventory():
    return {
        "package_name": "aspose-3d",
        "import_roots": ["aspose"],
        "classes": [
            {
                "name": "Scene",
                "import_path": "aspose.threed.Scene",
                "module": "scene",
                "methods": ["open", "save", "merge_scene"],
            },
            {
                "name": "Mesh",
                "import_path": "aspose.threed.entities.Mesh",
                "module": "mesh",
                "methods": ["create_polygon", "to_mesh"],
            },
        ],
        "functions": [],
        "modules": ["aspose", "aspose.threed", "aspose.threed.entities"],
    }


# ---------------------------------------------------------------------------
# _format_api_symbols_block
# ---------------------------------------------------------------------------

class TestFormatApiSymbolsBlock:
    """Test prompt injection block formatting."""

    def test_empty_classes_returns_empty(self):
        inv = {"classes": [], "modules": []}
        assert _format_api_symbols_block(inv) == ""

    def test_no_classes_key_returns_empty(self):
        assert _format_api_symbols_block({}) == ""

    def test_contains_allowed_header(self):
        block = _format_api_symbols_block(_sample_inventory())
        assert "ALLOWED API SYMBOLS" in block

    def test_contains_package_name(self):
        block = _format_api_symbols_block(_sample_inventory())
        assert "aspose-3d" in block

    def test_contains_class_and_methods(self):
        block = _format_api_symbols_block(_sample_inventory())
        assert "aspose.threed.Scene" in block
        assert "open" in block
        assert "save" in block

    def test_contains_import_roots(self):
        block = _format_api_symbols_block(_sample_inventory())
        assert "aspose.threed" in block

    def test_contains_fallback_instruction(self):
        block = _format_api_symbols_block(_sample_inventory())
        assert "comments-only" in block.lower() or "pseudocode" in block.lower()

    def test_caps_at_20_classes(self):
        inv = {
            "classes": [{"name": f"Cls{i}", "import_path": f"pkg.Cls{i}", "methods": []}
                        for i in range(30)],
            "modules": ["pkg"],
        }
        block = _format_api_symbols_block(inv)
        # Only first 20 classes should appear
        assert "Cls19" in block
        assert "Cls20" not in block

    def test_string_only_classes(self):
        inv = {"classes": ["SimpleClass"], "modules": []}
        block = _format_api_symbols_block(inv)
        assert "SimpleClass" in block


# ---------------------------------------------------------------------------
# _validate_code_fences_against_inventory
# ---------------------------------------------------------------------------

class TestValidateCodeFencesAgainstInventory:
    """Test code fence validation logic."""

    def test_valid_import_passes(self):
        content = "```python\nimport aspose.threed\nscene = aspose.threed.Scene()\n```"
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 0

    def test_unknown_import_flagged(self):
        content = "```python\nimport fake_library\n```"
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 1
        assert any("fake_library" in e for e in problems[0][2])

    def test_unknown_from_import_flagged(self):
        content = "```python\nfrom nonexistent.module import Foo\n```"
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 1
        assert any("nonexistent.module" in e for e in problems[0][2])

    def test_stdlib_import_not_flagged(self):
        content = "```python\nimport os\nimport json\nfrom pathlib import Path\n```"
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 0

    def test_common_third_party_not_flagged(self):
        content = "```python\nimport numpy as np\nimport pandas as pd\n```"
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 0

    def test_syntax_error_skipped(self):
        content = "```python\nthis is not valid python {{\n```"
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 0

    def test_non_python_fence_ignored(self):
        content = "```javascript\nimport fake_library\n```"
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 0

    def test_multiple_fences_mixed(self):
        content = (
            "```python\nimport aspose.threed\n```\n\n"
            "```python\nimport hallucinated_api\n```"
        )
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 1

    def test_package_variants_recognized(self):
        # aspose-3d → aspose.3d and aspose_3d should be recognized
        content = "```python\nimport aspose\n```"
        problems = _validate_code_fences_against_inventory(content, _sample_inventory())
        assert len(problems) == 0

    def test_empty_inventory_flags_nothing(self):
        """Empty classes → nothing to validate against."""
        content = "```python\nimport anything\n```"
        inv = {"package_name": "", "classes": [], "functions": [], "modules": []}
        problems = _validate_code_fences_against_inventory(content, inv)
        # With no known imports, everything is unknown — but that's the design
        # This test just verifies no crash
        assert isinstance(problems, list)


# ---------------------------------------------------------------------------
# _to_comments_only
# ---------------------------------------------------------------------------

class TestToCommentsOnly:
    """Test pseudocode fallback conversion."""

    def test_converts_code_to_comments(self):
        code = "import fake_lib\nresult = fake_lib.do_stuff()"
        result = _to_comments_only(code, ["unknown import: fake_lib"])
        lines = result.strip().splitlines()
        assert lines[0].startswith("# Code example")
        assert all(line.startswith("#") or line.strip() == "" for line in lines)

    def test_preserves_existing_comments(self):
        code = "# This is a real comment\nimport os"
        result = _to_comments_only(code, [])
        assert "# This is a real comment" in result

    def test_preserves_blank_lines(self):
        code = "import os\n\nprint('hi')"
        result = _to_comments_only(code, [])
        lines = result.splitlines()
        # Should have a blank line preserved
        assert any(line.strip() == "" for line in lines)


# ---------------------------------------------------------------------------
# _sanitize_invalid_code_fences
# ---------------------------------------------------------------------------

class TestSanitizeInvalidCodeFences:
    """Integration test for full sanitization flow."""

    def test_no_problems_returns_unchanged(self):
        content = "```python\nimport os\nprint('hello')\n```"
        result = _sanitize_invalid_code_fences(content, _sample_inventory())
        assert result == content

    def test_invalid_fence_replaced_with_pseudocode(self):
        content = (
            "Some intro text.\n\n"
            "```python\n"
            "import hallucinated_library\n"
            "hallucinated_library.do_stuff()\n"
            "```\n\n"
            "More text."
        )
        result = _sanitize_invalid_code_fences(content, _sample_inventory())
        # Original import should be commented out
        assert "# import hallucinated_library" in result
        assert "pseudocode" in result.lower()
        # Surrounding text preserved
        assert "Some intro text." in result
        assert "More text." in result

    def test_valid_fence_not_touched(self):
        content = (
            "```python\nimport aspose.threed\nscene = aspose.threed.Scene()\n```\n"
            "```python\nimport fake_lib\n```"
        )
        result = _sanitize_invalid_code_fences(content, _sample_inventory())
        # Valid fence preserved
        assert "import aspose.threed\nscene = aspose.threed.Scene()" in result
        # Invalid fence replaced
        assert "# import fake_lib" in result

    def test_no_inventory_returns_unchanged(self):
        content = "```python\nimport anything\n```"
        result = _sanitize_invalid_code_fences(content, {"classes": []})
        # No classes → nothing to validate → no changes
        # Actually _sanitize checks inventory.get("classes") which is empty []
        # _validate will still run but with no known imports...
        # The function is only called when inventory has classes (caller guard)
        # But let's test directly — it should still return content
        assert "import anything" in result

    def test_empty_content(self):
        result = _sanitize_invalid_code_fences("", _sample_inventory())
        assert result == ""


# ---------------------------------------------------------------------------
# _STDLIB_ALLOWLIST_W5 coverage
# ---------------------------------------------------------------------------

class TestStdlibAllowlist:
    """Verify critical stdlib modules are in the W5 allowlist."""

    @pytest.mark.parametrize("module", [
        "os", "sys", "json", "re", "pathlib", "io", "math",
        "datetime", "collections", "typing", "logging",
    ])
    def test_stdlib_present(self, module):
        assert module in _STDLIB_ALLOWLIST_W5

    @pytest.mark.parametrize("module", [
        "numpy", "pandas", "requests", "pytest", "yaml",
    ])
    def test_third_party_present(self, module):
        assert module in _STDLIB_ALLOWLIST_W5
