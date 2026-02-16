"""Tests for SiteConfig (Phase 1B).

Validates centralized URL generation and output path computation.
"""
import pytest
from launch.models.site_config import SiteConfig, DEFAULT_SITE_CONFIG, DEFAULT_SUBDOMAIN_MAP


class TestSiteConfigDefaults:
    def test_default_domain(self):
        assert DEFAULT_SITE_CONFIG.domain == "aspose.org"

    def test_default_subdomain_map(self):
        assert DEFAULT_SITE_CONFIG.subdomain_map == DEFAULT_SUBDOMAIN_MAP

    def test_get_subdomain_docs(self):
        assert DEFAULT_SITE_CONFIG.get_subdomain("docs") == "docs.aspose.org"

    def test_get_subdomain_products(self):
        assert DEFAULT_SITE_CONFIG.get_subdomain("products") == "products.aspose.org"

    def test_get_subdomain_blog(self):
        assert DEFAULT_SITE_CONFIG.get_subdomain("blog") == "blog.aspose.org"

    def test_get_subdomain_unknown_falls_back(self):
        result = DEFAULT_SITE_CONFIG.get_subdomain("unknown")
        assert result == "docs.aspose.org"  # Falls back to docs


class TestBuildUrl:
    def test_basic_url(self):
        url = DEFAULT_SITE_CONFIG.build_url("docs", "cells", "overview")
        assert url == "https://docs.aspose.org/cells/overview/"

    def test_url_with_platform(self):
        url = DEFAULT_SITE_CONFIG.build_url("docs", "cells", "overview", platform="python")
        assert url == "https://docs.aspose.org/cells/python/overview/"

    def test_blog_url(self):
        url = DEFAULT_SITE_CONFIG.build_url("blog", "3d", "announcement")
        assert url == "https://blog.aspose.org/3d/announcement/"

    def test_kb_url(self):
        url = DEFAULT_SITE_CONFIG.build_url("kb", "cells", "faq")
        assert url == "https://kb.aspose.org/cells/faq/"

    def test_products_url(self):
        url = DEFAULT_SITE_CONFIG.build_url("products", "cells", "overview")
        assert url == "https://products.aspose.org/cells/overview/"

    def test_reference_url_with_platform(self):
        url = DEFAULT_SITE_CONFIG.build_url("reference", "cells", "api", platform="python")
        assert url == "https://reference.aspose.org/cells/python/api/"


class TestBuildUrlPath:
    def test_basic_path(self):
        path = DEFAULT_SITE_CONFIG.build_url_path("docs", "cells", "overview")
        assert path == "/cells/overview/"

    def test_path_with_platform(self):
        path = DEFAULT_SITE_CONFIG.build_url_path("docs", "cells", "overview", platform="python")
        assert path == "/cells/python/overview/"


class TestBuildOutputPath:
    def test_docs_output_path(self):
        path = DEFAULT_SITE_CONFIG.build_output_path(
            "docs", "overview", "cells", locale="en"
        )
        assert path == "content/docs.aspose.org/cells/en/overview.md"

    def test_docs_output_path_with_platform(self):
        path = DEFAULT_SITE_CONFIG.build_output_path(
            "docs", "overview", "cells", locale="en", platform="python"
        )
        assert path == "content/docs.aspose.org/cells/en/python/overview.md"

    def test_blog_output_path(self):
        path = DEFAULT_SITE_CONFIG.build_output_path(
            "blog", "announcement", "3d"
        )
        assert path == "content/blog.aspose.org/3d/announcement/index.md"

    def test_blog_output_path_with_platform(self):
        path = DEFAULT_SITE_CONFIG.build_output_path(
            "blog", "announcement", "3d", platform="python"
        )
        assert path == "content/blog.aspose.org/3d/python/announcement/index.md"

    def test_products_output_path(self):
        path = DEFAULT_SITE_CONFIG.build_output_path(
            "products", "overview", "cells"
        )
        # Products uses same family-first ordering as all non-blog sections
        assert path == "content/products.aspose.org/cells/en/overview.md"

    def test_subdomain_override(self):
        path = DEFAULT_SITE_CONFIG.build_output_path(
            "docs", "overview", "cells", subdomain="custom.example.org"
        )
        assert path == "content/custom.example.org/cells/en/overview.md"


class TestCustomSiteConfig:
    def test_custom_domain(self):
        config = SiteConfig(domain="example.com")
        # Unknown section falls back using custom domain
        subdomain = config.get_subdomain("unknown")
        assert subdomain == "docs.example.com"

    def test_custom_subdomain_map(self):
        config = SiteConfig(
            subdomain_map={"docs": "documentation.example.com"}
        )
        assert config.get_subdomain("docs") == "documentation.example.com"

    def test_custom_url_scheme(self):
        config = SiteConfig(url_scheme="http")
        url = config.build_url("docs", "cells", "overview")
        assert url.startswith("http://")


class TestFromRunConfig:
    def test_default_when_no_config(self):
        config = SiteConfig.from_run_config(None)
        assert config.domain == "aspose.org"

    def test_default_when_empty_site_layout(self):
        config = SiteConfig.from_run_config({"site_layout": {}})
        assert config.domain == "aspose.org"

    def test_custom_domain_from_run_config(self):
        config = SiteConfig.from_run_config({
            "site_layout": {"domain": "example.com"}
        })
        assert config.domain == "example.com"

    def test_custom_output_template(self):
        config = SiteConfig.from_run_config({
            "site_layout": {
                "output_path_template": "output/{family}/{slug}.md"
            }
        })
        path = config.build_output_path("docs", "overview", "cells")
        assert path == "output/cells/overview.md"
