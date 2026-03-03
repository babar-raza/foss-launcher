"""Tests for placeholder link stripping and doubled path segment deduplication.

Agent-D / D1 + D2: Validates deterministic link sanitizer functions.
"""

import pytest

from launch.workers._shared.content_sanitizer import (
    strip_placeholder_links,
    fix_doubled_path_segments,
    _is_placeholder_url,
)
from launch.workers._shared.markdown_zones import apply_to_prose_zones


# ── D1: strip_placeholder_links ──────────────────────────────────────────────


class TestIsPlaceholderUrl:
    """Unit tests for the _is_placeholder_url helper."""

    @pytest.mark.parametrize("url", [
        "https://example.com/foo",
        "http://example.org/bar",
        "https://example.net/baz",
        "http://localhost:8080/api",
        "http://127.0.0.1/api",
        "http://0.0.0.0:3000",
        "https://your-domain.com/api",
        "https://api.example.com/v1",
        "https://my-app.com/TODO/setup",
        "https://site.com/FIXME/path",
        "https://real.com/PLACEHOLDER/item",
        "https://your-api.example.com/v2",
        "https://app.com/change-me/endpoint",
    ])
    def test_placeholder_detected(self, url):
        assert _is_placeholder_url(url) is True

    @pytest.mark.parametrize("url", [
        "https://docs.aspose.org/3d/python/overview/",
        "https://github.com/aspose/repo",
        "https://pypi.org/project/aspose-3d/",
        "/3d/python/getting-started/",
        "#section-anchor",
    ])
    def test_real_url_not_flagged(self, url):
        assert _is_placeholder_url(url) is False


class TestStripPlaceholderLinks:
    """Tests for strip_placeholder_links()."""

    def test_markdown_link_example_com_stripped(self):
        md = "See [the docs](https://example.com/getting-started) for details."
        result = strip_placeholder_links(md)
        assert result == "See the docs for details."

    def test_markdown_link_localhost_stripped(self):
        md = "Visit [API](http://localhost:8080/api) to test."
        result = strip_placeholder_links(md)
        assert result == "Visit API to test."

    def test_markdown_link_todo_token_stripped(self):
        md = "Check [link](https://real-site.com/TODO/setup) here."
        result = strip_placeholder_links(md)
        assert result == "Check link here."

    def test_markdown_link_your_domain_stripped(self):
        md = "Go to [portal](https://your-domain.com/login) now."
        result = strip_placeholder_links(md)
        assert result == "Go to portal now."

    def test_real_link_preserved(self):
        md = "See [Aspose.3D](https://docs.aspose.org/3d/python/) for details."
        result = strip_placeholder_links(md)
        assert result == md

    def test_multiple_links_mixed(self):
        md = (
            "Use [real](https://docs.aspose.org/3d/) and "
            "[fake](https://example.com/api) together."
        )
        result = strip_placeholder_links(md)
        assert "[real](https://docs.aspose.org/3d/)" in result
        assert "[fake]" not in result
        assert "example.com" not in result

    def test_autolink_example_stripped_to_plain_text(self):
        """SR-03: autolink replaced with plain-text URL (not empty string)."""
        md = "Endpoint: <https://example.com/api/v1> is the base."
        result = strip_placeholder_links(md)
        assert "<https://example.com" not in result  # angle brackets gone
        assert "https://example.com/api/v1" in result  # URL kept as plain text
        assert "Endpoint:" in result

    def test_autolink_real_preserved(self):
        md = "Endpoint: <https://docs.aspose.org/api/v1> is live."
        result = strip_placeholder_links(md)
        assert "<https://docs.aspose.org/api/v1>" in result

    def test_change_me_token(self):
        md = "Use [endpoint](https://api.com/change-me/v1) to configure."
        result = strip_placeholder_links(md)
        assert result == "Use endpoint to configure."

    def test_fixme_token_case_insensitive(self):
        md = "See [bug](https://tracker.com/fixme/123) report."
        result = strip_placeholder_links(md)
        assert result == "See bug report."

    def test_placeholder_token_case_insensitive(self):
        md = "Read [ref](https://site.com/Placeholder/doc)."
        result = strip_placeholder_links(md)
        assert result == "Read ref."

    def test_empty_content(self):
        assert strip_placeholder_links("") == ""

    def test_no_links(self):
        md = "Just plain text with no links."
        assert strip_placeholder_links(md) == md

    def test_anchor_link_preserved(self):
        md = "See [section](#overview) below."
        assert strip_placeholder_links(md) == md


