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
    platform: str  # e.g., "python" (empty for V1)
    section_path: List[str]  # e.g., ["developer-guide", "quickstart"]
    page_kind: PageKind  # section_index, leaf_page, or bundle_page
    slug: str  # e.g., "overview" (empty for section_index)


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
        Canonical URL path (e.g., "/cells/python/overview/")
    """
    # Validate and normalize components
    family = _validate_component(target.family)
    locale = _validate_component(target.locale)
    platform = _validate_component(target.platform) if target.platform else ""
    slug = _validate_component(target.slug) if target.slug else ""
    section_path = [_validate_component(s) for s in target.section_path if s]

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

    # Determine platform segment (empty for V1)
    platform_segment = "/" + platform if platform else ""

    # Build section path segment
    section_segment = "/" + "/".join(section_path) if section_path else ""

    # Build slug segment based on page kind
    if target.page_kind == PageKind.SECTION_INDEX:
        slug_segment = ""
    else:
        # Both LEAF_PAGE and BUNDLE_PAGE map the slug to URL
        slug_segment = "/" + slug if slug else ""

    # Compose URL path based on subdomain type
    if target.subdomain == "blog.aspose.org":
        # Blog: locale prefix + family + platform + section + slug
        # (no locale folder in content, but URL may have locale prefix)
        url_path = locale_prefix + "/" + family + platform_segment + section_segment + slug_segment + "/"
    else:
        # Non-blog: locale prefix + family + platform + section + slug
        url_path = locale_prefix + "/" + family + platform_segment + section_segment + slug_segment + "/"

    return _normalize_path(url_path)


def resolve_url_from_content_path(
    content_path: str,
    hugo_facts: HugoFacts,
    layout_mode: str = "v2",
) -> str:
    """
    Resolve public URL from a content file path.

    This is a convenience function that parses a content path and resolves the URL.

    Args:
        content_path: Content file path (e.g., "content/docs.aspose.org/cells/en/python/overview.md")
        hugo_facts: Hugo configuration facts
        layout_mode: "v1" or "v2" (default "v2")

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

    # Parse locale and platform based on layout mode and subdomain
    if subdomain == "blog.aspose.org":
        # Blog: no locale folder
        locale = "en"  # Default, may be overridden by filename suffix
        if layout_mode == "v2" and path_parts:
            platform = path_parts[0]
            section_path = path_parts[1:]
        else:
            platform = ""
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

        if layout_mode == "v2" and len(path_parts) > 1:
            platform = path_parts[1]
            section_path = path_parts[2:]
        else:
            platform = ""
            section_path = path_parts[1:]

    target = PublicUrlTarget(
        subdomain=subdomain,
        family=family,
        locale=locale,
        platform=platform,
        section_path=list(section_path),
        page_kind=page_kind,
        slug=slug,
    )

    return resolve_public_url(target, hugo_facts)
