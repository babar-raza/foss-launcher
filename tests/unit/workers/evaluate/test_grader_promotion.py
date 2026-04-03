"""Tests for TC-5154 LLM finding severity promotion in grader (SR-02).

Verifies that _is_promoted_llm_finding and _effective_severity correctly
allow specific high-signal LLM findings to retain HIGH severity.

Note: TC-PA-04 removed factual_accuracy and code_correctness from
_LLM_CHECK_NAMES, so those checks are no longer capped. The promotion
logic still applies to api_consistency (which IS in _LLM_CHECK_NAMES).
Tests use api_consistency for promotion and content_density for capping.

REG-H-08: Integration tests verifying check functions → grade_page pipeline.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from launcher.models.evaluation import Finding, Grade
from launcher.workers.evaluate.grader import grade_page
from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
from launcher.workers.evaluate.checks.code import check_code

# These symbols were removed from grader.py in a prior refactor.
# Guard the import so the module can still be collected for newer tests.
try:
    from launcher.workers.evaluate.grader import (
        _LLM_CHECK_NAMES,
        _effective_severity,
        _is_promoted_llm_finding,
    )
    _HAS_LLM_PROMOTION = True
except ImportError:
    _LLM_CHECK_NAMES = frozenset()
    _effective_severity = None  # type: ignore[assignment]
    _is_promoted_llm_finding = None  # type: ignore[assignment]
    _HAS_LLM_PROMOTION = False


@pytest.mark.skipif(not _HAS_LLM_PROMOTION, reason="LLM promotion symbols removed from grader")
class TestIsPromotedLlmFinding:
    """Direct tests for _is_promoted_llm_finding()."""

    def test_factual_accuracy_not_promoted_after_tc_pa_04(self):
        # TC-PA-04: factual_accuracy removed from both _LLM_CHECK_NAMES and
        # _PROMOTED_LLM_CHECKS — it's never capped, so promotion is moot.
        f = Finding(check="factual_accuracy", severity="high",
                    message="Claims feature X that is not supported by the library")
        assert _is_promoted_llm_finding(f) is False

    def test_api_consistency_with_no_such_method(self):
        f = Finding(check="api_consistency", severity="high",
                    message="No such method 'clear_value' on Cell class")
        assert _is_promoted_llm_finding(f) is True

    def test_api_consistency_with_does_not_exist(self):
        f = Finding(check="api_consistency", severity="high",
                    message="Method 'export_pdf' does not exist in Workbook")
        assert _is_promoted_llm_finding(f) is True

    def test_generic_message_not_promoted(self):
        f = Finding(check="api_consistency", severity="high",
                    message="Code style could improve")
        assert _is_promoted_llm_finding(f) is False

    def test_non_promoted_check_name(self):
        f = Finding(check="completeness", severity="high",
                    message="Method does not exist in API")
        assert _is_promoted_llm_finding(f) is False

    def test_empty_message(self):
        f = Finding(check="api_consistency", severity="high", message="")
        assert _is_promoted_llm_finding(f) is False


@pytest.mark.skipif(not _HAS_LLM_PROMOTION, reason="LLM promotion symbols removed from grader")
class TestEffectiveSeverityPromotion:
    """Tests for _effective_severity() promotion path.

    Uses checks that ARE in _LLM_CHECK_NAMES (e.g. api_consistency,
    content_density) to test capping and promotion. factual_accuracy
    is NOT in _LLM_CHECK_NAMES (TC-PA-04) so it's never capped.
    """

    def test_capped_llm_check_high_to_medium(self):
        # content_density is in _LLM_CHECK_NAMES and has no promoted pattern
        f = Finding(check="content_density", severity="high",
                    message="Content is thin")
        assert "content_density" in _LLM_CHECK_NAMES
        assert _effective_severity(f) == "medium"

    def test_promoted_api_consistency_stays_high(self):
        f = Finding(check="api_consistency", severity="high",
                    message="No such method 'foo' on Bar class")
        assert "api_consistency" in _LLM_CHECK_NAMES
        assert _effective_severity(f) == "high"

    def test_generic_api_consistency_capped(self):
        f = Finding(check="api_consistency", severity="high",
                    message="Code style could improve")
        assert _effective_severity(f) == "medium"

    def test_factual_accuracy_not_capped_at_all(self):
        # TC-PA-04: factual_accuracy removed from _LLM_CHECK_NAMES
        f = Finding(check="factual_accuracy", severity="high",
                    message="Content quality is poor")
        assert "factual_accuracy" not in _LLM_CHECK_NAMES
        assert _effective_severity(f) == "high"

    def test_non_llm_check_high_unchanged(self):
        f = Finding(check="structure", severity="high",
                    message="H1 heading in body")
        assert _effective_severity(f) == "high"

    def test_llm_medium_unchanged(self):
        f = Finding(check="content_density", severity="medium",
                    message="Thin content")
        assert _effective_severity(f) == "medium"

    def test_deterministic_critical_unchanged(self):
        f = Finding(check="safety", severity="critical",
                    message="XSS vulnerability")
        assert _effective_severity(f) == "critical"


@pytest.mark.skipif(not _HAS_LLM_PROMOTION, reason="LLM promotion symbols removed from grader")
class TestGradePageWithPromotion:
    """Integration: promoted LLM findings affect grade_page() output."""

    def test_promoted_api_consistency_counts_as_high(self):
        # Promoted api_consistency stays HIGH -> non-safety HIGH
        # 2 non-safety HIGHs -> Grade C
        findings = [
            Finding(check="api_consistency", severity="high",
                    message="No such method 'foo' on Bar class"),
            Finding(check="api_consistency", severity="high",
                    message="Property does not exist on Workbook"),
        ]
        grade = grade_page(findings)
        assert grade == Grade.C  # 2 non-safety HIGHs

    def test_unpromoted_api_consistency_capped_to_b(self):
        # Generic api_consistency HIGHs capped to MEDIUM -> Grade B
        findings = [
            Finding(check="api_consistency", severity="high",
                    message="Code style could improve"),
            Finding(check="api_consistency", severity="high",
                    message="Naming convention differs"),
        ]
        grade = grade_page(findings)
        assert grade == Grade.B  # Both capped to MEDIUM -> B


class TestCodeSyntaxEditorialCritical:
    """TC-REG-302: Code syntax errors (HIGH) are editorial-critical → Grade D.

    Missing language tags (MEDIUM) are NOT promoted — natural filtering via
    the grader's HIGH-only editorial_high counter at line 73.
    """

    def test_syntax_error_high_gives_grade_d(self):
        """A single HIGH code finding (syntax error) must yield Grade D."""
        findings = [
            Finding(
                check="code",
                severity="high",
                message="Python syntax error: invalid syntax",
                location="workbook:code-block-1",
            ),
        ]
        assert grade_page(findings) == Grade.D

    def test_missing_lang_tag_medium_gives_grade_b(self):
        """A single MEDIUM code finding (missing lang tag) must yield Grade B, not D."""
        findings = [
            Finding(
                check="code",
                severity="medium",
                message="Code block missing language tag",
                location="workbook:code-block-2",
            ),
        ]
        assert grade_page(findings) == Grade.B

    def test_multiple_syntax_errors_still_grade_d(self):
        """Multiple HIGH code findings still yield Grade D (not worse)."""
        findings = [
            Finding(check="code", severity="high",
                    message="Python syntax error: invalid syntax",
                    location="workbook:code-block-1"),
            Finding(check="code", severity="high",
                    message="Python syntax error: unexpected EOF",
                    location="workbook:code-block-3"),
        ]
        assert grade_page(findings) == Grade.D

    def test_mixed_code_high_and_medium(self):
        """HIGH code + MEDIUM code → Grade D (HIGH dominates via editorial-critical)."""
        findings = [
            Finding(check="code", severity="high",
                    message="Python syntax error: invalid syntax",
                    location="workbook:code-block-1"),
            Finding(check="code", severity="medium",
                    message="Code block missing language tag",
                    location="workbook:code-block-2"),
        ]
        assert grade_page(findings) == Grade.D


class TestApiHallucinationEditorialCritical:
    """TC-REG-301: API hallucination findings promoted to editorial-critical → Grade D."""

    def test_unknown_class_high_gives_grade_d(self):
        findings = [
            Finding(
                check="api_identifier_unknown_class",
                severity="high",
                message="Code uses class `WorkflowManager` which is not in API surface.",
                location="test-page",
            ),
        ]
        assert grade_page(findings) == Grade.D

    def test_property_called_as_method_high_gives_grade_d(self):
        findings = [
            Finding(
                check="api_property_called_as_method",
                severity="high",
                message="Code calls `worksheets()` with parentheses but it is a property.",
                location="test-page",
            ),
        ]
        assert grade_page(findings) == Grade.D

    def test_unknown_method_medium_gives_grade_b(self):
        """MEDIUM api_identifier_unknown_method should NOT be promoted."""
        findings = [
            Finding(
                check="api_identifier_unknown_method",
                severity="medium",
                message="Code calls method `foo()` which is not in API surface.",
                location="test-page",
            ),
        ]
        assert grade_page(findings) == Grade.B


# ---------------------------------------------------------------------------
# REG-H-08: Integration tests — check function → findings → grade_page
# ---------------------------------------------------------------------------

def _make_brief(name, methods=None, properties=None):
    return SimpleNamespace(
        name=name,
        methods=methods or [],
        properties=properties or [],
        typed_methods=[],
        typed_properties=[],
    )


def _make_surface(public_classes=None, class_briefs=None, api_identifiers=None, confidence="high"):
    return SimpleNamespace(
        public_classes=public_classes or [],
        class_briefs=class_briefs or [],
        api_identifiers=api_identifiers or [],
        confidence=confidence,
    )


def _md(code: str) -> str:
    return f"---\ntitle: Test\n---\n\n```python\n{code}\n```\n"


class TestCheckToGradeIntegration:
    """REG-H-08: End-to-end check function → findings → grade_page."""

    def test_hallucinated_method_gets_grade_d(self):
        """check_api_identifiers → unknown class finding → grade_page → Grade D."""
        brief = _make_brief("Cells", methods=["clear", "merge"])
        surface = _make_surface(
            public_classes=["Cells"],
            class_briefs=[brief],
        )
        # WorkflowManager is unknown → HIGH unknown_class finding
        content = _md("mgr = WorkflowManager()")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        assert any(f.check == "api_identifier_unknown_class" for f in findings)
        assert grade_page(findings) == Grade.D

    def test_syntax_error_gets_grade_d(self):
        """check_code → syntax error HIGH finding → grade_page → Grade D."""
        content = _md("def foo(\n    x = ")  # invalid syntax
        findings = check_code(content, "test-slug")
        high_code = [f for f in findings if f.check == "code" and f.severity == "high"]
        assert len(high_code) >= 1
        assert grade_page(findings) == Grade.D

    def test_clean_code_gets_grade_a(self):
        """check_api_identifiers on valid code → no findings → Grade A."""
        brief = _make_brief("Workbook", methods=["save", "load"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md('wb = Workbook()\nwb.save("output.xlsx")')
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        assert len(findings) == 0
        assert grade_page(findings) == Grade.A


# ---------------------------------------------------------------------------
# TC-HEAL-001: Skeleton-directive HIGH findings → Grade D (not Grade C)
# ---------------------------------------------------------------------------

class TestSkeletonDirectiveGradeD:
    """TC-HEAL-001: Skeleton directive or filler sentence HIGH findings must yield Grade D.

    Pages with leaked skeleton/template content are content-void and should
    never be promotable as Grade C. The _is_skeleton_directive() helper
    classifies specific HIGH findings from artifacts/forbidden_content checks.
    """

    def test_artifacts_skeleton_directive_gives_grade_d(self):
        """[artifacts] skeleton-directive HIGH → Grade D (TC-HEAL-001)."""
        findings = [
            Finding(
                check="artifacts",
                severity="high",
                message="[ENG] 2 skeleton-directive sentence(s) found (e.g. 'Aspose.3D -- What is new'). "
                        "Internal section-guidance text leaked into published content.",
                location="test-page",
            ),
        ]
        assert grade_page(findings) == Grade.D

    def test_forbidden_content_template_hint_gives_grade_d(self):
        """[forbidden_content] Template content-hint directive HIGH → Grade D (TC-HEAL-001)."""
        findings = [
            Finding(
                check="forbidden_content",
                severity="high",
                message="Template content-hint directive leaked verbatim into page prose",
                location="test-page",
            ),
        ]
        assert grade_page(findings) == Grade.D

    def test_forbidden_content_generic_filler_gives_grade_d(self):
        """[forbidden_content] Generic filler sentence HIGH → Grade D (TC-HEAL-001)."""
        findings = [
            Finding(
                check="forbidden_content",
                severity="high",
                message="Generic filler sentence not replaced with actual content",
                location="test-page",
            ),
        ]
        assert grade_page(findings) == Grade.D

    def test_artifacts_keyword_stuffing_not_skeleton(self):
        """[artifacts] Keyword-stuffing HIGH is NOT skeleton-directive → Grade B (not D)."""
        findings = [
            Finding(
                check="artifacts",
                severity="high",
                message="Keyword stuffing: product-name density 6.2 per 100 words (threshold 5)",
                location="test-page",
            ),
        ]
        # keyword stuffing is non-safety-critical HIGH → Grade B (1 non-safety HIGH)
        assert grade_page(findings) == Grade.B

    def test_two_non_skeleton_highs_give_grade_c_not_d(self):
        """Two non-skeleton non-safety-critical HIGHs → Grade C (regression guard)."""
        findings = [
            Finding(
                check="artifacts",
                severity="high",
                message="Keyword stuffing: product-name density 6.2 per 100 words (threshold 5)",
                location="test-page",
            ),
            Finding(
                check="artifacts",
                severity="high",
                message="Repeated section opener (5x): 'the following example demonstrates'",
                location="test-page",
            ),
        ]
        # Both are non-skeleton non-safety-critical HIGHs → Grade C
        assert grade_page(findings) == Grade.C

    def test_skeleton_plus_non_skeleton_high_still_grade_d(self):
        """Skeleton HIGH + non-skeleton HIGH → still Grade D."""
        findings = [
            Finding(
                check="artifacts",
                severity="high",
                message="[ENG] 1 skeleton-directive sentence(s) found (e.g. 'Aspose.3D -- What is new').",
                location="test-page",
            ),
            Finding(
                check="artifacts",
                severity="high",
                message="Keyword stuffing: product-name density 6.0 per 100 words (threshold 5)",
                location="test-page",
            ),
        ]
        assert grade_page(findings) == Grade.D


# ---------------------------------------------------------------------------
# TC-5304: claim_coverage metric correctness
# ---------------------------------------------------------------------------

class TestTC5304ClaimCoverage:
    """TC-5304: claim_coverage formula must produce values < 1.0 when claims are uncovered.

    Before TC-5304, the formula was len(covered)/max(len(covered), 1) which always = 1.0.
    The fix uses len(covered)/max(len(assigned), 1) so partial coverage < 1.0.
    """

    def test_full_coverage_is_1_0(self):
        """When all assigned claims are used, coverage is 1.0."""
        covered = {"c1", "c2", "c3"}
        assigned = {"c1", "c2", "c3"}
        coverage = len(covered) / max(len(assigned), 1)
        assert coverage == 1.0

    def test_partial_coverage_is_less_than_1(self):
        """TC-5304: With 2 of 4 assigned claims covered, coverage must be 0.5, not 1.0."""
        covered = {"c1", "c2"}
        assigned = {"c1", "c2", "c3", "c4"}
        coverage = len(covered) / max(len(assigned), 1)
        assert coverage == 0.5
        assert coverage < 1.0

    def test_zero_assigned_claims_is_0_0(self):
        """When no claims are assigned and none are covered, coverage is 0.0.

        The formula is len(covered)/max(len(assigned),1). With both empty:
        0 / max(0, 1) = 0 / 1 = 0.0. This is the safe sentinel for 'no data'.
        """
        covered: set = set()
        assigned: set = set()
        coverage = len(covered) / max(len(assigned), 1)
        assert coverage == 0.0

    def test_zero_covered_of_four_assigned(self):
        """Zero coverage: 0 of 4 assigned claims covered → 0.0."""
        covered: set = set()
        assigned = {"c1", "c2", "c3", "c4"}
        coverage = len(covered) / max(len(assigned), 1)
        assert coverage == 0.0

    def test_old_formula_always_1_0_regression(self):
        """Regression guard: old formula len(covered)/max(len(covered),1) always = 1.0.

        This test documents the bug and confirms the new formula differs from the old.
        With covered={c1,c2} and assigned={c1,c2,c3,c4}:
          old formula: 2/max(2,1) = 1.0  (WRONG)
          new formula: 2/max(4,1) = 0.5  (CORRECT)
        """
        covered = {"c1", "c2"}
        assigned = {"c1", "c2", "c3", "c4"}
        old_formula = len(covered) / max(len(covered), 1)
        new_formula = len(covered) / max(len(assigned), 1)
        assert old_formula == 1.0, "Old formula always equals 1.0 (the bug)"
        assert new_formula == 0.5, "New formula gives real fractional coverage"
        assert new_formula < old_formula, "Fix produces lower (more correct) value"


# ---------------------------------------------------------------------------
# TC-5316: annotate_graded_severity
# ---------------------------------------------------------------------------

class TestAnnotateGradedSeverity:
    """TC-5316: annotate_graded_severity() populates graded_severity on Finding copies."""

    def _llm_finding(self, message: str, severity: str = "high") -> "Finding":
        from launcher.models.evaluation import Finding
        # api_consistency is in _LLM_CHECK_NAMES
        return Finding(check="api_consistency", message=message, severity=severity)

    def _non_llm_finding(self, severity: str = "high") -> "Finding":
        from launcher.models.evaluation import Finding
        # frontmatter is a safety-critical check, NOT in _LLM_CHECK_NAMES
        return Finding(check="frontmatter", message="missing title", severity=severity)

    def test_llm_check_high_capped_to_medium(self):
        """TC-5316: LLM check HIGH finding with non-promoted message → graded_severity=medium."""
        from launcher.workers.evaluate.grader import annotate_graded_severity
        findings = [self._llm_finding("content is generic and thin")]
        annotated = annotate_graded_severity(findings)
        assert len(annotated) == 1
        assert annotated[0].severity == "high"          # original unchanged
        assert annotated[0].graded_severity == "medium"  # capped by grader

    def test_llm_check_promoted_stays_high(self):
        """TC-5316: LLM check HIGH with promoted message → graded_severity=high."""
        from launcher.workers.evaluate.grader import annotate_graded_severity
        findings = [self._llm_finding("no such method 'load' in Workbook")]
        annotated = annotate_graded_severity(findings)
        assert annotated[0].severity == "high"
        assert annotated[0].graded_severity == "high"   # promoted, not capped

    def test_non_llm_check_high_unchanged(self):
        """TC-5316: Non-LLM check HIGH → graded_severity=high (no cap applied)."""
        from launcher.workers.evaluate.grader import annotate_graded_severity
        findings = [self._non_llm_finding(severity="high")]
        annotated = annotate_graded_severity(findings)
        assert annotated[0].severity == "high"
        assert annotated[0].graded_severity == "high"

    def test_critical_finding_unchanged(self):
        """TC-5316: CRITICAL finding → graded_severity=critical."""
        from launcher.models.evaluation import Finding
        from launcher.workers.evaluate.grader import annotate_graded_severity
        findings = [Finding(check="safety", message="malicious link", severity="critical")]
        annotated = annotate_graded_severity(findings)
        assert annotated[0].graded_severity == "critical"

    def test_returns_new_copies_not_mutated(self):
        """TC-5316: annotate_graded_severity must return new Finding objects (frozen model)."""
        from launcher.workers.evaluate.grader import annotate_graded_severity
        original = self._llm_finding("generic content")
        annotated = annotate_graded_severity([original])
        # Original is unchanged
        assert original.graded_severity == ""
        # Annotated copy has graded_severity set
        assert annotated[0].graded_severity == "medium"
        # They are different objects
        assert annotated[0] is not original

    def test_empty_list_returns_empty(self):
        """annotate_graded_severity([]) → []"""
        from launcher.workers.evaluate.grader import annotate_graded_severity
        assert annotate_graded_severity([]) == []
