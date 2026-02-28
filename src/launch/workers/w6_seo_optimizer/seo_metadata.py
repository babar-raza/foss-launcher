"""SEO metadata optimization for frontmatter."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ...util.logging import get_logger

logger = get_logger()

# TC-3560: Placeholder patterns that should be replaced on _index.md files
_INDEX_DESC_PLACEHOLDER_RE = re.compile(
    r"^\s*(TODO|TBD|fill\s+desc|placeholder|template[-\s]driven)\b",
    re.IGNORECASE,
)


def optimize_seo_metadata(
    content: str,
    page: Dict[str, Any],
    keywords: List[str],
    product_name: str,
    platform: str,
    section: str = "docs",
    family: str = "",
    *,
    is_section_index: bool = False,
    llm_client: Optional[Any] = None,
) -> str:
    """Optimize frontmatter SEO fields on final .md content.

    Updates/adds:
    - seoTitle: <=60 chars, keyword-rich
    - description: <=160 chars, keyword-rich, unique
    - keywords: top 8 relevant keywords
    - canonical: absolute canonical URL
    - robots: "noindex, follow" for Hugo _index.md section indices; "index, follow" otherwise
    """
    # Determine subdomain
    subdomain_map = {
        "docs": "docs.aspose.org",
        "reference": "reference.aspose.org",
        "kb": "kb.aspose.org",
        "blog": "blog.aspose.org",
        "products": "products.aspose.org",
    }
    subdomain = subdomain_map.get(section, "docs.aspose.org")

    slug = page.get("slug", "page")
    title = page.get("title", slug.replace("-", " ").title())
    purpose = page.get("purpose", "")
    url_path = page.get("url_path", "")

    # Build canonical URL
    if url_path:
        canonical = f"https://{subdomain}/{url_path.strip('/')}/"
    else:
        parts = [family, platform, slug] if platform else [family, slug]
        canonical = f"https://{subdomain}/{'/'.join(p for p in parts if p)}/"

    # Build SEO title (<=60 chars)
    seo_title = _build_seo_title(title, product_name, platform, max_length=60)

    # Build SEO description (<=160 chars)
    seo_description = _build_seo_description(
        title, purpose, product_name, platform, keywords, max_length=160
    )

    # Determine robots directive
    robots = "noindex, follow" if is_section_index else "index, follow"

    # Format keywords for frontmatter
    kw_yaml = ", ".join(f'"{k}"' for k in keywords[:8])

    # Inject into frontmatter
    content = _inject_frontmatter_field(content, "seoTitle", f'"{seo_title}"')
    content = _inject_frontmatter_field(content, "robots", f'"{robots}"')

    # TC-3400: Always set canonical to computed value (update if stale, inject if absent)
    existing_canonical = _get_frontmatter_field(content, "canonical")
    if existing_canonical:
        content = _update_frontmatter_field(content, "canonical", f'"{canonical}"')
    else:
        content = _inject_frontmatter_field(content, "canonical", f'"{canonical}"')

    # Only add keywords if we have them
    if keywords:
        content = _inject_frontmatter_field(content, "keywords", f"[{kw_yaml}]")

    # TC-3400: Always inject description when absent (prevents G4-SEO-001)
    content = _inject_frontmatter_field(content, "description", f'"{seo_description}"')

    # Update description if generic or too short
    existing_desc = _get_frontmatter_field(content, "description")
    if existing_desc and (
        "documentation and resources" in existing_desc.lower() or
        len(existing_desc) < 30
    ):
        content = _update_frontmatter_field(content, "description", f'"{seo_description}"')

    # TC-3560: For _index.md section pages, replace placeholder or empty
    # descriptions with a deterministic template (no LLM required).
    if is_section_index:
        existing_desc = _get_frontmatter_field(content, "description") or ""
        if (
            not existing_desc.strip()
            or _INDEX_DESC_PLACEHOLDER_RE.match(existing_desc)
        ):
            product_label = (product_name or "Product").strip()
            platform_label = f" for {platform}" if platform else ""
            index_desc = (
                f"{product_label}{platform_label} — documentation, code examples, "
                f"and developer resources."
            )[:160]
            content = _update_frontmatter_field(content, "description", f'"{index_desc}"')

    return content


def _build_seo_title(
    title: str, product_name: str, platform: str, max_length: int = 60
) -> str:
    """Build SEO-optimized title <=max_length chars."""
    # Start with the page title
    seo_title = title

    # If title doesn't include product name, prepend it
    short_product = product_name.split(" for ")[0] if " for " in product_name else product_name
    if short_product.lower() not in seo_title.lower():
        seo_title = f"{short_product} {seo_title}"

    # Truncate if needed
    if len(seo_title) > max_length:
        seo_title = seo_title[:max_length - 3].rsplit(" ", 1)[0] + "..."

    return seo_title


def _build_seo_description(
    title: str, purpose: str, product_name: str, platform: str,
    keywords: List[str], max_length: int = 160
) -> str:
    """Build SEO-optimized description <=max_length chars."""
    short_product = (
        product_name.split(" for ")[0] if " for " in product_name else product_name
    )
    platform_label = platform.title() if platform else ""

    # Try purpose first
    if purpose and len(purpose) > 30:
        desc = f"{short_product} {platform_label}: {purpose}"
    else:
        desc = f"{title} for {short_product} {platform_label}"

    # Add a keyword if space allows
    if keywords and len(desc) < max_length - 20:
        kw = keywords[0]
        if kw.lower() not in desc.lower():
            desc += f". Learn about {kw}"

    # Ensure it ends cleanly
    if len(desc) > max_length:
        desc = desc[:max_length - 1].rsplit(" ", 1)[0] + "."

    return desc.strip()


def _inject_frontmatter_field(content: str, field: str, value: str) -> str:
    """Add a field to frontmatter if not already present."""
    if not content.startswith("---"):
        return content

    # Check if field already exists
    if re.search(rf'^{re.escape(field)}:', content, re.MULTILINE):
        return content

    # Find the closing --- and insert before it
    lines = content.split('\n')
    fm_end = -1
    found_first = False
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if not found_first:
                found_first = True
            else:
                fm_end = i
                break

    if fm_end > 0:
        lines.insert(fm_end, f"{field}: {value}")
        return '\n'.join(lines)

    return content


def _update_frontmatter_field(content: str, field: str, value: str) -> str:
    """Update an existing frontmatter field value."""
    pattern = rf'^({re.escape(field)}:)\s*.*$'
    return re.sub(pattern, rf'\1 {value}', content, count=1, flags=re.MULTILINE)


def _get_frontmatter_field(content: str, field: str) -> Optional[str]:
    """Extract a frontmatter field value."""
    match = re.search(
        rf'^{re.escape(field)}:\s*"?([^"\n]*)"?\s*$', content, re.MULTILINE
    )
    return match.group(1) if match else None
