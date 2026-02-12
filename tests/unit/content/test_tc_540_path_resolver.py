"""
Unit tests for TC-540: Content Path Resolver.

Verifies path resolution with Hugo layout rules per specs/33_public_url_mapping.md
and specs/06_page_planning.md.

V2 platform-aware layout: platform segment inserted after locale (non-blog)
or after family (blog).
"""

import pytest

from launch.content import (
    ContentPathResolver,
    ContentStyle,
    HugoConfig,
    PageIdentifier,
    generate_slug,
    parse_content_path,
    resolve_content_path,
    resolve_permalink,
)


class TestSlugGeneration:
    """Tests for slug generation from page titles."""

    def test_basic_slug_generation(self):
        """Basic title should convert to lowercase with hyphens."""
        assert generate_slug("Getting Started") == "getting-started"

    def test_special_characters_removed(self):
        """Special characters should be removed."""
        assert generate_slug("API Reference: Python") == "api-reference-python"

    def test_accents_normalized(self):
        """Accented characters should be converted to ASCII."""
        assert generate_slug("Déjà Vu") == "deja-vu"
        assert generate_slug("Café") == "cafe"

    def test_consecutive_hyphens_collapsed(self):
        """Multiple consecutive hyphens should be collapsed to one."""
        assert generate_slug("Test -- Double") == "test-double"

    def test_leading_trailing_hyphens_stripped(self):
        """Leading and trailing hyphens should be removed."""
        assert generate_slug("-Leading") == "leading"
        assert generate_slug("Trailing-") == "trailing"

    def test_empty_title_raises_error(self):
        """Empty title should raise ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            generate_slug("")

    def test_title_producing_empty_slug_raises_error(self):
        """Title that produces empty slug should raise error."""
        with pytest.raises(ValueError, match="produces empty slug"):
            generate_slug("!!!!")

    def test_numbers_preserved(self):
        """Numbers should be preserved in slugs."""
        assert generate_slug("Version 2.0") == "version-20"

    def test_underscores_converted_to_hyphens(self):
        """Underscores should be converted to hyphens."""
        assert generate_slug("test_file_name") == "test-file-name"


class TestContentPathResolution:
    """Tests for resolving page identifiers to content paths (V2 layout)."""

    def test_flat_style_docs_page(self):
        """Flat style doc page with platform should resolve to <locale>/<platform>/<slug>.md."""
        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            platform="python",
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/docs.aspose.org/cells/en/python/overview.md"

    def test_bundle_style_docs_page(self):
        """Bundle style doc page with platform should resolve to <locale>/<platform>/<slug>/index.md."""
        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            platform="python",
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        path = resolve_content_path(page_id, config, ContentStyle.BUNDLE)
        assert path == "content/docs.aspose.org/cells/en/python/overview/index.md"

    def test_section_index_page(self):
        """Section index page with platform should include platform segment."""
        page_id = PageIdentifier(
            section="docs",
            slug="",
            locale="en",
            platform="python",
            is_section_index=True,
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        path = resolve_content_path(page_id, config, ContentStyle.SECTION_INDEX)
        assert path == "content/docs.aspose.org/cells/en/python/_index.md"

    def test_nested_subsections(self):
        """Pages with subsections should include platform before subsection paths."""
        page_id = PageIdentifier(
            section="docs",
            slug="quickstart",
            locale="en",
            platform="python",
            subsections=["developer-guide", "getting-started"],
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/docs.aspose.org/cells/en/python/developer-guide/getting-started/quickstart.md"

    def test_non_default_language(self):
        """Non-default language with platform should use correct locale folder."""
        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="fr",
            platform="python",
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
            default_language="en",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/docs.aspose.org/cells/fr/python/overview.md"

    def test_blog_post_default_language(self):
        """Blog post with platform should include platform after family."""
        page_id = PageIdentifier(
            section="blog",
            slug="2024-01-15-new-release",
            locale="en",
            platform="python",
            year="2024",
        )
        config = HugoConfig(
            subdomain="blog.aspose.org",
            family="cells",
            default_language="en",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/blog.aspose.org/cells/python/2024-01-15-new-release.md"

    def test_blog_post_non_default_language(self):
        """Blog post in non-default language with platform should use .<lang>.md suffix."""
        page_id = PageIdentifier(
            section="blog",
            slug="2024-01-15-new-release",
            locale="fr",
            platform="python",
            year="2024",
        )
        config = HugoConfig(
            subdomain="blog.aspose.org",
            family="cells",
            default_language="en",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/blog.aspose.org/cells/python/2024-01-15-new-release.fr.md"

    def test_blog_section_index_default_language(self):
        """Blog section index with platform in default language."""
        page_id = PageIdentifier(
            section="blog",
            slug="",
            locale="en",
            platform="python",
            is_section_index=True,
        )
        config = HugoConfig(
            subdomain="blog.aspose.org",
            family="cells",
            default_language="en",
        )
        path = resolve_content_path(page_id, config, ContentStyle.SECTION_INDEX)
        assert path == "content/blog.aspose.org/cells/python/_index.md"

    def test_blog_section_index_non_default_language(self):
        """Blog section index with platform in non-default language."""
        page_id = PageIdentifier(
            section="blog",
            slug="",
            locale="fr",
            platform="python",
            is_section_index=True,
        )
        config = HugoConfig(
            subdomain="blog.aspose.org",
            family="cells",
            default_language="en",
        )
        path = resolve_content_path(page_id, config, ContentStyle.SECTION_INDEX)
        assert path == "content/blog.aspose.org/cells/python/_index.fr.md"

    def test_products_section(self):
        """Products section with platform should use products.aspose.org subdomain."""
        page_id = PageIdentifier(
            section="products",
            slug="features",
            locale="en",
            platform="python",
        )
        config = HugoConfig(
            subdomain="products.aspose.org",
            family="words",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/products.aspose.org/words/en/python/features.md"

    def test_kb_section(self):
        """KB section with platform should use kb.aspose.org subdomain."""
        page_id = PageIdentifier(
            section="kb",
            slug="troubleshooting",
            locale="en",
            platform="python",
        )
        config = HugoConfig(
            subdomain="kb.aspose.org",
            family="cells",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/kb.aspose.org/cells/en/python/troubleshooting.md"

    def test_reference_section(self):
        """Reference section with platform should use reference.aspose.org subdomain."""
        page_id = PageIdentifier(
            section="reference",
            slug="workbook",
            locale="en",
            platform="python",
        )
        config = HugoConfig(
            subdomain="reference.aspose.org",
            family="cells",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/reference.aspose.org/cells/en/python/workbook.md"


class TestContentPathBackwardCompat:
    """Tests verifying backward compatibility with empty platform (V1 behavior)."""

    def test_no_platform_docs(self):
        """Empty platform should produce V1 paths (no platform segment)."""
        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/docs.aspose.org/cells/en/overview.md"

    def test_no_platform_blog(self):
        """Empty platform should produce V1 blog paths (no platform segment)."""
        page_id = PageIdentifier(
            section="blog",
            slug="announcement",
            locale="en",
        )
        config = HugoConfig(
            subdomain="blog.aspose.org",
            family="cells",
            default_language="en",
        )
        path = resolve_content_path(page_id, config, ContentStyle.FLAT)
        assert path == "content/blog.aspose.org/cells/announcement.md"


class TestPermalinkGeneration:
    """Tests for generating canonical public URLs (V2 layout)."""

    def test_default_language_drops_locale(self):
        """Default language should not include locale in URL, but include platform."""
        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            platform="python",
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
            default_language="en",
        )
        url = resolve_permalink(page_id, config)
        assert url == "/cells/python/overview/"

    def test_non_default_language_includes_locale(self):
        """Non-default language should include locale prefix before family and platform."""
        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="fr",
            platform="python",
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
            default_language="en",
        )
        url = resolve_permalink(page_id, config)
        assert url == "/fr/cells/python/overview/"

    def test_default_language_in_subdir(self):
        """When default_language_in_subdir=true, all languages get prefix."""
        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            platform="python",
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
            default_language="en",
            default_language_in_subdir=True,
        )
        url = resolve_permalink(page_id, config)
        assert url == "/en/cells/python/overview/"

    def test_subsections_in_url(self):
        """Subsection segments should appear after platform."""
        page_id = PageIdentifier(
            section="docs",
            slug="quickstart",
            locale="en",
            platform="python",
            subsections=["developer-guide"],
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        url = resolve_permalink(page_id, config)
        assert url == "/cells/python/developer-guide/quickstart/"

    def test_section_index_no_slug_in_url(self):
        """Section index should not include slug in URL."""
        page_id = PageIdentifier(
            section="docs",
            slug="",
            locale="en",
            platform="python",
            subsections=["developer-guide"],
            is_section_index=True,
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        url = resolve_permalink(page_id, config)
        assert url == "/cells/python/developer-guide/"


class TestPermalinkBackwardCompat:
    """Tests verifying backward compatibility with empty platform for permalinks."""

    def test_no_platform_permalink(self):
        """Empty platform should produce V1 URLs (no platform segment)."""
        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
        )
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
            default_language="en",
        )
        url = resolve_permalink(page_id, config)
        assert url == "/cells/overview/"


class TestContentPathResolver:
    """Tests for the ContentPathResolver class."""

    def test_resolve_path_caching(self):
        """Resolver should cache resolved paths."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        resolver = ContentPathResolver(config)

        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            platform="python",
        )

        # First call
        path1 = resolver.resolve_path(page_id)
        # Second call should return cached result
        path2 = resolver.resolve_path(page_id)

        assert path1 == path2
        assert path1 == "content/docs.aspose.org/cells/en/python/overview.md"

    def test_resolve_url_caching(self):
        """Resolver should cache resolved URLs."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        resolver = ContentPathResolver(config)

        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            platform="python",
        )

        # First call
        url1 = resolver.resolve_url(page_id)
        # Second call should return cached result
        url2 = resolver.resolve_url(page_id)

        assert url1 == url2
        assert url1 == "/cells/python/overview/"

    def test_detect_collisions_none(self):
        """No collisions should return empty dict."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        resolver = ContentPathResolver(config)

        page1 = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            platform="python",
        )
        page2 = PageIdentifier(
            section="docs",
            slug="quickstart",
            locale="en",
            platform="python",
        )

        resolver.resolve_url(page1)
        resolver.resolve_url(page2)

        collisions = resolver.detect_collisions()
        assert collisions == {}

    def test_detect_collisions_found(self):
        """Collisions should be detected and reported."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        resolver = ContentPathResolver(config)

        page1 = PageIdentifier(
            section="docs",
            slug="",
            locale="en",
            platform="python",
            is_section_index=True,
        )
        url1 = resolver.resolve_url(page1)

        # Simulate collision by directly tracking
        resolver._collision_tracker["/cells/python/"] = {
            "content/docs.aspose.org/cells/en/python/_index.md",
            "content/docs.aspose.org/cells/en/python/index.md",
        }

        collisions = resolver.detect_collisions()
        assert "/cells/python/" in collisions
        assert len(collisions["/cells/python/"]) == 2

    def test_clear_cache(self):
        """Clear cache should reset all internal state."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        resolver = ContentPathResolver(config)

        page_id = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            platform="python",
        )

        resolver.resolve_path(page_id)
        resolver.resolve_url(page_id)

        assert len(resolver._path_cache) > 0
        assert len(resolver._url_cache) > 0

        resolver.clear_cache()

        assert len(resolver._path_cache) == 0
        assert len(resolver._url_cache) == 0
        assert len(resolver._collision_tracker) == 0


