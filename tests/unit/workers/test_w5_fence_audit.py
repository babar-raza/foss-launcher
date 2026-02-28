"""Tests for TC-3110: W5 Symbol Grounding Guardrail - pre-refine code fence audit."""
import pytest
from unittest.mock import MagicMock

from launch.workers._shared.code_fence_validator import (
    build_compact_allowlist,
    extract_identifiers_heuristic,
    audit_fence,
    CompactAllowlist,
    FenceAuditResult,
    GENERIC_FENCE_RE,
)

try:
    from launch.workers.w5_section_writer.multi_pass import (
        _audit_code_fences,
        _format_compact_repair_prompt,
    )
    MULTI_PASS_AVAILABLE = True
except ImportError:
    MULTI_PASS_AVAILABLE = False
    _audit_code_fences = None
    _format_compact_repair_prompt = None


SAMPLE_INVENTORY = {
    "package_name": "aspose-3d",
    "import_roots": ["aspose"],
    "modules": ["aspose", "aspose.threed"],
    "classes": [
        {
            "name": "Scene",
            "import_path": "aspose.threed.Scene",
            "methods": ["open", "save", "merge_scene"],
            "properties": ["root_node", "library"],
            "class_constants": ["FORMAT_FBX", "FORMAT_GLB"],
        },
        {
            "name": "Mesh",
            "import_path": "aspose.threed.Mesh",
            "methods": ["triangulate", "get_vertices"],
            "properties": ["vertices"],
        },
    ],
    "functions": ["create_scene"],
    "public_surface": {"confidence": "unknown", "classes": []},
}


class TestCompactAllowlist:
    """Tests for build_compact_allowlist()."""

    def test_builds_from_sample_inventory(self):
        """CompactAllowlist populated correctly from sample inventory."""
        allowlist = build_compact_allowlist(SAMPLE_INVENTORY)
        assert "Scene" in allowlist.class_names
        assert "Mesh" in allowlist.class_names
        assert "open" in allowlist.method_index.get("Scene", set())
        assert "triangulate" in allowlist.method_index.get("Mesh", set())
        assert "create_scene" in allowlist.known_functions
        assert "aspose" in allowlist.package_stems

    def test_empty_inventory_empty_allowlist(self):
        """Empty inventory produces empty CompactAllowlist without crash."""
        allowlist = build_compact_allowlist({})
        assert len(allowlist.class_names) == 0
        assert len(allowlist.method_index) == 0

    def test_package_stem_variants(self):
        """Package name variants all included in package_stems."""
        inv = {"package_name": "aspose-3d", "classes": [], "modules": []}
        allowlist = build_compact_allowlist(inv)
        assert any("aspose" in s for s in allowlist.package_stems)


class TestExtractIdentifiers:
    """Tests for extract_identifiers_heuristic()."""

    def test_python_ast_extracts_imports(self):
        """Python AST extracts import module roots."""
        code = "from aspose.threed import Scene\nscene = Scene()\nscene.save('out.fbx')"
        ids = extract_identifiers_heuristic(code, "python")
        assert "aspose" in ids or "Scene" in ids

    def test_python_syntax_error_fallback(self):
        """SyntaxError falls back to regex (no crash)."""
        code = '# Not valid Python\n<<< this is pseudocode >>>'
        ids = extract_identifiers_heuristic(code, "python")
        assert isinstance(ids, set)

    def test_typescript_import_extracted(self):
        """TypeScript import {{ X }} from '...' extracts module."""
        code = "import { FakeClass } from 'fake-lib';\nconst x = new FakeClass();"
        ids = extract_identifiers_heuristic(code, "typescript")
        assert "FakeClass" in ids or "fake-lib" in ids

    def test_go_qualified_call_extracted(self):
        """Go pkg.Function() pattern extracts package name."""
        code = 'import "fakepkg"\nresult := fakepkg.Load("file.fbx")'
        ids = extract_identifiers_heuristic(code, "go")
        assert "fakepkg" in ids

    def test_unknown_language_returns_empty(self):
        """Unknown language returns empty set (safe skip)."""
        ids = extract_identifiers_heuristic("some code", "brainfuck")
        assert ids == set()


class TestAuditFence:
    """Tests for audit_fence()."""

    def _make_allowlist(self):
        return build_compact_allowlist(SAMPLE_INVENTORY)

    def test_valid_python_fence_is_valid(self):
        """Valid Python fence using known symbols -> is_valid=True."""
        allowlist = self._make_allowlist()
        code = "from aspose.threed import Scene\nscene = Scene()\nscene.save('out.fbx')"
        result = audit_fence(code, "python", allowlist)
        assert result.is_valid, f"Expected valid, got unknowns: {result.unknown_ids}"

    def test_unknown_import_is_invalid(self):
        """Python fence with unknown import -> is_valid=False."""
        allowlist = self._make_allowlist()
        code = 'import totally_fake_lib\nobj = totally_fake_lib.DoSomething()'
        result = audit_fence(code, "python", allowlist)
        assert not result.is_valid
        assert len(result.unknown_ids) > 0

    def test_stdlib_import_not_flagged(self):
        """stdlib imports (os, pathlib) -> is_valid=True."""
        allowlist = self._make_allowlist()
        code = "import os\nfrom pathlib import Path\np = Path('out.fbx')"
        result = audit_fence(code, "python", allowlist)
        assert result.is_valid, f"Stdlib should pass, got unknowns: {result.unknown_ids}"

    def test_unknown_language_always_valid(self):
        """Unknown language fence -> always is_valid=True (safe skip)."""
        allowlist = self._make_allowlist()
        result = audit_fence("totally fake code @@@@", "cobol", allowlist)
        assert result.is_valid
        assert result.unknown_ids == set()


