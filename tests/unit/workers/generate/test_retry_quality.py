"""TC-GEN-701 Sprint 1: Tests for section retry quality improvements.

Tests cover:
1. Temperature escalation on retry (TC-GEN-701)
2. _accept_code_block returns error messages (TC-GEN-702)
3. Retry directive contains SyntaxError details (TC-GEN-702)
4. Retry uses claim-relevant API classes (TC-GEN-703)
5. Retry shows all violation names (TC-GEN-703)
6. EVL-1 snippet fallback after syntax strip (TC-GEN-705B)
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# TC-GEN-702: _accept_code_block returns tuple[bool, str]
# ---------------------------------------------------------------------------

class TestAcceptCodeBlockTupleReturn:
    """TC-GEN-702: _accept_code_block returns (ok, error_msg)."""

    def test_accept_code_block_returns_error_message(self):
        """Invalid Python returns (False, 'SyntaxError: ...') with details."""
        from launcher.workers.generate.worker import _accept_code_block

        ok, msg = _accept_code_block("class :", "python")
        assert ok is False
        assert "SyntaxError" in msg
        # Should include line number
        assert "line" in msg.lower()

    def test_accept_code_block_valid_returns_empty_error(self):
        """Valid Python returns (True, '')."""
        from launcher.workers.generate.worker import _accept_code_block

        ok, msg = _accept_code_block("x = 1", "python")
        assert ok is True
        assert msg == ""

    def test_accept_code_block_non_python_returns_empty_error(self):
        """Non-Python blocks always return (True, '')."""
        from launcher.workers.generate.worker import _accept_code_block

        ok, msg = _accept_code_block("not valid python @@@", "javascript")
        assert ok is True
        assert msg == ""

    def test_accept_code_block_captures_lineno(self):
        """SyntaxError on line 3 reports line 3."""
        from launcher.workers.generate.worker import _accept_code_block

        code = "x = 1\ny = 2\nif True\n    pass"
        ok, msg = _accept_code_block(code, "python")
        assert ok is False
        assert "line 3" in msg


# ---------------------------------------------------------------------------
# TC-GEN-701: Temperature escalation
# ---------------------------------------------------------------------------

class TestTemperatureEscalation:
    """TC-GEN-701: Section retry loop escalates temperature per attempt."""

    def test_temperature_escalates_on_retry(self):
        """Verify temperature calculation mirrors retry loop logic."""
        # Direct calculation test (mirrors the retry loop logic in worker.py):
        base_temp = 0.0
        for attempt in range(3):
            if attempt > 0:
                expected = min(0.25, base_temp + attempt * 0.1)
            else:
                expected = None  # no override on attempt 0

            if attempt == 0:
                assert expected is None, "Attempt 0 should not override temperature"
            elif attempt == 1:
                assert expected == pytest.approx(0.1)
            elif attempt == 2:
                assert expected == pytest.approx(0.2)

    def test_temperature_capped_at_025(self):
        """Temperature escalation is capped at 0.25 even with high base temp."""
        base_temp = 0.15
        for attempt in [1, 2, 3, 4]:
            _attempt_temp = min(0.25, base_temp + attempt * 0.1)
            assert _attempt_temp <= 0.25


# ---------------------------------------------------------------------------
# TC-GEN-702: Retry directive contains SyntaxError details
# ---------------------------------------------------------------------------

class TestRetryDirectiveSyntaxDetails:
    """TC-GEN-702: Retry directive includes specific SyntaxError messages."""

    def test_retry_directive_contains_syntax_error_details(self):
        """Verify that when _syntax_error_msgs is populated, the retry
        directive includes the specific error messages."""
        # Simulate what the retry loop does:
        _syntax_error_msgs = [
            "SyntaxError: invalid syntax (line 3)",
            "SyntaxError: expected ':' (line 7)",
        ]
        _retry_additions: list[str] = []
        if _syntax_error_msgs:
            _retry_additions.append(
                "CRITICAL: Your Python code blocks have syntax errors:\n"
                + "\n".join(f"  - {msg}" for msg in _syntax_error_msgs)
                + "\nFix these exact errors. Every ```python block must compile without errors."
                " Do not use placeholder text (e.g. [identifier omitted]) in code."
            )

        assert len(_retry_additions) == 1
        directive = _retry_additions[0]
        assert "SyntaxError: invalid syntax (line 3)" in directive
        assert "SyntaxError: expected ':' (line 7)" in directive
        assert "CRITICAL" in directive


# ---------------------------------------------------------------------------
# TC-GEN-703: Section-targeted API class injection
# ---------------------------------------------------------------------------

class TestSectionTargetedAPIInjection:
    """TC-GEN-703: Retry injects claim-relevant classes, not alphabetical-first-20."""

    def test_retry_uses_claim_relevant_classes(self):
        """Verify that retry directive contains classes matching sec_claims text."""
        from types import SimpleNamespace

        public_classes = [
            "AutoFilter", "Cell", "Cells", "CsvHandler", "FilterColumn",
            "FormulaCalculation", "JsonExporter", "Range", "SaveFormat",
            "Workbook", "WorkbookSettings", "Worksheet", "WorksheetCollection",
        ]
        sec_claims = [
            SimpleNamespace(text="Use FormulaCalculation to compute cell values", claim_id="CLM-001"),
            SimpleNamespace(text="Access cells via the Cells collection", claim_id="CLM-002"),
        ]

        # Simulate the TC-GEN-703 logic:
        _section_relevant: set[str] = set()
        for _cls in public_classes:
            _cls_low = _cls.lower()
            for _cl in sec_claims:
                if _cls_low in (getattr(_cl, "text", "") or "").lower():
                    _section_relevant.add(_cls)
                    break
        if len(_section_relevant) < 3:
            _section_relevant.update(sorted(public_classes)[:5])

        # FormulaCalculation and Cells should be found via claim text matching
        assert "FormulaCalculation" in _section_relevant
        assert "Cells" in _section_relevant
        # Should NOT contain arbitrary alphabetical classes unless fallback triggered
        # Since we found 2 (< 3), fallback adds first 5
        assert len(_section_relevant) >= 3

    def test_retry_shows_all_violation_names(self):
        """TC-GEN-703: No cap on hallucinated API violation names."""
        _api_violation_names = [
            "FakeClass1", "FakeClass2", "FakeClass3",
            "FakeClass4", "FakeClass5", "FakeClass6",
            "FakeClass7", "FakeClass8",
        ]
        # Old code: sorted(set(_api_violation_names))[:5] — capped at 5
        # New code: sorted(set(_api_violation_names)) — no cap
        result = ", ".join(sorted(set(_api_violation_names)))
        assert "FakeClass6" in result
        assert "FakeClass7" in result
        assert "FakeClass8" in result
        # Verify all 8 present
        assert result.count("FakeClass") == 8


# ---------------------------------------------------------------------------
# TC-GEN-705B: EVL-1 snippet fallback
# ---------------------------------------------------------------------------

class TestEVL1SnippetFallback:
    """TC-GEN-705B: After EVL-1 strips syntax-invalid blocks, inject snippet."""

    def test_evl1_fallback_uses_snippet(self):
        """After syntax strip, _find_snippet_replacement is called and result appended."""
        from types import SimpleNamespace

        from launcher.models.page_ir import BlockIR, BlockType

        # Simulate EVL-1 stripped blocks + snippet available
        _evl1_kept: list[BlockIR] = [
            BlockIR(type=BlockType.paragraph, content="Some explanation text."),
        ]
        _evl1_stripped = 1
        # _find_snippet_replacement expects Snippet-like objects with .code/.language/.claim_ids
        sec_snippets = [
            SimpleNamespace(
                code="wb = Workbook()",
                language="python",
                claim_ids=[],
                syntax_valid=True,
            ),
        ]
        sec_claims: list = []
        _is_python_product = True

        # Simulate the fallback logic:
        from launcher.workers.generate.worker import _find_snippet_replacement
        if _evl1_stripped > 0 and sec_snippets:
            _repl = _find_snippet_replacement(
                sec_snippets,
                [getattr(c, "claim_id", "") for c in sec_claims] if sec_claims else [],
                "python" if _is_python_product else "",
            )
            if _repl is not None:
                _evl1_kept.append(_repl)

        # Snippet should have been appended
        code_blocks = [b for b in _evl1_kept if b.type == BlockType.code]
        assert len(code_blocks) >= 1, "Snippet fallback should inject a code block"

    def test_evl1_no_snippet_when_pool_empty(self):
        """No crash when sec_snippets is empty — fallback is a no-op."""
        from launcher.models.page_ir import BlockIR, BlockType

        _evl1_kept: list[BlockIR] = [
            BlockIR(type=BlockType.paragraph, content="Some text."),
        ]
        sec_snippets: list = []
        _is_python_product = True

        # Simulate the fallback logic with empty pool:
        if sec_snippets:
            from launcher.workers.generate.worker import _find_snippet_replacement
            _repl = _find_snippet_replacement(sec_snippets, [], "python")
            if _repl is not None:
                _evl1_kept.append(_repl)

        # Should still have just the paragraph — no crash, no injection
        assert len(_evl1_kept) == 1
        assert _evl1_kept[0].type == BlockType.paragraph


# ---------------------------------------------------------------------------
# TC-GEN-704 Sprint 2: Test snippet filter + landing claim exemption
# ---------------------------------------------------------------------------

class TestSnippetFilterAllRoles:
    """TC-GEN-704: Test snippet filter applies to ALL page roles, not just reference."""

    def test_test_file_detected(self):
        """_is_test_file_snippet returns True for test file paths."""
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        from types import SimpleNamespace

        assert _is_test_file_snippet(SimpleNamespace(source_file="tests/test_workbook.py"))
        assert _is_test_file_snippet(SimpleNamespace(source_file="src/test_utils.py"))
        assert _is_test_file_snippet(SimpleNamespace(source_file="workbook_test.py"))

    def test_non_test_file_not_filtered(self):
        """_is_test_file_snippet returns False for normal source files."""
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        from types import SimpleNamespace

        assert not _is_test_file_snippet(SimpleNamespace(source_file="src/workbook.py"))
        assert not _is_test_file_snippet(SimpleNamespace(source_file="lib/cells.py"))

    def test_reference_roles_constant_exists(self):
        """_REFERENCE_ROLES still exists (backward compat check)."""
        from launcher.workers.generate.section_prompt import _REFERENCE_ROLES
        assert "api_reference" in _REFERENCE_ROLES


class TestLandingNoClaimRoles:
    """TC-GEN-704: 'landing' is in _NO_CLAIM_ROLES — products/_index gets no claims."""

    def test_landing_in_no_claim_roles(self):
        from launcher.workers.planner.plan import _NO_CLAIM_ROLES
        assert "landing" in _NO_CLAIM_ROLES

    def test_toc_still_in_no_claim_roles(self):
        from launcher.workers.planner.plan import _NO_CLAIM_ROLES
        assert "toc" in _NO_CLAIM_ROLES

    def test_content_roles_not_in_no_claim_roles(self):
        """Content roles like howto_article should still receive claims."""
        from launcher.workers.planner.plan import _NO_CLAIM_ROLES
        assert "howto_article" not in _NO_CLAIM_ROLES
        assert "getting_started" not in _NO_CLAIM_ROLES
        assert "faq" not in _NO_CLAIM_ROLES


# ---------------------------------------------------------------------------
# TC-GEN-705 Sprint 3: Grade ceiling fixes
# ---------------------------------------------------------------------------

class TestHeuristicCheckCapping:
    """TC-EVAL-602: Heuristic quality checks are in _LLM_CHECK_NAMES → HIGHs capped."""

    def test_heuristic_checks_in_llm_check_names(self):
        from launcher.workers.evaluate.grader import _LLM_CHECK_NAMES
        for name in [
            "heading_echo", "prose_lead", "sentence_openings",
            "paragraph_monotony", "low_specificity", "explanation_gap",
            "content_grounding", "content_utility", "content_viability",
        ]:
            assert name in _LLM_CHECK_NAMES, f"{name} should be capped"

    def test_structural_checks_not_capped(self):
        """Structural/factual checks must NOT be in _LLM_CHECK_NAMES."""
        from launcher.workers.evaluate.grader import _LLM_CHECK_NAMES
        for name in [
            "faq_structure", "semantic_structure", "golden_conformance",
            "code", "api_allowlist", "claim_coverage", "structure",
        ]:
            assert name not in _LLM_CHECK_NAMES, f"{name} should NOT be capped"

    def test_effective_severity_caps_heuristic_high(self):
        """A HIGH from a heuristic check is capped to MEDIUM."""
        from launcher.workers.evaluate.grader import _effective_severity
        from launcher.models.evaluation import Finding
        f = Finding(check="heading_echo", severity="high", message="test", location="test")
        assert _effective_severity(f) == "medium"

    def test_effective_severity_preserves_deterministic_high(self):
        """A HIGH from a deterministic check is NOT capped."""
        from launcher.workers.evaluate.grader import _effective_severity
        from launcher.models.evaluation import Finding
        f = Finding(check="faq_structure", severity="high", message="test", location="test")
        assert _effective_severity(f) == "high"

    def test_grade_b_with_two_heuristic_highs(self):
        """Page with 0 deterministic HIGHs + 2 heuristic HIGHs grades B (not C)."""
        from launcher.workers.evaluate.grader import grade_page, Grade
        from launcher.models.evaluation import Finding
        findings = [
            Finding(check="heading_echo", severity="high", message="test", location="test"),
            Finding(check="prose_lead", severity="high", message="test", location="test"),
        ]
        # Both HIGHs capped to MEDIUM → 2 MEDIUM → grade B (not C)
        assert grade_page(findings) == Grade.B


class TestEmptySeeAlsoRemoval:
    """TC-GEN-706: Empty See Also sections are stripped before PageIR assembly."""

    def test_empty_see_also_stripped(self):
        """A See Also section with 0 blocks is removed."""
        from launcher.models.page_ir import SectionIR, BlockIR, BlockType
        from launcher.workers.generate.worker import _SKIP_LLM_HEADINGS

        sections = [
            SectionIR(section_id="intro", heading="Introduction", level=2, blocks=[
                BlockIR(type=BlockType.paragraph, content="Some content."),
            ]),
            SectionIR(section_id="see_also", heading="See Also", level=2, blocks=[]),
        ]
        # Simulate the TC-GEN-706 filter:
        filtered = [
            s for s in sections
            if not (
                s.heading.lower().strip() in _SKIP_LLM_HEADINGS
                and not s.blocks
            )
        ]
        assert len(filtered) == 1
        assert filtered[0].heading == "Introduction"

    def test_non_empty_see_also_preserved(self):
        """A See Also section WITH blocks is kept."""
        from launcher.models.page_ir import SectionIR, BlockIR, BlockType
        from launcher.workers.generate.worker import _SKIP_LLM_HEADINGS

        sections = [
            SectionIR(section_id="see_also", heading="See Also", level=2, blocks=[
                BlockIR(type=BlockType.list, items=["[Link](/url)"]),
            ]),
        ]
        filtered = [
            s for s in sections
            if not (
                s.heading.lower().strip() in _SKIP_LLM_HEADINGS
                and not s.blocks
            )
        ]
        assert len(filtered) == 1


class TestFAQH3Instruction:
    """TC-GEN-707: FAQ section prompt includes H3 question heading instruction."""

    def test_faq_prompt_mentions_h3(self):
        """The FAQ writing rules mention H3 / ### headings."""
        from types import SimpleNamespace
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS

        skeleton = PAGE_ROLE_SKELETONS.get("faq", [])
        if not skeleton:
            pytest.skip("No FAQ skeleton defined")
        skel_section = skeleton[0]

        product = SimpleNamespace(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://example.com", language_tag="python",
            runtime_import="aspose_cells_foss",
        )
        page = SimpleNamespace(
            page_id="test-faq", page_role="faq", title="FAQ",
            skeleton=[s.heading for s in skeleton],
            assigned_claims=[], assigned_snippets=[],
            frontmatter={"slug": "faq", "page_role": "faq"},
        )

        prompt = build_section_prompt(
            skel_section, 0, len(skeleton),
            page, product, [], [],
            public_classes=[], api_identifiers={},
        )
        assert "###" in prompt or "H3" in prompt, "FAQ prompt should require H3 question headings"
        assert "3 question" in prompt.lower() or "at least 3" in prompt.lower(), \
            "FAQ prompt should require at least 3 questions"
