"""
Unit tests for public URL resolver.

Verifies the binding contract in specs/33_public_url_mapping.md.
"""

import pytest

from launch.resolvers.public_urls import (
    HugoFacts,
    PageKind,
    PublicUrlTarget,
    resolve_public_url,
    resolve_url_from_content_path,
)


# Default Hugo facts for tests
DEFAULT_HUGO_FACTS = HugoFacts(
    default_language="en",
    default_language_in_subdir=False,
    permalinks={},
)


class TestResolvePublicUrl:
    """Tests for resolve_public_url function."""

    def test_default_language_drops_locale_prefix(self):
        """Default language (en) should not have locale prefix in URL."""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/words/"

    def test_non_default_language_includes_locale_prefix(self):
        """Non-default language should have locale prefix in URL."""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="fr",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/fr/words/"

    def test_section_path_after_family(self):
        """Section path segments should appear after family."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["developer-guide"],
            page_kind=PageKind.LEAF_PAGE,
            slug="quickstart",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/developer-guide/quickstart/"

    def test_nested_slugs_map_correctly(self):
        """Nested section paths should map to nested URL segments."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["api", "workbook"],
            page_kind=PageKind.LEAF_PAGE,
            slug="save-methods",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/api/workbook/save-methods/"

    def test_section_index_no_slug_in_url(self):
        """Section indexes (_index.md) should not have slug in URL."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["developer-guide"],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/developer-guide/"

    def test_family_root_index(self):
        """Family root _index.md should map to /family/."""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/words/"

    def test_v1_layout_no_platform(self):
        """V1 layout (no platform) should omit platform segment."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["getting-started"],
            page_kind=PageKind.LEAF_PAGE,
            slug="overview",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/getting-started/overview/"

    def test_default_language_in_subdir_true(self):
        """When default_language_in_subdir=true, all languages have prefix."""
        hugo_facts = HugoFacts(
            default_language="en",
            default_language_in_subdir=True,
            permalinks={},
        )
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        url = resolve_public_url(target, hugo_facts)
        assert url == "/en/cells/"

    def test_blog_default_language(self):
        """Blog with default language should drop locale prefix."""
        target = PublicUrlTarget(
            subdomain="blog.aspose.org",
            family="cells",
            locale="en",
            section_path=[],
            page_kind=PageKind.LEAF_PAGE,
            slug="2024-01-15-new-release",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/2024-01-15-new-release/"

    def test_blog_non_default_language(self):
        """Blog with non-default language should include locale prefix."""
        target = PublicUrlTarget(
            subdomain="blog.aspose.org",
            family="cells",
            locale="fr",
            section_path=[],
            page_kind=PageKind.LEAF_PAGE,
            slug="2024-01-15-new-release",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/fr/cells/2024-01-15-new-release/"

    def test_bundle_page_same_as_leaf(self):
        """Bundle pages (slug/index.md) should map same as leaf pages."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["guide"],
            page_kind=PageKind.BUNDLE_PAGE,
            slug="installation",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/guide/installation/"


class TestResolveUrlFromContentPath:
    """Tests for resolve_url_from_content_path function."""

    def test_products_default_lang(self):
        """Products path with default language."""
        url = resolve_url_from_content_path(
            "content/products.aspose.org/words/en/_index.md",
            DEFAULT_HUGO_FACTS,
        )
        assert url == "/words/"

    def test_docs_nested_page(self):
        """Docs path with nested section."""
        url = resolve_url_from_content_path(
            "content/docs.aspose.org/cells/en/developer-guide/quickstart.md",
            DEFAULT_HUGO_FACTS,
        )
        assert url == "/cells/developer-guide/quickstart/"

    def test_non_default_language(self):
        """Non-default language path should include locale in URL."""
        url = resolve_url_from_content_path(
            "content/products.aspose.org/words/fr/_index.md",
            DEFAULT_HUGO_FACTS,
        )
        assert url == "/fr/words/"

    def test_v1_layout(self):
        """V1 layout path (no platform folder)."""
        url = resolve_url_from_content_path(
            "content/docs.aspose.org/cells/en/getting-started.md",
            DEFAULT_HUGO_FACTS,
        )
        assert url == "/cells/getting-started/"

    def test_section_index_detection(self):
        """_index.md files should be detected as section indexes."""
        url = resolve_url_from_content_path(
            "content/docs.aspose.org/cells/en/developer-guide/_index.md",
            DEFAULT_HUGO_FACTS,
        )
        assert url == "/cells/developer-guide/"


class TestHugoFactsFromDict:
    """Tests for HugoFacts.from_dict class method."""

    def test_from_dict_complete(self):
        """Create HugoFacts from complete dictionary."""
        data = {
            "default_language": "de",
            "default_language_in_subdir": True,
            "permalinks": {"blog": "/:year/:month/:slug/"},
        }
        facts = HugoFacts.from_dict(data)
        assert facts.default_language == "de"
        assert facts.default_language_in_subdir is True
        assert facts.permalinks == {"blog": "/:year/:month/:slug/"}

    def test_from_dict_defaults(self):
        """Create HugoFacts with defaults for missing keys."""
        facts = HugoFacts.from_dict({})
        assert facts.default_language == "en"
        assert facts.default_language_in_subdir is False
        assert facts.permalinks == {}


class TestPathValidation:
    """Tests for path component validation."""

    def test_rejects_path_traversal(self):
        """Path components with '..' should be rejected."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=[".."],
            page_kind=PageKind.LEAF_PAGE,
            slug="test",
        )
        with pytest.raises(ValueError):
            resolve_public_url(target, DEFAULT_HUGO_FACTS)

    def test_rejects_slash_in_component(self):
        """Path components with '/' should be rejected."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["path/traversal"],
            page_kind=PageKind.LEAF_PAGE,
            slug="test",
        )
        with pytest.raises(ValueError):
            resolve_public_url(target, DEFAULT_HUGO_FACTS)


class TestSpecExamples:
    """Tests verifying examples from specs/33_public_url_mapping.md."""

    def test_products_words_en_root(self):
        """Example: products.aspose.org/words/en/_index.md -> /words/"""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/words/"

    def test_products_words_en_overview(self):
        """Example: products/words/en/overview.md -> /words/overview/"""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="en",
            section_path=[],
            page_kind=PageKind.LEAF_PAGE,
            slug="overview",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/words/overview/"

    def test_products_words_fr_root(self):
        """Example: products/words/fr/_index.md -> /fr/words/"""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="fr",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/fr/words/"

    def test_docs_cells_developer_guide_index(self):
        """Example: docs/cells/en/developer-guide/_index.md -> /cells/developer-guide/"""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["developer-guide"],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/cells/developer-guide/"

    def test_docs_cells_developer_guide_quickstart(self):
        """Example: docs/cells/en/developer-guide/quickstart.md -> /cells/developer-guide/quickstart/"""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["developer-guide"],
            page_kind=PageKind.LEAF_PAGE,
            slug="quickstart",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/cells/developer-guide/quickstart/"

    def test_kb_cells_troubleshooting(self):
        """Example: kb/cells/en/troubleshooting.md -> /cells/troubleshooting/"""
        target = PublicUrlTarget(
            subdomain="kb.aspose.org",
            family="cells",
            locale="en",
            section_path=[],
            page_kind=PageKind.LEAF_PAGE,
            slug="troubleshooting",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/cells/troubleshooting/"

    def test_reference_cells_root(self):
        """Example: reference/cells/en/_index.md -> /cells/"""
        target = PublicUrlTarget(
            subdomain="reference.aspose.org",
            family="cells",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/cells/"
