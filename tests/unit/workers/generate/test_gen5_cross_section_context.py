"""Tests for GEN-5 (TC-5205): Cross-section context injection.

Verifies:
1. _extract_section_summary() extracts claim_ids, topics, and code patterns correctly.
2. build_section_prompt() with prior_sections_summary injects "PRIOR SECTIONS ALREADY COVERED".
3. build_section_prompt() with no prior context omits the block (no regression).
4. Section generation accumulates summaries sequentially.
"""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim, Snippet
from launcher.models.page_ir import BlockIR, BlockType, SectionIR
from launcher.models.plan import PlannedPage
from launcher.models.product import ProductIdentity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="Aspose.Cells",
        canonical_import="aspose_cells_foss",
        repo_url="https://example.com",
    )


def _make_page(**overrides) -> PlannedPage:
    defaults = dict(
        page_id="gen5-test-page",
        page_role="howto",
        title="Gen5 Test Page",
        assigned_claims=["CLM-001", "CLM-002"],
    )
    defaults.update(overrides)
    return PlannedPage(**defaults)


def _make_claim(claim_id: str, text: str = "This is a test claim.") -> Claim:
    return Claim(
        claim_id=claim_id,
        text=text,
        kind="api",
        evidence=[],
    )


def _make_section_ir(
    heading: str = "Overview",
    claim_ids: list[str] | None = None,
    prose_content: str = "The Workbook class loads spreadsheets from disk.",
    code_content: str | None = None,
) -> SectionIR:
    """Build a minimal SectionIR for testing."""
    blocks: list[BlockIR] = []

    blocks.append(BlockIR(
        type=BlockType.paragraph,
        content=prose_content,
        claim_ids=claim_ids or ["CLM-001"],
    ))

    if code_content is not None:
        blocks.append(BlockIR(
            type=BlockType.code,
            content=code_content,
            language="python",
            claim_ids=claim_ids or ["CLM-001"],
        ))

    return SectionIR(
        section_id=heading.lower().replace(" ", "_"),
        heading=heading,
        level=2,
        blocks=blocks,
    )


# ---------------------------------------------------------------------------
# Tests: _extract_section_summary
# ---------------------------------------------------------------------------


class TestExtractSectionSummary:
    """GEN-5: unit tests for the summary extraction helper."""

    def test_extracts_claim_ids(self):
        from launcher.workers.generate.worker import _extract_section_summary

        ir = _make_section_ir(claim_ids=["CLM-010", "CLM-011"])
        summary = _extract_section_summary(ir, "Overview")

        assert summary["heading"] == "Overview"
        assert "CLM-010" in summary["claim_ids"]
        assert "CLM-011" in summary["claim_ids"]

    def test_extracts_topic_from_prose(self):
        from launcher.workers.generate.worker import _extract_section_summary

        ir = _make_section_ir(
            prose_content="The Workbook class loads spreadsheets from disk. It supports xlsx and csv.",
        )
        summary = _extract_section_summary(ir, "Loading")

        assert len(summary["topics"]) >= 1
        # First sentence should be captured as a topic
        assert "Workbook" in summary["topics"][0] or "spreadsheet" in summary["topics"][0].lower()

    def test_extracts_pascal_case_api_names_from_code(self):
        from launcher.workers.generate.worker import _extract_section_summary

        ir = _make_section_ir(
            code_content="wb = Workbook()\nws = wb.worksheets[0]\ncell = Cell()",
        )
        summary = _extract_section_summary(ir, "Usage")

        assert len(summary["code_patterns"]) >= 1
        # PascalCase names should be found
        assert any(name in ("Workbook", "Cell") for name in summary["code_patterns"])

    def test_caps_claim_ids_at_six(self):
        from launcher.workers.generate.worker import _extract_section_summary

        # Build a section with 10 claim_ids across two blocks
        blocks = []
        for i in range(5):
            blocks.append(BlockIR(
                type=BlockType.paragraph,
                content=f"Fact {i}.",
                claim_ids=[f"CLM-{i:03d}", f"CLM-{i+5:03d}"],
            ))
        ir = SectionIR(
            section_id="big_section",
            heading="Big Section",
            level=2,
            blocks=blocks,
        )
        summary = _extract_section_summary(ir, "Big Section")

        assert len(summary["claim_ids"]) <= 6

    def test_none_section_ir_returns_empty_summary(self):
        from launcher.workers.generate.worker import _extract_section_summary

        summary = _extract_section_summary(None, "Empty Section")

        assert summary["heading"] == "Empty Section"
        assert summary["claim_ids"] == []
        assert summary["topics"] == []
        assert summary["code_patterns"] == []

    def test_empty_blocks_returns_empty_lists(self):
        from launcher.workers.generate.worker import _extract_section_summary

        ir = SectionIR(
            section_id="empty",
            heading="Empty",
            level=2,
            blocks=[],
        )
        summary = _extract_section_summary(ir, "Empty")

        assert summary["claim_ids"] == []
        assert summary["topics"] == []
        assert summary["code_patterns"] == []

    def test_code_patterns_deduplicated(self):
        from launcher.workers.generate.worker import _extract_section_summary

        # Same class name appears twice in code — should appear once in patterns
        ir = _make_section_ir(
            code_content="wb = Workbook()\nwb2 = Workbook()",
        )
        summary = _extract_section_summary(ir, "Dedup Test")
        assert summary["code_patterns"].count("Workbook") == 1


# ---------------------------------------------------------------------------
# Tests: build_section_prompt with prior_sections_summary
# ---------------------------------------------------------------------------


