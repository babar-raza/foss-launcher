"""Tests for TC-5195: assigned_claim_ids wired in GeneratedPage constructor.

Verifies that:
1. GeneratedPage has an assigned_claim_ids field accepting the planner's full list.
2. assigned_claim_count reflects len(assigned_claim_ids), not len(claim_ids_used).
3. assigned_claim_ids is always a superset of (or equal to) claim_ids_used.
"""
from __future__ import annotations

from launcher.models.content import GeneratedPage


class TestAssignedClaimIdsWiring:
    """TC-5195: assigned_claim_ids must carry the planner's full claim list."""

    def test_assigned_claim_ids_field_exists(self) -> None:
        """GeneratedPage must have an assigned_claim_ids field."""
        page = GeneratedPage(slug="test", page_role="guide", section="docs")
        assert hasattr(page, "assigned_claim_ids")
        assert page.assigned_claim_ids == []

    def test_assigned_claim_ids_populated(self) -> None:
        """assigned_claim_ids stores the full planner claim list."""
        assigned = ["c-001", "c-002", "c-003", "c-004"]
        cited = ["c-001", "c-003"]

        page = GeneratedPage(
            slug="test-guide",
            page_role="guide",
            section="docs",
            claim_ids_used=cited,
            assigned_claim_ids=assigned,
            assigned_claim_count=len(assigned),
        )

        assert page.assigned_claim_ids == assigned
        assert page.claim_ids_used == cited

    def test_assigned_claim_count_matches_assigned_not_cited(self) -> None:
        """assigned_claim_count must equal len(assigned_claim_ids), not len(claim_ids_used)."""
        assigned = ["c-001", "c-002", "c-003", "c-004", "c-005"]
        cited = ["c-002", "c-004"]

        page = GeneratedPage(
            slug="test-ref",
            page_role="reference",
            section="reference",
            claim_ids_used=cited,
            assigned_claim_ids=assigned,
            assigned_claim_count=len(assigned),
        )

        assert page.assigned_claim_count == 5
        assert page.assigned_claim_count == len(page.assigned_claim_ids)
        assert page.assigned_claim_count != len(page.claim_ids_used)

    def test_assigned_superset_of_cited(self) -> None:
        """assigned_claim_ids must be a superset of claim_ids_used (invariant)."""
        assigned = ["c-001", "c-002", "c-003"]
        cited = ["c-001", "c-003"]

        page = GeneratedPage(
            slug="test",
            page_role="guide",
            section="docs",
            claim_ids_used=cited,
            assigned_claim_ids=assigned,
            assigned_claim_count=len(assigned),
        )

        assert set(page.claim_ids_used).issubset(set(page.assigned_claim_ids))
        assert page.assigned_claim_count >= len(page.claim_ids_used)

    def test_no_claims_assigned(self) -> None:
        """Pages with zero assigned claims should have empty lists and count=0."""
        page = GeneratedPage(
            slug="overview",
            page_role="landing",
            section="products",
            claim_ids_used=[],
            assigned_claim_ids=[],
            assigned_claim_count=0,
        )

        assert page.assigned_claim_ids == []
        assert page.claim_ids_used == []
        assert page.assigned_claim_count == 0

    def test_all_assigned_claims_cited(self) -> None:
        """When all assigned claims are cited, counts must match."""
        claims = ["c-010", "c-020"]
        page = GeneratedPage(
            slug="full-cite",
            page_role="guide",
            section="docs",
            claim_ids_used=claims,
            assigned_claim_ids=claims,
            assigned_claim_count=len(claims),
        )

        assert page.assigned_claim_count == len(page.claim_ids_used)
        assert page.assigned_claim_ids == page.claim_ids_used
