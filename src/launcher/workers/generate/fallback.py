"""Deterministic fallback renderer for when LLM fails.

Produces a guaranteed C-grade output by rendering claims as bullet lists
and snippets as code blocks.  No LLM required.
"""
from __future__ import annotations

from launcher.models.claims import Claim, Snippet
from launcher.models.page_ir import BlockIR, BlockType, SectionIR
from launcher.models.product import ProductIdentity
from launcher.shared.page_skeletons import SkeletonSection
from launcher.shared.platform_utils import get_lang_tag

# Sections that should render as tables instead of bullet lists (TC-3802)
_TABULAR_HEADINGS: frozenset[str] = frozenset({
    "constructors", "constructor", "properties", "methods",
    "key members", "api summary", "error messages", "supported formats",
})

# TC-3912: Boilerplate section headings that get deterministic content when
# claims=[] and snippets=[], instead of the placeholder "see the docs" stub.
_PREREQUISITES_HEADINGS: frozenset[str] = frozenset({
    "prerequisites", "requirements", "setup", "installation prerequisites",
    "before you begin", "what you need",
})

_CODE_EXAMPLE_HEADINGS: frozenset[str] = frozenset({
    "code example", "code examples", "code sample", "code samples",
    "working example", "example code", "complete code example",
})


def _render_prerequisites_blocks(product: ProductIdentity) -> list[BlockIR]:
    """Deterministic Prerequisites blocks for zero-claim sections (TC-3912).

    Produces a list block with install/version info and a code block
    with the runtime import — always factual, never fabricated.
    """
    lang = get_lang_tag(product.platform)
    pip_name = product.canonical_import or "aspose_foss"
    code_import = product.runtime_import or product.canonical_import or "aspose_foss"
    items = [
        f"Python 3.7+ (or the supported runtime for {product.platform})",
        f"Install via pip: `pip install {pip_name.replace('_', '-')}`",
    ]
    return [
        BlockIR(type=BlockType.list, items=items),
        BlockIR(type=BlockType.code, content=f"import {code_import}", language=lang),
    ]


def _render_code_example_blocks(product: ProductIdentity) -> list[BlockIR]:
    """Deterministic Code Example blocks for zero-claim sections (TC-3912).

    Produces a minimal, runnable import-level example using the runtime
    import. Never fabricates API calls not in the API surface.
    """
    lang = get_lang_tag(product.platform)
    code_import = product.runtime_import or product.canonical_import or "aspose_foss"
    code = (
        f"import {code_import}\n\n"
        f"# Initialize — see the {code_import} API reference for available classes"
    )
    return [
        BlockIR(
            type=BlockType.paragraph,
            content=(
                f"The following example demonstrates how to get started with "
                f"{product.display_name}."
            ),
        ),
        BlockIR(type=BlockType.code, content=code, language=lang),
    ]


def _claims_to_table(claims: list[Claim]) -> str:
    """Build a 2-column markdown table from claims."""
    header = "| Item | Description |"
    separator = "| --- | --- |"
    rows: list[str] = []
    for c in claims:
        parts = c.text.split(". ", 1)
        name = parts[0].strip().replace("|", "\\|")
        desc = parts[1].strip().replace("|", "\\|") if len(parts) > 1 else ""
        rows.append(f"| {name} | {desc} |")
    return "\n".join([header, separator] + rows)


