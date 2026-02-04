"""TC-964: Unit tests for W5 SectionWriter blog template token rendering.

Tests token generation in W4 IAPlanner and token application in W5 SectionWriter
to ensure blog template placeholders are filled correctly and deterministically.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

# Import functions to test
from src.launch.workers.w4_ia_planner.worker import generate_content_tokens
from src.launch.workers.w5_section_writer.worker import apply_token_mappings


class TestTokenGeneration:
    """Test W4 IAPlanner token generation for blog templates."""

    def test_generate_content_tokens_blog(self):
        """Test case 1: Token generation produces expected keys.

        Verify that generate_content_tokens() produces all required tokens
        for blog template frontmatter and body content.
        """
        page_spec = {
            "slug": "index",
            "section": "blog",
        }

        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="3d",
            platform="python",
            locale="en",
        )

        # Verify all required frontmatter tokens present
        assert "__TITLE__" in tokens
        assert "__SEO_TITLE__" in tokens
        assert "__DESCRIPTION__" in tokens
        assert "__SUMMARY__" in tokens
        assert "__AUTHOR__" in tokens
        assert "__DATE__" in tokens
        assert "__DRAFT__" in tokens
        assert "__TAG_1__" in tokens
        assert "__PLATFORM__" in tokens
        assert "__CATEGORY_1__" in tokens

        # Verify all required body tokens present
        assert "__BODY_INTRO__" in tokens
        assert "__BODY_OVERVIEW__" in tokens
        assert "__BODY_CODE_SAMPLES__" in tokens
        assert "__BODY_CONCLUSION__" in tokens
        assert "__BODY_PREREQUISITES__" in tokens
        assert "__BODY_STEPS__" in tokens
        assert "__BODY_KEY_TAKEAWAYS__" in tokens
        assert "__BODY_TROUBLESHOOTING__" in tokens
        assert "__BODY_NOTES__" in tokens
        assert "__BODY_SEE_ALSO__" in tokens

        # Verify token values are non-empty strings
        for token_name, token_value in tokens.items():
            assert isinstance(token_value, str), f"Token {token_name} should be string"
            assert len(token_value) > 0, f"Token {token_name} should not be empty"

        # Verify specific values for critical tokens
        assert "Aspose.3d for Python" in tokens["__TITLE__"]
        assert tokens["__AUTHOR__"] == "Aspose Documentation Team"
        assert tokens["__DRAFT__"] == "false"
        assert tokens["__TAG_1__"] == "3d"
        assert tokens["__PLATFORM__"] == "python"
        assert tokens["__CATEGORY_1__"] == "documentation"

    def test_token_generation_deterministic(self):
        """Test case 2: Token generation is deterministic.

        Verify that calling generate_content_tokens() twice with identical
        inputs produces identical outputs (required for VFV determinism).
        """
        page_spec = {
            "slug": "getting-started",
            "section": "blog",
        }

        # Generate tokens twice with same inputs
        tokens1 = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="note",
            platform="java",
            locale="en",
        )

        tokens2 = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="note",
            platform="java",
            locale="en",
        )

        # Verify exact match (determinism)
        assert tokens1 == tokens2, "Token generation must be deterministic"

        # Verify all token values match
        for token_name in tokens1.keys():
            assert tokens1[token_name] == tokens2[token_name], \
                f"Token {token_name} differs between runs"

    def test_token_generation_different_families(self):
        """Test token generation for different product families.

        Verify tokens are generated correctly for different families (3d, note).
        """
        page_spec = {"slug": "index", "section": "blog"}

        tokens_3d = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="3d",
            platform="python",
        )

        tokens_note = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="note",
            platform="python",
        )

        # Verify families are reflected in tokens
        assert "3d" in tokens_3d["__TITLE__"].lower()
        assert "note" in tokens_note["__TITLE__"].lower()
        assert tokens_3d["__TAG_1__"] == "3d"
        assert tokens_note["__TAG_1__"] == "note"


class TestTokenApplication:
    """Test W5 SectionWriter token application to templates."""

    def test_apply_token_mappings(self):
        """Test case 3: Token replacement works correctly.

        Verify that apply_token_mappings() replaces all tokens in template
        content with their mapped values.
        """
        template_content = """---
title: "__TITLE__"
date: "__DATE__"
author: "__AUTHOR__"
---
__BODY_INTRO__

