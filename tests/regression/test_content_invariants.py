"""Regression invariant tests for content quality (TC-2920).

Lightweight tests that check structural invariants on inline markdown
fixtures.  These do NOT call LLMs or run pilots — they verify that
detection logic catches known-bad patterns and passes known-good content.

Invariants covered:
1. Scaffold / prompt leak detection
2. Limitations section size caps
3. Code fence fragmentation (consecutive same-language fences)
4. Mandatory sections (blog + KB how-to) via existing gate functions
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.regression.invariant_helpers import (
    check_limitations_cap,
    detect_consecutive_same_lang_fences,
    detect_scaffold_leaks,
)

# Gate functions used directly for mandatory-section tests
from launch.workers.w9_validator.gates.gate_blog_mandatory import (
    execute_gate as blog_execute_gate,
)
from launch.workers.w9_validator.gates.gate_kb_howto_mandatory import (
    execute_gate as kb_execute_gate,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _write_page_plan(run_dir: Path, pages: List[Dict[str, Any]]) -> None:
    """Write a minimal page_plan.json to *run_dir*/artifacts/."""
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "page_plan.json").write_text(
        json.dumps({"pages": pages}, indent=2), encoding="utf-8"
    )


def _kb_page(slug: str, topic_category: str) -> Dict[str, Any]:
    """Build a single KB how-to page dict for page_plan fixtures."""
    return {
        "section": "kb",
        "page_role": "howto_article",
        "slug": slug,
        "topic_category": topic_category,
    }


def _all_required_kb_pages() -> List[Dict[str, Any]]:
    """Build the minimum 5 KB how-to pages covering all 5 required categories."""
    return [
        _kb_page("how-to-open-3d-files-python", "load_file"),
        _kb_page("how-to-save-3d-files-python", "save_file"),
        _kb_page("how-to-convert-3d-formats-python", "convert_formats"),
        _kb_page("how-to-fix-3d-errors-python", "troubleshoot"),
        _kb_page("how-to-optimize-3d-performance-python", "optimize_performance"),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# 1. Scaffold / Prompt Leak Invariant
# ═════════════════════════════════════════════════════════════════════════════


class TestScaffoldLeakInvariant:
    """Invariant: published markdown must not contain scaffold/prompt leaks."""

    # ── Bad content (must be detected) ───────────────────────────────────

    def test_product_context_json_block_detected(self) -> None:
        content = textwrap.dedent("""\
            ## Product Context
            {"product_name": "Aspose.3D", "api_surface": ["Scene", "Mesh"]}

            ## Overview
            Aspose.3D provides 3D processing capabilities.
        """)
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1
        errors = [l for l in leaks if l["severity"] == "error"]
        assert len(errors) >= 1

    def test_w55_review_marker_detected(self) -> None:
        content = "Some text. W5.5_REVIEW: needs improvement. More text."
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_as_an_ai_detected(self) -> None:
        content = "As an AI language model, I cannot verify this claim."
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_ill_help_you_detected(self) -> None:
        content = "I'll help you understand how to use this library."
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_claim_id_in_prose_detected(self) -> None:
        content = "This feature (claim_id: abc123-def456) is powerful."
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_evidence_score_detected(self) -> None:
        content = "The API supports many formats. evidence_score: 8"
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_instructions_heading_detected(self) -> None:
        content = textwrap.dedent("""\
            ## Instructions
            1. Write in professional tone
            2. Include code examples

            ## Overview
            Real content here.
        """)
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_claim_html_comment_detected(self) -> None:
        content = "Supports FBX. <!-- claim.C001 evidence --> Also OBJ."
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_system_prefix_detected(self) -> None:
        content = "System: You are a technical writer for Aspose."
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_pipeline_json_key_detected(self) -> None:
        content = textwrap.dedent("""\
            ## Overview
            "claims": [{"id": "C001", "text": "supports FBX"}]
        """)
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    def test_xml_prompt_tag_detected(self) -> None:
        content = "Some text <instructions> Write a blog post </instructions> more text."
        leaks = detect_scaffold_leaks(content)
        assert len(leaks) >= 1

    # ── TC-2890: 5 missing scaffold patterns ──────────────────────────────

    def test_available_claims_heading_detected(self) -> None:
        """TC-2890: Available Claims heading detected as scaffold leak."""
        content = "## Available Claims\n\nclaim-001: The product supports FBX format.\n\n## Overview\n\nReal content."
        leaks = detect_scaffold_leaks(content)
        errors = [lk for lk in leaks if lk["severity"] == "error"]
        assert len(errors) >= 1

    def test_issues_found_heading_detected(self) -> None:
        """TC-2890: Issues Found heading detected as scaffold leak."""
        content = "## Issues Found\n\n1. Missing code examples.\n\n## Content\n\nReal content."
        leaks = detect_scaffold_leaks(content)
        errors = [lk for lk in leaks if lk["severity"] == "error"]
        assert len(errors) >= 1

    def test_original_content_heading_detected(self) -> None:
        """TC-2890: Original Content heading detected as scaffold leak."""
        content = "## Original Content\n\nThe old draft text.\n\n## Updated\n\nNew."
        leaks = detect_scaffold_leaks(content)
        errors = [lk for lk in leaks if lk["severity"] == "error"]
        assert len(errors) >= 1

    # ── Good content (must NOT be detected as errors) ────────────────────

    def test_clean_technical_content_passes(self) -> None:
        content = textwrap.dedent("""\
            ## Overview
            Aspose.3D for Python provides 3D processing capabilities.

            ## Key Features
            - Load and save FBX, OBJ, STL files
            - Convert between formats

            ```python
            from aspose.threed import Scene
            scene = Scene.from_file("input.fbx")
            scene.save("output.obj")
            ```
        """)
        leaks = detect_scaffold_leaks(content)
        errors = [l for l in leaks if l["severity"] == "error"]
        assert errors == []

    def test_pipeline_diagnostics_in_fence_not_error(self) -> None:
        content = textwrap.dedent("""\
            ## Example

            ```python
            # claim_id: this is a variable name in test code
            claim_id = "abc123-def456"
            evidence_score = 8
            ```
        """)
        leaks = detect_scaffold_leaks(content)
        errors = [l for l in leaks if l["severity"] == "error"]
        assert errors == []


# ═════════════════════════════════════════════════════════════════════════════
# 2. Limitations Cap Invariant
# ═════════════════════════════════════════════════════════════════════════════


class TestLimitationsCapInvariant:
    """Invariant: ## Limitations must not exceed a reasonable size cap."""

    def test_short_limitations_passes(self) -> None:
        content = textwrap.dedent("""\
            ## Limitations
            - Does not support binary STL files
            - Maximum mesh size: 10M vertices
            - No animation support in free tier
        """)
        result = check_limitations_cap(content)
        assert result is None

    def test_oversized_bullets_detected(self) -> None:
        bullets = "\n".join(
            f"- Limitation number {i} with extra words to inflate count"
            for i in range(20)
        )
        content = f"## Limitations\n{bullets}\n\n## Next Section\nContent here."
        result = check_limitations_cap(content)
        assert result is not None
        assert result["bullets"] > 15

    def test_wordy_limitations_detected(self) -> None:
        paragraph = " ".join(["word"] * 350)
        content = f"## Limitations\n{paragraph}\n\n## Next Section\nMore."
        result = check_limitations_cap(content)
        assert result is not None
        assert result["words"] > 300

    def test_no_limitations_section_passes(self) -> None:
        content = "## Overview\nSome content.\n## Features\nMore content."
        result = check_limitations_cap(content)
        assert result is None

    def test_limitations_at_eof_handled(self) -> None:
        content = "## Overview\nContent.\n\n## Limitations\n- One issue"
        result = check_limitations_cap(content)
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# 3. Code Fence Fragmentation Invariant
# ═════════════════════════════════════════════════════════════════════════════


