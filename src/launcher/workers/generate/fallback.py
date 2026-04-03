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

# TC-5313: Platform-aware prerequisites content.
# Maps platform slug → (runtime requirement text, install command template).
# {package} is replaced with the product's canonical_import.
_RUNTIME_REQUIREMENTS: dict[str, str] = {
    "python": "Python 3.7+",
    "java": "Java 8+",
    "dotnet": ".NET 6.0+",
    "cpp": "C++17 compatible compiler",
    "typescript": "Node.js 14+",
    "nodejs": "Node.js 14+",
}

_INSTALL_COMMANDS: dict[str, str] = {
    "python": "Install via pip: `pip install {package}`",
    "java": "Add to your Maven `pom.xml` or Gradle `build.gradle`: `{package}`",
    "dotnet": "Install via NuGet: `dotnet add package {package}`",
    "cpp": "Install via vcpkg: `vcpkg install {package}`",
    "typescript": "Install via npm: `npm install {package}`",
    "nodejs": "Install via npm: `npm install {package}`",
}

# TC-5313: Platform-aware import/usage syntax for the code example block.
# {import_path} is replaced with the product's runtime_import or canonical_import.
_IMPORT_SYNTAX: dict[str, str] = {
    "python": "import {import_path}",
    "java": "import {import_path}.*;",
    "dotnet": "using {import_path};",
    "cpp": "// Include {import_path} headers\n// See installation guide for include paths",
    "typescript": 'import * as aspose from "{import_path}";',
    "nodejs": 'const aspose = require("{import_path}");',
}


def _render_prerequisites_blocks(product: ProductIdentity) -> list[BlockIR]:
    """Deterministic Prerequisites blocks for zero-claim sections (TC-3912).

    Produces a list block with install/version info and a code block
    with the runtime import — always factual, never fabricated.
    Platform-aware: dispatches on product.platform (TC-5313).
    """
    lang = get_lang_tag(product.platform)
    platform = (product.platform or "python").lower()
    package = product.canonical_import or "aspose-foss"
    import_path = product.runtime_import or product.canonical_import or "aspose_foss"

    runtime_req = _RUNTIME_REQUIREMENTS.get(platform, f"Supported runtime for {platform}")
    install_cmd = _INSTALL_COMMANDS.get(
        platform, f"Install `{package}` using your platform's package manager"
    ).format(package=package.replace("_", "-"))
    import_stmt = _IMPORT_SYNTAX.get(platform, f"// Use {import_path}").format(
        import_path=import_path
    )

    items = [runtime_req, install_cmd]
    return [
        BlockIR(type=BlockType.list, items=items),
        BlockIR(type=BlockType.code, content=import_stmt, language=lang),
    ]


def _render_code_example_blocks(product: ProductIdentity) -> list[BlockIR]:
    """Deterministic Code Example blocks for zero-claim sections (TC-3912).

    Produces a minimal, runnable import-level example using the runtime
    import. Never fabricates API calls not in the API surface.
    Platform-aware: dispatches on product.platform (TC-5313).
    """
    lang = get_lang_tag(product.platform)
    platform = (product.platform or "python").lower()
    import_path = product.runtime_import or product.canonical_import or "aspose_foss"

    import_stmt = _IMPORT_SYNTAX.get(platform, f"// Use {import_path}").format(
        import_path=import_path
    )
    comment_char = "//" if platform in ("cpp", "java", "dotnet", "typescript", "nodejs") else "#"
    code = (
        f"{import_stmt}\n\n"
        f"{comment_char} Initialize — see the {product.display_name} API reference for available classes"
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

    Note: The ``content_hint`` field from the skeleton is intentionally
    NOT emitted as content — it is an internal engineering scaffold note
    and must never appear in published output.

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