def render_section_deterministic(
    section: SkeletonSection,
    claims: list[Claim],
    snippets: list[Snippet],
    product: ProductIdentity,
) -> SectionIR:
    """Render a section deterministically from claims and snippets.

    This is the last-resort fallback when both primary and fallback LLMs
    fail.  Produces structured content that passes all safety gates but
    is intentionally plain (bullet lists + verbatim code).

    Parameters
    ----------
    section:
        Skeleton section definition.
    claims:
        Claims assigned to this section.
    snippets:
        Code snippets linked to this section's claims.
    product:
        Product identity for display name and language tag.

    Returns
    -------
    SectionIR
        A section with deterministic blocks.
    """
    blocks: list[BlockIR] = []

    # Opening paragraph from content hint
    if section.content_hint:
        blocks.append(
            BlockIR(
                type=BlockType.paragraph,
                content=f"{product.display_name} -- {section.content_hint}.",
            )
        )

    # Claims as table (for tabular sections) or bullet list (default)
    if claims:
        if section.heading.lower() in _TABULAR_HEADINGS:
            blocks.append(
                BlockIR(
                    type=BlockType.table,
                    content=_claims_to_table(claims),
                    claim_ids=[c.claim_id for c in claims],
                )
            )
        else:
            # TC-4031 Wave 3C: produce a prose paragraph from the first 1-2 claims
            # instead of a raw bullet list — reads as content, not a bot dump.
            intro_parts = [claims[0].text.rstrip(".")]
            intro_claim_ids = [claims[0].claim_id]
            if len(claims) > 1:
                intro_parts.append(claims[1].text.rstrip("."))
                intro_claim_ids.append(claims[1].claim_id)
            intro = f"{product.display_name} {intro_parts[0]}."
            if len(intro_parts) > 1:
                intro += f" {intro_parts[1]}."
            blocks.append(
                BlockIR(
                    type=BlockType.paragraph,
                    content=intro,
                    claim_ids=intro_claim_ids,
                )
            )
            # Remaining claims (3+) rendered as a bullet list.
            if len(claims) > 2:
                blocks.append(
                    BlockIR(
                        type=BlockType.list,
                        items=[c.text for c in claims[2:]],
                        claim_ids=[c.claim_id for c in claims[2:]],
                    )
                )

    # Code snippets as code blocks
    lang = get_lang_tag(product.platform)
    for snippet in snippets:
        blocks.append(
            BlockIR(
                type=BlockType.code,
                content=snippet.code,
                language=lang,
                claim_ids=snippet.claim_ids,
            )
        )

    # If no claims or snippets, generate deterministic content for well-known
    # boilerplate section types (TC-3912), or fall back to a minimal placeholder
    # for unknown sections so the section is never empty.
    if not claims and not snippets:
        heading_lower = section.heading.lower()
        if heading_lower in _PREREQUISITES_HEADINGS:
            blocks.extend(_render_prerequisites_blocks(product))
        elif heading_lower in _CODE_EXAMPLE_HEADINGS:
            blocks.extend(_render_code_example_blocks(product))
        else:
            blocks.append(
                BlockIR(
                    type=BlockType.paragraph,
                    content=(
                        f"For details on {section.heading.lower()}, "
                        f"see the {product.display_name} documentation."
                    ),
                )
            )

    section_id = section.heading.lower().replace(" ", "_")
    return SectionIR(
        section_id=section_id,
        heading=section.heading,
        level=section.level,
        blocks=blocks,
    )


def render_page_deterministic(
    page_id: str,
    page_role: str,
    title: str,
    skeleton: list[SkeletonSection],
    claims: list[Claim],
    snippets: list[Snippet],
    product: ProductIdentity,
) -> list[SectionIR]:
    """Render all sections of a page deterministically.

    Claims and snippets are distributed across sections by round-robin
    so every section receives a fair share of material.

    Parameters
    ----------
    page_id:
        Unique page identifier (unused here but kept for caller symmetry).
    page_role:
        Page role slug (unused here but kept for caller symmetry).
    title:
        Page title (unused here but kept for caller symmetry).
    skeleton:
        Ordered skeleton sections for this page role.
    claims:
        All claims assigned to this page.
    snippets:
        All snippets assigned to this page.
    product:
        Product identity.

    Returns
    -------
    list[SectionIR]
        One ``SectionIR`` per skeleton section.
    """
    sections: list[SectionIR] = []
    total = len(skeleton)

    for i, skel_section in enumerate(skeleton):
        # Distribute claims round-robin
        section_claims = (
            [c for j, c in enumerate(claims) if j % total == i] if claims else []
        )
        # Link snippets to section claims
        section_claim_ids = {c.claim_id for c in section_claims}
        section_snippets = [
            s for s in snippets if set(s.claim_ids) & section_claim_ids
        ]

        section_ir = render_section_deterministic(
            skel_section, section_claims, section_snippets, product
        )
        sections.append(section_ir)

    return sections