class TestCodeFenceFragmentationInvariant:
    """Invariant: no consecutive same-language code fences separated by only whitespace."""

    def test_adjacent_python_fences_detected(self) -> None:
        content = textwrap.dedent("""\
            ## Example

            ```python
            from aspose.threed import Scene
            scene = Scene()
            ```

            ```python
            scene.save("output.obj")
            ```
        """)
        hits = detect_consecutive_same_lang_fences(content)
        assert len(hits) >= 1
        assert hits[0]["lang"] == "python"

    def test_adjacent_fences_different_lang_ok(self) -> None:
        content = textwrap.dedent("""\
            ```python
            import aspose
            ```

            ```bash
            pip install aspose-3d
            ```
        """)
        hits = detect_consecutive_same_lang_fences(content)
        assert hits == []

    def test_fences_separated_by_prose_ok(self) -> None:
        content = textwrap.dedent("""\
            ```python
            scene = Scene()
            ```

            After loading the scene object you can manipulate it in various ways
            including converting formats and modifying mesh properties.

            ```python
            scene.save("output.obj")
            ```
        """)
        hits = detect_consecutive_same_lang_fences(content)
        assert hits == []

    def test_fences_separated_by_heading_ok(self) -> None:
        content = textwrap.dedent("""\
            ```python
            scene = Scene()
            ```

            ### Step 2

            ```python
            scene.save("output.obj")
            ```
        """)
        hits = detect_consecutive_same_lang_fences(content)
        assert hits == []

    def test_three_consecutive_fences_detected(self) -> None:
        content = textwrap.dedent("""\
            ```python
            import aspose
            ```

            ```python
            scene = Scene()
            ```

            ```python
            scene.save("out.fbx")
            ```
        """)
        hits = detect_consecutive_same_lang_fences(content)
        assert len(hits) >= 2

    def test_bare_fences_no_lang_detected(self) -> None:
        content = "```\ncode1\n```\n\n```\ncode2\n```"
        hits = detect_consecutive_same_lang_fences(content)
        assert len(hits) >= 1

    def test_single_fence_passes(self) -> None:
        content = "## Example\n\n```python\nimport aspose\n```\n\nDone."
        hits = detect_consecutive_same_lang_fences(content)
        assert hits == []


