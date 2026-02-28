"""Tests for W10 scaffold leak auto-fix (TC-2880).

Covers all 5 SCAFFOLD_* categories, fence safety, multi-file scanning,
idempotency, routing, and end-to-end behavior.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

from launch.workers.w10_fixer.worker import (
    apply_fix,
    fix_scaffold_leak,
    fix_formatting_defect,
    fix_frontmatter_missing,
    parse_frontmatter,
    _strip_all_scaffold,
    _strip_prompt_xml_blocks,
    _strip_llm_meta_lines,
    _strip_pipeline_json_keys,
    _strip_pipeline_diagnostics,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    """Create temporary run directory with required structure."""
    run_dir = tmp_path / "runs" / "test_run"
    run_dir.mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    (run_dir / "reports").mkdir()
    (run_dir / "work" / "site").mkdir(parents=True)
    (run_dir / "events.ndjson").touch()
    return run_dir


@pytest.fixture
def mock_llm_client() -> MagicMock:
    return MagicMock()


def _make_issue(error_code: str, file_path: str = "", line: int = 1) -> Dict[str, Any]:
    """Build a minimal issue dict for testing."""
    return {
        "issue_id": f"test_{error_code.lower()}_{line}",
        "error_code": error_code,
        "gate": "gate_scaffold_leak",
        "location": {"path": file_path, "line": line},
        "message": f"Test issue for {error_code}",
    }


# ── A. SCAFFOLD_LLM_SCAFFOLD (4 tests) ───────────────────────────────────────


class TestLLMScaffoldFix:
    """Fix LLM completion artifacts."""

    def test_you_now_have_complete_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("# Title\n\nGood content here.\n\nYou now have a complete solution.\n\nMore content.", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_SCAFFOLD", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "You now have a complete" not in content
        assert "Good content here." in content
        assert "More content." in content

    def test_you_now_have_working_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("Setup done.\n\nYou now have a working environment.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_SCAFFOLD", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert "You now have a working" not in md.read_text(encoding="utf-8")

    def test_heres_a_complete_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("# Guide\n\nHere's a complete example of the API.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_SCAFFOLD", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert "Here's a complete" not in md.read_text(encoding="utf-8")

    def test_here_is_a_complete_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("Here is a complete implementation.\n\nReal content follows.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_SCAFFOLD", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "Here is a complete" not in content
        assert "Real content follows." in content


# ── B. SCAFFOLD_LLM_META (6 tests) ───────────────────────────────────────────


class TestLLMMetaFix:
    """Fix LLM self-reference and meta-commentary."""

    def test_as_an_ai_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("# Title\n\nAs an AI, I cannot verify this claim.\n\nValid sentence.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "As an AI" not in content
        assert "Valid sentence." in content

    def test_ill_help_you_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("I'll help you understand the API.\n\nThe API provides...\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert "I'll help you" not in md.read_text(encoding="utf-8")

    def test_i_will_help_you_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("I will help you set up the library.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert "I will help you" not in md.read_text(encoding="utf-8")

    def test_let_me_explain_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("Let me explain how this works.\n\nThe converter accepts...\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "Let me explain" not in content
        assert "The converter accepts" in content

    def test_let_me_show_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("Let me show you a quick demo.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert "Let me show" not in md.read_text(encoding="utf-8")

    def test_let_me_demonstrate_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("Let me demonstrate the conversion.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert "Let me demonstrate" not in md.read_text(encoding="utf-8")


# ── C. SCAFFOLD_PIPELINE_DIAGNOSTIC (4 tests) ────────────────────────────────


class TestPipelineDiagnosticFix:
    """Fix pipeline diagnostic markers leaked into prose."""

    def test_claim_id_in_prose_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("# Title\n\nclaim_id: abc123-def456\n\nReal content.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_PIPELINE_DIAGNOSTIC", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "claim_id:" not in content
        assert "Real content." in content

    def test_evidence_score_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("Some text.\n\nevidence_score: 8\n\nMore text.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_PIPELINE_DIAGNOSTIC", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert "evidence_score:" not in md.read_text(encoding="utf-8")

    def test_claim_html_comment_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("Text before.\n\n<!-- claim.C001 evidence -->\n\nText after.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_PIPELINE_DIAGNOSTIC", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "claim.C001" not in content
        assert "Text before." in content

    def test_diagnostic_in_fence_preserved(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\n```python\n# claim_id: abc123-def456\nprint('hello')\n```\n\nProse.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PIPELINE_DIAGNOSTIC", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        # Should NOT remove content inside fence
        content = md.read_text(encoding="utf-8")
        assert "claim_id: abc123-def456" in content
        assert "print('hello')" in content


# ── D. SCAFFOLD_PROMPT_LEAK (11 tests) ───────────────────────────────────────


class TestPromptLeakFix:
    """Fix leaked prompt/scaffold headings, labels, markers, and XML tags."""

    def test_product_context_heading_and_body_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            '# Title\n\n## Product Context\n\n{"product_name": "Aspose"}\n\n## Real Section\n\nContent.\n',
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "Product Context" not in content
        assert "product_name" not in content
        assert "## Real Section" in content
        assert "Content." in content

    def test_instructions_heading_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\n## Instructions\n\n1. Follow the template.\n2. Use claims.\n\n## Overview\n\nContent.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "## Instructions" not in content
        assert "Follow the template" not in content
        assert "## Overview" in content

    def test_output_rules_heading_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "## Output Rules\n\nRule 1.\nRule 2.\n\n## Content\n\nReal.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "Output Rules" not in content
        assert "Rule 1" not in content
        assert "## Content" in content

    def test_source_material_heading_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "## Source Material\n\nRaw data here.\n\n## Features\n\nGood content.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "Source Material" not in content
        assert "Raw data" not in content
        assert "## Features" in content

    def test_bold_product_context_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\n**Product Context**\n\nJSON blob.\n\n## Section\n\nContent.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "Product Context" not in content

    def test_product_context_label_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "Product Context:\n\nSome details.\n\n## Section\n\nContent.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert "Product Context:" not in md.read_text(encoding="utf-8")

    def test_w_review_marker_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\nW5.5_REVIEW: check this section for accuracy\n\nContent.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "W5.5_REVIEW" not in content
        assert "Content." in content

    def test_xml_instructions_tag_pair_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\n<instructions>\nFollow the rules.\n</instructions>\n\nContent.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "<instructions>" not in content
        assert "</instructions>" not in content
        assert "Follow the rules" not in content
        assert "Content." in content

    def test_xml_context_tag_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "<context>\nProduct info here.\n</context>\n\nReal content.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "<context>" not in content
        assert "</context>" not in content

    def test_system_prefix_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "System: You are a technical documentation writer.\n\n# Title\n\nContent.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "System:" not in content
        assert "# Title" in content

    def test_prompt_leak_in_fence_still_removed(self, run_dir, mock_llm_client):
        """PROMPT_LEAK is never legitimate, even in code fences."""
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\n```\n<instructions>\nDo this.\n</instructions>\n```\n\nContent.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert "<instructions>" not in content
        assert "</instructions>" not in content


# ── E. SCAFFOLD_PIPELINE_JSON (4 tests) ──────────────────────────────────────


class TestPipelineJSONFix:
    """Fix pipeline-internal JSON keys outside fences."""

    def test_claims_json_key_outside_fence_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            '# Title\n\n"claims": [\n  {"id": "c1"}\n]\n\nContent.\n',
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PIPELINE_JSON", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        assert '"claims":' not in content
        assert "Content." in content

    def test_page_plan_json_key_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            '# Title\n\n"page_plan": {}\n\nContent.\n',
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PIPELINE_JSON", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert '"page_plan":' not in md.read_text(encoding="utf-8")

    def test_shared_facts_json_key_removed(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            '# Title\n\n  "shared_facts": {}\n\nContent.\n',
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PIPELINE_JSON", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert '"shared_facts":' not in md.read_text(encoding="utf-8")

    def test_pipeline_json_in_fence_preserved(self, run_dir, mock_llm_client):
        """JSON keys inside code fences should be preserved (could be example)."""
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            '# Title\n\n```json\n"claims": [\n  {"id": "c1"}\n]\n```\n\nContent.\n',
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PIPELINE_JSON", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        content = md.read_text(encoding="utf-8")
        assert '"claims":' in content


# ── F. Fence Safety (3 tests) ────────────────────────────────────────────────


class TestFenceSafety:
    """Verify code fence content is preserved (except PROMPT_LEAK)."""

    def test_code_fence_content_preserved(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\n```python\n"
            "# This is normal code\n"
            "print('hello world')\n"
            "result = process(data)\n"
            "```\n\nContent.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        content = md.read_text(encoding="utf-8")
        assert "print('hello world')" in content
        assert "result = process(data)" in content

    def test_mixed_fence_and_prose_leaks(self, run_dir, mock_llm_client):
        """Prose leaks removed but fenced content preserved."""
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\n"
            "As an AI, I'll explain.\n\n"
            "```python\n# evidence_score: 9\nprint('ok')\n```\n\n"
            "Let me show you the result.\n\n"
            "```bash\n# claim_id: aaa-bbb\necho done\n```\n\n"
            "Real content.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        # Prose leaks removed
        assert "As an AI" not in content
        assert "Let me show you" not in content
        # Fenced content preserved
        assert "evidence_score: 9" in content
        assert "claim_id: aaa-bbb" in content
        assert "print('ok')" in content
        assert "echo done" in content
        assert "Real content." in content

    def test_fence_toggle_tracking(self, run_dir, mock_llm_client):
        """Verify fence state tracks correctly across multiple fence blocks."""
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "evidence_score: 1\n\n"
            "```\nfenced evidence_score: 2\n```\n\n"
            "evidence_score: 3\n\n"
            "```\nfenced evidence_score: 4\n```\n\n"
            "evidence_score: 5\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PIPELINE_DIAGNOSTIC", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        content = md.read_text(encoding="utf-8")
        # Prose diagnostics removed
        assert "evidence_score: 1" not in content
        assert "evidence_score: 3" not in content
        assert "evidence_score: 5" not in content
        # Fenced diagnostics preserved
        assert "fenced evidence_score: 2" in content
        assert "fenced evidence_score: 4" in content


# ── G. Multi-file + Idempotency (4 tests) ────────────────────────────────────


class TestMultiFileAndIdempotency:
    """Multi-file scanning and fix idempotency."""

    def test_scans_all_md_files(self, run_dir, mock_llm_client):
        """All .md files under work/site/ are scanned and fixed."""
        site = run_dir / "work" / "site"
        (site / "a.md").write_text("As an AI, I cannot.\n\nContent A.\n", encoding="utf-8")
        (site / "subdir").mkdir()
        (site / "subdir" / "b.md").write_text("You now have a complete guide.\n\nContent B.\n", encoding="utf-8")
        (site / "c.md").write_text('"claims": []\n\nContent C.\n', encoding="utf-8")

        issue = _make_issue("SCAFFOLD_LLM_META", str(site / "a.md"))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert len(result["files_changed"]) == 3

        assert "As an AI" not in (site / "a.md").read_text(encoding="utf-8")
        assert "You now have a complete" not in (site / "subdir" / "b.md").read_text(encoding="utf-8")
        assert '"claims":' not in (site / "c.md").read_text(encoding="utf-8")

    def test_idempotent_second_run_returns_not_fixed(self, run_dir, mock_llm_client):
        """Running fix twice: first fixes, second reports no change."""
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("As an AI, I suggest.\n\nContent.\n", encoding="utf-8")

        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result1 = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result1["fixed"] is True

        result2 = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result2["fixed"] is False

    def test_no_site_dir_returns_not_fixed(self, tmp_path, mock_llm_client):
        """Missing work/site/ directory returns error."""
        run_dir = tmp_path / "empty_run"
        run_dir.mkdir()
        issue = _make_issue("SCAFFOLD_LLM_META")
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is False
        assert "work/site/" in result["error"]

    def test_clean_content_returns_not_fixed(self, run_dir, mock_llm_client):
        """Clean content with no scaffold leaks returns not-fixed."""
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("# Title\n\nThis is perfectly clean content.\n\n## Section\n\nMore content.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is False


# ── H. Routing (5 tests) ─────────────────────────────────────────────────────


class TestScaffoldRouting:
    """apply_fix() routes all SCAFFOLD_* codes to fix_scaffold_leak."""

    def test_routes_scaffold_llm_scaffold(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("You now have a full setup.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_SCAFFOLD", str(md))
        result = apply_fix(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True

    def test_routes_scaffold_llm_meta(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("As an AI, I suggest.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_LLM_META", str(md))
        result = apply_fix(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True

    def test_routes_scaffold_pipeline_diagnostic(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("claim_id: abc-def-123\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_PIPELINE_DIAGNOSTIC", str(md))
        result = apply_fix(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True

    def test_routes_scaffold_prompt_leak(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text("## Product Context\n\nJSON.\n\n## Real\n\nContent.\n", encoding="utf-8")
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = apply_fix(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True

    def test_routes_scaffold_pipeline_json(self, run_dir, mock_llm_client):
        md = run_dir / "work" / "site" / "page.md"
        md.write_text('"evidence_map": {}\n\nContent.\n', encoding="utf-8")
        issue = _make_issue("SCAFFOLD_PIPELINE_JSON", str(md))
        result = apply_fix(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True


# ── I. End-to-end (1 test) ───────────────────────────────────────────────────


class TestEndToEnd:
    """Full pipeline: issue dict -> fix_scaffold_leak -> verified clean file."""

    def test_full_scaffold_cleanup(self, run_dir, mock_llm_client):
        """A file with multiple scaffold categories is fully cleaned."""
        md = run_dir / "work" / "site" / "page.md"
        md.write_text(
            "# Title\n\n"
            "## Product Context\n\n"
            '{"product_name": "Aspose"}\n\n'
            "## Overview\n\n"
            "As an AI, I'll explain the library.\n\n"
            "The library converts documents.\n\n"
            "```python\nimport aspose\n```\n\n"
            '<instructions>\nFollow the rules.\n</instructions>\n\n'
            "claim_id: abc-123\n\n"
            '"shared_facts": {}\n\n'
            "You now have a complete understanding.\n\n"
            "W7_REVIEW: check quality\n\n"
            "## Conclusion\n\n"
            "The library is useful.\n",
            encoding="utf-8",
        )
        issue = _make_issue("SCAFFOLD_PROMPT_LEAK", str(md))
        result = fix_scaffold_leak(issue, run_dir, mock_llm_client)
        assert result["fixed"] is True
        assert str(md) in result["files_changed"]

        content = md.read_text(encoding="utf-8")
        # All scaffold removed
        assert "Product Context" not in content
        assert "product_name" not in content
        assert "As an AI" not in content
        assert "<instructions>" not in content
        assert "claim_id:" not in content
        assert '"shared_facts":' not in content
        assert "You now have a complete" not in content
        assert "W7_REVIEW" not in content
        # Good content preserved
        assert "# Title" in content
        assert "## Overview" in content
        assert "The library converts documents." in content
        assert "import aspose" in content
        assert "## Conclusion" in content
        assert "The library is useful." in content


# ── J. Unit tests for helper functions ────────────────────────────────────────


class TestStripHelpers:
    """Direct unit tests for private helper functions."""

    def test_strip_prompt_xml_blocks_paired(self):
        content = "Before.\n<instructions>\nDo this.\n</instructions>\nAfter."
        result = _strip_prompt_xml_blocks(content)
        assert "<instructions>" not in result
        assert "Do this." not in result
        assert "Before." in result
        assert "After." in result

    def test_strip_prompt_xml_blocks_orphan_opening(self):
        content = "Before.\n<context>\nAfter."
        result = _strip_prompt_xml_blocks(content)
        assert "<context>" not in result
        assert "After." in result

    def test_strip_prompt_xml_blocks_orphan_closing(self):
        content = "Before.\n</issues>\nAfter."
        result = _strip_prompt_xml_blocks(content)
        assert "</issues>" not in result

    def test_strip_llm_meta_lines_fence_aware(self):
        content = "As an AI, I suggest.\n```\nAs an AI inside fence.\n```\nClean."
        result = _strip_llm_meta_lines(content)
        assert "As an AI, I suggest." not in result
        assert "As an AI inside fence." in result
        assert "Clean." in result

    def test_strip_pipeline_json_keys_fence_aware(self):
        content = '"claims": []\n```json\n"claims": []\n```\nClean.'
        result = _strip_pipeline_json_keys(content)
        lines = result.split("\n")
        # Outside fence: removed
        assert '"claims": []' not in lines[0] if lines[0] else True
        # Inside fence: preserved
        assert '"claims": []' in result.split("```json\n")[1].split("\n```")[0]

    def test_strip_pipeline_diagnostics_fence_aware(self):
        content = "evidence_score: 5\n```\nevidence_score: 9\n```\nClean."
        result = _strip_pipeline_diagnostics(content)
        assert result.startswith("```") or result.startswith("\n")
        assert "evidence_score: 9" in result

    def test_strip_all_scaffold_returns_count(self):
        content = "As an AI.\n\nevidence_score: 5\n\nClean text.\n"
        cleaned, count = _strip_all_scaffold(content)
        assert count >= 2
        assert "As an AI" not in cleaned
        assert "evidence_score:" not in cleaned
        assert "Clean text." in cleaned

    def test_strip_all_scaffold_collapses_blank_lines(self):
        content = "Line 1.\n\n\n\n\nLine 2.\n"
        cleaned, _ = _strip_all_scaffold(content)
        assert "\n\n\n" not in cleaned
        assert "Line 1." in cleaned
        assert "Line 2." in cleaned


# ---------------------------------------------------------------------------
# TC-3211: FQ-4 heading+paragraph fusion fix
# ---------------------------------------------------------------------------

class TestFQ4HeadingParagraphFusion:
    """Tests for Fix 3 in fix_formatting_defect(): camelCase-based heading+paragraph split.

    Fix 3 handles long heading lines (>60 chars) where heading text and following
    paragraph are concatenated without a newline, e.g.:
        ## Data Validation RulesAspose.Cells FOSS for Python lets you...
    The fix scans for the first camelCase junction (lowercase→uppercase) and splits there.
    """

    def _make_issue(self, path: str) -> dict:
        return {
            "issue_id": f"gate17_fq4_fusion_{Path(path).stem}_1",
            "gate": "gate_17_formatting_quality",
            "severity": "error",
            "error_code": "G17-FQ-4",
            "message": "Heading+paragraph fusion detected",
            "location": {"path": path, "line": 1},
            "status": "OPEN",
        }

    def test_fq4_heading_paragraph_fusion_split(self, tmp_path: Path):
        """Heading+paragraph fusion is split at camelCase boundary."""
        content = (
            "---\ntitle: Test\n---\n"
            "## Data Validation RulesAspose.Cells FOSS for Python lets you control cell input.\n"
        )
        page = tmp_path / "fused.md"
        page.write_text(content, encoding="utf-8")

        issue = self._make_issue(str(page))
        result = fix_formatting_defect(issue, tmp_path, None)

        assert result["fixed"] is True
        fixed = page.read_text(encoding="utf-8")
        # The heading and paragraph should be on separate lines now
        assert "## Data Validation Rules\n" in fixed or "## Data Validation Rules" in fixed
        assert "Aspose.Cells" in fixed
        # They should not be on the same line
        lines = fixed.splitlines()
        for line in lines:
            if line.startswith("## ") and "Rules" in line:
                assert "Aspose" not in line, f"Fusion not split: {line!r}"

    def test_fq4_heading_fusion_idempotent(self, tmp_path: Path):
        """Running fix_formatting_defect for FQ-4 twice produces the same result."""
        content = (
            "---\ntitle: Test\n---\n"
            "## ComparisonThe library handles all cell value data types automatically.\n"
        )
        page = tmp_path / "idempotent.md"
        page.write_text(content, encoding="utf-8")

        issue = self._make_issue(str(page))
        fix_formatting_defect(issue, tmp_path, None)
        first_pass = page.read_text(encoding="utf-8")

        fix_formatting_defect(issue, tmp_path, None)
        second_pass = page.read_text(encoding="utf-8")

        assert first_pass == second_pass, "Fix is not idempotent — running twice produces different output"

    def test_fq4_short_heading_not_split_by_fix3(self, tmp_path: Path):
        """Fix 3 only fires on lines >60 chars; a normal well-formed heading is preserved."""
        # A heading with no camelCase junction — no concat pattern present
        content = (
            "---\ntitle: Test\n---\n"
            "## Valid Heading\n\nSome body text here.\n"
        )
        page = tmp_path / "short.md"
        page.write_text(content, encoding="utf-8")

        issue = self._make_issue(str(page))
        fix_formatting_defect(issue, tmp_path, None)

        fixed = page.read_text(encoding="utf-8")
        # Well-formed heading with body already on the next line: heading line unchanged
        assert "## Valid Heading" in fixed
        assert "Some body text here." in fixed

    def test_fq4_adjacent_headings_fix_unaffected(self, tmp_path: Path):
        """Existing Fix 1 (adjacent headings → blank line) still works after Fix 3 is added."""
        content = (
            "---\ntitle: Test\n---\n"
            "## First Heading\n"
            "## Second Heading\n"
            "Body text.\n"
        )
        page = tmp_path / "adjacent.md"
        page.write_text(content, encoding="utf-8")

        issue = self._make_issue(str(page))
        fix_formatting_defect(issue, tmp_path, None)
        fixed = page.read_text(encoding="utf-8")

        assert "## First Heading\n\n## Second Heading" in fixed


# ---------------------------------------------------------------------------
# TC-3212: Placeholder page frontmatter injection
# ---------------------------------------------------------------------------

class TestPlaceholderFrontmatter:
    """Tests for placeholder-aware frontmatter injection (TC-3212).

    Covers:
    - Placeholder page gets layout + permalink injected
    - Existing partial frontmatter gets missing fields added
    - Non-placeholder pages are not affected
    - Idempotency
    """

    def _make_issue(self, path: str, error_code: str = "GATE_FRONTMATTER_MISSING") -> dict:
        return {
            "issue_id": f"gate4_{Path(path).stem}",
            "gate": "gate_4_frontmatter_required_fields",
            "severity": "error",
            "error_code": error_code,
            "message": "Frontmatter missing or incomplete",
            "location": {"path": path},
            "status": "OPEN",
        }

    def test_placeholder_page_gets_layout_and_permalink(self, tmp_path: Path):
        """Placeholder page with no frontmatter gets layout=kb-howto and permalink."""
        # Create content path structure
        kb_dir = tmp_path / "work" / "site" / "content" / "kb.aspose.org" / "cells" / "en" / "python"
        kb_dir.mkdir(parents=True)
        page = kb_dir / "how-to-note-this-method-is-a-placeholder.md"
        page.write_text("# Some content\n", encoding="utf-8")

        issue = self._make_issue(str(page))
        result = fix_frontmatter_missing(issue, tmp_path, None)

        assert result["fixed"] is True
        content = page.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(content)
        assert fm is not None
        assert fm.get("layout") == "kb-howto"
        assert "placeholder" in fm.get("permalink", "")

    def test_existing_partial_frontmatter_gets_missing_fields(self, tmp_path: Path):
        """Placeholder page with partial frontmatter (title+type, no layout/permalink) gets them added."""
        kb_dir = tmp_path / "work" / "site" / "content" / "kb.aspose.org" / "cells" / "en" / "python"
        kb_dir.mkdir(parents=True)
        page = kb_dir / "how-to-do-a-placeholder.md"
        page.write_text(
            "---\ntitle: Placeholder Page\ntype: docs\n---\nBody.\n",
            encoding="utf-8",
        )

        issue = self._make_issue(str(page), error_code="GATE_FRONTMATTER_REQUIRED_FIELD_MISSING")
        result = fix_frontmatter_missing(issue, tmp_path, None)

        assert result["fixed"] is True
        content = page.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        assert fm is not None
        assert fm.get("layout") is not None
        assert fm.get("permalink") is not None
        assert "Body." in body

    def test_non_placeholder_page_gets_generic_frontmatter(self, tmp_path: Path):
        """Non-placeholder page gets frontmatter but no placeholder-specific layout."""
        regular_dir = tmp_path / "work" / "site" / "content"
        regular_dir.mkdir(parents=True)
        page = regular_dir / "regular-guide.md"
        page.write_text("Body content.\n", encoding="utf-8")

        issue = self._make_issue(str(page))
        result = fix_frontmatter_missing(issue, tmp_path, None)

        assert result["fixed"] is True
        content = page.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(content)
        assert fm is not None
        # Should have generic fields — layout and permalink still injected (TC-3212 ensures all pages get them)
        assert "title" in fm

    def test_placeholder_frontmatter_idempotent(self, tmp_path: Path):
        """Running fix twice on placeholder page produces the same result."""
        kb_dir = tmp_path / "work" / "site" / "content" / "kb.aspose.org" / "cells" / "en" / "python"
        kb_dir.mkdir(parents=True)
        page = kb_dir / "how-to-note-this-method-is-a-placeholder.md"
        page.write_text("Body content.\n", encoding="utf-8")

        issue = self._make_issue(str(page))
        fix_frontmatter_missing(issue, tmp_path, None)
        first_pass = page.read_text(encoding="utf-8")

        # Second run with REQUIRED_FIELD_MISSING (simulating re-check)
        issue2 = self._make_issue(str(page), error_code="GATE_FRONTMATTER_REQUIRED_FIELD_MISSING")
        fix_frontmatter_missing(issue2, tmp_path, None)
        second_pass = page.read_text(encoding="utf-8")

        # Content should be the same (idempotent)
        fm1, _ = parse_frontmatter(first_pass)
        fm2, _ = parse_frontmatter(second_pass)
        assert fm1.get("layout") == fm2.get("layout")
        assert fm1.get("permalink") == fm2.get("permalink")


# ── TC-3263: FQ-3 Truncated Bullet Repair ─────────────────────────────────────

class TestFQ3TruncatedBulletRepair:
    """TC-3263: FQ-3 truncated bullet repair — improved two-step strategy."""

    def _make_issue(self, file_path):
        return {
            "issue_id": "test-fq3-001",
            "error_code": "G17-FQ-3",
            "location": {"path": str(file_path), "line": 1},
            "message": "Truncated bullet ending",
        }

    def test_fq3_trailing_comma_becomes_period(self, tmp_path):
        """Bullet ending with comma → comma stripped, period appended."""
        md = tmp_path / "page.md"
        md.write_text("---\ntitle: T\n---\n\n- Converts files using the library,\n")
        issue = self._make_issue(md)
        result = fix_formatting_defect(issue, tmp_path, llm_client=None)
        assert result["fixed"] is True
        content = md.read_text()
        # Must NOT end with comma; must end with period
        assert not any(line.rstrip().endswith(",") for line in content.splitlines() if line.strip())
        assert any(line.rstrip().endswith(".") for line in content.splitlines() if "Converts" in line)

    def test_fq3_trailing_connector_gets_ellipsis(self, tmp_path):
        """Bullet ending with connector word → ellipsis appended."""
        md = tmp_path / "page.md"
        md.write_text("---\ntitle: T\n---\n\n- Supports conversion using the\n")
        issue = self._make_issue(md)
        result = fix_formatting_defect(issue, tmp_path, llm_client=None)
        assert result["fixed"] is True
        content = md.read_text()
        # Must end with ellipsis (connector word not stripped)
        assert any("..." in line for line in content.splitlines() if "Supports" in line)

    def test_fq3_repair_is_idempotent(self, tmp_path):
        """Running FQ-3 fix twice produces the same result."""
        md = tmp_path / "page.md"
        md.write_text("---\ntitle: T\n---\n\n- Converts files using the library,\n")
        issue = self._make_issue(md)
        fix_formatting_defect(issue, tmp_path, llm_client=None)
        content_after_first = md.read_text()
        fix_formatting_defect(issue, tmp_path, llm_client=None)
        content_after_second = md.read_text()
        assert content_after_first == content_after_second

    def test_fq3_short_line_not_modified(self, tmp_path):
        """Very short lines (<20 chars) with connector word are NOT appended with ellipsis."""
        md = tmp_path / "page.md"
        # "- Use the" is short (9 chars content); should not get ellipsis
        md.write_text("---\ntitle: T\n---\n\n- Use the\n")
        issue = self._make_issue(md)
        result = fix_formatting_defect(issue, tmp_path, llm_client=None)
        content = md.read_text()
        # Ellipsis should NOT be appended to very short line
        assert "- Use the..." not in content
