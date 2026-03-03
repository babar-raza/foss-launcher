"""Tests for TC-3681: Verify strip_heading_trailing_punct and canonicalize_product_names
are wired into run_pipeline() and that the G5 space-after-dot fix works correctly.
"""

from __future__ import annotations

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from launch.workers._shared.content_sanitizer import (
    SanitizerContext,
    canonicalize_product_names,
    run_pipeline,
    strip_heading_trailing_punct,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_ctx(**overrides) -> SanitizerContext:
    """Build a minimal SanitizerContext for testing."""
    defaults = dict(
        page={"slug": "test-page", "section": "docs", "page_role": "guide"},
        product_facts={"product_name": "Aspose.Cells FOSS for Python"},
        run_config={},
        section="docs",
        slug="test-page",
        page_slug="test-page",
        repo_url="https://github.com/aspose/cells",
        product_name="Aspose.Cells FOSS for Python",
        family="cells",
        platform="python",
        page_url="/cells/python/test-page/",
        snippet_catalog=None,
        llm_client=None,
    )
    defaults.update(overrides)
    ctx = MagicMock(spec=SanitizerContext)
    for k, v in defaults.items():
        setattr(ctx, k, v)
    return ctx


# ── Pipeline Wiring Tests ────────────────────────────────────────────────────

class TestPipelineWiring:
    """Verify that strip_heading_trailing_punct and canonicalize_product_names
    are actually called within run_pipeline()."""

    def test_strip_heading_trailing_punct_is_called(self):
        """run_pipeline() should invoke strip_heading_trailing_punct."""
        sentinel_input = "## Unique Sentinel Heading."
        sentinel_output = "## Unique Sentinel Heading"
        with patch(
            "launch.workers._shared.content_sanitizer.strip_heading_trailing_punct",
            wraps=strip_heading_trailing_punct,
        ) as mock_fn:
            content = textwrap.dedent(f"""\
                ---
                title: "Test"
                ---

                {sentinel_input}

                This is a paragraph with enough content to pass quality floor checks.
                It contains multiple sentences about Aspose.Cells FOSS for Python.
                The library provides spreadsheet processing capabilities for developers.
                You can create, read, and modify Excel files programmatically.
                This paragraph ensures the content meets minimum word count requirements.
            """)
            ctx = _make_ctx()
            run_pipeline(content, ctx)
            mock_fn.assert_called_once()

    def test_canonicalize_product_names_is_called(self):
        """run_pipeline() should invoke canonicalize_product_names."""
        with patch(
            "launch.workers._shared.content_sanitizer.canonicalize_product_names",
            wraps=canonicalize_product_names,
        ) as mock_fn:
            content = textwrap.dedent("""\
                ---
                title: "Test"
                ---

                ## Overview

                Use Aspire.Cells to process spreadsheets in Python applications.
                The library provides spreadsheet processing capabilities for developers.
                You can create, read, and modify Excel files programmatically.
                This paragraph ensures the content meets minimum word count requirements.
            """)
            ctx = _make_ctx()
            run_pipeline(content, ctx)
            mock_fn.assert_called_once()


# ── Space-After-Dot Tests ────────────────────────────────────────────────────

class TestSpaceAfterDot:
    """Test the _G5_SPACE_AFTER_DOT_RE pattern in canonicalize_product_names."""

    def test_single_space(self):
        result = canonicalize_product_names("Use Aspose. Cells for Python.")
        assert result == "Use Aspose.Cells for Python."

    def test_double_space(self):
        result = canonicalize_product_names("Use Aspose.  Note for Python.")
        assert result == "Use Aspose.Note for Python."

    def test_all_products(self):
        """All known product names should be handled."""
        products = ["Cells", "Note", "Words", "Pdf", "Slides", "Email", "Imaging", "3D"]
        for product in products:
            result = canonicalize_product_names(f"Use Aspose. {product} library.")
            assert f"Aspose.{product}" in result, f"Failed for {product}"
            assert f"Aspose. {product}" not in result, f"Not fixed for {product}"

    def test_correct_name_unchanged(self):
        """Already-correct names should not be modified."""
        content = "Use Aspose.Cells for Python."
        result = canonicalize_product_names(content)
        assert result == content

    def test_code_fence_protection(self):
        """Space-after-dot inside code fences should NOT be fixed."""
        content = textwrap.dedent("""\
            Some prose.

            ```python
            # Aspose. Cells is used here
            from aspose. cells import Workbook
            ```

            More prose with Aspose. Cells issue.""")
        result = canonicalize_product_names(content)
        # Inside fence: unchanged
        assert "# Aspose. Cells is used here" in result
        # Outside fence: fixed
        assert "More prose with Aspose.Cells issue." in result


# ── Frontmatter Tests ────────────────────────────────────────────────────────

class TestFrontmatterSpaceFix:
    """Test that space-after-dot fix applies to frontmatter title/description."""

    def test_title_field_fixed(self):
        content = textwrap.dedent("""\
            ---
            title: "Aspose. Cells for Python"
            permalink: /cells/python/
            ---

            Content here.""")
        result = canonicalize_product_names(content)
        assert 'title: "Aspose.Cells for Python"' in result

    def test_description_field_fixed(self):
        content = textwrap.dedent("""\
            ---
            title: "Overview"
            description: "Learn about Aspose. Note for Python"
            ---

            Content here.""")
        result = canonicalize_product_names(content)
        assert 'description: "Learn about Aspose.Note for Python"' in result

    def test_other_frontmatter_fields_unchanged(self):
        """Non-title/description fields should not be modified."""
        content = textwrap.dedent("""\
            ---
            title: "Overview"
            permalink: /aspose. cells/python/
            weight: 10
            ---

            Content here.""")
        result = canonicalize_product_names(content)
        # permalink is not title/description, so should be unchanged
        assert "permalink: /aspose. cells/python/" in result

    def test_frontmatter_misspelling_not_fixed(self):
        """Misspelling fix should NOT apply in frontmatter (only space-after-dot)."""
        content = textwrap.dedent("""\
            ---
            title: "Aspire.Cells for Python"
            ---

            Content here.""")
        result = canonicalize_product_names(content)
        # Misspelling in frontmatter should remain (only space-after-dot is applied)
        assert 'title: "Aspire.Cells for Python"' in result

    def test_yaml_structure_preserved(self):
        """YAML structure should remain valid after fix."""
        content = textwrap.dedent("""\
            ---
            title: "Aspose. Cells FOSS for Python"
            description: "Work with Aspose. Cells"
            permalink: /cells/python/overview/
            weight: 10
            ---

            ## Overview""")
        result = canonicalize_product_names(content)
        lines = result.split("\n")
        # First and closing --- must still be present
        assert lines[0].strip() == "---"
        # Find closing ---
        closing_idx = None
        for idx, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                closing_idx = idx
                break
        assert closing_idx is not None, "Closing --- not found"
        # Title and description fixed
        assert 'title: "Aspose.Cells FOSS for Python"' in result
        assert 'description: "Work with Aspose.Cells"' in result


# ── Idempotency Tests ────────────────────────────────────────────────────────

class TestIdempotency:
    """Verify f(f(x)) == f(x) for both sanitizers."""

    def test_strip_heading_trailing_punct_idempotent(self):
        content = "## Getting Started.\n\nSome content.\n\n## See Also:\n"
        once = strip_heading_trailing_punct(content)
        twice = strip_heading_trailing_punct(once)
        assert once == twice

    def test_canonicalize_product_names_idempotent(self):
        content = textwrap.dedent("""\
            ---
            title: "Aspose. Cells for Python"
            ---

            Use Aspire. Cells for Python for Python with Aspose. Note.""")
        once = canonicalize_product_names(content)
        twice = canonicalize_product_names(once)
        assert once == twice

    def test_canonicalize_space_dot_idempotent(self):
        """Space-after-dot fix: applying twice = same result."""
        content = "Aspose. Cells and Aspose.  Note"
        once = canonicalize_product_names(content)
        twice = canonicalize_product_names(once)
        assert once == twice
        assert once == "Aspose.Cells and Aspose.Note"
