"""Tests for evidence packs and post-draft consistency (TC-2482/2483).

Validates:
- _build_evidence_packs() builds per-section packs from outline + context
- _check_draft_consistency() detects missing claims, leaked claims, version mismatches
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest


@dataclass
class MockRichContext:
    """Minimal RichContext mock for evidence pack tests."""
    page_claims: List[Dict[str, Any]] = field(default_factory=list)
    relevant_snippets: List[Dict[str, Any]] = field(default_factory=list)

    def to_prompt_vars(self):
        return {"claims": "", "snippets": "", "cross_page_summaries": ""}


@pytest.fixture
def orchestrator():
    """Create a MultiPassOrchestrator with mocked dependencies."""
    from src.launch.workers.w5_section_writer.multi_pass import MultiPassOrchestrator

    mock_llm = MagicMock()
    mock_prompt_loader = MagicMock()
    orch = MultiPassOrchestrator(mock_llm, mock_prompt_loader, run_config={})
    return orch


# ── _build_evidence_packs ────────────────────────────────────────────────────

class TestBuildEvidencePacks:
    def test_builds_one_pack_per_section(self, orchestrator):
        outline = {
            "sections": [
                {"heading": "Goal", "level": 2, "claim_ids": ["c1"]},
                {"heading": "Steps", "level": 2, "claim_ids": ["c2", "c3"]},
                {"heading": "See Also", "level": 2, "claim_ids": []},
            ]
        }
        rich_ctx = MockRichContext(
            page_claims=[
                {"claim_id": "c1", "claim_text": "Feature A"},
                {"claim_id": "c2", "claim_text": "Feature B"},
                {"claim_id": "c3", "claim_text": "Feature C"},
            ],
            relevant_snippets=[
                {"snippet_id": "s1", "language": "python", "code": "import x"},
            ],
        )
        page = {"slug": "test-page"}

        packs = orchestrator._build_evidence_packs(outline, rich_ctx, page)

        assert len(packs) == 3
        assert packs[0]["heading"] == "Goal"
        assert "c1" in packs[0]["claim_ids"]
        assert packs[1]["heading"] == "Steps"

    def test_packs_include_canonical_facts(self, orchestrator):
        orchestrator._shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
            "package_name": "aspose-3d",
            "installation_method": "pip install aspose-3d",
            "supported_formats": ["FBX", "OBJ"],
            "product_slug": "3d",  # should be excluded from canonical
        }
        outline = {"sections": [{"heading": "Test", "level": 2, "claim_ids": []}]}
        rich_ctx = MockRichContext()
        page = {"slug": "test"}

        packs = orchestrator._build_evidence_packs(outline, rich_ctx, page)

        assert len(packs) == 1
        canon = packs[0]["canonical_facts"]
        assert "runtime_versions" in canon
        assert "package_name" in canon
        assert "product_slug" not in canon  # excluded

    def test_packs_include_forbidden_topics(self, orchestrator):
        outline = {"sections": [{"heading": "Test", "level": 2, "claim_ids": []}]}
        rich_ctx = MockRichContext()
        page = {
            "slug": "test",
            "content_strategy": {"forbidden_topics": ["pricing", "licensing"]},
        }

        packs = orchestrator._build_evidence_packs(outline, rich_ctx, page)

        assert packs[0]["forbidden_topics"] == ["pricing", "licensing"]

    def test_empty_outline_returns_empty(self, orchestrator):
        packs = orchestrator._build_evidence_packs(
            {"sections": []}, MockRichContext(), {"slug": "test"}
        )
        assert packs == []

    def test_none_outline_returns_empty(self, orchestrator):
        packs = orchestrator._build_evidence_packs(
            None, MockRichContext(), {"slug": "test"}
        )
        assert packs == []


# ── _check_draft_consistency ─────────────────────────────────────────────────

class TestCheckDraftConsistency:
    def test_clean_draft_no_violations(self, orchestrator):
        draft = (
            "## Goal\n"
            "<!-- claim: c1 --> Feature A.\n"
            "## Steps\n"
            "<!-- claim: c2 --> Feature B.\n"
        )
        packs = [
            {"claim_ids": ["c1"]},
            {"claim_ids": ["c2"]},
        ]
        violations = orchestrator._check_draft_consistency(draft, packs, {})
        assert violations == []

    def test_missing_claims_detected(self, orchestrator):
        draft = "## Goal\nNo claim markers here.\n"
        packs = [
            {"claim_ids": ["c1", "c2", "c3", "c4"]},
        ]
        violations = orchestrator._check_draft_consistency(draft, packs, {})
        assert any("MISSING_CLAIMS" in v for v in violations)

    def test_leaked_claims_detected(self, orchestrator):
        draft = (
            "## Goal\n"
            "<!-- claim: c1 --> Feature A.\n"
            "<!-- claim: c99 --> Leaked claim.\n"
        )
        packs = [{"claim_ids": ["c1"]}]
        violations = orchestrator._check_draft_consistency(draft, packs, {})
        assert any("LEAKED_CLAIMS" in v for v in violations)

    def test_version_mismatch_detected(self, orchestrator):
        orchestrator._shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
        }
        draft = "## Prerequisites\nRequires Python 3.5+.\n"
        packs = [{"claim_ids": []}]
        violations = orchestrator._check_draft_consistency(draft, packs, {})
        assert any("CORRECTION" in v and "3.5" in v for v in violations)

    def test_version_match_no_violation(self, orchestrator):
        orchestrator._shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
        }
        draft = "## Prerequisites\nRequires Python 3.8+.\n"
        packs = [{"claim_ids": []}]
        violations = orchestrator._check_draft_consistency(draft, packs, {})
        assert not any("CORRECTION" in v and "version" in v.lower() for v in violations)

    def test_adjacent_version_tolerance(self, orchestrator):
        """Python 3.9 vs canonical 3.8 is within tolerance (±1 minor)."""
        orchestrator._shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
        }
        draft = "Supports Python 3.9 and above.\n"
        packs = [{"claim_ids": []}]
        violations = orchestrator._check_draft_consistency(draft, packs, {})
        assert not any("CORRECTION" in v and "version" in v.lower() for v in violations)

    def test_no_shared_facts_skips_version_check(self, orchestrator):
        orchestrator._shared_facts = {}
        draft = "Requires Python 2.7.\n"
        packs = [{"claim_ids": []}]
        violations = orchestrator._check_draft_consistency(draft, packs, {})
        assert not any("CORRECTION" in v and "version" in v.lower() for v in violations)

    def test_empty_packs_no_violations(self, orchestrator):
        violations = orchestrator._check_draft_consistency("some content", [], {})
        assert violations == []

    def test_partial_claim_coverage_under_threshold(self, orchestrator):
        """Less than 50% missing claims should NOT trigger MISSING_CLAIMS."""
        draft = (
            "<!-- claim: c1 --> A.\n"
            "<!-- claim: c2 --> B.\n"
            "<!-- claim: c3 --> C.\n"
        )
        packs = [{"claim_ids": ["c1", "c2", "c3", "c4"]}]
        violations = orchestrator._check_draft_consistency(draft, packs, {})
        # 1 out of 4 missing = 25% < 50% threshold
        assert not any("MISSING_CLAIMS" in v for v in violations)
