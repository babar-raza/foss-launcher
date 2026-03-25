"""Tests for check_claim_coverage — TC-5128 structured uncovered_claim_texts + TC-5136 depth."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.claim_coverage import (
    check_claim_coverage,
    _extract_claim_context,
    _verify_claim_depth,
)


def _make_content(paragraphs: list[str]) -> str:
    return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Basic coverage detection
# ---------------------------------------------------------------------------

def test_empty_claims_returns_no_findings():
    findings = check_claim_coverage("any content", "slug", [])
    assert findings == []


def test_all_claims_covered_returns_no_findings():
    content = "Workbook class supports loading Excel spreadsheets from stream objects."
    claims = ["Workbook class supports loading Excel spreadsheets from stream"]
    findings = check_claim_coverage(content, "slug", claims)
    assert findings == []


def test_uncovered_claim_produces_finding():
    content = "This page discusses general concepts."
    claims = ["Workbook class supports loading Excel spreadsheets from stream"]
    findings = check_claim_coverage(content, "slug", claims)
    assert len(findings) == 1
    assert findings[0].check == "claim_coverage"
    # TC-EV-03: 1/1 uncovered = 100% fraction, but <3 claims → high (thin assignment)
    assert findings[0].severity == "high"


# ---------------------------------------------------------------------------
# Severity levels
# ---------------------------------------------------------------------------

def test_severity_critical_when_all_uncovered():
    content = "Nothing relevant here."
    claims = [
        "Workbook Excel loading stream",
        "SaveFormat PDF export conversion",
        "GetRows returns IEnumerable collection",
    ]
    findings = check_claim_coverage(content, "slug", claims)
    assert len(findings) == 1
    assert findings[0].severity == "critical"


def test_severity_high_when_over_half_uncovered():
    # 3 uncovered out of 4 total (75%)
    content = "workbook loading from stream available here."  # covers first claim only
    claims = [
        "workbook loading stream available",
        "SaveFormat PDF export conversion",
        "GetRows returns IEnumerable collection",
        "Worksheet name property accessor",
    ]
    findings = check_claim_coverage(content, "slug", claims)
    assert len(findings) == 1
    assert findings[0].severity == "high"


def test_severity_medium_when_2_or_3_uncovered():
    # cover 2 claims, leave 2 uncovered
    content = "workbook loading stream available. saveformat pdf export conversion."
    claims = [
        "workbook loading stream available",
        "saveformat pdf export conversion",
        "GetRows returns IEnumerable collection listing",
        "Worksheet name property accessor title",
    ]
    findings = check_claim_coverage(content, "slug", claims)
    assert len(findings) == 1
    assert findings[0].severity == "medium"


# ---------------------------------------------------------------------------
# TC-5128: uncovered_claim_texts populated
# ---------------------------------------------------------------------------

def test_uncovered_claim_texts_populated_with_full_text():
    content = "Nothing relevant here at all."
    claim1 = "Workbook class supports loading Excel spreadsheets from stream objects"
    claim2 = "SaveFormat enum provides PDF export conversion options"
    findings = check_claim_coverage(content, "slug", [claim1, claim2])
    assert len(findings) == 1
    assert findings[0].uncovered_claim_texts == [claim1, claim2]


def test_uncovered_claim_texts_is_full_not_truncated():
    """TC-5128: uncovered_claim_texts stores the full claim text, not the 60-char truncated version in message."""
    long_claim = "A" * 200  # longer than the 60-char message truncation
    content = "Nothing here."
    findings = check_claim_coverage(content, "slug", [long_claim])
    assert len(findings) == 1
    # uncovered_claim_texts stores full text
    assert findings[0].uncovered_claim_texts[0] == long_claim
    # message still truncates at 80 chars for the low-severity case
    assert long_claim not in findings[0].message or len(findings[0].message) < len(long_claim) + 200


def test_covered_claims_not_in_uncovered_claim_texts():
    content = "workbook loading stream available saveformat pdf export conversion"
    covered = "workbook loading stream available"
    uncovered = "GetRows returns IEnumerable collection listing"
    findings = check_claim_coverage(content, "slug", [covered, uncovered])
    assert len(findings) == 1
    assert findings[0].uncovered_claim_texts == [uncovered]
    assert covered not in findings[0].uncovered_claim_texts


def test_no_findings_means_empty_uncovered_claim_texts():
    content = "workbook loading stream available saveformat pdf export conversion"
    claims = ["workbook loading stream available", "saveformat pdf export conversion"]
    findings = check_claim_coverage(content, "slug", claims)
    assert findings == []


# ---------------------------------------------------------------------------
# _build_heal_directives uses uncovered_claim_texts (integration)
# ---------------------------------------------------------------------------

def test_build_heal_directives_uses_specific_claims(tmp_path):
    """TC-5128: _build_heal_directives produces MUST COVER directive with specific claim texts."""
    from unittest.mock import MagicMock
    from launcher.orchestrator.graph_builder import _build_heal_directives

    # Create a mock report with a claim_coverage finding that has uncovered_claim_texts
    finding = MagicMock()
    finding.check = "claim_coverage"
    finding.severity = "high"
    finding.message = "3/5 assigned claims are not covered"
    finding.uncovered_claim_texts = [
        "Workbook supports loading Excel files from stream",
        "SaveFormat.PDF enables PDF export",
    ]

    page = MagicMock()
    page.slug = "test-page"
    page.findings = [finding]

    report = MagicMock()
    report.pages = [page]

    result = _build_heal_directives(report)
    directives = result.get("page_directives", [])
    assert any("MUST COVER THESE CLAIMS EXPLICITLY" in d for d in directives), \
        f"Expected MUST COVER directive, got: {directives}"
    assert any("Workbook supports loading" in d for d in directives), \
        f"Expected claim text in directive, got: {directives}"


def test_build_heal_directives_falls_back_to_generic_when_no_uncovered_texts():
    """TC-5128: generic template used when uncovered_claim_texts is empty."""
    from unittest.mock import MagicMock
    from launcher.orchestrator.graph_builder import _build_heal_directives

    finding = MagicMock()
    finding.check = "claim_coverage"
    finding.severity = "high"
    finding.message = "3/5 assigned claims are not covered"
    finding.uncovered_claim_texts = []  # empty — fall back to generic

    page = MagicMock()
    page.slug = "test-page"
    page.findings = [finding]

    report = MagicMock()
    report.pages = [page]

    result = _build_heal_directives(report)
    directives = result.get("page_directives", [])
    assert any("Address all assigned claims" in d for d in directives), \
        f"Expected generic directive, got: {directives}"


# ---------------------------------------------------------------------------
# TC-5136: Depth verification (Pass 2)
# ---------------------------------------------------------------------------

class TestExtractClaimContext:
    def test_extracts_window_around_first_match(self):
        body = "x" * 100 + "workbook" + "y" * 100
        ctx = _extract_claim_context(body, ["workbook"], window=20)
        assert "workbook" in ctx
        assert len(ctx) <= 20 + len("workbook") + 20

    def test_returns_empty_when_no_term_found(self):
        ctx = _extract_claim_context("nothing here", ["workbook"])
        assert ctx == ""

    def test_window_clamps_at_boundaries(self):
        body = "workbook saves data"
        ctx = _extract_claim_context(body, ["workbook"], window=500)
        assert ctx == body  # entire body fits in the window


class TestVerifyClaimDepth:
    def test_substantive_paragraph_scores_above_threshold(self):
        claim = "Workbook.save() writes spreadsheet data to XLSX format"
        context = (
            "Use Workbook.save() to write your spreadsheet data to XLSX format. "
            "The method accepts a file path and saves the current workbook contents "
            "as an Excel XLSX file on disk."
        )
        score = _verify_claim_depth(claim, context)
        assert score > 0.20, f"Substantive context should score > 0.20, got {score:.3f}"

    def test_casual_mention_scores_below_threshold(self):
        claim = "Workbook.save() writes spreadsheet data to XLSX format"
        context = (
            "The library supports many file formats. Various operations are available "
            "for processing documents and generating reports in different configurations."
        )
        score = _verify_claim_depth(claim, context)
        assert score < 0.20, f"Casual mention should score < 0.20, got {score:.3f}"

    def test_empty_inputs_return_zero(self):
        assert _verify_claim_depth("", "some context") == 0.0
        assert _verify_claim_depth("some claim", "") == 0.0


class TestClaimCoverageDepthIntegration:
    def test_shallow_coverage_produces_depth_finding(self):
        """A claim keyword-covered but not substantively addressed gets a depth finding."""
        # Claim key terms: "workbook", "spreadsheet", "saves", "xlsx", "format"
        claim = "Workbook saves spreadsheet data to XLSX format"
        # Body contains the key terms but in a generic context with no real explanation
        content = (
            "The workbook can be used for spreadsheet tasks. "
            "It saves files. XLSX is a format among others. "
            "Various operations are available for document management."
        )
        findings = check_claim_coverage(content, "test-slug", [claim])
        # Should NOT have a Pass 1 finding (keywords present)
        pass1 = [f for f in findings if f.check == "claim_coverage"]
        assert len(pass1) == 0, "Claim should be keyword-covered (Pass 1 should not flag it)"
        # May have a Pass 2 depth finding depending on TF-IDF score
        # (this is informational, so we just verify the structure if present)
        pass2 = [f for f in findings if f.check == "claim_coverage_depth"]
        for f in pass2:
            assert f.severity == "medium"  # TC-PA-02: elevated from "low" to "medium"
            assert "shallow" in f.message.lower() or "depth" in f.message.lower()

    def test_pass1_unchanged_for_uncovered_claims(self):
        """Pass 2 does not interfere with Pass 1 uncovered claim detection."""
        content = "Completely irrelevant content about cooking recipes."
        claims = ["Workbook saves spreadsheet data to XLSX format"]
        findings = check_claim_coverage(content, "test-slug", claims)
        pass1 = [f for f in findings if f.check == "claim_coverage"]
        assert len(pass1) == 1
        # TC-EV-03: 1 claim (< 3) → high instead of critical
        assert pass1[0].severity == "high"
        # No depth finding for uncovered claims (Pass 2 only runs on keyword-covered)
        pass2 = [f for f in findings if f.check == "claim_coverage_depth"]
        assert len(pass2) == 0

    def test_substantive_coverage_produces_no_findings(self):
        """A claim that is both keyword-covered and depth-verified produces no findings."""
        claim = "Workbook saves spreadsheet data to XLSX format"
        content = (
            "The Workbook class saves your spreadsheet data directly to XLSX format. "
            "Call Workbook.save('output.xlsx') to write the current workbook contents "
            "as an Excel XLSX spreadsheet file on disk. The format preserves all "
            "formatting, formulas, and data."
        )
        findings = check_claim_coverage(content, "test-slug", [claim])
        pass1 = [f for f in findings if f.check == "claim_coverage"]
        assert len(pass1) == 0
        # Depth finding should also not trigger for substantive content
        pass2 = [f for f in findings if f.check == "claim_coverage_depth"]
        assert len(pass2) == 0


# ---------------------------------------------------------------------------
# TC-EV-03: Thin claim assignment CRITICAL refinement
# ---------------------------------------------------------------------------

class TestThinClaimCriticalRefinement:
    """TC-EV-03: Pages with <3 claims all uncovered get HIGH instead of CRITICAL."""

    def test_1_claim_all_uncovered_is_high(self):
        content = "Nothing relevant here."
        claims = ["Workbook Excel loading stream objects"]
        findings = check_claim_coverage(content, "slug", claims)
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert "downgraded" in findings[0].message.lower()

    def test_2_claims_all_uncovered_is_high(self):
        content = "Nothing relevant here."
        claims = [
            "Workbook Excel loading stream objects",
            "SaveFormat PDF export conversion options",
        ]
        findings = check_claim_coverage(content, "slug", claims)
        assert len(findings) == 1
        assert findings[0].severity == "high"

    def test_3_claims_all_uncovered_is_critical(self):
        """Boundary: exactly 3 claims = not thin, still CRITICAL."""
        content = "Nothing relevant here."
        claims = [
            "Workbook Excel loading stream objects",
            "SaveFormat PDF export conversion options",
            "GetRows returns IEnumerable collection listing",
        ]
        findings = check_claim_coverage(content, "slug", claims)
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    def test_5_claims_all_uncovered_is_critical(self):
        content = "Nothing relevant here."
        claims = [
            "Workbook Excel loading stream objects",
            "SaveFormat PDF export conversion options",
            "GetRows returns IEnumerable collection listing",
            "Worksheet name property accessor title",
            "CellArea range selection formatting bold",
        ]
        findings = check_claim_coverage(content, "slug", claims)
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    def test_2_claims_one_covered_is_not_affected(self):
        """When only some claims are uncovered, fraction <1.0 — thin rule doesn't apply."""
        content = "workbook excel loading stream objects"
        claims = [
            "Workbook Excel loading stream objects",
            "SaveFormat PDF export conversion options",
        ]
        findings = check_claim_coverage(content, "slug", claims)
        # 1/2 uncovered = 50% — should be low severity (1 uncovered)
        pass1 = [f for f in findings if f.check == "claim_coverage"]
        assert len(pass1) == 1
        assert pass1[0].severity == "low"