class TestParseContentPath:
    """Tests for parsing content paths back to page identifiers."""

    def test_parse_flat_docs_page(self):
        """Parse flat style docs page."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        page_id = parse_content_path(
            "content/docs.aspose.org/cells/en/overview.md",
            config,
        )
        assert page_id.section == "docs"
        assert page_id.slug == "overview"
        assert page_id.locale == "en"
        assert page_id.is_section_index is False

    def test_parse_bundle_page(self):
        """Parse bundle style page."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        page_id = parse_content_path(
            "content/docs.aspose.org/cells/en/overview/index.md",
            config,
        )
        assert page_id.section == "docs"
        assert page_id.slug == "overview"
        assert page_id.locale == "en"
        assert page_id.is_section_index is False

    def test_parse_section_index(self):
        """Parse section index page."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        page_id = parse_content_path(
            "content/docs.aspose.org/cells/en/_index.md",
            config,
        )
        assert page_id.section == "docs"
        assert page_id.slug == ""
        assert page_id.locale == "en"
        assert page_id.is_section_index is True

    def test_parse_with_subsections(self):
        """Parse page with nested subsections."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )
        page_id = parse_content_path(
            "content/docs.aspose.org/cells/en/developer-guide/quickstart.md",
            config,
        )
        assert page_id.section == "docs"
        assert page_id.slug == "quickstart"
        assert page_id.locale == "en"
        assert page_id.subsections == ["developer-guide"]

    def test_parse_blog_post_with_date(self):
        """Parse blog post with date prefix."""
        config = HugoConfig(
            subdomain="blog.aspose.org",
            family="cells",
        )
        page_id = parse_content_path(
            "content/blog.aspose.org/cells/2024-01-15-new-release.md",
            config,
        )
        assert page_id.section == "blog"
        assert page_id.slug == "new-release"
        assert page_id.locale == "en"
        assert page_id.year == "2024"

    def test_parse_blog_post_non_default_language(self):
        """Parse blog post in non-default language."""
        config = HugoConfig(
            subdomain="blog.aspose.org",
            family="cells",
            default_language="en",
        )
        page_id = parse_content_path(
            "content/blog.aspose.org/cells/2024-01-15-new-release.fr.md",
            config,
        )
        assert page_id.section == "blog"
        assert page_id.slug == "new-release"
        assert page_id.locale == "fr"

    def test_parse_products_section(self):
        """Parse products section page."""
        config = HugoConfig(
            subdomain="products.aspose.org",
            family="words",
        )
        page_id = parse_content_path(
            "content/products.aspose.org/words/en/features.md",
            config,
        )
        assert page_id.section == "products"
        assert page_id.slug == "features"

    def test_parse_invalid_path_raises_error(self):
        """Invalid path should raise ValueError."""
        config = HugoConfig()
        with pytest.raises(ValueError, match="Invalid content path"):
            parse_content_path("invalid", config)


