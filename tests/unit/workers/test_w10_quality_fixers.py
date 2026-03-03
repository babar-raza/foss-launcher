"""Unit tests for G1-G7 quality gate fixers and triage routing (TC-3671).

Tests:
- Triage match functions: each G1-G7 error code routes correctly
- Triage rule_id stability: IDs do not change
- G1 fixer: artifact preamble removal (deterministic, idempotent)
- G4 fixer: heading trailing punct removal (deterministic, idempotent)
- G5 fixer: product name canonicalization (deterministic, idempotent)
- Stop-the-line: G2/G3/G6/G7 raise FixerUnfixableError
- End-to-end: gate detects → W10 fixes → gate passes (G1 + G4)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from launch.cli.triage import (
    _match_g1_artifact,
    _match_g2_repetition,
    _match_g3_import,
    _match_g4_structure,
    _match_g5_product_name,
    _match_g6_permalink,
    _match_g7_spec_leak,
    recommend_action,
)
from launch.workers._shared.content_sanitizer import (
    canonicalize_product_names,
    remove_llm_artifact_preambles,
    strip_heading_trailing_punct,
)
from launch.workers.w10_fixer.worker import (
    FixerUnfixableError,
    apply_fix,
    fix_g1_artifact_phrases,
    fix_g4_heading_punct,
    fix_g5_product_name,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_issue(error_code: str, gate: str = "", path: str = "", line: int = 0) -> Dict[str, Any]:
    return {
        "issue_id": f"test_{error_code}",
        "gate": gate,
        "severity": "error",
        "error_code": error_code,
        "message": f"Test issue: {error_code}",
        "location": {"path": path, "line": line} if path else {},
        "status": "OPEN",
    }


def _make_report(issues: List[Dict[str, Any]], gates: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "ok": False,
        "profile": "ci",
        "gates": gates or [],
        "issues": issues,
    }


def _write_md(run_dir: Path, rel_path: str, content: str) -> Path:
    full = run_dir / "work" / "site" / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


def _write_artifact(run_dir: Path, filename: str, data: Any) -> Path:
    art_dir = run_dir / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    p = art_dir / filename
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ── Triage Match Tests ──────────────────────────────────────────────────


class TestTriageMatchG1G7:
    """TC-3671: Triage match functions for G1-G7 error codes."""

    def test_g1_matches_artifact_codes(self):
        assert _match_g1_artifact(_make_issue("G1_PREAMBLE_WHEN_WORKING"), [])
        assert _match_g1_artifact(_make_issue("G1_FILLER_TRANSITION"), [])

    def test_g1_does_not_match_other_codes(self):
        assert not _match_g1_artifact(_make_issue("G2_NEAR_DUPLICATE"), [])
        assert not _match_g1_artifact(_make_issue("SCAFFOLD_XML"), [])

    def test_g2_matches_repetition_codes(self):
        assert _match_g2_repetition(_make_issue("G2_NEAR_DUPLICATE_PARAGRAPHS"), [])

    def test_g2_does_not_match_other_codes(self):
        assert not _match_g2_repetition(_make_issue("G1_PREAMBLE"), [])

    def test_g3_matches_import_codes(self):
        assert _match_g3_import(_make_issue("G3_IMPORT_NOT_ALLOWLISTED"), [])

    def test_g3_does_not_match_other_codes(self):
        assert not _match_g3_import(_make_issue("G4_DUPLICATE_H2"), [])

    def test_g4_matches_structure_codes(self):
        assert _match_g4_structure(_make_issue("G4_HEADING_TRAILING_PUNCT"), [])
        assert _match_g4_structure(_make_issue("G4_DUPLICATE_H2"), [])
        assert _match_g4_structure(_make_issue("G4_SEE_ALSO_NOT_LAST"), [])

    def test_g5_matches_product_name_codes(self):
        assert _match_g5_product_name(_make_issue("G5_MISSPELLED_BRAND"), [])
        assert _match_g5_product_name(_make_issue("G5_DOUBLED_PLATFORM"), [])

    def test_g6_matches_permalink_codes(self):
        assert _match_g6_permalink(_make_issue("G6_PERMALINK_COLLISION"), [])
        assert _match_g6_permalink(_make_issue("G6_DOUBLED_SEGMENT"), [])

    def test_g7_matches_spec_leak_codes(self):
        assert _match_g7_spec_leak(_make_issue("G7_SPEC_LEAKAGE"), [])

    def test_g7_does_not_match_g1(self):
        assert not _match_g7_spec_leak(_make_issue("G1_PREAMBLE"), [])


class TestTriageRuleIdStability:
    """TC-3671: Triage rule_id slugs must be stable."""

    def test_g1_g7_rule_ids_in_recommendations(self, tmp_path):
        run_dir = tmp_path / "run"
        # Create a report with one issue per G-family
        issues = [
            _make_issue("G1_PREAMBLE_WHEN_WORKING", "gate_llm_artifact_phrases"),
            _make_issue("G4_HEADING_TRAILING_PUNCT", "gate_section_structure"),
            _make_issue("G5_MISSPELLED_BRAND", "gate_product_name_integrity"),
            _make_issue("G2_NEAR_DUPLICATE_PARAGRAPHS", "gate_intra_page_repetition"),
            _make_issue("G3_IMPORT_NOT_ALLOWLISTED", "gate_api_import_allowlist"),
            _make_issue("G6_PERMALINK_COLLISION", "gate_permalink_uniqueness"),
            _make_issue("G7_SPEC_LEAKAGE", "gate_spec_leakage"),
        ]
        report = _make_report(issues)
        recs = recommend_action(run_dir, report)

        # All G-family rules route to W10, so only one W10 rec (first match wins)
        rec_ids = [r["id"] for r in recs]
        # The first G-family match should be g1_artifact (listed first in rules)
        assert any("g1_artifact" in rid for rid in rec_ids)

    def test_stable_rule_id_format(self, tmp_path):
        run_dir = tmp_path / "run"
        issues = [_make_issue("G1_PREAMBLE_WHEN_WORKING", "gate_llm_artifact_phrases")]
        report = _make_report(issues)
        recs = recommend_action(run_dir, report)

        # Find the G1 recommendation
        g_recs = [r for r in recs if "g1_artifact" in r["id"]]
        assert len(g_recs) == 1
        assert g_recs[0]["id"] == "triage:g1_artifact->W10"


# ── Sanitizer Function Tests ────────────────────────────────────────────


class TestRemoveLlmArtifactPreambles:
    """TC-3671: remove_llm_artifact_preambles() sanitizer."""

    def test_removes_when_working_with(self):
        content = "## Overview\n\nWhen working with Aspose.Cells for Python, you can...\n\nReal content here."
        result = remove_llm_artifact_preambles(content)
        assert "When working with" not in result
        assert "Real content here." in result

    def test_removes_in_this_article(self):
        content = "In this article, we will explore the features.\n\nActual content."
        result = remove_llm_artifact_preambles(content)
        assert "In this article" not in result
        assert "Actual content." in result

    def test_removes_lets_explore(self):
        content = "Let's explore the API surface.\n\nUseful info."
        result = remove_llm_artifact_preambles(content)
        assert "Let's explore" not in result
        assert "Useful info." in result

    def test_preserves_code_fences(self):
        content = "## Code\n\n```python\nWhen working with files, use open():\n```\n\nEnd."
        result = remove_llm_artifact_preambles(content)
        assert "When working with files" in result  # Inside fence, preserved

    def test_preserves_frontmatter(self):
        content = "---\ntitle: When working with Cells\n---\n\nContent."
        result = remove_llm_artifact_preambles(content)
        assert "When working with Cells" in result  # Inside frontmatter

    def test_idempotent(self):
        content = "When working with Aspose.\n\nReal."
        first = remove_llm_artifact_preambles(content)
        second = remove_llm_artifact_preambles(first)
        assert first == second

    def test_clean_content_unchanged(self):
        content = "## Overview\n\nAspose.Cells provides spreadsheet APIs.\n\n## See Also"
        result = remove_llm_artifact_preambles(content)
        assert result == content


class TestStripHeadingTrailingPunct:
    """TC-3671: strip_heading_trailing_punct() sanitizer."""

    def test_strips_trailing_period(self):
        content = "## Quick Start.\n\nContent here."
        result = strip_heading_trailing_punct(content)
        assert "## Quick Start\n" in result

    def test_strips_trailing_comma(self):
        content = "## Overview,\n\nContent."
        result = strip_heading_trailing_punct(content)
        assert "## Overview\n" in result

    def test_strips_trailing_semicolon(self):
        content = "### Methods;\n\nList."
        result = strip_heading_trailing_punct(content)
        assert "### Methods\n" in result

    def test_preserves_clean_headings(self):
        content = "## Clean Heading\n\nText."
        result = strip_heading_trailing_punct(content)
        assert result == content

    def test_preserves_question_mark(self):
        # Question marks in FAQ headings should be preserved (not in the punct set)
        content = "## How do I convert files?\n\nAnswer."
        result = strip_heading_trailing_punct(content)
        assert "?" in result

    def test_preserves_code_fences(self):
        content = "```\n## Heading.\n```"
        result = strip_heading_trailing_punct(content)
        assert "## Heading." in result  # Inside fence, preserved

    def test_idempotent(self):
        content = "## See Also.\n\nLinks."
        first = strip_heading_trailing_punct(content)
        second = strip_heading_trailing_punct(first)
        assert first == second

    def test_multiple_trailing_punct(self):
        content = "## Title...\n\nText."
        result = strip_heading_trailing_punct(content)
        assert "## Title\n" in result


class TestCanonicalizeProductNames:
    """TC-3671: canonicalize_product_names() sanitizer."""

    def test_fixes_aspire_misspelling(self):
        content = "Use Aspire.Cells for spreadsheet manipulation."
        result = canonicalize_product_names(content)
        assert "Aspose.Cells" in result
        assert "Aspire" not in result

    def test_fixes_aspuse_misspelling(self):
        content = "Aspuse.Note helps with document processing."
        result = canonicalize_product_names(content)
        assert "Aspose.Note" in result

    def test_fixes_doubled_platform(self):
        content = "Aspose.Cells for Python for Python is great."
        result = canonicalize_product_names(content)
        assert "for Python for Python" not in result
        assert "for Python" in result

    def test_preserves_correct_names(self):
        content = "Aspose.Cells for Python provides APIs."
        result = canonicalize_product_names(content)
        assert result == content

    def test_preserves_code_fences(self):
        content = "```\nAspire.Cells\n```"
        result = canonicalize_product_names(content)
        assert "Aspire.Cells" in result  # Inside fence, preserved

    def test_preserves_frontmatter(self):
        content = "---\ntitle: Aspire.Cells\n---\n\nContent."
        result = canonicalize_product_names(content)
        assert "Aspire.Cells" in result  # Inside frontmatter, preserved

    def test_idempotent(self):
        content = "Aspire.Note is a library."
        first = canonicalize_product_names(content)
        second = canonicalize_product_names(first)
        assert first == second

    def test_case_insensitive_brand(self):
        content = "aspire.cells is used for spreadsheets."
        result = canonicalize_product_names(content)
        assert "Aspose.cells" in result


# ── W10 Fixer Handler Tests ─────────────────────────────────────────────


class TestFixG1ArtifactPhrases:
    """TC-3671: fix_g1_artifact_phrases() W10 handler."""

    def test_fixes_artifact_preambles(self, tmp_path):
        _write_md(
            tmp_path,
            "content/guide.md",
            "## Guide\n\nWhen working with Aspose.Cells, you can do things.\n\nActual guide content.",
        )
        result = fix_g1_artifact_phrases(
            _make_issue("G1_PREAMBLE_WHEN_WORKING"), tmp_path, None
        )
        assert result["fixed"] is True
        assert len(result["files_changed"]) == 1
        # Verify the file was actually modified
        fixed_content = Path(result["files_changed"][0]).read_text(encoding="utf-8")
        assert "When working with" not in fixed_content
        assert "Actual guide content." in fixed_content

    def test_no_op_when_clean(self, tmp_path):
        _write_md(tmp_path, "content/clean.md", "## Clean\n\nGood content here.")
        result = fix_g1_artifact_phrases(
            _make_issue("G1_PREAMBLE_WHEN_WORKING"), tmp_path, None
        )
        assert result["fixed"] is False

    def test_missing_site_dir(self, tmp_path):
        result = fix_g1_artifact_phrases(
            _make_issue("G1_PREAMBLE"), tmp_path, None
        )
        assert result["fixed"] is False


class TestFixG4HeadingPunct:
    """TC-3671: fix_g4_heading_punct() W10 handler."""

    def test_fixes_trailing_period(self, tmp_path):
        _write_md(
            tmp_path,
            "content/page.md",
            "## Quick Start.\n\nContent.\n\n## See Also.\n\nLinks.",
        )
        result = fix_g4_heading_punct(
            _make_issue("G4_HEADING_TRAILING_PUNCT"), tmp_path, None
        )
        assert result["fixed"] is True
        fixed_content = Path(result["files_changed"][0]).read_text(encoding="utf-8")
        assert "## Quick Start\n" in fixed_content
        assert "## See Also\n" in fixed_content

    def test_no_op_when_clean(self, tmp_path):
        _write_md(tmp_path, "content/clean.md", "## Clean\n\nContent.")
        result = fix_g4_heading_punct(
            _make_issue("G4_HEADING_TRAILING_PUNCT"), tmp_path, None
        )
        assert result["fixed"] is False


class TestFixG5ProductName:
    """TC-3671: fix_g5_product_name() W10 handler."""

    def test_fixes_misspelled_brand(self, tmp_path):
        _write_md(
            tmp_path,
            "content/page.md",
            "## Overview\n\nAspire.Cells is a spreadsheet library.",
        )
        _write_artifact(tmp_path, "product_facts.json", {"product_name": "Aspose.Cells for Python"})
        result = fix_g5_product_name(
            _make_issue("G5_MISSPELLED_BRAND"), tmp_path, None
        )
        assert result["fixed"] is True
        fixed_content = Path(result["files_changed"][0]).read_text(encoding="utf-8")
        assert "Aspose.Cells" in fixed_content
        assert "Aspire" not in fixed_content

    def test_no_op_when_clean(self, tmp_path):
        _write_md(tmp_path, "content/page.md", "## Overview\n\nAspose.Cells works great.")
        result = fix_g5_product_name(
            _make_issue("G5_MISSPELLED_BRAND"), tmp_path, None
        )
        assert result["fixed"] is False


# ── Stop-the-line Tests ─────────────────────────────────────────────────


class TestStopTheLine:
    """TC-3671: Stop-the-line behavior for G2/G3/G6/G7."""

    def test_g2_raises_unfixable(self, tmp_path):
        with pytest.raises(FixerUnfixableError, match="Stop-the-line"):
            apply_fix(_make_issue("G2_NEAR_DUPLICATE_PARAGRAPHS"), tmp_path, None)

    def test_g3_raises_unfixable(self, tmp_path):
        with pytest.raises(FixerUnfixableError, match="Stop-the-line"):
            apply_fix(_make_issue("G3_IMPORT_NOT_ALLOWLISTED"), tmp_path, None)

    def test_g6_raises_unfixable(self, tmp_path):
        with pytest.raises(FixerUnfixableError, match="Stop-the-line"):
            apply_fix(_make_issue("G6_PERMALINK_COLLISION"), tmp_path, None)

    def test_g7_raises_unfixable(self, tmp_path):
        with pytest.raises(FixerUnfixableError, match="Stop-the-line"):
            apply_fix(_make_issue("G7_SPEC_LEAKAGE"), tmp_path, None)

    def test_stop_the_line_error_message_includes_code(self, tmp_path):
        with pytest.raises(FixerUnfixableError, match="G2_NEAR_DUPLICATE"):
            apply_fix(_make_issue("G2_NEAR_DUPLICATE_PARAGRAPHS"), tmp_path, None)


# ── apply_fix Routing Tests ─────────────────────────────────────────────


class TestApplyFixRouting:
    """TC-3671: apply_fix() routes G1-G7 error codes correctly."""

    def test_g1_routes_to_fixer(self, tmp_path):
        _write_md(
            tmp_path,
            "content/page.md",
            "When working with Aspose, you should know.\n\nReal content.",
        )
        result = apply_fix(_make_issue("G1_PREAMBLE_WHEN_WORKING"), tmp_path, None)
        assert result["fixed"] is True

    def test_g4_routes_to_fixer(self, tmp_path):
        _write_md(tmp_path, "content/page.md", "## Title.\n\nContent.")
        result = apply_fix(_make_issue("G4_HEADING_TRAILING_PUNCT"), tmp_path, None)
        assert result["fixed"] is True

    def test_g5_routes_to_fixer(self, tmp_path):
        _write_md(tmp_path, "content/page.md", "Aspire.Cells is great.")
        result = apply_fix(_make_issue("G5_MISSPELLED_BRAND"), tmp_path, None)
        assert result["fixed"] is True

    def test_legacy_scaffold_still_routes(self, tmp_path):
        """Ensure existing SCAFFOLD_ routing is not broken."""
        _write_md(tmp_path, "content/page.md", "<instructions>hidden</instructions>\n\nReal content.")
        result = apply_fix(_make_issue("SCAFFOLD_XML_TAG"), tmp_path, None)
        assert result["fixed"] is True


# ── End-to-End: Gate Detects → W10 Fixes → Gate Passes ──────────────────


class TestGateFixGateE2E:
    """TC-3671: End-to-end test: gate detects → W10 fixes → gate passes."""

    def test_g1_gate_fix_gate_cycle(self, tmp_path):
        """G1 artifact detected → fix applied → gate passes."""
        from launch.workers.w9_validator.gates.gate_llm_artifact_phrases import (
            execute_gate as g1_gate,
        )

        # Setup: content with G1 artifact
        _write_md(
            tmp_path,
            "content/guide.md",
            (
                "## Guide\n\n"
                "When working with Aspose.Cells for Python, you need to understand the API.\n\n"
                "The library provides spreadsheet manipulation features."
            ),
        )

        # Step 1: Gate detects issue
        passed, issues = g1_gate(tmp_path, "ci")
        assert not passed, "Gate should FAIL before fix"
        assert any(i["error_code"].startswith("G1_") for i in issues)

        # Step 2: Fix applied
        result = fix_g1_artifact_phrases(
            _make_issue("G1_PREAMBLE_WHEN_WORKING"), tmp_path, None
        )
        assert result["fixed"] is True

        # Step 3: Gate passes after fix
        passed_after, issues_after = g1_gate(tmp_path, "ci")
        assert passed_after, f"Gate should PASS after fix, but got issues: {issues_after}"

    def test_g4_gate_fix_gate_cycle(self, tmp_path):
        """G4 heading punct detected → fix applied → gate passes."""
        from launch.workers.w9_validator.gates.gate_section_structure import (
            execute_gate as g4_gate,
        )

        # Setup: content with trailing punct on heading
        _write_md(
            tmp_path,
            "content/page.md",
            "## Quick Start.\n\nContent here.\n\n## See Also\n\nLinks.",
        )

        # Step 1: Gate detects issue
        passed, issues = g4_gate(tmp_path, "ci")
        assert not passed, "Gate should FAIL before fix"
        assert any(i["error_code"] == "G4_HEADING_TRAILING_PUNCT" for i in issues)

        # Step 2: Fix applied
        result = fix_g4_heading_punct(
            _make_issue("G4_HEADING_TRAILING_PUNCT"), tmp_path, None
        )
        assert result["fixed"] is True

        # Step 3: Gate passes after fix
        passed_after, issues_after = g4_gate(tmp_path, "ci")
        assert passed_after, f"Gate should PASS after fix, but got issues: {issues_after}"

    def test_g5_gate_fix_gate_cycle(self, tmp_path):
        """G5 product name error detected → fix applied → gate passes."""
        from launch.workers.w9_validator.gates.gate_product_name_integrity import (
            execute_gate as g5_gate,
        )

        # Setup: content with misspelled brand
        _write_md(
            tmp_path,
            "content/page.md",
            "## Overview\n\nAspire.Cells provides powerful spreadsheet APIs.",
        )
        _write_artifact(tmp_path, "product_facts.json", {"product_name": "Aspose.Cells for Python"})

        # Step 1: Gate detects issue
        passed, issues = g5_gate(tmp_path, "ci")
        assert not passed, "Gate should FAIL before fix"
        assert any(i["error_code"].startswith("G5_") for i in issues)

        # Step 2: Fix applied
        result = fix_g5_product_name(
            _make_issue("G5_MISSPELLED_BRAND"), tmp_path, None
        )
        assert result["fixed"] is True

        # Step 3: Gate passes after fix
        passed_after, issues_after = g5_gate(tmp_path, "ci")
        # Filter to only G5 issues (original space corruption uses profile-based severity)
        g5_issues = [i for i in issues_after if i.get("error_code", "").startswith("G5_")]
        assert not g5_issues, f"G5 issues should be fixed, but got: {g5_issues}"
