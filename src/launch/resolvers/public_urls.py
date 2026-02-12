"""
Public URL Resolver - Maps content paths to canonical public URLs.

Implements the binding contract defined in specs/33_public_url_mapping.md.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import re


class PageKind(Enum):
    """Type of page for URL resolution."""

    SECTION_INDEX = "section_index"  # _index.md
    LEAF_PAGE = "leaf_page"  # <slug>.md (flat style)
    BUNDLE_PAGE = "bundle_page"  # <slug>/index.md (bundle style)


@dataclass(frozen=True)
class HugoFacts:
    """Minimal Hugo facts needed for URL resolution."""

    default_language: str
    default_language_in_subdir: bool
    permalinks: dict  # Custom permalink patterns by section

    @classmethod
    def from_dict(cls, data: dict) -> "HugoFacts":
        """Create HugoFacts from a dictionary (e.g., loaded from JSON)."""
        return cls(
            default_language=data.get("default_language", "en"),
            default_language_in_subdir=data.get("default_language_in_subdir", False),
            permalinks=data.get("permalinks", {}),
        )


@dataclass(frozen=True)
class PublicUrlTarget:
    """Input parameters for URL resolution."""

    subdomain: str  # e.g., "docs.aspose.org"
    family: str  # e.g., "cells"
    locale: str  # e.g., "en"
    section_path: List[str] = None  # e.g., ["developer-guide", "quickstart"]
    page_kind: PageKind = PageKind.LEAF_PAGE  # section_index, leaf_page, or bundle_page
    slug: str = ""  # e.g., "overview" (empty for section_index)
    platform: str = ""  # V2: Platform identifier (e.g., "python", "typescript")


def _normalize_path(path: str) -> str:
    """
    Normalize URL path:
    - Remove double slashes
    - Ensure leading slash
    - Ensure trailing slash
    """
    # Remove consecutive slashes
    while "//" in path:
        path = path.replace("//", "/")

    # Ensure leading slash
    if not path.startswith("/"):
        path = "/" + path

    # Ensure trailing slash
    if not path.endswith("/"):
        path = path + "/"

    return path


def _validate_component(component: str) -> str:
    """
    Validate and normalize a path component.
    Raises ValueError if component contains invalid characters.
    """
    if not component:
        return component

    # Reject path traversal attempts
    if ".." in component or "/" in component or "\\" in component:
        raise ValueError(f"Invalid path component: {component}")

    # Normalize: lowercase, replace spaces with hyphens
    normalized = component.lower().replace(" ", "-")

    # Allow only safe characters
    if not re.match(r"^[a-z0-9\-_.]+$", normalized):
        # Remove invalid characters
        normalized = re.sub(r"[^a-z0-9\-_.]", "", normalized)

    return normalized


def resolve_public_url(target: PublicUrlTarget, hugo_facts: HugoFacts) -> str:
    """
    Resolve a public URL path from content target parameters.

    Implements specs/33_public_url_mapping.md binding contract.

    Args:
        target: The content target parameters
        hugo_facts: Hugo configuration facts for URL computation

    Returns:
        Canonical URL path (e.g., "/cells/overview/")
    """
    # Validate and normalize components
    family = _validate_component(target.family)
    locale = _validate_component(target.locale)
    slug = _validate_component(target.slug) if target.slug else ""
    platform = _validate_component(target.platform) if target.platform else ""
    section_path_list = target.section_path if target.section_path else []
    section_path = [_validate_component(s) for s in section_path_list if s]

    # Determine locale prefix based on Hugo config
    if (
        locale == hugo_facts.default_language
        and not hugo_facts.default_language_in_subdir
    ):
        # Default language: no locale prefix in URL
        locale_prefix = ""
    else:
        # Non-default language or default_language_in_subdir=true: include locale
        locale_prefix = "/" + locale

    # V2: Build platform segment (insert after family)
    platform_segment = "/" + platform if platform else ""

    # Build section path segment
    section_segment = "/" + "/".join(section_path) if section_path else ""

    # Build slug segment based on page kind
    if target.page_kind == PageKind.SECTION_INDEX:
        slug_segment = ""
    else:
        # Both LEAF_PAGE and BUNDLE_PAGE map the slug to URL
        slug_segment = "/" + slug if slug else ""

    # Compose URL path: locale prefix + family + platform + section + slug
    # V2: Platform comes after family, before section_path
    url_path = locale_prefix + "/" + family + platform_segment + section_segment + slug_segment + "/"

    return _normalize_path(url_path)


def build_absolute_public_url(
    section: str,
    family: str,
    locale: str,
    slug: str,
    subsections: Optional[List[str]] = None,
    hugo_facts: Optional[HugoFacts] = None,
    platform: str = "",  # V2: Platform identifier (e.g., "python", "typescript")
) -> str:
    """
    Build absolute public URL for cross-section links (TC-938).

    This function creates absolute URLs with scheme + subdomain for cross-section
    navigation (e.g., docs -> reference, blog -> products). All cross-subdomain
    links must be absolute to work correctly.

    V2: When platform is provided, inserts platform segment after family in URL.

    Args:
        section: Section name (products, docs, reference, kb, blog)
        family: Product family (cells, words, etc.)
        locale: Language code (en, fr, etc.)
        slug: Page slug (empty for section index pages)
        subsections: Optional nested section path (e.g., ["developer-guide", "quickstart"])
        hugo_facts: Hugo configuration facts (uses defaults if not provided)
        platform: V2 platform identifier (e.g., "python", "typescript"). Empty = no platform segment.

    Returns:
        Absolute URL with scheme + subdomain (e.g., https://docs.aspose.org/cells/python/overview/)

    Raises:
        ValueError: If section is unknown

    Examples:
        >>> build_absolute_public_url("docs", "cells", "en", "overview", platform="python")
        'https://docs.aspose.org/cells/python/overview/'
        >>> build_absolute_public_url("reference", "cells", "en", "api", platform="python")
        'https://reference.aspose.org/cells/python/api/'
    """
    # Map section to subdomain
    subdomain_map = {
        "products": "products.aspose.org",
        "docs": "docs.aspose.org",
        "reference": "reference.aspose.org",
        "kb": "kb.aspose.org",
        "blog": "blog.aspose.org",
    }

    subdomain = subdomain_map.get(section)
    if not subdomain:
        raise ValueError(f"Unknown section: {section}")

    # Determine page kind based on slug
    if not slug:
        page_kind = PageKind.SECTION_INDEX
    else:
        page_kind = PageKind.LEAF_PAGE

    # Build PublicUrlTarget
    target = PublicUrlTarget(
        subdomain=subdomain,
        family=family,
        locale=locale,
        section_path=subsections or [],
        page_kind=page_kind,
        slug=slug,
        platform=platform,
    )

    # Use provided hugo_facts or defaults
    if hugo_facts is None:
        hugo_facts = HugoFacts(
            default_language="en",
            default_language_in_subdir=False,
            permalinks={},
        )

    # Resolve URL path using existing resolver
    url_path = resolve_public_url(target, hugo_facts)

    # Combine scheme + subdomain + url_path
    return f"https://{subdomain}{url_path}"


def resolve_url_from_content_path(
    content_path: str,
    hugo_facts: HugoFacts,
    layout_mode: str = "v1",
) -> str:
    """
    Resolve public URL from a content file path.

    This is a convenience function that parses a content path and resolves the URL.

    Args:
        content_path: Content file path (e.g., "content/docs.aspose.org/cells/en/overview.md")
        hugo_facts: Hugo configuration facts
        layout_mode: DEPRECATED - ignored, kept for backward compatibility

    Returns:
        Canonical URL path
    """
    # Normalize path separators
    content_path = content_path.replace("\\", "/")

    # Strip "content/" prefix if present
    if content_path.startswith("content/"):
        content_path = content_path[8:]

    # Parse path components
    parts = content_path.split("/")
    if len(parts) < 3:
        raise ValueError(f"Invalid content path: {content_path}")

    subdomain = parts[0]
    family = parts[1]

    # Determine page kind from filename
    filename = parts[-1]
    if filename == "_index.md" or filename.startswith("_index."):
        page_kind = PageKind.SECTION_INDEX
        slug = ""
        path_parts = parts[2:-1]  # Everything between family and _index.md
    elif filename == "index.md" or filename.startswith("index."):
        page_kind = PageKind.BUNDLE_PAGE
        # For bundle pages, the parent folder is the slug
        slug = parts[-2] if len(parts) > 3 else ""
        path_parts = parts[2:-2]  # Everything between family and slug folder
    else:
        page_kind = PageKind.LEAF_PAGE
        # Extract slug from filename (remove .md extension and language suffix)
        slug = re.sub(r"\.[a-z]{2}\.md$", "", filename)  # Remove .fr.md etc
        slug = re.sub(r"\.md$", "", slug)  # Remove .md
        path_parts = parts[2:-1]  # Everything between family and filename

    # Parse locale and section_path (no platform segment)
    if subdomain == "blog.aspose.org":
        # Blog: no locale folder
        locale = "en"  # Default, may be overridden by filename suffix
        section_path = path_parts

        # Check for language suffix in filename
        lang_match = re.search(r"\.([a-z]{2})\.md$", filename)
        if lang_match:
            locale = lang_match.group(1)
    else:
        # Non-blog: locale is a folder
        if not path_parts:
            raise ValueError(f"Missing locale in content path: {content_path}")

        locale = path_parts[0]
        section_path = path_parts[1:]

    target = PublicUrlTarget(
        subdomain=subdomain,
        family=family,
        locale=locale,
        section_path=list(section_path),
        page_kind=page_kind,
        slug=slug,
    )

    return resolve_public_url(target, hugo_facts)
