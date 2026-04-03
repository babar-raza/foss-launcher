"""TC-5301: Regression tests — fallback.py must never emit skeleton directive paragraphs.

Verifies that ``render_section_deterministic`` does NOT emit the internal
``"{display_name} -- {content_hint}."`` engineering note as a content block,
regardless of whether claims, snippets, or content_hint are present.
"""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim, Snippet
from launcher.models.page_ir import BlockType
from launcher.models.product import ProductIdentity
from launcher.shared.page_skeletons import SkeletonSection
from launcher.workers.generate.fallback import render_section_deterministic


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _product(display_name: str = "Aspose.3D", platform: str = "dotnet") -> ProductIdentity:
    return ProductIdentity(
        display_name=display_name,
        canonical_import="aspose-3d",
        platform=platform,
        family="3d",
        repo_url="https://github.com/example/repo",
    )


def _section(heading: str = "Overview", content_hint: str = "What is new and why it matters") -> SkeletonSection:
    return SkeletonSection(
        heading=heading,
        level=2,
        required=True,
        content_hint=content_hint,
        min_words=30,
        max_words=200,
    )


def _claim(text: str = "Aspose.3D supports loading FBX files.", claim_id: str = "c1") -> Claim:
    return Claim(
        claim_id=claim_id,
        text=text,
        kind="feature",
        confidence=0.9,
    )


def _snippet(code: str = "var scene = new Scene();", claim_ids: list[str] | None = None) -> Snippet:
    return Snippet(
        snippet_id="s1",
        code=code,
        claim_ids=claim_ids or ["c1"],
        language="csharp",
    )


# ---------------------------------------------------------------------------
# TC-5301-T1: content_hint present + claims → NO skeleton paragraph
# ---------------------------------------------------------------------------


def test_fallback_no_skeleton_with_content_hint_and_claims():
    """TC-5301-T1: section with content_hint and claims must NOT emit skeleton paragraph.

    The ``"{display_name} -- {content_hint}."`` pattern was previously emitted as an
    opening paragraph. It must never appear in fallback output.
    """
    product = _product()
    sec = render_section_deterministic(
        _section("Overview", "What is new and why it matters"),
        claims=[_claim("Aspose.3D provides 3D file conversion capabilities.")],
        snippets=[],
        product=product,
    )

    skeleton_pattern = f"{product.display_name} --"
    for block in sec.blocks:
        content = block.content or ""
        assert skeleton_pattern not in content, (
            f"TC-5301: Skeleton directive emitted in fallback output: {content!r}"
        )
        if block.items:
            for item in block.items:
                assert skeleton_pattern not in item, (
                    f"TC-5301: Skeleton directive in list item: {item!r}"
                )


# ---------------------------------------------------------------------------
# TC-5301-T2: content_hint present + NO claims + NO snippets → NO skeleton paragraph
# ---------------------------------------------------------------------------


def test_fallback_no_claims_no_snippets_no_skeleton():
    """TC-5301-T2: zero claims, zero snippets, content_hint present → NO skeleton paragraph.

    When no evidence exists, fallback produces a minimal see-the-docs paragraph —
    never the internal ``"{display_name} -- {content_hint}."`` engineering note.
    """
    product = _product()
    sec = render_section_deterministic(
        _section("Model Optimization", "Techniques for optimizing 3D models"),
        claims=[],
        snippets=[],
        product=product,
    )

    skeleton_pattern = f"{product.display_name} --"
    assert len(sec.blocks) > 0, "TC-5301: Expected at least one block in fallback output"
    for block in sec.blocks:
        content = block.content or ""
        assert skeleton_pattern not in content, (
            f"TC-5301: Skeleton directive in no-claims fallback output: {content!r}"
        )


# ---------------------------------------------------------------------------
# TC-5301-T3: claims still rendered correctly after skeleton removal
# ---------------------------------------------------------------------------


def test_fallback_with_claims_produces_prose():
    """TC-5301-T3: claims still produce intro prose paragraph after skeleton paragraph removal."""
    product = _product()
    claims = [
        _claim("Aspose.3D supports FBX format loading.", "c1"),
        _claim("Aspose.3D supports OBJ format loading.", "c2"),
    ]

    sec = render_section_deterministic(
        _section("Overview", "Main feature overview"),
        claims=claims,
        snippets=[],
        product=product,
    )

    # Must have at least one paragraph block with claim text
    para_blocks = [b for b in sec.blocks if b.type == BlockType.paragraph]
    assert len(para_blocks) >= 1, "TC-5301: Expected at least one paragraph block from claims"

    all_content = " ".join(b.content or "" for b in para_blocks)
    assert "Aspose.3D" in all_content, "TC-5301: Expected product name in claims prose"
    assert "FBX" in all_content or "supports" in all_content.lower(), (
        "TC-5301: Expected claim text to appear in output prose"
    )


# ---------------------------------------------------------------------------
# TC-5301-T4: snippets still rendered as code blocks after skeleton removal
# ---------------------------------------------------------------------------


def test_fallback_with_snippets_produces_code_block():
    """TC-5301-T4: snippets still produce code blocks after skeleton paragraph removal."""
    product = _product()
    claim = _claim("Aspose.3D allows creating 3D scenes programmatically.", "c1")
    snippet = _snippet("var scene = new Scene();\nscene.Save(\"output.fbx\");", ["c1"])

    sec = render_section_deterministic(
        _section("Code Example", "How to create a scene"),
        claims=[claim],
        snippets=[snippet],
        product=product,
    )

    code_blocks = [b for b in sec.blocks if b.type == BlockType.code]
    assert len(code_blocks) >= 1, "TC-5301: Expected at least one code block from snippets"
    assert "scene" in code_blocks[0].content.lower(), (
        "TC-5301: Expected snippet code to appear in code block"
    )

    # And still no skeleton directive
    skeleton_pattern = f"{product.display_name} --"
    for block in sec.blocks:
        content = block.content or ""
        assert skeleton_pattern not in content