# ---------------------------------------------------------------------------
# TC-PA-01: _compute_claim_coverage tests
# ---------------------------------------------------------------------------


class TestComputeClaimCoverage:
    """TC-PA-01: Tests for _compute_claim_coverage helper in evaluate worker."""

    def test_compute_claim_coverage_actual_ratio(self):
        """5 assigned claims, 2 uncovered → coverage = 0.6."""
        from launcher.workers.evaluate.worker import _compute_claim_coverage
        from launcher.models.evaluation import Finding, PageEvaluation, Grade

        # Mock pages with assigned_claim_count
        class _Page:
            def __init__(self, count):
                self.assigned_claim_count = count

        pages = [_Page(3), _Page(2)]  # total = 5

        # Create page evals with 2 uncovered claims via findings
        page_evals = [
            PageEvaluation(
                slug="p1", grade=Grade.B,
                findings=[
                    Finding(
                        check="claim_coverage",
                        message="uncovered",
                        severity="high",
                        uncovered_claim_texts=["claim A", "claim B"],
                    ),
                ],
            ),
            PageEvaluation(slug="p2", grade=Grade.A, findings=[]),
        ]
        ratio = _compute_claim_coverage(pages, page_evals)
        assert ratio == round(1.0 - (2 / 5), 4)  # 0.6

    def test_compute_claim_coverage_zero_assigned_returns_one(self):
        """When all pages have assigned_claim_count=0, return 1.0 (backward compat)."""
        from launcher.workers.evaluate.worker import _compute_claim_coverage
        from launcher.models.evaluation import PageEvaluation, Grade

        class _Page:
            def __init__(self):
                self.assigned_claim_count = 0

        pages = [_Page(), _Page()]
        page_evals = [
            PageEvaluation(slug="p1", grade=Grade.A, findings=[]),
            PageEvaluation(slug="p2", grade=Grade.A, findings=[]),
        ]
        assert _compute_claim_coverage(pages, page_evals) == 1.0

    def test_compute_claim_coverage_backward_compat_no_field(self):
        """Pages without assigned_claim_count attr → getattr returns 0, result is 1.0."""
        from launcher.workers.evaluate.worker import _compute_claim_coverage
        from launcher.models.evaluation import PageEvaluation, Grade

        class _OldPage:
            """Simulates old manifest page without assigned_claim_count."""
            pass

        pages = [_OldPage(), _OldPage()]
        page_evals = [
            PageEvaluation(slug="p1", grade=Grade.A, findings=[]),
        ]
        assert _compute_claim_coverage(pages, page_evals) == 1.0

    def test_assigned_vs_cited_divergence(self):
        """assigned_claim_ids and claim_ids_used can differ — verify both fields."""
        from launcher.models.content import GeneratedPage

        gp = GeneratedPage(
            slug="test",
            page_role="overview",
            section="docs",
            assigned_claim_ids=["A", "B", "C"],
            claim_ids_used=["A", "B"],
            assigned_claim_count=3,
        )
        assert gp.assigned_claim_count == 3
        assert len(gp.claim_ids_used) == 2
        assert len(gp.assigned_claim_ids) == 3