class TestStripPlaceholderLinksZoneSafety:
    """SR-01: Tests proving apply_to_prose_zones protects fences + frontmatter."""

    def test_code_fence_preserved_via_zone_wrapper(self):
        md = (
            "```python\n"
            'url = "https://example.com/api"\n'
            'link = "[click](https://example.com/foo)"\n'
            "```\n"
        )
        result = apply_to_prose_zones(strip_placeholder_links, md)
        assert result == md

    def test_outside_fence_stripped_inside_preserved_via_zone(self):
        md = (
            "Visit [docs](https://example.com/guide) for help.\n"
            "\n"
            "```yaml\n"
            "base_url: https://example.com/api\n"
            "```\n"
            "\n"
            "Also see [more](https://example.org/ref).\n"
        )
        result = apply_to_prose_zones(strip_placeholder_links, md)
        assert "Visit docs for help." in result
        assert "base_url: https://example.com/api" in result  # inside fence
        assert "[more]" not in result

    def test_autolink_inside_fence_preserved_via_zone(self):
        md = (
            "```\n"
            "See <https://example.com/api>\n"
            "```\n"
        )
        result = apply_to_prose_zones(strip_placeholder_links, md)
        assert result == md

    def test_frontmatter_canonical_not_stripped(self):
        """SR-01 acceptance: frontmatter YAML with placeholder URL survives."""
        md = (
            "---\n"
            "title: Getting Started\n"
            "canonical: https://example.com/getting-started\n"
            "---\n"
            "\n"
            "Visit [docs](https://example.com/guide) for help.\n"
        )
        result = apply_to_prose_zones(strip_placeholder_links, md)
        # Frontmatter preserved
        assert "canonical: https://example.com/getting-started" in result
        # Prose link stripped
        assert "Visit docs for help." in result

    def test_frontmatter_with_example_url_fully_protected(self):
        """Both canonical and base_url in frontmatter must survive."""
        md = (
            "---\n"
            "title: Test\n"
            "canonical: https://example.org/page\n"
            "base_url: http://localhost:3000/api\n"
            "---\n"
            "\n"
            "Hello world.\n"
        )
        result = apply_to_prose_zones(strip_placeholder_links, md)
        assert "canonical: https://example.org/page" in result
        assert "base_url: http://localhost:3000/api" in result


class TestFixDoubledPathSegmentsZoneSafety:
    """SR-01: Zone safety for fix_doubled_path_segments."""

    def test_code_fence_preserved_via_zone_wrapper(self):
        md = (
            "```bash\n"
            "curl https://api.com/python/python/endpoint\n"
            "```\n"
        )
        result = apply_to_prose_zones(fix_doubled_path_segments, md)
        assert result == md

    def test_outside_fence_fixed_inside_preserved_via_zone(self):
        md = (
            "See [api](https://site.com/python/python/ref/).\n"
            "\n"
            "```\n"
            'path = "/python/python/lib"\n'
            "```\n"
        )
        result = apply_to_prose_zones(fix_doubled_path_segments, md)
        assert "See [api](https://site.com/python/ref/)." in result
        assert '"/python/python/lib"' in result

    def test_frontmatter_url_not_modified(self):
        md = (
            "---\n"
            "title: Guide\n"
            "permalink: /python/python/overview/\n"
            "---\n"
            "\n"
            "See [guide](/python/python/getting-started/).\n"
        )
        result = apply_to_prose_zones(fix_doubled_path_segments, md)
        # Frontmatter preserved
        assert "permalink: /python/python/overview/" in result
        # Prose link fixed
        assert "See [guide](/python/getting-started/)." in result


