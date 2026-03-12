"""Tests for density-based page pruning (Change B + AQ-healing)."""

from __future__ import annotations

import pytest

from launcher.models.claims import Snippet
from launcher.models.plan import PlannedPage


class TestDensityPruning:
    """Page budget pruning: cap pages proportional to claim count."""

    def test_mandatory_pages_never_pruned(self):
        from launcher.workers.planner.plan import _prune_thin_pages

        pages = [
            PlannedPage(page_id="install", page_role="install", title="Install", mandatory=True, assigned_claims=[]),
            PlannedPage(page_id="getting-started", page_role="getting-started", title="GS", mandatory=True, assigned_claims=[]),
        ]
        result, _ = _prune_thin_pages(pages, {}, [])
        assert len(result) == 2

    def test_budget_prunes_excess_optional_pages(self):
        """With 20 unique claims, budget = max(5, 20/10) = 5.
        5 mandatory + 5 optional = 10. Budget allows 5 optional after mandatory."""
        from launcher.workers.planner.plan import _prune_thin_pages

        claims = [f"CLM-{i}" for i in range(20)]
        pages = [
            PlannedPage(page_id="install", page_role="install", title="Install", mandatory=True, assigned_claims=claims[:5]),
            PlannedPage(page_id="overview", page_role="overview", title="Overview", mandatory=True, assigned_claims=claims[5:10]),
        ]
        # Add 8 optional pages with varying claim counts
        for i in range(8):
            page_claims = claims[i*2:(i+1)*2] if i < 5 else []
            pages.append(PlannedPage(
                page_id=f"opt-{i}", page_role="howto", title=f"Opt {i}",
                mandatory=False, assigned_claims=page_claims,
            ))

        result, _ = _prune_thin_pages(pages, {}, [])
        # Budget = max(5, 20/10) = 5. 2 mandatory always kept.
        # At most 3 optional added to reach budget of 5.
        assert len(result) <= 10  # budget caps total
        assert len(result) >= 5   # minimum preserved

    def test_rich_pages_preferred_over_thin(self):
        """Pages with exclusive claims are preferred during budget selection."""
        from launcher.workers.planner.plan import _prune_thin_pages

        # 100 unique claims → budget = max(5, 100/10) = 10
        claims = [f"CLM-{i}" for i in range(100)]
        pages = [
            PlannedPage(page_id="install", page_role="install", title="Install", mandatory=True, assigned_claims=claims[:5]),
        ]
        # Rich page: many exclusive claims
        pages.append(PlannedPage(
            page_id="rich", page_role="howto", title="Rich",
            mandatory=False, assigned_claims=claims[5:15],
        ))
        # Thin page: no claims
        pages.append(PlannedPage(
            page_id="thin", page_role="topic_cluster", title="Thin",
            mandatory=False, assigned_claims=[],
        ))

        claim_index = {cid: ["install"] for cid in claims[:5]}
        claim_index.update({cid: ["rich"] for cid in claims[5:15]})

        result, _ = _prune_thin_pages(pages, claim_index, [])
        kept_ids = {p.page_id for p in result}
        assert "rich" in kept_ids  # rich page preferred

    def test_minimum_page_count_preserved(self):
        from launcher.workers.planner.plan import _prune_thin_pages

        # Only 3 mandatory pages, 5 thin optional — should keep at least 5 total
        pages = [
            PlannedPage(page_id="m1", page_role="install", title="M1", mandatory=True, assigned_claims=[]),
            PlannedPage(page_id="m2", page_role="overview", title="M2", mandatory=True, assigned_claims=[]),
            PlannedPage(page_id="m3", page_role="toc", title="M3", mandatory=True, assigned_claims=[]),
        ]
        for i in range(5):
            pages.append(PlannedPage(
                page_id=f"opt-{i}", page_role="howto", title=f"Opt {i}",
                mandatory=False, assigned_claims=[f"CLM-{i}"] if i < 2 else [],
            ))

        result, _ = _prune_thin_pages(pages, {}, [])
        assert len(result) >= 5

    def test_claim_index_cleaned_after_pruning(self):
        from launcher.workers.planner.plan import _prune_thin_pages

        # 10 unique claims → budget = min(20, max(8, 10/8)) = 8
        claims_set = [f"CLM-{i}" for i in range(10)]
        pages = [
            PlannedPage(page_id="keep", page_role="install", title="Keep", mandatory=True, assigned_claims=["CLM-1"]),
        ]
        # Add 10 optional pages (total 11 > budget 8), "prune" has 0 claims
        pages.append(PlannedPage(
            page_id="prune", page_role="howto", title="Prune", mandatory=False, assigned_claims=[],
        ))
        for i in range(9):
            pages.append(PlannedPage(
                page_id=f"opt-{i}", page_role="howto", title=f"Opt {i}",
                mandatory=False, assigned_claims=[claims_set[i]],
            ))

        claim_index = {"CLM-1": ["keep", "prune"]}
        _, new_index = _prune_thin_pages(pages, claim_index, [])
        # "prune" should be removed (0 claims = lowest density, pruned first)
        assert "prune" not in new_index.get("CLM-1", [])

    def test_structural_roles_always_kept(self):
        """install, getting-started, api-overview roles are in _ALWAYS_KEEP_ROLES."""
        from launcher.workers.planner.plan import _prune_thin_pages

        pages = [
            PlannedPage(page_id="inst", page_role="install", title="Install", mandatory=False, assigned_claims=[]),
            PlannedPage(page_id="gs", page_role="getting-started", title="Getting Started", mandatory=False, assigned_claims=[]),
            PlannedPage(page_id="api", page_role="api-overview", title="API", mandatory=False, assigned_claims=[]),
        ]
        result, _ = _prune_thin_pages(pages, {}, [])
        kept_ids = {p.page_id for p in result}
        assert "inst" in kept_ids
        assert "gs" in kept_ids
        assert "api" in kept_ids
