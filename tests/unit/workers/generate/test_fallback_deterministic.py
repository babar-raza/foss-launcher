"""Tests for TC-3912: deterministic fallback for zero-claim boilerplate sections.

Verifies that Prerequisites and Code Example sections produce real content
(not placeholder stubs) when claims=[] and snippets=[].
"""
from __future__ import annotations

import pytest

from launcher.models.page_ir import BlockType
from launcher.models.product import ProductIdentity
from launcher.shared.page_skeletons import SkeletonSection
from launcher.workers.generate.fallback import render_section_deterministic


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _product(canonical_import: str = "aspose_cells_foss", platform: str = "python") -> ProductIdentity:
    return ProductIdentity(
        display_name="Aspose.Cells",
        canonical_import=canonical_import,
        platform=platform,
        family="cells",
        repo_url="https://github.com/example/repo",
    )


def _section(heading: str, content_hint: str = "") -> SkeletonSection:
    return SkeletonSection(
        heading=heading,
        level=2,
        required=True,
        content_hint=content_hint,
        min_words=30,
        max_words=100,
    )


# ---------------------------------------------------------------------------
# TC-3912-T1: Prerequisites — zero claims → list + code block
# ---------------------------------------------------------------------------

def test_prerequisites_zero_claims_produces_list_and_code():
    """Prerequisites section with no claims → list block + code block, no placeholder."""
    sec = render_section_deterministic(
        _section("Prerequisites", "Required setup and knowledge"),
        claims=[],
        snippets=[],
        product=_product(),
    )

    block_types = [b.type for b in sec.blocks]
    # Must have a list block (install steps) and a code block (import)
    assert BlockType.list in block_types, "Expected list block in Prerequisites"
    assert BlockType.code in block_types, "Expected code block in Prerequisites"

    # Verify no placeholder stub
    for b in sec.blocks:
        content = getattr(b, "content", "") or ""
        assert "For details on" not in content, f"Placeholder stub found: {content!r}"
        assert "see the Aspose.Cells documentation" not in content

    # Verify code block contains canonical import
    code_blocks = [b for b in sec.blocks if b.type == BlockType.code]
    assert any("aspose_cells_foss" in (b.content or "") for b in code_blocks)


def test_prerequisites_variants_all_trigger_deterministic():
    """All heading variants in _PREREQUISITES_HEADINGS produce real content."""
    headings = ["prerequisites", "Requirements", "Setup", "Before You Begin"]
    for heading in headings:
        sec = render_section_deterministic(
            _section(heading),
            claims=[],
            snippets=[],
            product=_product(),
        )
        block_types = [b.type for b in sec.blocks]
        assert BlockType.list in block_types or BlockType.code in block_types, (
            f"Heading '{heading}' should produce list or code, got {block_types}"
        )


# ---------------------------------------------------------------------------
# TC-3912-T2: Code Example — zero claims → paragraph + code block
# ---------------------------------------------------------------------------

def test_code_example_zero_claims_produces_paragraph_and_code():
    """Code Example section with no claims → paragraph + code block, no placeholder."""
    sec = render_section_deterministic(
        _section("Code Example", "Runnable code example using canonical import"),
        claims=[],
        snippets=[],
        product=_product("aspose_3d_foss", "python"),
    )

    block_types = [b.type for b in sec.blocks]
    assert BlockType.paragraph in block_types, "Expected paragraph in Code Example"
    assert BlockType.code in block_types, "Expected code block in Code Example"

    for b in sec.blocks:
        content = getattr(b, "content", "") or ""
        assert "For details on" not in content

    code_blocks = [b for b in sec.blocks if b.type == BlockType.code]
    assert any("aspose_3d_foss" in (b.content or "") for b in code_blocks)


def test_code_example_heading_variants():
    """Code Examples, Code Samples, Working Example all trigger deterministic path."""
    headings = ["Code Examples", "code samples", "Working Example", "Complete Code Example"]
    for heading in headings:
        sec = render_section_deterministic(
            _section(heading),
            claims=[],
            snippets=[],
            product=_product(),
        )
        block_types = [b.type for b in sec.blocks]
        assert BlockType.code in block_types, (
            f"Heading '{heading}' should produce code block, got {block_types}"
        )


# ---------------------------------------------------------------------------
# TC-3912-T3: Other sections — still use placeholder stub
# ---------------------------------------------------------------------------

def test_other_section_zero_claims_still_uses_fallback_stub():
    """Non-boilerplate sections still get the 'For details...' placeholder when no claims."""
    sec = render_section_deterministic(
        _section("Remarks", "API notes"),
        claims=[],
        snippets=[],
        product=_product(),
    )
    # Should have the 'For details...' placeholder
    all_content = " ".join(
        getattr(b, "content", "") or ""
        for b in sec.blocks
    )
    assert "For details on" in all_content or "see the" in all_content


# ---------------------------------------------------------------------------
# TC-3912-T4: With claims — boilerplate path NOT triggered
# ---------------------------------------------------------------------------

def test_prerequisites_with_claims_uses_claims_not_boilerplate():
    """When claims exist, Prerequisites uses claim bullets (not boilerplate)."""
    from launcher.models.claims import Claim
    claim = Claim(
        claim_id="CLM-001",
        text="Install via: pip install aspose_cells_foss",
        kind="feature",
    )
    sec = render_section_deterministic(
        _section("Prerequisites"),
        claims=[claim],
        snippets=[],
        product=_product(),
    )
    # TC-4031 Wave 3C: single claim → paragraph block (not list), not boilerplate.
    para_blocks = [b for b in sec.blocks if b.type == BlockType.paragraph]
    assert para_blocks, "Expected paragraph block from claim (TC-4031 Wave 3C)"
    # The paragraph should contain the claim text
    assert any("aspose_cells_foss" in (b.content or "") for b in para_blocks)


# ---------------------------------------------------------------------------
# TC-3912-T5: Content hint stub still generated before boilerplate
# ---------------------------------------------------------------------------

def test_content_hint_stub_still_generated_for_prerequisites():
    """content_hint paragraph is still prepended before boilerplate blocks."""
    sec = render_section_deterministic(
        _section("Prerequisites", "Required setup and knowledge"),
        claims=[],
        snippets=[],
        product=_product(),
    )
    # First block should be the content_hint paragraph
    assert sec.blocks[0].type == BlockType.paragraph
    assert "Aspose.Cells -- Required setup and knowledge" in sec.blocks[0].content


# ---------------------------------------------------------------------------
# TC-3912-T6: canonical_import=None guard
# ---------------------------------------------------------------------------

def test_prerequisites_no_canonical_import_does_not_crash():
    """When canonical_import is None or empty, fallback uses 'aspose_foss' guard."""
    product = ProductIdentity(
        display_name="Aspose.Test",
        canonical_import="",
        platform="python",
        family="test",
        repo_url="https://github.com/example/repo",
    )
    sec = render_section_deterministic(
        _section("Prerequisites"),
        claims=[],
        snippets=[],
        product=product,
    )
    assert sec.blocks  # Must produce at least one block
    assert sec.heading == "Prerequisites"
