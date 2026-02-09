"""
Link transformer for cross-subdomain absolute URL conversion (TC-938).

Transforms relative cross-section links to absolute URLs during draft generation.
This completes TC-938 integration into the W5 SectionWriter pipeline.

Per specs/06_page_planning.md and specs/33_public_url_mapping.md, cross-section
links must be absolute URLs with scheme + subdomain to work correctly in the
subdomain architecture (blog.aspose.org, docs.aspose.org, etc.).

Example transformations:
    Input:  [Guide](../../docs/3d/guide/)
    Output: [Guide](https://docs.aspose.org/3d/guide/)

Usage:
    from .link_transformer import transform_cross_section_links

    content = transform_cross_section_links(
        markdown_content="See [Guide](../../docs/3d/guide/).",
        current_section="blog",
        page_metadata={"locale": "en", "family": "3d"},
    )
"""

import re
from typing import Dict, Any, Optional
from ...resolvers.public_urls import build_absolute_public_url
from ...util.logging import get_logger

logger = get_logger()


def transform_cross_section_links(
    markdown_content: str,
    current_section: str,
    page_metadata: Dict[str, Any],
) -> str:
    """
    Transform relative cross-section links to absolute URLs.

    Detects markdown links [text](url) and converts relative cross-section
    links to absolute URLs with scheme + subdomain. Only transforms links
    that cross section boundaries (blog → docs, docs → reference, etc.).

    Same-section links, internal anchors, and external links are preserved.

    Args:
        markdown_content: Raw markdown content with links
        current_section: Current page section (blog, docs, kb, reference, products)
        page_metadata: Page metadata dictionary containing:
            - locale: Language code (e.g., "en", "fr")
            - family: Product family (e.g., "cells", "3d", "words")

    Returns:
        Markdown content with transformed cross-section links

    Examples:
        >>> content = "See [Guide](../../docs/3d/guide/)."
        >>> transform_cross_section_links(content, "blog", {"locale": "en", "family": "3d"})
        'See [Guide](https://docs.aspose.org/3d/guide/).'

        >>> content = "See [Next Page](./next-page/)."
        >>> transform_cross_section_links(content, "docs", {"locale": "en", "family": "cells"})
        'See [Next Page](./next-page/).'  # Unchanged (same section)
    """
    # Section URL patterns (relative paths that indicate cross-section links)
    # These patterns match relative URLs like ../../docs/ or ../docs/ or docs/
    section_patterns = {
        "docs": r"(?:\.\.\/)*docs\/",
        "reference": r"(?:\.\.\/)*reference\/",
        "products": r"(?:\.\.\/)*products\/",
        "kb": r"(?:\.\.\/)*kb\/",
        "blog": r"(?:\.\.\/)*blog\/",
    }

    # Regex to match markdown links: [text](url)
    # Captures: group(1) = link text, group(2) = URL
    link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"

    def transform_link(match):
        """Process a single markdown link match."""
        link_text = match.group(1)
        link_url = match.group(2)

        # Skip external links (already absolute)
        if link_url.startswith("http://") or link_url.startswith("https://"):
            return match.group(0)  # Return original

        # Skip internal anchors
        if link_url.startswith("#"):
            return match.group(0)  # Return original

        # Detect target section from URL pattern
        target_section = None
        for section, pattern in section_patterns.items():
            if re.search(pattern, link_url):
                target_section = section
                break

        # If no section detected, assume same-section link (keep relative)
        if target_section is None:
            return match.group(0)  # Return original

        # If same section, keep relative (e.g., docs → docs)
        if target_section == current_section:
            return match.group(0)  # Return original

        # Parse URL components (family, slug, subsections)
        # Example: ../../docs/3d/developer-guide/getting-started/
        # Split and remove empty parts and ".."
        parts = [p for p in link_url.split("/") if p and p != ".."]

        # Remove section name if present (e.g., "docs", "blog", "reference")
        if parts and parts[0] in section_patterns:
            parts = parts[1:]

        # Parse URL structure: [family, subsections..., slug]
        if len(parts) < 1:
            # Can't parse, keep original
            logger.warning(
                f"[LinkTransformer] Cannot parse cross-section link (too short): {link_url}"
            )
            return match.group(0)

        # Extract components based on URL structure
        family = parts[0] if len(parts) >= 1 else ""

        # Last part is slug (if not empty), middle parts are subsections
        if len(parts) >= 2:
            subsections = parts[1:-1]
            slug = parts[-1]
        else:
            # Just family (section index)
            subsections = []
            slug = ""

        # Build absolute URL using TC-938's build_absolute_public_url()
        try:
            locale = page_metadata.get("locale", "en")
            absolute_url = build_absolute_public_url(
                section=target_section,
                family=family,
                locale=locale,
                slug=slug,
                subsections=subsections,
            )

            logger.debug(
                f"[LinkTransformer] Transformed: {link_url} → {absolute_url}"
            )

            return f"[{link_text}]({absolute_url})"

        except Exception as e:
            # If transformation fails, keep original (graceful degradation)
            logger.warning(
                f"[LinkTransformer] Failed to transform link {link_url}: {e}. "
                f"Keeping original link."
            )
            return match.group(0)

    # Apply transformation to all links in content
    transformed_content = re.sub(link_pattern, transform_link, markdown_content)

    return transformed_content
