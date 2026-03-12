"""TC-4055: Tests for topic filter starvation fallback in _assign_claims().

When _TOPIC_KEYWORDS filter is active and all eligible (kind-filtered) candidate
claims fail keyword matching, _assign_claims() must fall back to eligible_kinds-only
and log a WARNING, rather than silently producing 0 claims.

Note: starvation only fires when eligible claims (passing kind filter) are blocked
by the topic filter. Claims that fail the kind filter do not trigger starvation.
"""
from __future__ import annotations

import logging

import pytest

from launcher.models.claims import Claim


def _make_page(slug: str, role: str, topic_category=None) -> dict:
    return {
        "page_id": slug,
        "slug": slug,
        "page_role": role,
        "mandatory": True,
        "topic_category": topic_category,
    }


def _make_claim(claim_id: str, text: str, kind: str = "workflow") -> Claim:
    # Default kind="workflow" is eligible for workflow_page role
    return Claim(claim_id=claim_id, text=text, kind=kind)


# Texts that have NONE of formula_calculation keywords:
# {"formula", "calculat", "comput", "function", "sum"}
# Carefully verified: no substring matches.
_NO_FORMULA_TEXTS = [
    "Loading binary data streams efficiently",
    "Provides workbook editing capabilities",
    "Supports rendering charts to images",
    "Encoding configuration for output paths",
]


class TestTopicFilterStarvation:
    """_assign_claims() starvation guard (TC-4055)."""

    def test_starvation_triggers_fallback(self):
        """All eligible claims fail formula_calculation keyword -> fallback assigns them."""
        from launcher.workers.planner.plan import _assign_claims

        page = _make_page("formula-calculation", "workflow_page", topic_category="formula_calculation")
        # kind="workflow" is eligible for workflow_page; texts have NO formula keywords
        claims = [_make_claim(f"C{i}", t, kind="workflow") for i, t in enumerate(_NO_FORMULA_TEXTS)]
        pages, _ = _assign_claims([page], claims, [])
        assert len(pages) == 1
        assert len(pages[0].assigned_claims) > 0, (
            "Starvation fallback must assign claims when keyword filter starves the page"
        )

    def test_starvation_logs_warning(self, caplog):
        """Starvation triggers a WARNING log with slug and topic info."""
        from launcher.workers.planner.plan import _assign_claims

        page = _make_page("formula-calculation", "workflow_page", topic_category="formula_calculation")
        claims = [_make_claim("C1", "Loading binary data streams efficiently", kind="workflow")]
        with caplog.at_level(logging.WARNING, logger="launcher.workers.planner.plan"):
            _assign_claims([page], claims, [])

        assert any("topic_filter_starvation" in r.message for r in caplog.records), (
            "Expected WARNING with 'topic_filter_starvation' in message"
        )

    def test_starvation_marks_page(self):
        """Page dict gets _topic_filter_relaxed=True when fallback fires."""
        from launcher.workers.planner.plan import _assign_claims

        page = _make_page("formula-calculation", "workflow_page", topic_category="formula_calculation")
        claims = [_make_claim("C1", "Supports rendering charts to images", kind="workflow")]
        _assign_claims([page], claims, [])
        assert page.get("_topic_filter_relaxed") is True

    def test_normal_filter_path_unchanged(self):
        """Claims that match topic keywords are assigned normally; no fallback."""
        from launcher.workers.planner.plan import _assign_claims

        page = _make_page("formula-calculation", "workflow_page", topic_category="formula_calculation")
        claims = [
            _make_claim("C1", "How to calculate formula results in a spreadsheet", kind="workflow"),
            _make_claim("C2", "Supports computing values with built-in function library", kind="workflow"),
        ]
        pages, _ = _assign_claims([page], claims, [])
        assert len(pages[0].assigned_claims) == 2
        assert not page.get("_topic_filter_relaxed", False)

    def test_no_topic_filter_no_starvation_check(self):
        """Pages without topic_category are never subject to starvation guard."""
        from launcher.workers.planner.plan import _assign_claims

        page = _make_page("some-page", "howto_article", topic_category=None)
        # kind="tutorial" is eligible for howto_article
        claims = [_make_claim("C1", "General workflow description", kind="tutorial")]
        pages, _ = _assign_claims([page], claims, [])
        assert len(pages[0].assigned_claims) > 0
        assert not page.get("_topic_filter_relaxed", False)

    def test_ineligible_kind_does_not_trigger_starvation(self):
        """Claims blocked by eligible_kinds (not topic filter) do NOT trigger starvation."""
        from launcher.workers.planner.plan import _assign_claims

        page = _make_page("formula-calculation", "workflow_page", topic_category="formula_calculation")
        # kind="feature" is NOT eligible for workflow_page — blocked by eligible_kinds, not topic
        claims = [
            _make_claim("C1", "Spreadsheet processing capability", kind="feature"),
            _make_claim("C2", "Formula evaluation support", kind="feature"),
        ]
        pages, _ = _assign_claims([page], claims, [])
        # No starvation fallback -- ineligible kinds, not topic-filtered
        assert not page.get("_topic_filter_relaxed", False)
        assert len(pages[0].assigned_claims) == 0
