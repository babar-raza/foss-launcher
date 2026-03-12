"""Tests for page role validation in PlannerWorker.self_review() (P7A-01 G-01)."""

import pytest

from launcher.models.plan import PlanBundle, PlannedPage
from launcher.workers.planner.worker import PlannerWorker
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS


def _make_bundle(pages: list[PlannedPage]) -> PlanBundle:
    """Build a minimal PlanBundle from the given pages."""
    claim_index: dict[str, list[str]] = {}
    for page in pages:
        for cid in page.assigned_claims:
            claim_index.setdefault(cid, []).append(page.page_id)
    return PlanBundle(pages=pages, claim_assignment_index=claim_index)


def _valid_page(page_id: str = "page-1") -> PlannedPage:
    """Create a PlannedPage with a valid role and at least one claim."""
    return PlannedPage(
        page_id=page_id,
        page_role="workflow_page",
        title=f"Test Page {page_id}",  # unique per page_id — avoids title_uniqueness finding
        assigned_claims=["CLM-0001"],
    )


class TestPlannerRoleValidation:
    """Tests for invalid_role detection in PlannerWorker.self_review()."""

    @pytest.mark.asyncio
    async def test_valid_roles_self_review_passes(self):
        """PlanBundle with all valid page_roles → self_review has no high-severity findings."""
        bundle = _make_bundle([_valid_page("page-1"), _valid_page("page-2")])
        worker = PlannerWorker()
        result = await worker.self_review(bundle)
        high_findings = [f for f in result.findings if f.get("severity") == "high"]
        assert not high_findings, f"Unexpected high findings: {high_findings}"

    @pytest.mark.asyncio
    async def test_invalid_role_produces_finding(self):
        """A page with an unregistered page_role produces an invalid_role finding."""
        bad_page = PlannedPage(
            page_id="bad-role-page",
            page_role="nonexistent_role_abc",
            title="Bad Role Page",
            assigned_claims=["CLM-0002"],
        )
        bundle = _make_bundle([_valid_page("good-page"), bad_page])
        worker = PlannerWorker()
        result = await worker.self_review(bundle)
        role_findings = [f for f in result.findings if f.get("category") == "invalid_role"]
        assert role_findings, "Expected invalid_role finding for unregistered role"

    @pytest.mark.asyncio
    async def test_invalid_role_sets_passed_false(self):
        """A high-severity invalid_role finding causes passed=False."""
        bad_page = PlannedPage(
            page_id="bad-role-page",
            page_role="totally_fake_role",
            title="Bad Page",
            assigned_claims=["CLM-0003"],
        )
        bundle = _make_bundle([bad_page])
        worker = PlannerWorker()
        result = await worker.self_review(bundle)
        assert result.passed is False, (
            "passed should be False when a high-severity invalid_role finding is present"
        )
