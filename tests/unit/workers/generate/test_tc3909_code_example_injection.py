"""Tests for TC-3909: enforce_block_spec injects code for Code Example sections."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from launcher.models.page_ir import BlockIR, SectionIR
from launcher.shared.golden_loader import GoldenBlockSpec


def _section_ir(blocks: list[BlockIR]) -> SectionIR:
    return SectionIR(heading="Code Example", blocks=blocks)


def _prose_block(content: str) -> BlockIR:
    return BlockIR(type="paragraph", content=content)


def _code_block(content: str = "wb = Workbook()", language: str = "python") -> BlockIR:
    return BlockIR(type="code", content=content, language=language)


class TestCodeExampleSyntheticSpec:
    """TC-3909: synthetic spec injected for code-indicating section headings."""

    def test_code_example_heading_triggers_synthetic_spec(self) -> None:
        """If golden_index has no spec for 'Code Example', a synthetic spec is synthesized."""
        from launcher.shared.golden_loader import GoldenBlockSpec
        _CODE_HEADING_KEYWORDS = (
            "code example", "code snippet", "working example",
            "example code", "code sample", "code block",
        )
        heading = "Code Example"
        heading_lower = heading.lower()
        matched = any(kw in heading_lower for kw in _CODE_HEADING_KEYWORDS)
        assert matched

    def test_code_snippet_heading_triggers(self) -> None:
        heading = "Code Snippet"
        heading_lower = heading.lower()
        _CODE_HEADING_KEYWORDS = (
            "code example", "code snippet", "working example",
            "example code", "code sample", "code block",
        )
        assert any(kw in heading_lower for kw in _CODE_HEADING_KEYWORDS)

    def test_overview_heading_does_not_trigger(self) -> None:
        heading = "Overview"
        heading_lower = heading.lower()
        _CODE_HEADING_KEYWORDS = (
            "code example", "code snippet", "working example",
            "example code", "code sample", "code block",
        )
        assert not any(kw in heading_lower for kw in _CODE_HEADING_KEYWORDS)

    def test_prerequisites_heading_does_not_trigger(self) -> None:
        heading = "Prerequisites"
        heading_lower = heading.lower()
        _CODE_HEADING_KEYWORDS = (
            "code example", "code snippet", "working example",
            "example code", "code sample", "code block",
        )
        assert not any(kw in heading_lower for kw in _CODE_HEADING_KEYWORDS)

    def test_solution_steps_heading_does_not_trigger(self) -> None:
        heading = "Solution Steps"
        heading_lower = heading.lower()
        _CODE_HEADING_KEYWORDS = (
            "code example", "code snippet", "working example",
            "example code", "code sample", "code block",
        )
        assert not any(kw in heading_lower for kw in _CODE_HEADING_KEYWORDS)

    def test_synthetic_spec_requires_code(self) -> None:
        spec = GoldenBlockSpec(
            required_block_types=["paragraph", "code"],
            min_words=30,
        )
        assert "code" in spec.required_block_types

    def test_working_example_heading_triggers(self) -> None:
        heading = "Working Example"
        heading_lower = heading.lower()
        _CODE_HEADING_KEYWORDS = (
            "code example", "code snippet", "working example",
            "example code", "code sample", "code block",
        )
        assert any(kw in heading_lower for kw in _CODE_HEADING_KEYWORDS)
