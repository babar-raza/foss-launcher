"""
Content Path Resolver - Maps logical page IDs to Hugo content paths.

Implements content path resolution per specs/33_public_url_mapping.md and specs/06_page_planning.md.
Handles Hugo content organization conventions and language-specific paths.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import re
import unicodedata


class ContentStyle(Enum):
    """Hugo content file organization style."""

    FLAT = "flat"  # content/<section>/<slug>.md
    BUNDLE = "bundle"  # content/<section>/<slug>/index.md
    SECTION_INDEX = "section_index"  # content/<section>/_index.md


@dataclass(frozen=True)
class PageIdentifier:
    """Logical page identifier for path resolution."""

    section: str  # products, docs, reference, kb, blog
    slug: str  # Page slug (empty for section index)
    locale: str  # Language code (e.g., en, fr, zh, ja)
    platform: str = ""  # V2: Platform identifier (e.g., "python", "typescript", "java")
    subsections: Optional[List[str]] = None  # Nested subsections (e.g., ["developer-guide", "quickstart"])
    year: Optional[str] = None  # Year for blog posts (e.g., "2024")
    is_section_index: bool = False  # True for _index.md files

    def __post_init__(self):
        """Validate page identifier."""
        if self.is_section_index and self.slug:
            raise ValueError("Section index pages cannot have a slug")
        if not self.is_section_index and not self.slug:
            raise ValueError("Non-index pages must have a slug")


@dataclass(frozen=True)
class HugoConfig:
    """Hugo site configuration for path resolution."""

    default_language: str = "en"
    default_language_in_subdir: bool = False
    content_root: str = "content"
    subdomain: str = "docs.aspose.org"
    family: str = "cells"

    @classmethod
    def from_dict(cls, data: Dict) -> "HugoConfig":
        """Create HugoConfig from a dictionary."""
        return cls(
            default_language=data.get("default_language", "en"),
            default_language_in_subdir=data.get("default_language_in_subdir", False),
            content_root=data.get("content_root", "content"),
            subdomain=data.get("subdomain", "docs.aspose.org"),
            family=data.get("family", "cells"),
        )


def generate_slug(title: str) -> str:
    """
    Generate a URL-safe slug from a page title.

    Rules:
    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove accents and special characters
    - Keep only ASCII alphanumeric, hyphens, and underscores

    Args:
        title: The page title

    Returns:
        URL-safe slug

    Examples:
        >>> generate_slug("Getting Started")
        'getting-started'
        >>> generate_slug("API Reference: Python")
        'api-reference-python'
        >>> generate_slug("Déjà Vu")
        'deja-vu'
    """
    if not title:
        raise ValueError("Title cannot be empty")

    # Normalize unicode characters (remove accents)
    normalized = unicodedata.normalize('NFKD', title)
    ascii_text = normalized.encode('ASCII', 'ignore').decode('ASCII')

    # Convert to lowercase
    slug = ascii_text.lower()

    # Replace spaces and underscores with hyphens
    slug = slug.replace(' ', '-').replace('_', '-')

    # Remove any non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)

    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Strip leading/trailing hyphens
    slug = slug.strip('-')

    if not slug:
        raise ValueError(f"Title '{title}' produces empty slug")

    return slug


def resolve_content_path(
    page_id: PageIdentifier,
    hugo_config: HugoConfig,
    style: ContentStyle = ContentStyle.FLAT,
) -> str:
    """
    Resolve a content file path from a page identifier.

    Implements Hugo content organization conventions per specs/33_public_url_mapping.md.

    Args:
        page_id: The page identifier
        hugo_config: Hugo site configuration
        style: Content organization style (flat, bundle, or section_index)

    Returns:
        Content file path relative to site root (e.g., "content/docs.aspose.org/cells/en/overview.md")

    Raises:
        ValueError: If page_id or configuration is invalid
    """
    # Start with content root
    path_parts = [hugo_config.content_root]

    # Add subdomain
    path_parts.append(hugo_config.subdomain)

    # Add family
    path_parts.append(hugo_config.family)

    # Handle blog section differently (filename-based i18n)
    if page_id.section == "blog":
        # Blog uses filename-based i18n, not locale folders
        # V2: Insert platform after family for blog paths
        if page_id.platform:
            path_parts.append(page_id.platform)

        # Blog post filename includes date if year is specified
        if page_id.year:
            # Format: <year>-<month>-<day>-<slug>.md or <year>-<month>-<day>-<slug>.<lang>.md
            filename = page_id.slug
            if page_id.locale != hugo_config.default_language:
                filename = f"{page_id.slug}.{page_id.locale}"
        else:
            # No date prefix
            filename = page_id.slug
            if page_id.locale != hugo_config.default_language:
                filename = f"{filename}.{page_id.locale}"

        if page_id.is_section_index:
            if page_id.locale == hugo_config.default_language:
                path_parts.append("_index.md")
            else:
                path_parts.append(f"_index.{page_id.locale}.md")
        else:
            path_parts.append(f"{filename}.md")
    else:
        # Non-blog sections: use locale folders
        path_parts.append(page_id.locale)

        # V2: Insert platform after locale for non-blog paths
        if page_id.platform:
            path_parts.append(page_id.platform)

        # Add subsections if present
        if page_id.subsections:
            path_parts.extend(page_id.subsections)

        # Add filename based on style
        if page_id.is_section_index or style == ContentStyle.SECTION_INDEX:
            path_parts.append("_index.md")
        elif style == ContentStyle.BUNDLE:
            # Bundle style: <slug>/index.md
            path_parts.append(page_id.slug)
            path_parts.append("index.md")
        else:
            # Flat style: <slug>.md
            path_parts.append(f"{page_id.slug}.md")

    return "/".join(path_parts)


def resolve_permalink(
    page_id: PageIdentifier,
    hugo_config: HugoConfig,
) -> str:
    """
    Generate the canonical public URL path for a page.

    This implements the URL computation rules from specs/33_public_url_mapping.md.

    Args:
        page_id: The page identifier
        hugo_config: Hugo site configuration

    Returns:
        Canonical URL path (e.g., "/cells/overview/")
    """
    # Start with empty path
    path_segments = []

    # Add locale prefix (unless default language and not in subdir)
    if page_id.locale != hugo_config.default_language or hugo_config.default_language_in_subdir:
        path_segments.append(page_id.locale)

    # Add family
    path_segments.append(hugo_config.family)

    # V2: Add platform after family
    if page_id.platform:
        path_segments.append(page_id.platform)

    # Add subsections
    if page_id.subsections:
        path_segments.extend(page_id.subsections)

    # Add slug (unless section index)
    if not page_id.is_section_index:
        path_segments.append(page_id.slug)

    # Join with slashes and ensure leading/trailing slashes
    url_path = "/" + "/".join(path_segments) + "/"

    # Normalize (remove double slashes)
    while "//" in url_path:
        url_path = url_path.replace("//", "/")

    return url_path


class ContentPathResolver:
    """
    Resolves content paths and permalinks for Hugo sites.

    This class provides methods to map logical page identifiers to Hugo content
    paths and public URLs, following the conventions in specs/33_public_url_mapping.md.
    """

    def __init__(self, hugo_config: HugoConfig):
        """
        Initialize the resolver with Hugo configuration.

        Args:
            hugo_config: Hugo site configuration
        """
        self.hugo_config = hugo_config
        self._path_cache: Dict[PageIdentifier, str] = {}
        self._url_cache: Dict[PageIdentifier, str] = {}
        self._collision_tracker: Dict[str, Set[str]] = {}

    def resolve_path(
        self,
        page_id: PageIdentifier,
        style: ContentStyle = ContentStyle.FLAT,
    ) -> str:
        """
        Resolve content file path for a page.

        Args:
            page_id: The page identifier
            style: Content organization style

        Returns:
            Content file path relative to site root
        """
        # Use cached result if available
        cache_key = page_id
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]

        # Resolve path
        path = resolve_content_path(page_id, self.hugo_config, style)

        # Cache result
        self._path_cache[cache_key] = path

        return path

    def resolve_url(self, page_id: PageIdentifier) -> str:
        """
        Resolve public URL path for a page.

        Args:
            page_id: The page identifier

        Returns:
            Canonical URL path
        """
        # Use cached result if available
        if page_id in self._url_cache:
            return self._url_cache[page_id]

        # Resolve URL
        url = resolve_permalink(page_id, self.hugo_config)

        # Track potential collisions
        if url in self._collision_tracker:
            # Add this page to collision set
            content_path = self.resolve_path(page_id)
            self._collision_tracker[url].add(content_path)
        else:
            content_path = self.resolve_path(page_id)
            self._collision_tracker[url] = {content_path}

        # Cache result
        self._url_cache[page_id] = url

        return url

    def detect_collisions(self) -> Dict[str, List[str]]:
        """
        Detect URL path collisions.

        Returns a dictionary mapping URL paths to lists of content paths that
        resolve to the same URL. Only includes URLs with multiple content paths.

        Returns:
            Dictionary of URL collisions
        """
        collisions = {}
        for url_path, content_paths in self._collision_tracker.items():
            if len(content_paths) > 1:
                collisions[url_path] = sorted(content_paths)
        return collisions

    def clear_cache(self):
        """Clear all cached paths and URLs."""
        self._path_cache.clear()
        self._url_cache.clear()
        self._collision_tracker.clear()


def parse_content_path(content_path: str, hugo_config: HugoConfig) -> PageIdentifier:
    """
    Parse a content file path to extract page identifier components.

    This is the inverse operation of resolve_content_path.

    Args:
        content_path: Content file path (e.g., "content/docs.aspose.org/cells/en/overview.md")
        hugo_config: Hugo site configuration

    Returns:
        PageIdentifier extracted from the path

    Raises:
        ValueError: If path format is invalid
    """
    # Normalize path separators
    content_path = content_path.replace("\\", "/")

    # Strip content root prefix if present
    if content_path.startswith(hugo_config.content_root + "/"):
        content_path = content_path[len(hugo_config.content_root) + 1:]

    # Split into parts
    parts = content_path.split("/")
    if len(parts) < 3:
        raise ValueError(f"Invalid content path: {content_path}")

    subdomain = parts[0]
    family = parts[1]

    # Determine section from subdomain
    if subdomain.startswith("products."):
        section = "products"
    elif subdomain.startswith("docs."):
        section = "docs"
    elif subdomain.startswith("reference."):
        section = "reference"
    elif subdomain.startswith("kb."):
        section = "kb"
    elif subdomain.startswith("blog."):
        section = "blog"
    else:
        # Default to docs
        section = "docs"

    # Parse filename
    filename = parts[-1]
    is_section_index = filename.startswith("_index")

    # Blog section uses different structure
    if section == "blog":
        # Blog: filename-based i18n
        locale = hugo_config.default_language

        # Check for language suffix
        lang_match = re.search(r"\.([a-z]{2})\.md$", filename)
        if lang_match:
            locale = lang_match.group(1)
            # Remove language suffix from filename
            filename = re.sub(r"\.[a-z]{2}\.md$", ".md", filename)

        subsections = parts[2:-1] if len(parts) > 3 else None

        # Extract slug from filename
        if is_section_index:
            slug = ""
        else:
            slug = re.sub(r"\.md$", "", filename)
            # Check for date prefix in blog posts
            date_match = re.match(r"(\d{4})-\d{2}-\d{2}-(.+)", slug)
            if date_match:
                year = date_match.group(1)
                slug = date_match.group(2)
            else:
                year = None
    else:
        # Non-blog: locale folder structure
        locale = parts[2]

        subsections = parts[3:-1] if len(parts) > 4 else None

        # Extract slug from filename
        if is_section_index:
            slug = ""
            year = None
        elif filename == "index.md":
            # Bundle page: slug is parent folder
            slug = parts[-2]
            year = None
        else:
            # Flat page: slug is filename without .md
            slug = re.sub(r"\.md$", "", filename)
            year = None

    return PageIdentifier(
        section=section,
        slug=slug,
        locale=locale,
        subsections=list(subsections) if subsections else None,
        year=year if section == "blog" else None,
        is_section_index=is_section_index,
    )