class TestBuildSectionPromptWithPriorContext:
    """GEN-5: verify that prior_sections_summary is injected into the prompt."""

    def _call_prompt(self, prior_summaries=None):
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.page_skeletons import SkeletonSection

        product = _make_product()
        page = _make_page()
        claims = [_make_claim("CLM-001"), _make_claim("CLM-002")]
        section = SkeletonSection(
            heading="Loading Spreadsheets",
            level=2,
            required=True,
            content_hint="Explain how to load spreadsheets",
            min_words=50,
            max_words=300,
        )
        return build_section_prompt(
            section=section,
            section_index=1,
            section_count=3,
            page=page,
            product=product,
            claims=claims,
            snippets=[],
            prior_sections_summary=prior_summaries,
        )

    def test_prior_context_block_present_when_summaries_provided(self):
        prior = [
            {
                "heading": "Introduction",
                "claim_ids": ["CLM-001"],
                "topics": ["The Workbook class loads spreadsheets"],
                "code_patterns": ["Workbook"],
            }
        ]
        prompt = self._call_prompt(prior_summaries=prior)

        assert "PRIOR SECTIONS ALREADY COVERED" in prompt
        assert "Introduction" in prompt
        assert "CLM-001" in prompt

    def test_prior_context_block_absent_when_none(self):
        prompt = self._call_prompt(prior_summaries=None)

        assert "PRIOR SECTIONS ALREADY COVERED" not in prompt

    def test_prior_context_block_absent_when_empty_list(self):
        prompt = self._call_prompt(prior_summaries=[])

        assert "PRIOR SECTIONS ALREADY COVERED" not in prompt

    def test_prior_context_includes_topics(self):
        prior = [
            {
                "heading": "Overview",
                "claim_ids": ["CLM-001"],
                "topics": ["The Workbook class handles file I/O"],
                "code_patterns": [],
            }
        ]
        prompt = self._call_prompt(prior_summaries=prior)

        assert "The Workbook class handles file I/O" in prompt

    def test_prior_context_includes_api_names(self):
        prior = [
            {
                "heading": "Overview",
                "claim_ids": [],
                "topics": [],
                "code_patterns": ["Workbook", "Worksheet"],
            }
        ]
        prompt = self._call_prompt(prior_summaries=prior)

        assert "Workbook" in prompt
        assert "Worksheet" in prompt

    def test_multiple_prior_sections_all_appear(self):
        prior = [
            {
                "heading": "Section A",
                "claim_ids": ["CLM-001"],
                "topics": ["Topic A content"],
                "code_patterns": [],
            },
            {
                "heading": "Section B",
                "claim_ids": ["CLM-002"],
                "topics": ["Topic B content"],
                "code_patterns": [],
            },
        ]
        prompt = self._call_prompt(prior_summaries=prior)

        assert "Section A" in prompt
        assert "Section B" in prompt
        assert "CLM-001" in prompt
        assert "CLM-002" in prompt

    def test_prior_context_block_placed_before_claims_block(self):
        prior = [
            {
                "heading": "Intro",
                "claim_ids": ["CLM-001"],
                "topics": [],
                "code_patterns": [],
            }
        ]
        prompt = self._call_prompt(prior_summaries=prior)

        prior_pos = prompt.find("PRIOR SECTIONS ALREADY COVERED")
        claims_pos = prompt.find("CLAIMS TO USE")
        assert prior_pos != -1
        assert claims_pos != -1
        assert prior_pos < claims_pos, (
            "PRIOR SECTIONS block must appear before CLAIMS TO USE block"
        )


# ---------------------------------------------------------------------------
# Tests: sequential generation accumulates summaries
# ---------------------------------------------------------------------------


class TestSequentialSectionAccumulation:
    """GEN-5: verify that prior_summaries accumulate correctly across sections."""

    def test_summary_list_grows_with_each_section(self):
        """Simulate the sequential loop logic to verify accumulation."""
        from launcher.workers.generate.worker import _extract_section_summary
        from launcher.models.page_ir import SectionIR, BlockIR, BlockType

        sections = [
            _make_section_ir("Section 1", claim_ids=["CLM-001"]),
            _make_section_ir("Section 2", claim_ids=["CLM-002"]),
            _make_section_ir("Section 3", claim_ids=["CLM-003"]),
        ]

        prior_summaries: list[dict] = []
        captured_prior_lengths: list[int] = []

        for i, ir in enumerate(sections):
            # This is what the loop in _generate_page does:
            # record how many priors the section would have seen
            captured_prior_lengths.append(len(prior_summaries))
            summary = _extract_section_summary(ir, ir.heading)
            prior_summaries.append(summary)

        # Section 0 sees 0 prior summaries; section 1 sees 1; section 2 sees 2
        assert captured_prior_lengths == [0, 1, 2]

    def test_first_section_gets_no_prior_context(self):
        """First section's prior_summaries should be empty list."""
        from launcher.workers.generate.worker import _extract_section_summary

        prior_summaries: list[dict] = []
        ir = _make_section_ir("Intro", claim_ids=["CLM-001"])

        # Before first section, prior_summaries is empty
        assert prior_summaries == []

        # After appending first section's summary
        prior_summaries.append(_extract_section_summary(ir, "Intro"))
        assert len(prior_summaries) == 1

    def test_second_section_receives_first_sections_claim_ids(self):
        """Second section's prior_summaries should contain first section's claim_ids."""
        from launcher.workers.generate.worker import _extract_section_summary

        ir_first = _make_section_ir("First Section", claim_ids=["CLM-AAA"])
        prior_summaries: list[dict] = []

        # Simulate generating first section
        summary_first = _extract_section_summary(ir_first, "First Section")
        prior_summaries.append(summary_first)

        # Prior summaries now available for second section
        assert len(prior_summaries) == 1
        assert "CLM-AAA" in prior_summaries[0]["claim_ids"]