# ── D2: fix_doubled_path_segments (unit / raw function) ──────────────────────


class TestFixDoubledPathSegments:
    """Tests for fix_doubled_path_segments()."""

    def test_doubled_segment_deduplicated(self):
        md = "See [docs](https://docs.aspose.org/3d/python/python/overview/)."
        result = fix_doubled_path_segments(md)
        assert result == "See [docs](https://docs.aspose.org/3d/python/overview/)."

    def test_multiple_doubled_segments(self):
        md = "Visit [page](https://site.com/docs/docs/api/api/ref/)."
        result = fix_doubled_path_segments(md)
        assert "/docs/docs/" not in result
        assert "/api/api/" not in result

    def test_no_doubled_segment_unchanged(self):
        md = "See [docs](https://docs.aspose.org/3d/python/overview/)."
        result = fix_doubled_path_segments(md)
        assert result == md

    def test_different_segments_not_collapsed(self):
        md = "See [x](https://site.com/docs/api/ref/)."
        result = fix_doubled_path_segments(md)
        assert result == md

    def test_empty_content(self):
        assert fix_doubled_path_segments("") == ""

    def test_no_links(self):
        md = "Just plain text."
        assert fix_doubled_path_segments(md) == md

    def test_relative_link_deduplicated(self):
        md = "See [guide](/python/python/getting-started/)."
        result = fix_doubled_path_segments(md)
        assert result == "See [guide](/python/getting-started/)."

    def test_triple_segment_reduced(self):
        """Three consecutive identical segments: /a/a/a/ reduced."""
        md = "See [x](https://site.com/a/a/a/)."
        result = fix_doubled_path_segments(md)
        assert "/a/a/a/" not in result


# ── SR-03: False-positive prevention tests ────────────────────────────────────


class TestPlaceholderFalsePositivePrevention:
    """SR-03: Paths containing domain-like substrings must NOT be stripped."""

    def test_relative_path_containing_localhost_not_stripped(self):
        md = "See [guide](/docs/localhost-migration-guide/) for details."
        result = strip_placeholder_links(md)
        assert result == md

    def test_relative_path_containing_example_not_stripped(self):
        md = "See [ref](/docs/example-usage/) for help."
        result = strip_placeholder_links(md)
        assert result == md

    def test_relative_path_127_not_stripped(self):
        md = "See [fix](/docs/fix-127.0.0.1-binding/) here."
        result = strip_placeholder_links(md)
        assert result == md

    def test_autolink_no_double_space(self):
        """SR-03: Autolink replaced with plain text, no double space."""
        md = "See <https://example.com/api> for details."
        result = strip_placeholder_links(md)
        assert "  " not in result
        assert "https://example.com/api" in result

    def test_autolink_placeholder_keeps_url_text(self):
        """SR-03: Autolink becomes plain URL text, not empty."""
        md = "Use <http://localhost:3000/endpoint> here."
        result = strip_placeholder_links(md)
        assert "http://localhost:3000/endpoint" in result
        assert "<http://localhost" not in result


# ── SR-02: Reference-style and image link tests ──────────────────────────────


class TestReferenceStyleLinks:
    """SR-02: Reference-style links with placeholder URLs."""

    def test_reference_style_placeholder_stripped(self):
        md = (
            "See [click here][1] for details.\n"
            "\n"
            "[1]: https://example.com/guide\n"
        )
        result = strip_placeholder_links(md)
        assert "click here" in result
        assert "[1]" not in result
        assert "example.com" not in result

    def test_reference_style_real_link_preserved(self):
        md = (
            "See [docs][api] for reference.\n"
            "\n"
            "[api]: https://docs.aspose.org/3d/python/api/\n"
        )
        result = strip_placeholder_links(md)
        assert "[docs][api]" in result
        assert "[api]: https://docs.aspose.org" in result

    def test_reference_style_mixed(self):
        """Real and placeholder ref definitions in same doc."""
        md = (
            "See [real][a] and [fake][b].\n"
            "\n"
            "[a]: https://docs.aspose.org/page\n"
            "[b]: https://example.com/page\n"
        )
        result = strip_placeholder_links(md)
        assert "[real][a]" in result
        assert "[a]: https://docs.aspose.org/page" in result
        assert "fake" in result  # text preserved
        assert "[b]" not in result  # ref stripped
        assert "example.com" not in result

    def test_reference_style_inside_fence_not_matched(self):
        """Via apply_to_prose_zones, ref defs in fences survive."""
        md = (
            "```\n"
            "[1]: https://example.com/api\n"
            "```\n"
        )
        result = apply_to_prose_zones(strip_placeholder_links, md)
        assert result == md