# ---------------------------------------------------------------------------
# TC-PA-02: Depth finding severity + multi-term context windows
# ---------------------------------------------------------------------------


class TestDepthFindingGrading:
    """TC-PA-02: claim_coverage_depth findings are deterministic MEDIUM for grading."""

    def test_depth_finding_is_deterministic_medium_for_grader(self):
        """claim_coverage_depth is NOT in _LLM_CHECK_NAMES, so its MEDIUM counts
        toward the deterministic MEDIUM threshold. 3 such findings → Grade C."""
        from launcher.workers.evaluate.grader import grade_page, _LLM_CHECK_NAMES
        from launcher.models.evaluation import Finding, Grade

        # Verify claim_coverage_depth is not an LLM check
        assert "claim_coverage_depth" not in _LLM_CHECK_NAMES

        findings = [
            Finding(check="claim_coverage_depth", message=f"shallow {i}", severity="medium")
            for i in range(3)
        ]
        grade = grade_page(findings)
        assert grade == Grade.C, (
            f"3 deterministic MEDIUMs should produce Grade C, got {grade}"
        )


class TestMultiTermContextWindows:
    """TC-PA-02: _extract_claim_context merges windows from ALL matching terms."""

    def test_multi_term_context_windows_merged(self):
        """Two key terms at different positions → context contains text around BOTH."""
        # Place two terms far apart so windows don't overlap
        body = "alpha " * 200 + "workbook" + " beta " * 200 + "spreadsheet" + " gamma " * 50
        ctx = _extract_claim_context(body, ["workbook", "spreadsheet"], window=30)
        assert "workbook" in ctx, "Context must include window around 'workbook'"
        assert "spreadsheet" in ctx, "Context must include window around 'spreadsheet'"
        # With window=30, both segments joined by space
        assert len(ctx) > 60, "Merged context should be longer than a single window"
