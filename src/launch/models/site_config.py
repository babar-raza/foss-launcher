"""SiteConfig: Central configuration for URL generation and output paths.

Replaces hardcoded subdomain maps in W4 (get_subdomain_for_section) and
public_urls.py (build_absolute_public_url). Provides configurable URL and
output path templates.

Usage:
    from launch.models.site_config import SiteConfig, DEFAULT_SITE_CONFIG

    config = SiteConfig.from_run_config(run_config)
    url = config.build_url(section="docs", family="cells", platform="python", slug="overview")
    path = config.build_output_path(section="docs", family="cells", platform="python", slug="overview")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# Default subdomain mapping — single source of truth (DRY)
DEFAULT_SUBDOMAIN_MAP: Dict[str, str] = {
    "products": "products.aspose.org",
    "docs": "docs.aspose.org",
    "reference": "reference.aspose.org",
    "kb": "kb.aspose.org",
    "blog": "blog.aspose.org",
}

# Default domain
DEFAULT_DOMAIN = "aspose.org"


@dataclass
class SiteConfig:
    """Central site configuration for URL and path generation.

    All URL and output path computation flows through this config, making
    the system portable across different site structures and domains.
    """

    # Base domain (e.g., "aspose.org")
    domain: str = DEFAULT_DOMAIN

    # Section → subdomain mapping
    subdomain_map: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SUBDOMAIN_MAP))

    # URL template for absolute URLs
    # Available placeholders: {scheme}, {subdomain}, {family}, {platform}, {slug}
    # Platform segment is omitted when platform is empty
    url_scheme: str = "https"

    # Output path template for content files (TC-2000: no {section} subdirectory)
    # All non-blog sections use the same {family}/{locale} ordering
    # Available placeholders: {subdomain}, {family}, {locale}, {platform}, {slug}
    # Platform segment is omitted when empty
    output_path_template: str = "content/{subdomain}/{family}/{locale}/{platform}/{slug}.md"

    # Blog output path template (different structure)
    blog_output_path_template: str = "content/blog.{domain}/{family}/{platform}/{slug}/index.md"

    def get_subdomain(self, section: str) -> str:
        """Get subdomain for a section. Falls back to docs subdomain."""
        return self.subdomain_map.get(section, f"docs.{self.domain}")

    def build_url(
        self,
        section: str,
        family: str,
        slug: str,
        platform: str = "",
    ) -> str:
        """Build absolute URL for a page.

        Args:
            section: Section name (products, docs, reference, kb, blog)
            family: Product family slug (e.g., "cells")
            slug: Page slug (e.g., "overview")
            platform: Platform identifier (e.g., "python"). Empty for no platform.

        Returns:
            Absolute URL (e.g., "https://docs.aspose.org/cells/python/overview/")
        """
        subdomain = self.get_subdomain(section)

        # Build path segments
        parts = [family]
        if platform:
            parts.append(platform)
        parts.append(slug)

        path = "/" + "/".join(parts) + "/"
        return f"{self.url_scheme}://{subdomain}{path}"

    def build_url_path(
        self,
        section: str,
        family: str,
        slug: str,
        platform: str = "",
    ) -> str:
        """Build root-relative URL path (without scheme+domain).

        For backwards compatibility with code that needs just the path part.
        """
        parts = [family]
        if platform:
            parts.append(platform)
        parts.append(slug)
        return "/" + "/".join(parts) + "/"

    def build_output_path(
        self,
        section: str,
        slug: str,
        family: str,
        locale: str = "en",
        platform: str = "",
        subdomain: Optional[str] = None,
    ) -> str:
        """Build output file path relative to site repo root.

        Hugo-correct layout (TC-2000/2002):
        - Non-blog: content/<subdomain>/<family>/<locale>/[<platform>/]<slug>.md
        - Blog: content/blog.<domain>/<family>/[<platform>/]<slug>/index.md

        Args:
            section: Section name
            slug: Page slug
            family: Product family slug
            locale: Language code (default "en")
            platform: Platform identifier
            subdomain: Override subdomain (auto-resolved from section if not given)

        Returns:
            Relative file path (e.g., "content/docs.aspose.org/cells/en/overview.md")
        """
        if subdomain is None:
            subdomain = self.get_subdomain(section)

        # TC-2002: Hugo section pages need _index.md (branch bundle), not index.md
        if (slug == "index" or slug == "_index") and section != "blog":
            effective_slug = "_index"
        else:
            effective_slug = slug

        # Blog has a different path structure
        if section == "blog":
            template = self.blog_output_path_template
            path = template.format(
                domain=self.domain,
                family=family,
                platform=platform,
                slug=slug,
            )
        else:
            # TC-2000: All non-blog sections use same template (no section subdirectory)
            path = self.output_path_template.format(
                subdomain=subdomain,
                family=family,
                locale=locale,
                platform=platform,
                slug=effective_slug,
            )

        # Clean up double slashes from empty platform segments
        while "//" in path:
            path = path.replace("//", "/")

        return path

    @classmethod
    def from_run_config(cls, run_config: Optional[Dict[str, Any]] = None) -> SiteConfig:
        """Create SiteConfig from run_config dict.

        Reads site configuration from run_config.site_layout if available,
        otherwise returns defaults.
        """
        if run_config is None:
            return cls()

        site_layout = run_config.get("site_layout", {})
        if not isinstance(site_layout, dict):
            site_layout = {}

        return cls(
            domain=site_layout.get("domain", DEFAULT_DOMAIN),
            subdomain_map=site_layout.get("subdomain_map", dict(DEFAULT_SUBDOMAIN_MAP)),
            url_scheme=site_layout.get("url_scheme", "https"),
            output_path_template=site_layout.get(
                "output_path_template",
                "content/{subdomain}/{family}/{locale}/{platform}/{slug}.md",
            ),
            blog_output_path_template=site_layout.get(
                "blog_output_path_template",
                "content/blog.{domain}/{family}/{platform}/{slug}/index.md",
            ),
        )


# Singleton default config
DEFAULT_SITE_CONFIG = SiteConfig()