class TestImageLinks:
    """SR-02: Image links with placeholder URLs."""

    def test_image_link_placeholder_stripped(self):
        md = "Logo: ![company logo](https://example.com/logo.png) here."
        result = strip_placeholder_links(md)
        assert result == "Logo: company logo here."

    def test_image_link_real_preserved(self):
        md = "![diagram](https://docs.aspose.org/img/arch.png)"
        result = strip_placeholder_links(md)
        assert result == md

    def test_image_link_localhost_stripped(self):
        md = "Preview: ![preview](http://localhost:3000/preview.jpg)."
        result = strip_placeholder_links(md)
        assert result == "Preview: preview."

    def test_image_link_inside_fence_preserved(self):
        md = (
            "```markdown\n"
            "![alt](https://example.com/img.png)\n"
            "```\n"
        )
        result = apply_to_prose_zones(strip_placeholder_links, md)
        assert result == md


# ── SR-04: Logging test ──────────────────────────────────────────────────────


class TestPlaceholderLinkLogging:
    """SR-04: Debug logging emitted when placeholder links are stripped."""

    def test_debug_log_on_strip(self, capsys):
        strip_placeholder_links("See [docs](https://example.com/api).")
        captured = capsys.readouterr()
        assert "Stripped placeholder link" in captured.out


# ── SR-05: Pipeline integration tests ────────────────────────────────────────


class TestPlaceholderLinkPipelineIntegration:
    """SR-05: Verify run_pipeline() invokes placeholder + dedup sanitizers."""

    def test_placeholder_link_stripped_by_pipeline(self):
        from launch.workers._shared.content_sanitizer import run_pipeline, SanitizerContext
        ctx = SanitizerContext()
        md = (
            "---\n"
            "title: Test\n"
            "---\n"
            "\n"
            "## Overview\n"
            "\n"
            "See [docs](https://example.com/guide) for details.\n"
        )
        result = run_pipeline(md, ctx)
        assert "example.com" not in result
        assert "docs" in result  # link text preserved

    def test_doubled_segment_fixed_by_pipeline(self):
        from launch.workers._shared.content_sanitizer import run_pipeline, SanitizerContext
        ctx = SanitizerContext()
        md = (
            "---\n"
            "title: Test\n"
            "---\n"
            "\n"
            "## Overview\n"
            "\n"
            "See [api](https://docs.aspose.org/3d/python/python/ref/).\n"
        )
        result = run_pipeline(md, ctx)
        assert "/python/python/" not in result

    def test_placeholder_stripped_before_absolutize(self):
        """Ordering proof: placeholder stripped, real relative link absolutized."""
        from launch.workers._shared.content_sanitizer import run_pipeline, SanitizerContext
        ctx = SanitizerContext(
            page={"section": "docs", "slug": "test"},
            product_facts={"product_family": "3d"},
        )
        md = (
            "---\n"
            "title: Test\n"
            "---\n"
            "\n"
            "## Overview\n"
            "\n"
            "See [fake](https://example.com/api) and [real](/docs/getting-started/).\n"
        )
        result = run_pipeline(md, ctx)
        # Placeholder gone
        assert "example.com" not in result
        # Real link absolutized (has https:// prefix from absolutize_links)
        assert "https://" in result or "/docs/getting-started/" in result
