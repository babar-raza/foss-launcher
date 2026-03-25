"""Tests for TC-PLAN-204: completeness.missing_signals surfacing into evidence_missing.

Verifies that extraction_db.completeness.missing_signals are merged into
every PlannedPage.evidence_missing so the Generate worker can activate
the THIN EVIDENCE strategy when evidence is structurally sparse.
"""

from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.product import ProductIdentity, RichnessResult, RichnessTier
from launcher.models.understanding import ExtractionCompleteness, ExtractionDatabase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="Aspose.Cells for Python",
        canonical_import="aspose.cells",
        repo_url="https://github.com/example",
    )


def _make_richness(tier: str = "B") -> RichnessResult:
    return RichnessResult(tier=RichnessTier(tier), score=15, reason="test")


def _make_claim(claim_id: str, kind: str = "feature", text: str = "feature claim") -> Claim:
    return Claim(claim_id=claim_id, text=text, kind=kind)


def _make_extraction_db(missing_signals: list[str]) -> ExtractionDatabase:
    completeness = ExtractionCompleteness(missing_signals=missing_signals)
    return ExtractionDatabase(completeness=completeness)


def _run(claims, extraction_db=None):
    from launcher.workers.planner.plan import run_plan
    product = _make_product()
    richness = _make_richness("B")
    pages, _ = run_plan(
        product, richness, claims, [],
        extraction_db=extraction_db,
    )
    return pages


# ---------------------------------------------------------------------------
# Tests: completeness signals merging
# ---------------------------------------------------------------------------

class TestCompletenessSignals:
    def test_signals_added_to_all_pages(self):
        """When extraction_db has missing_signals, ALL surviving pages get them."""
        claims = [_make_claim(f"CLM-{i}") for i in range(5)]
        db = _make_extraction_db(["no_formats", "thin_api"])
        pages = _run(claims, db)

        assert len(pages) > 0
        for page in pages:
            assert "no_formats" in page.evidence_missing, (
                f"Page {page.page_id} (role={page.page_role}) missing 'no_formats' signal"
            )
            assert "thin_api" in page.evidence_missing, (
                f"Page {page.page_id} (role={page.page_role}) missing 'thin_api' signal"
            )

    def test_no_extraction_db_leaves_evidence_missing_unchanged(self):
        """When extraction_db is None, evidence_missing is not modified."""
        claims = [_make_claim(f"CLM-{i}") for i in range(5)]
        pages_with_db = _run(claims, _make_extraction_db(["no_formats"]))
        pages_without_db = _run(claims, None)

        # Pages without db should NOT have completeness signals
        for page in pages_without_db:
            assert "no_formats" not in page.evidence_missing

        # Pages with db SHOULD have the signal
        for page in pages_with_db:
            assert "no_formats" in page.evidence_missing

    def test_empty_missing_signals_leaves_evidence_missing_unchanged(self):
        """When completeness.missing_signals is empty, no signals are added."""
        claims = [_make_claim(f"CLM-{i}") for i in range(5)]
        db = _make_extraction_db([])  # empty missing_signals
        pages = _run(claims, db)

        # Evidence missing may have signals from page_evidence_index, but not from completeness
        # (We just check no unexpected completeness signals appear)
        for page in pages:
            # These would only come from completeness signals — should be absent
            assert "no_snippets" not in page.evidence_missing
            assert "thin_api" not in page.evidence_missing

    def test_deduplication_no_repeated_signals(self):
        """If a signal already appears in evidence_missing (from page_evidence_index),
        it should not be duplicated by the completeness surfacing block."""
        # We can't easily pre-inject page_evidence_index signals, but we can
        # verify that passing the same signal in missing_signals twice produces
        # only one occurrence in the final evidence_missing list.
        claims = [_make_claim(f"CLM-{i}") for i in range(5)]
        db = _make_extraction_db(["no_formats", "no_formats"])  # duplicate input
        pages = _run(claims, db)

        for page in pages:
            count = page.evidence_missing.count("no_formats")
            assert count <= 1, (
                f"Page {page.page_id}: 'no_formats' appears {count} times in evidence_missing"
            )

    def test_backward_compatible_without_extraction_db(self):
        """run_plan with no extraction_db keyword still works (backward compat)."""
        from launcher.workers.planner.plan import run_plan
        product = _make_product()
        richness = _make_richness("B")
        claims = [_make_claim(f"CLM-{i}") for i in range(5)]
        # No extraction_db argument at all
        pages, claim_index = run_plan(product, richness, claims, [])
        assert isinstance(pages, list)
        assert len(pages) > 0
        # No completeness signals should appear
        for page in pages:
            assert "no_formats" not in page.evidence_missing
            assert "thin_api" not in page.evidence_missing

    def test_single_signal_all_pages(self):
        """A single signal is correctly distributed to all pages."""
        claims = [_make_claim(f"CLM-{i}") for i in range(5)]
        db = _make_extraction_db(["no_snippets"])
        pages = _run(claims, db)

        assert len(pages) > 0
        for page in pages:
            assert "no_snippets" in page.evidence_missing
