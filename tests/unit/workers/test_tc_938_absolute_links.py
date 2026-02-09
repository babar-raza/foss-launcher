"""
TC-938: Unit tests for absolute cross-subdomain links.

Tests the build_absolute_public_url() function to ensure cross-section links
are generated with absolute URLs (scheme + subdomain + path).
"""

import pytest
from src.launch.resolvers.public_urls import (
    build_absolute_public_url,
    HugoFacts,
)


class TestBuildAbsolutePublicUrl:
    """Test suite for build_absolute_public_url() function (TC-938)."""

    def test_docs_section_absolute_url(self):
        """Test absolute URL generation for docs section."""
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="overview",
        )
        assert result == "https://docs.aspose.org/cells/overview/"

    def test_reference_section_absolute_url(self):
        """Test absolute URL generation for reference section."""
        result = build_absolute_public_url(
            section="reference",
            family="cells",
            locale="en",
            slug="api",
        )
        assert result == "https://reference.aspose.org/cells/api/"

    def test_products_section_absolute_url(self):
        """Test absolute URL generation for products section."""
        result = build_absolute_public_url(
            section="products",
            family="cells",
            locale="en",
            slug="features",
        )
        assert result == "https://products.aspose.org/cells/features/"

    def test_kb_section_absolute_url(self):
        """Test absolute URL generation for kb section."""
        result = build_absolute_public_url(
            section="kb",
            family="cells",
            locale="en",
            slug="troubleshooting",
        )
        assert result == "https://kb.aspose.org/cells/troubleshooting/"

    def test_blog_section_absolute_url(self):
        """Test absolute URL generation for blog section."""
        result = build_absolute_public_url(
            section="blog",
            family="cells",
            locale="en",
            slug="announcement",
        )
        assert result == "https://blog.aspose.org/cells/announcement/"

    def test_section_index_absolute_url(self):
        """Test absolute URL generation for section index (no slug)."""
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="",  # Empty slug for section index
        )
        assert result == "https://docs.aspose.org/cells/"

    def test_non_default_locale_absolute_url(self):
        """Test absolute URL with non-default locale (includes locale prefix)."""
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="fr",
            slug="overview",
        )
        assert result == "https://docs.aspose.org/fr/cells/overview/"

    def test_subsections_in_absolute_url(self):
        """Test absolute URL with nested subsections."""
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="quickstart",
            subsections=["developer-guide", "getting-started"],
        )
        assert result == "https://docs.aspose.org/cells/developer-guide/getting-started/quickstart/"

    def test_v1_layout(self):
        """Test absolute URL for V1 layout (no platform segment)."""
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="overview",
        )
        assert result == "https://docs.aspose.org/cells/overview/"

    def test_unknown_section_raises_error(self):
        """Test that unknown section raises ValueError."""
        with pytest.raises(ValueError, match="Unknown section"):
            build_absolute_public_url(
                section="unknown_section",
                family="cells",
                locale="en",
                slug="test",
            )

    def test_custom_hugo_facts(self):
        """Test absolute URL with custom HugoFacts."""
        hugo_facts = HugoFacts(
            default_language="en",
            default_language_in_subdir=True,  # Include locale for all languages
            permalinks={},
        )
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="overview",
            hugo_facts=hugo_facts,
        )
        # With default_language_in_subdir=True, even default language includes locale
        assert result == "https://docs.aspose.org/en/cells/overview/"

    def test_blog_section_family_slug_pattern(self):
        """Test blog URL follows pattern: blog.aspose.org/<family>/<slug>/"""
        result = build_absolute_public_url(
            section="blog",
            family="words",
            locale="en",
            slug="new-release",
        )
        assert result == "https://blog.aspose.org/words/new-release/"

    def test_all_sections_map_to_correct_subdomain(self):
        """Test that all sections map to their correct subdomains."""
        sections = {
            "products": "products.aspose.org",
            "docs": "docs.aspose.org",
            "reference": "reference.aspose.org",
            "kb": "kb.aspose.org",
            "blog": "blog.aspose.org",
        }

        for section, expected_subdomain in sections.items():
            result = build_absolute_public_url(
                section=section,
                family="cells",
                locale="en",
                slug="test",
            )
            assert result.startswith(f"https://{expected_subdomain}/")

    def test_url_has_trailing_slash(self):
        """Test that generated URLs always have trailing slash."""
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="overview",
        )
        assert result.endswith("/")

    def test_url_has_no_double_slashes(self):
        """Test that generated URLs have no double slashes."""
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="overview",
        )
        # Check no double slashes (except in https://)
        assert "//" not in result.replace("https://", "")


class TestCrossSectionLinkScenarios:
    """Test realistic cross-section linking scenarios (TC-938)."""

    def test_docs_to_reference_link(self):
        """Test link from docs page to reference page."""
        # Scenario: Docs page wants to link to API reference
        result = build_absolute_public_url(
            section="reference",
            family="cells",
            locale="en",
            slug="",  # Reference section index
        )
        assert result == "https://reference.aspose.org/cells/"

    def test_blog_to_products_link(self):
        """Test link from blog post to products page."""
        # Scenario: Blog announcement wants to link to product page
        result = build_absolute_public_url(
            section="products",
            family="cells",
            locale="en",
            slug="features",
        )
        assert result == "https://products.aspose.org/cells/features/"

    def test_kb_to_docs_link(self):
        """Test link from kb article to docs guide."""
        # Scenario: KB troubleshooting article references docs guide
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="installation",
        )
        assert result == "https://docs.aspose.org/cells/installation/"

    def test_products_to_docs_quickstart(self):
        """Test link from products landing to docs quickstart."""
        # Scenario: Products page links to getting started guide
        result = build_absolute_public_url(
            section="docs",
            family="cells",
            locale="en",
            slug="getting-started",
        )
        assert result == "https://docs.aspose.org/cells/getting-started/"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