@pytest.mark.skipif(not MULTI_PASS_AVAILABLE, reason="WS-B not yet complete")
class TestAuditCodeFences:
    """Tests for _audit_code_fences() from multi_pass.py."""

    def _make_inventory(self):
        return SAMPLE_INVENTORY

    def test_all_valid_content_returned_unchanged(self):
        """Content with only valid fences returned unchanged, corrections empty."""
        content = "## Example\n\n```python\nfrom aspose.threed import Scene\nscene = Scene()\nscene.save('out.fbx')\n```\n"
        result, corrections = _audit_code_fences(content, self._make_inventory(), None)
        assert result == content
        assert corrections == []

    def test_invalid_fence_with_llm_repair_success(self):
        """Invalid fence + LLM repair succeeds -> repaired code inline."""
        content = '```python\nimport totally_fake\nobj = totally_fake.FakeClass()\n```\n'
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {"content": "from aspose.threed import Scene\nscene = Scene()\nscene.save('out.fbx')"}
        result, corrections = _audit_code_fences(content, self._make_inventory(), mock_llm)
        assert mock_llm.chat_completion.call_count == 1
        assert "totally_fake" not in result
        assert corrections == []

    def test_invalid_fence_repair_fails_demoted_to_pseudocode(self):
        """Invalid fence + repair still invalid -> pseudocode (comments)."""
        content = '## Section\n\n```python\nimport totally_fake\nobj = totally_fake.FakeClass()\n```\n'
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {"content": 'import also_fake\nobj = also_fake.BadClass()'}
        result, corrections = _audit_code_fences(content, self._make_inventory(), mock_llm)
        assert len(corrections) == 1
        assert "CODE_FENCE_DEMOTED" in corrections[0]
        assert "# " in result

    def test_no_llm_demotes_to_pseudocode(self):
        """No LLM client -> invalid fence immediately demoted to pseudocode."""
        content = '```python\nimport totally_fake\nobj = totally_fake.FakeClass()\n```\n'
        result, corrections = _audit_code_fences(content, self._make_inventory(), None)
        assert len(corrections) == 1
        assert "CODE_FENCE_DEMOTED" in corrections[0]
        assert "# " in result

    def test_exactly_one_llm_call_per_fence(self):
        """LLM called exactly once per invalid fence (not 2)."""
        content = '```python\nimport fake1\nfake1.DoThing()\n```\n\n```python\nimport fake2\nfake2.DoOther()\n```\n'
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {"content": 'import still_fake\nstill_fake.Bad()'}
        _, _ = _audit_code_fences(content, self._make_inventory(), mock_llm)
        assert mock_llm.chat_completion.call_count == 2

    def test_empty_inventory_noop(self):
        """Empty inventory -> no audit, content returned as-is."""
        content = '```python\nimport whatever\n```\n'
        result, corrections = _audit_code_fences(content, {}, None)
        assert result == content
        assert corrections == []

    def test_correction_instructions_contain_fence_info(self):
        """Correction instructions describe which fence was demoted and why."""
        content = '```python\nimport totally_fake\nobj = totally_fake.FakeClass()\n```\n'
        _, corrections = _audit_code_fences(content, self._make_inventory(), None)
        assert len(corrections) == 1
        assert "python" in corrections[0].lower()
        assert "totally_fake" in corrections[0] or "unknown" in corrections[0].lower()


@pytest.mark.skipif(not MULTI_PASS_AVAILABLE, reason="WS-B not yet complete")
class TestCompactRepairPrompt:
    """Tests for _format_compact_repair_prompt()."""

    def test_contains_class_names(self):
        """Compact prompt includes class names from allowlist."""
        allowlist = build_compact_allowlist(SAMPLE_INVENTORY)
        prompt = _format_compact_repair_prompt(allowlist)
        assert "Scene" in prompt
        assert "Mesh" in prompt

    def test_token_count_reasonable(self):
        """Compact prompt is much smaller than full API symbols block (~200 tokens)."""
        allowlist = build_compact_allowlist(SAMPLE_INVENTORY)
        prompt = _format_compact_repair_prompt(allowlist)
        words = len(prompt.split())
        assert words < 300, f"Prompt too large: {words} words"

    def test_deterministic_output(self):
        """Same inventory always produces same compact prompt (sorted output)."""
        allowlist = build_compact_allowlist(SAMPLE_INVENTORY)
        prompt1 = _format_compact_repair_prompt(allowlist)
        prompt2 = _format_compact_repair_prompt(allowlist)
        assert prompt1 == prompt2
