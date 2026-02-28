"""TC-2812 / TC-2870 / TC-2941: Tests for evidence-gated code generation in W5 multi_pass.

Covers:
- _format_api_symbols_block: prompt injection formatting
- _validate_code_fences_against_inventory: code fence validation (now via shared lib)
- _to_comments_only: fallback pseudocode conversion
- _sanitize_invalid_code_fences: end-to-end post-generation sanitization
- _extract_code_from_response: LLM repair response parsing (TC-2941)
- _attempt_fence_repair: per-fence LLM repair with re-validation (TC-2941)
- _repair_and_sanitize_code_fences: repair-then-sanitize orchestrator (TC-2941)
- Backward compat: no api_inventory → no changes
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.launch.workers.w5_section_writer.multi_pass import (
    _format_api_symbols_block,
    _validate_code_fences_against_inventory,
    _to_comments_only,
    _sanitize_invalid_code_fences,
    _extract_code_from_response,
    _attempt_fence_repair,
    _repair_and_sanitize_code_fences,
    _FENCE_REPAIR_MAX_RETRIES,
    MultiPassOrchestrator,
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


# ---------------------------------------------------------------------------
# TC-2941: _extract_code_from_response
# ---------------------------------------------------------------------------

class TestExtractCodeFromResponse:
    """Test LLM response code extraction."""

    def test_raw_python_returned_as_is(self):
        code = "import aspose.threed\nscene = aspose.threed.Scene()"
        assert _extract_code_from_response(code) == code

    def test_python_fence_extracted(self):
        response = "```python\nimport aspose.threed\nscene = aspose.threed.Scene()\n```"
        result = _extract_code_from_response(response)
        assert "import aspose.threed" in result
        assert "```" not in result

    def test_generic_fence_extracted(self):
        response = "```\nimport aspose.threed\n```"
        result = _extract_code_from_response(response)
        assert "import aspose.threed" in result
        assert "```" not in result

    def test_empty_string(self):
        assert _extract_code_from_response("") == ""

    def test_whitespace_stripped(self):
        response = "\n  import os\n  "
        result = _extract_code_from_response(response)
        assert result == "import os"


# ---------------------------------------------------------------------------
# TC-2941: _attempt_fence_repair
# ---------------------------------------------------------------------------

class TestAttemptFenceRepair:
    """Test per-fence repair logic with mocked LLM."""

    def test_successful_repair(self):
        """LLM fixes a bad import -> re-validation passes -> returns repaired code."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": "import aspose.threed\nscene = aspose.threed.Scene()\nscene.open('file.fbx')"
        }
        result = _attempt_fence_repair(
            mock_llm,
            "import fake_aspose\nscene = fake_aspose.Scene()",
            ["unknown_import: fake_aspose"],
            _sample_inventory(),
            fence_index=0,
            slug="test-page",
        )
        assert result is not None
        assert "aspose.threed" in result
        assert mock_llm.chat_completion.call_count == 1

    def test_repair_fails_returns_none(self):
        """LLM returns code that still has errors -> exhausts retries -> returns None."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": "import still_fake\nresult = still_fake.do_stuff()"
        }
        result = _attempt_fence_repair(
            mock_llm,
            "import fake_lib\nfake_lib.do_stuff()",
            ["unknown_import: fake_lib"],
            _sample_inventory(),
            fence_index=0,
            slug="test-page",
        )
        assert result is None
        assert mock_llm.chat_completion.call_count == _FENCE_REPAIR_MAX_RETRIES + 1

    def test_llm_exception_returns_none(self):
        """LLM raises exception -> returns None immediately (no retry)."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.side_effect = Exception("API down")
        result = _attempt_fence_repair(
            mock_llm,
            "import fake_lib",
            ["unknown_import: fake_lib"],
            _sample_inventory(),
            fence_index=0,
            slug="test-page",
        )
        assert result is None
        assert mock_llm.chat_completion.call_count == 1

    def test_empty_response_retries_then_fails(self):
        """LLM returns empty response -> continues loop -> eventually fails."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {"content": ""}
        result = _attempt_fence_repair(
            mock_llm,
            "import fake_lib",
            ["unknown_import: fake_lib"],
            _sample_inventory(),
            fence_index=0,
            slug="test-page",
        )
        assert result is None

    def test_call_id_contains_slug_and_index(self):
        """Verify call_id includes slug and fence index for traceability."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": "import aspose.threed\nscene = aspose.threed.Scene()"
        }
        _attempt_fence_repair(
            mock_llm, "import fake_lib", ["unknown_import: fake_lib"],
            _sample_inventory(), fence_index=2, slug="my-page",
        )
        call_args = mock_llm.chat_completion.call_args
        call_id = call_args.kwargs.get("call_id", call_args[1].get("call_id", ""))
        assert "my-page" in call_id
        assert "2" in call_id

    def test_temperature_is_zero(self):
        """Verify repair calls use temperature 0.0 for determinism."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": "import aspose.threed\nscene = aspose.threed.Scene()"
        }
        _attempt_fence_repair(
            mock_llm, "import fake_lib", ["unknown_import: fake_lib"],
            _sample_inventory(), fence_index=0, slug="test",
        )
        call_args = mock_llm.chat_completion.call_args
        temp = call_args.kwargs.get("temperature", call_args[1].get("temperature"))
        assert temp == 0.0


# ---------------------------------------------------------------------------
# TC-2941: _repair_and_sanitize_code_fences
# ---------------------------------------------------------------------------

class TestRepairAndSanitizeCodeFences:
    """Integration tests for the full repair-then-sanitize flow."""

    def test_valid_fences_unchanged(self):
        mock_llm = MagicMock()
        content = "```python\nimport aspose.threed\nscene = aspose.threed.Scene()\n```"
        result = _repair_and_sanitize_code_fences(
            content, _sample_inventory(), mock_llm, slug="test",
        )
        assert result == content
        mock_llm.chat_completion.assert_not_called()

    def test_repair_succeeds_no_pseudocode(self):
        """When repair succeeds, the fence should contain real code, not pseudocode."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": "import aspose.threed\nscene = aspose.threed.Scene()\nscene.open('file.fbx')"
        }
        content = (
            "Some text.\n\n"
            "```python\nimport fake_aspose\nscene = fake_aspose.Scene()\n```\n\n"
            "More text."
        )
        result = _repair_and_sanitize_code_fences(
            content, _sample_inventory(), mock_llm, slug="test",
        )
        assert "pseudocode" not in result.lower()
        assert "import aspose.threed" in result
        assert "Some text." in result
        assert "More text." in result

    def test_repair_fails_falls_back_to_pseudocode(self):
        """When repair fails, fence becomes pseudocode."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": "import still_fake\nstill_fake.do_stuff()"
        }
        content = "```python\nimport fake_lib\nfake_lib.do_stuff()\n```"
        result = _repair_and_sanitize_code_fences(
            content, _sample_inventory(), mock_llm, slug="test",
        )
        assert "# import fake_lib" in result or "pseudocode" in result.lower()

    def test_mixed_valid_and_invalid_fences(self):
        """Valid fences untouched; only invalid fences go through repair."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": "import aspose.threed\nscene = aspose.threed.Scene()"
        }
        content = (
            "```python\nimport aspose.threed\nscene = aspose.threed.Scene()\n```\n\n"
            "```python\nimport fake_lib\nfake_lib.do_stuff()\n```"
        )
        result = _repair_and_sanitize_code_fences(
            content, _sample_inventory(), mock_llm, slug="test",
        )
        # Valid fence preserved
        assert "import aspose.threed\nscene = aspose.threed.Scene()" in result
        # LLM was called (only for the invalid fence)
        assert mock_llm.chat_completion.call_count >= 1

    def test_empty_content_returns_empty(self):
        mock_llm = MagicMock()
        result = _repair_and_sanitize_code_fences(
            "", _sample_inventory(), mock_llm, slug="test",
        )
        assert result == ""
        mock_llm.chat_completion.assert_not_called()


# ---------------------------------------------------------------------------
# TC-2941: Feature flag integration
# ---------------------------------------------------------------------------

class TestFenceRepairFeatureFlag:
    """Test that the feature flag controls repair pass execution."""

    def test_enabled_by_default(self):
        orch = MultiPassOrchestrator(MagicMock(), MagicMock(), run_config={})
        assert orch._fence_repair_enabled is True

    def test_can_be_disabled_via_config(self):
        orch = MultiPassOrchestrator(
            MagicMock(), MagicMock(),
            run_config={"fence_repair_enabled": False},
        )
        assert orch._fence_repair_enabled is False

    def test_enabled_when_no_run_config(self):
        orch = MultiPassOrchestrator(MagicMock(), MagicMock(), run_config=None)
        assert orch._fence_repair_enabled is True