## Overview
__BODY_OVERVIEW__
"""

        token_mappings = {
            "__TITLE__": "My Blog Post",
            "__DATE__": "2024-01-01",
            "__AUTHOR__": "Test Author",
            "__BODY_INTRO__": "This is the introduction.",
            "__BODY_OVERVIEW__": "This is the overview section.",
        }

        result = apply_token_mappings(template_content, token_mappings)

        # Verify all tokens replaced
        assert "__TITLE__" not in result
        assert "__DATE__" not in result
        assert "__AUTHOR__" not in result
        assert "__BODY_INTRO__" not in result
        assert "__BODY_OVERVIEW__" not in result

        # Verify correct values present
        assert "My Blog Post" in result
        assert "2024-01-01" in result
        assert "Test Author" in result
        assert "This is the introduction." in result
        assert "This is the overview section." in result

    def test_apply_token_mappings_no_unfilled_tokens(self):
        """Test that token application leaves no unfilled tokens.

        Verify that after applying token mappings, no placeholder tokens
        remain in the content (critical for W5 validation).
        """
        template_content = """---
title: "__TITLE__"
seoTitle: "__SEO_TITLE__"
description: "__DESCRIPTION__"
date: "__DATE__"
draft: __DRAFT__
---
__BODY_INTRO__
"""

        token_mappings = {
            "__TITLE__": "Test Title",
            "__SEO_TITLE__": "SEO Title",
            "__DESCRIPTION__": "Test Description",
            "__DATE__": "2024-01-01",
            "__DRAFT__": "false",
            "__BODY_INTRO__": "Introduction text",
        }

        result = apply_token_mappings(template_content, token_mappings)

        # Check for unfilled tokens using same pattern as W5
        import re
        pattern = r'__[A-Z_]+__'
        unfilled_tokens = re.findall(pattern, result)

        assert len(unfilled_tokens) == 0, \
            f"Found unfilled tokens after mapping: {unfilled_tokens}"

    def test_apply_token_mappings_partial(self):
        """Test token application with partial mappings.

        Verify behavior when only some tokens are mapped (some remain unfilled).
        """
        template_content = """---
title: "__TITLE__"
date: "__DATE__"
author: "__AUTHOR__"
---
__BODY__
"""

        # Only map some tokens
        token_mappings = {
            "__TITLE__": "Partial Mapping",
            "__DATE__": "2024-01-01",
        }

        result = apply_token_mappings(template_content, token_mappings)

        # Verify mapped tokens replaced
        assert "Partial Mapping" in result
        assert "2024-01-01" in result

        # Verify unmapped tokens remain (expected behavior)
        assert "__AUTHOR__" in result
        assert "__BODY__" in result


class TestIntegration:
    """Integration tests for W4→W5 token handoff."""

    def test_w4_w5_integration(self):
        """Test case 4: W4-W5 integration with token mappings.

        Verify that tokens generated by W4 can be used by W5 to fill
        a real blog template without unfilled tokens.
        """
        # Simulate W4 page spec generation
        page_spec = {
            "slug": "index",
            "section": "blog",
        }

        # W4: Generate tokens
        token_mappings = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="3d",
            platform="python",
        )

        # Simulate minimal blog template
        template_content = """---
title: "__TITLE__"
seoTitle: "__SEO_TITLE__"
description: "__DESCRIPTION__"
date: "__DATE__"
draft: __DRAFT__
author: "__AUTHOR__"
summary: "__SUMMARY__"
tags:
  - "__TAG_1__"
  - "__PLATFORM__"
categories:
  - "__CATEGORY_1__"
---
__BODY_INTRO__

## Overview

__BODY_OVERVIEW__

## Code examples

__BODY_CODE_SAMPLES__

## Conclusion

__BODY_CONCLUSION__
"""

        # W5: Apply tokens
        result = apply_token_mappings(template_content, token_mappings)

        # Verify no unfilled tokens remain
        import re
        pattern = r'__[A-Z_]+__'
        unfilled_tokens = re.findall(pattern, result)

        assert len(unfilled_tokens) == 0, \
            f"Integration test failed: unfilled tokens {unfilled_tokens}"

        # Verify frontmatter has valid values
        assert "Aspose.3d for Python" in result
        assert "Aspose Documentation Team" in result
        assert "2024-01-01" in result
        assert "draft: false" in result

    def test_determinism_end_to_end(self):
        """Test case 5: End-to-end determinism.

        Verify that the entire W4→W5 token generation and application
        process produces deterministic output (same inputs → same outputs).
        """
        page_spec = {"slug": "api-guide", "section": "blog"}

        # Run 1
        tokens1 = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="3d",
            platform="net",
        )
        template = "title: __TITLE__\ndate: __DATE__\n__BODY_INTRO__"
        result1 = apply_token_mappings(template, tokens1)

        # Run 2
        tokens2 = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="3d",
            platform="net",
        )
        result2 = apply_token_mappings(template, tokens2)

        # Verify exact match (determinism)
        assert result1 == result2, "End-to-end process must be deterministic"