class TestPageIdentifierValidation:
    """Tests for PageIdentifier validation."""

    def test_section_index_with_slug_raises_error(self):
        """Section index cannot have a slug."""
        with pytest.raises(ValueError, match="Section index pages cannot have a slug"):
            PageIdentifier(
                section="docs",
                slug="invalid",
                locale="en",
                platform="python",
                is_section_index=True,
            )

    def test_non_index_without_slug_raises_error(self):
        """Non-index pages must have a slug."""
        with pytest.raises(ValueError, match="Non-index pages must have a slug"):
            PageIdentifier(
                section="docs",
                slug="",
                locale="en",
                platform="python",
                is_section_index=False,
            )

    def test_platform_field_accessible(self):
        """PageIdentifier should expose platform field."""
        page = PageIdentifier(
            section="docs",
            slug="test",
            locale="en",
            platform="typescript",
        )
        assert page.platform == "typescript"

    def test_platform_defaults_to_empty(self):
        """Platform should default to empty string."""
        page = PageIdentifier(
            section="docs",
            slug="test",
            locale="en",
        )
        assert page.platform == ""


class TestHugoConfigFromDict:
    """Tests for HugoConfig.from_dict method."""

    def test_from_dict_complete(self):
        """Create HugoConfig from complete dictionary."""
        data = {
            "default_language": "de",
            "default_language_in_subdir": True,
            "content_root": "hugo/content",
            "subdomain": "docs.example.org",
            "family": "test",
        }
        config = HugoConfig.from_dict(data)
        assert config.default_language == "de"
        assert config.default_language_in_subdir is True
        assert config.content_root == "hugo/content"
        assert config.subdomain == "docs.example.org"
        assert config.family == "test"

    def test_from_dict_defaults(self):
        """Create HugoConfig with defaults for missing keys."""
        config = HugoConfig.from_dict({})
        assert config.default_language == "en"
        assert config.default_language_in_subdir is False
        assert config.content_root == "content"
        assert config.subdomain == "docs.aspose.org"
        assert config.family == "cells"


class TestRoundTripConversion:
    """Tests for round-trip conversion between paths and identifiers."""

    def test_roundtrip_flat_page(self):
        """Page ID -> path -> page ID should preserve all fields."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )

        original = PageIdentifier(
            section="docs",
            slug="overview",
            locale="en",
            subsections=["developer-guide"],
        )

        path = resolve_content_path(original, config, ContentStyle.FLAT)
        parsed = parse_content_path(path, config)

        assert parsed.section == original.section
        assert parsed.slug == original.slug
        assert parsed.locale == original.locale
        assert parsed.subsections == original.subsections

    def test_roundtrip_section_index(self):
        """Section index round-trip should preserve index flag."""
        config = HugoConfig(
            subdomain="docs.aspose.org",
            family="cells",
        )

        original = PageIdentifier(
            section="docs",
            slug="",
            locale="en",
            is_section_index=True,
        )

        path = resolve_content_path(original, config, ContentStyle.SECTION_INDEX)
        parsed = parse_content_path(path, config)

        assert parsed.is_section_index is True
        assert parsed.slug == ""