# ═════════════════════════════════════════════════════════════════════════════
# 4. Mandatory Sections Invariant
# ═════════════════════════════════════════════════════════════════════════════


class TestMandatorySectionsInvariant:
    """Invariant: page_plan must contain mandatory blog and KB how-to pages."""

    # ── Blog mandatory ───────────────────────────────────────────────────

    def test_blog_both_roles_present_passes(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        _write_page_plan(run_dir, [
            {"section": "blog", "page_role": "blog", "slug": "launch-post"},
            {"section": "blog", "page_role": "feature_blog", "slug": "feature-post"},
        ])
        ok, issues = blog_execute_gate(run_dir, "ci")
        assert ok is True
        assert issues == []

    def test_blog_missing_feature_blog_fails(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        _write_page_plan(run_dir, [
            {"section": "blog", "page_role": "blog", "slug": "launch-post"},
        ])
        ok, issues = blog_execute_gate(run_dir, "ci")
        assert ok is False
        assert any("feature_blog" in i["message"] for i in issues)

    def test_blog_missing_launch_fails(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        _write_page_plan(run_dir, [
            {"section": "blog", "page_role": "feature_blog", "slug": "feature-post"},
        ])
        ok, issues = blog_execute_gate(run_dir, "ci")
        assert ok is False

    # ── KB how-to mandatory ──────────────────────────────────────────────

    def test_kb_all_categories_present_passes(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        _write_page_plan(run_dir, _all_required_kb_pages())
        ok, issues = kb_execute_gate(run_dir, "ci")
        assert ok is True

    def test_kb_too_few_pages_fails(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        _write_page_plan(run_dir, [
            _kb_page("how-to-open-file", "load_file"),
        ])
        ok, issues = kb_execute_gate(run_dir, "ci")
        assert ok is False
        assert any("minimum" in i["message"].lower() for i in issues)

    def test_kb_missing_topic_category_fails(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        # 5 pages but missing 'troubleshoot'
        pages = [
            _kb_page("s1", "load_file"),
            _kb_page("s2", "save_file"),
            _kb_page("s3", "convert_formats"),
            _kb_page("s4", "optimize_performance"),
            _kb_page("s5", "load_file"),  # duplicate category, no troubleshoot
        ]
        _write_page_plan(run_dir, pages)
        ok, issues = kb_execute_gate(run_dir, "ci")
        assert ok is False
        assert any("troubleshoot" in i["message"] for i in issues)

    def test_empty_page_plan_fails_both(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        _write_page_plan(run_dir, [])
        blog_ok, _ = blog_execute_gate(run_dir, "ci")
        kb_ok, _ = kb_execute_gate(run_dir, "ci")
        assert blog_ok is False
        assert kb_ok is False
