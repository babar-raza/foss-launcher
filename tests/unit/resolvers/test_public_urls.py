"""
Unit tests for public URL resolver.

Verifies the binding contract in specs/33_public_url_mapping.md.

V2 platform-aware layout: platform segment inserted after family in URLs.
URL pattern: /{family}/{platform}/{section_path}/{slug}/
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
    """Tests for resolve_public_url function (V2 layout)."""

    def test_default_language_drops_locale_prefix(self):
        """Default language (en) should not have locale prefix in URL."""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/words/python/"

    def test_non_default_language_includes_locale_prefix(self):
        """Non-default language should have locale prefix in URL."""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="fr",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/fr/words/python/"

    def test_section_path_after_platform(self):
        """Section path segments should appear after platform."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["developer-guide"],
            page_kind=PageKind.LEAF_PAGE,
            slug="quickstart",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/python/developer-guide/quickstart/"

    def test_nested_slugs_map_correctly(self):
        """Nested section paths should map to nested URL segments after platform."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["api", "workbook"],
            page_kind=PageKind.LEAF_PAGE,
            slug="save-methods",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/python/api/workbook/save-methods/"

    def test_section_index_no_slug_in_url(self):
        """Section indexes (_index.md) should not have slug in URL."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["developer-guide"],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/python/developer-guide/"

    def test_family_root_index_with_platform(self):
        """Family root _index.md with platform should map to /family/platform/."""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/words/python/"

    def test_backward_compat_no_platform(self):
        """Empty platform should omit platform segment (V1 backward compat)."""
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
            platform="python",
        )
        url = resolve_public_url(target, hugo_facts)
        assert url == "/en/cells/python/"

    def test_blog_default_language(self):
        """Blog with default language and platform should drop locale prefix."""
        target = PublicUrlTarget(
            subdomain="blog.aspose.org",
            family="cells",
            locale="en",
            section_path=[],
            page_kind=PageKind.LEAF_PAGE,
            slug="2024-01-15-new-release",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/python/2024-01-15-new-release/"

    def test_blog_non_default_language(self):
        """Blog with non-default language and platform should include locale prefix."""
        target = PublicUrlTarget(
            subdomain="blog.aspose.org",
            family="cells",
            locale="fr",
            section_path=[],
            page_kind=PageKind.LEAF_PAGE,
            slug="2024-01-15-new-release",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/fr/cells/python/2024-01-15-new-release/"

    def test_bundle_page_same_as_leaf(self):
        """Bundle pages (slug/index.md) should map same as leaf pages."""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["guide"],
            page_kind=PageKind.BUNDLE_PAGE,
            slug="installation",
            platform="python",
        )
        url = resolve_public_url(target, DEFAULT_HUGO_FACTS)
        assert url == "/cells/python/guide/installation/"


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
            platform="python",
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
            platform="python",
        )
        with pytest.raises(ValueError):
            resolve_public_url(target, DEFAULT_HUGO_FACTS)


class TestSpecExamples:
    """Tests verifying examples from specs/33_public_url_mapping.md (V2 layout)."""

    def test_products_words_en_root(self):
        """Example: products.aspose.org/words/python/ (section index)"""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
            platform="python",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/words/python/"

    def test_products_words_en_overview(self):
        """Example: products/words/python/overview/"""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="en",
            section_path=[],
            page_kind=PageKind.LEAF_PAGE,
            slug="overview",
            platform="python",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/words/python/overview/"

    def test_products_words_fr_root(self):
        """Example: /fr/words/python/ (non-default locale)"""
        target = PublicUrlTarget(
            subdomain="products.aspose.org",
            family="words",
            locale="fr",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
            platform="python",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/fr/words/python/"

    def test_docs_cells_developer_guide_index(self):
        """Example: /cells/python/developer-guide/ (section index)"""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["developer-guide"],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
            platform="python",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/cells/python/developer-guide/"

    def test_docs_cells_developer_guide_quickstart(self):
        """Example: /cells/python/developer-guide/quickstart/"""
        target = PublicUrlTarget(
            subdomain="docs.aspose.org",
            family="cells",
            locale="en",
            section_path=["developer-guide"],
            page_kind=PageKind.LEAF_PAGE,
            slug="quickstart",
            platform="python",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/cells/python/developer-guide/quickstart/"

    def test_kb_cells_troubleshooting(self):
        """Example: /cells/python/troubleshooting/"""
        target = PublicUrlTarget(
            subdomain="kb.aspose.org",
            family="cells",
            locale="en",
            section_path=[],
            page_kind=PageKind.LEAF_PAGE,
            slug="troubleshooting",
            platform="python",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/cells/python/troubleshooting/"

    def test_reference_cells_root(self):
        """Example: /cells/python/ (reference section index)"""
        target = PublicUrlTarget(
            subdomain="reference.aspose.org",
            family="cells",
            locale="en",
            section_path=[],
            page_kind=PageKind.SECTION_INDEX,
            slug="",
            platform="python",
        )
        assert resolve_public_url(target, DEFAULT_HUGO_FACTS) == "/cells/python/"
