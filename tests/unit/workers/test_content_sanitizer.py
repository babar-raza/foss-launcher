"""Tests for the shared Content Sanitizer module.

Validates:
- SanitizerContext correctly exposes page/product_facts metadata
- run_pipeline() applies all sanitizer phases in order
- Individual sanitizer functions work correctly when called standalone
- Pipeline is equivalent to the old sequential call chain in worker.py
"""

import pytest

from launch.workers._shared.content_sanitizer import (
    SanitizerContext,
    run_pipeline,
    # Phase 1: Early/Structural
    strip_source_annotations,
    strip_orphan_claim_markers,
    fix_prose_in_code_blocks,
    fence_bare_commands,
    fix_license_page,
    ensure_related_links,
    fix_self_referential_links,
    ensure_h2_intros,
    inject_machine_readable,
    # Phase 2: Fence normalization
    fix_excess_backtick_fences,
    fix_collapsed_frontmatter,
    fix_inline_html_claim_markers,
    close_unclosed_fences,
    fix_nested_fences,
    fix_code_fences,
    merge_adjacent_code_blocks,
    fix_unicode_in_code_blocks,
    validate_code_blocks,
    fix_single_backtick_code_blocks,
    # Phase 3: Content-level
    strip_product_name_prefix,
    fix_trailing_whitespace_in_links,
    remove_empty_sections,
    # Phase 4: Strip patterns
    fix_faq_doubled_prefix,
    fix_faq_doubled_answer_prefix,
    strip_boilerplate_sentences,
    strip_visible_claim_markers,
    absolutize_links,
    strip_double_periods,
    strip_emojis,
    strip_ci_badges,
    strip_illustrative_comments,
    fix_truncated_sentences,
    normalize_module_names,
    # Phase 5: Quality
    enforce_quality_floor,
    # Constants
    MIN_BODY_WORDS,
)


class TestSanitizerContext:
    """Tests for the SanitizerContext helper object."""

    def test_default_context(self):
        ctx = SanitizerContext()
        assert ctx.page == {}
        assert ctx.product_facts == {}
        assert ctx.product_name == ""
        assert ctx.page_slug == ""
        assert ctx.page_url == ""
        assert ctx.section == "default"
        assert ctx.repo_url == ""
        assert ctx.family == ""

    def test_context_with_data(self):
        ctx = SanitizerContext(
            page={"slug": "overview", "url_path": "/3d/python/overview/", "section": "docs"},
            product_facts={"product_name": "Aspose.3D", "repo_url": "https://github.com/test", "product_family": "3d"},
        )
        assert ctx.product_name == "Aspose.3D"
        assert ctx.page_slug == "overview"
        assert ctx.page_url == "/3d/python/overview/"
        assert ctx.section == "docs"
        assert ctx.repo_url == "https://github.com/test"
        assert ctx.family == "3d"

    def test_context_llm_client(self):
        ctx = SanitizerContext(llm_client="mock_client")
        assert ctx.llm_client == "mock_client"


class TestRunPipeline:
    """Tests for the run_pipeline() orchestrator."""

    def test_pipeline_returns_string(self):
        ctx = SanitizerContext()
        result = run_pipeline("## Hello\n\nSome content here.", ctx)
        assert isinstance(result, str)

    def test_pipeline_strips_source_annotations(self):
        content = "---\ntitle: Test\n---\n<!-- source: readme.md -->\nActual content."
        ctx = SanitizerContext()
        result = run_pipeline(content, ctx)
        assert "<!-- source:" not in result
        assert "Actual content." in result

    def test_pipeline_strips_emojis(self):
        content = "---\ntitle: Test\n---\n## Features\n\nGreat library! \U0001F680 Fast processing."
        ctx = SanitizerContext()
        result = run_pipeline(content, ctx)
        assert "\U0001F680" not in result

    def test_pipeline_strips_double_periods(self):
        content = "---\ntitle: Test\n---\n\nThis is great.. Really."
        ctx = SanitizerContext()
        result = run_pipeline(content, ctx)
        assert ".." not in result

    def test_pipeline_fixes_collapsed_frontmatter(self):
        content = '---\ntitle: "Test" description: "A test page"\n---\nBody'
        ctx = SanitizerContext()
        result = run_pipeline(content, ctx)
        # After fix, title and description should be on separate lines
        assert 'title: "Test"' in result
        assert 'description: "A test page"' in result

    def test_pipeline_strips_visible_claim_markers(self):
        content = "---\ntitle: Test\n---\n\nSome text [claim: abc123def] more text."
        ctx = SanitizerContext()
        result = run_pipeline(content, ctx)
        assert "[claim: abc123def]" not in result
        assert "Some text" in result

    def test_pipeline_strips_ci_badges(self):
        content = "---\ntitle: Test\n---\n\n[![CI](https://ci.example.com/badge)](https://ci.example.com)\n\nContent."
        ctx = SanitizerContext()
        result = run_pipeline(content, ctx)
        assert "[![CI]" not in result

    def test_pipeline_preserves_frontmatter(self):
        content = "---\ntitle: My Title\nlayout: docs\n---\n\n## Introduction\n\nSome text."
        ctx = SanitizerContext()
        result = run_pipeline(content, ctx)
        assert 'title: My Title' in result
        assert 'layout: docs' in result

    def test_pipeline_with_frontmatter_injection(self):
        content = "## No frontmatter\n\nSome content."
        ctx = SanitizerContext(page={"slug": "test", "section": "docs"})
        injected = False

        def mock_injector(c):
            nonlocal injected
            injected = True
            return "---\ntitle: Test\n---\n" + c

        result = run_pipeline(content, ctx, include_frontmatter_injection=True, frontmatter_injector=mock_injector)
        assert injected
        assert "title: Test" in result


class TestStripSourceAnnotations:
    """Standalone tests for strip_source_annotations."""

    def test_strips_full_line_annotation(self):
        content = "Before\n<!-- source: readme.md -->\nAfter"
        assert "<!-- source:" not in strip_source_annotations(content)

    def test_strips_inline_annotation(self):
        content = "Text <!-- source: code.py --> more text"
        result = strip_source_annotations(content)
        assert "<!-- source:" not in result
        assert "Text" in result
        assert "more text" in result

    def test_preserves_code_block_content(self):
        content = "```python\n<!-- source: test.py -->\n```"
        result = strip_source_annotations(content)
        assert "<!-- source: test.py -->" in result


class TestFixCodeFences:
    """Standalone tests for fix_code_fences."""

    def test_normalizes_pseudocode(self):
        content = "```pseudocode\nif True:\n    pass\n```"
        result = fix_code_fences(content)
        assert "```python" in result
        assert "```pseudocode" not in result

    def test_normalizes_language_tags(self):
        content = "```Python\nprint('hello')\n```"
        result = fix_code_fences(content)
        assert "```python" in result

    def test_removes_empty_code_blocks(self):
        content = "Before\n```python\n```\nAfter"
        result = fix_code_fences(content)
        assert "```python" not in result

    def test_closes_unclosed_fence_with_lang(self):
        content = "```python\nprint('hello')"
        result = fix_code_fences(content)
        assert result.rstrip().endswith("```")


class TestStripVisibleClaimMarkers:
    """Standalone tests for strip_visible_claim_markers."""

    def test_strips_bracket_markers(self):
        content = "Feature works well [claim: abc123de] and is fast."
        result = strip_visible_claim_markers(content)
        assert "[claim:" not in result

    def test_strips_fullwidth_markers(self):
        content = "Feature works\u3010abc123de\u3011and is fast."
        result = strip_visible_claim_markers(content)
        assert "\u3010" not in result

    def test_preserves_html_comment_markers(self):
        content = "Feature works well. <!-- claim: abc123de -->"
        result = strip_visible_claim_markers(content)
        assert "<!-- claim: abc123de -->" in result


class TestEnsureRelatedLinks:
    """Standalone tests for ensure_related_links."""

    def test_skips_index_pages(self):
        content = "Some content without links"
        result = ensure_related_links(content, page_slug="index", repo_url="", product_name="Test", family="3d")
        assert "## See Also" not in result

    def test_adds_see_also_when_few_links(self):
        content = "Some content without links"
        result = ensure_related_links(
            content, page_slug="overview", repo_url="https://github.com/test",
            product_name="Test", family="3d",
        )
        assert "## See Also" in result
        assert "Source Code Repository" in result

    def test_skips_when_enough_links(self):
        content = "[Link1](url1) and [Link2](url2)"
        result = ensure_related_links(content, page_slug="overview", repo_url="", product_name="Test")
        assert "## See Also" not in result


class TestFixCollapsedFrontmatter:
    """Standalone tests for fix_collapsed_frontmatter."""

    def test_splits_collapsed_keys(self):
        content = '---\ntitle: "A" description: "B"\n---\nBody'
        result = fix_collapsed_frontmatter(content)
        lines = result.split('\n')
        assert any('title:' in l and 'description:' not in l for l in lines)

    def test_preserves_valid_frontmatter(self):
        content = '---\ntitle: "A"\ndescription: "B"\n---\nBody'
        result = fix_collapsed_frontmatter(content)
        assert result == content

    def test_handles_quoted_colons(self):
        content = '---\ntitle: "Blog page: announcement"\n---\nBody'
        result = fix_collapsed_frontmatter(content)
        assert result == content


class TestStripEmojis:
    """Standalone tests for strip_emojis."""

    def test_strips_emojis_from_body(self):
        content = "---\ntitle: Test\n---\n\nHello \U0001F600 World"
        result = strip_emojis(content)
        assert "\U0001F600" not in result
        assert "Hello" in result

    def test_preserves_frontmatter(self):
        content = "---\ntitle: Test \U0001F600\n---\nBody"
        result = strip_emojis(content)
        # Frontmatter is preserved untouched
        assert "\U0001F600" in result.split("---")[1]


class TestMinBodyWords:
    """Verify MIN_BODY_WORDS constants are accessible."""

    def test_blog_minimum(self):
        assert MIN_BODY_WORDS["blog"] == 300

    def test_docs_minimum(self):
        assert MIN_BODY_WORDS["docs"] == 200

    def test_default_minimum(self):
        assert MIN_BODY_WORDS["default"] == 150


class TestFenceBareCmds:
    """Standalone tests for fence_bare_commands."""

    def test_wraps_pip_install(self):
        content = "Install it:\n\npip install aspose-3d\n\nThen use it."
        result = fence_bare_commands(content)
        assert "```bash" in result
        assert "pip install aspose-3d" in result

    def test_ignores_already_fenced(self):
        content = "```bash\npip install aspose-3d\n```"
        result = fence_bare_commands(content)
        # Should not double-wrap
        assert result.count("```bash") == 1


class TestNormalizeModuleNames:
    """Standalone tests for normalize_module_names."""

    def test_normalizes_3d_module(self):
        content = "```python\nimport aspose_3d\n```"
        facts = {"product_family": "3d", "product_name": "Aspose.3D"}
        result = normalize_module_names(content, facts)
        assert "aspose.threed" in result

    def test_no_change_for_unknown_family(self):
        content = "```python\nimport something\n```"
        facts = {"product_family": "unknown", "product_name": "Unknown"}
        result = normalize_module_names(content, facts)
        assert result == content


class TestFixFaqDoubledPrefix:
    """TC-1902: Standalone tests for fix_faq_doubled_prefix."""

    def test_fix_faq_doubled_prefix_strips_double(self):
        content = "### Q: Q: How do I install?"
        result = fix_faq_doubled_prefix(content)
        assert result == "### Q: How do I install?"

    def test_fix_faq_doubled_prefix_preserves_single(self):
        content = "### Q: How do I install?"
        result = fix_faq_doubled_prefix(content)
        assert result == "### Q: How do I install?"


class TestFixExcessBacktickFences:
    """TC-1903: Standalone tests for fix_excess_backtick_fences."""

    def test_fix_excess_backtick_fences_normalizes_five(self):
        content = '`````python\nprint("hello")\n`````'
        result = fix_excess_backtick_fences(content)
        assert result == '```python\nprint("hello")\n```'

    def test_fix_excess_backtick_fences_preserves_three(self):
        content = '```python\nprint("hello")\n```'
        result = fix_excess_backtick_fences(content)
        assert result == content


class TestFixSingleBacktickCodeBlockLanguage:
    """TC-2003: Language on first line of single-backtick code block should be extracted to fence."""

    def test_fix_single_backtick_code_block_with_language(self):
        """TC-2003: Language on first line should be extracted to fence."""
        content = "Some text\n`\npython\nimport aspose.threed as a3d\nscene = a3d.Scene()\n`\nMore text"
        result = fix_single_backtick_code_blocks(content)
        assert "```python" in result, f"Expected ```python fence but got: {result}"
        assert "\npython\n" not in result, "Language should not be inside the code block"

    def test_fix_single_backtick_code_block_with_bash_language(self):
        """TC-2003: Bash language should be extracted to fence."""
        content = "`\nbash\npip install aspose-3d\n`"
        result = fix_single_backtick_code_blocks(content)
        assert "```bash" in result

    def test_fix_single_backtick_code_block_no_language(self):
        """TC-2003: No language on first line -> bare ``` fence."""
        content = "`\nimport aspose.threed as a3d\nscene = a3d.Scene()\n`"
        result = fix_single_backtick_code_blocks(content)
        assert "```\n" in result
        assert "```python" not in result

    def test_fix_single_backtick_code_block_short_unchanged(self):
        """TC-2003: Short inline code should not be converted."""
        content = "Use `import os` in your code"
        result = fix_single_backtick_code_blocks(content)
        assert result == content


class TestFixFaqDoubledAnswerPrefix:
    """TC-2004: Doubled A: prefix in FAQ answers should be reduced."""

    def test_fix_faq_doubled_answer_prefix(self):
        """TC-2004: **A:** A: should be reduced to **A:**"""
        content = "**A:** A: The answer is here."
        result = fix_faq_doubled_answer_prefix(content)
        assert result == "**A:** The answer is here."

    def test_fix_faq_answer_prefix_no_change(self):
        """TC-2004: Correct **A:** prefix should be unchanged."""
        content = "**A:** The answer is here."
        result = fix_faq_doubled_answer_prefix(content)
        assert result == content


# ── Helper for R17-001 tests ──────────────────────────────────────────────────

def _extract_code_blocks(content: str) -> str:
    """Extract all content within code fences for testing."""
    blocks = []
    in_fence = False
    for line in content.split('\n'):
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            blocks.append(line)
    return '\n'.join(blocks)


# ── TC-2200 R17-001: fix_prose_in_code_blocks detects H1-H6 ──────────────────

class TestFixProseInCodeBlocksAllHeadings:
    """TC-2200 R17-001: fix_prose_in_code_blocks detects H1-H6, not just H2."""

    def test_h1_inside_fence_is_rescued(self):
        content = "```python\n# Title\ncode_here()\n```"
        result = fix_prose_in_code_blocks(content)
        assert "# Title" not in _extract_code_blocks(result)

    def test_h3_inside_fence_is_rescued(self):
        content = "```\n### Subsection\nsome code\n```"
        result = fix_prose_in_code_blocks(content)
        assert "### Subsection" not in _extract_code_blocks(result)

    def test_h4_inside_fence_is_rescued(self):
        content = "```\n#### Deep heading\nmore code\n```"
        result = fix_prose_in_code_blocks(content)
        assert "#### Deep heading" not in _extract_code_blocks(result)

    def test_h6_inside_fence_is_rescued(self):
        content = "```\n###### Very deep\ncode\n```"
        result = fix_prose_in_code_blocks(content)
        assert "###### Very deep" not in _extract_code_blocks(result)

    def test_python_comment_not_rescued(self):
        """Single # followed by non-space is a Python comment, not a heading."""
        content = "```python\n#comment\ncode()\n```"
        result = fix_prose_in_code_blocks(content)
        # Should stay inside the code block — it's a code comment, not a heading
        assert "#comment" in result


# ── TC-2200 R17-002: Strip backtick-wrapped HTML claim comments ───────────────

class TestStripBacktickWrappedClaimComments:
    """TC-2200 R17-002: Strip backtick-wrapped HTML claim comments."""

    def test_backtick_html_claim_stripped(self):
        content = "Some text `<!-- claim: abc123 -->` more text"
        result = strip_visible_claim_markers(content)
        assert "`<!-- claim:" not in result
        assert "Some text" in result
        assert "more text" in result

    def test_backtick_html_claim_no_space(self):
        content = "Text`<!-- claim:def456 -->`end"
        result = strip_visible_claim_markers(content)
        assert "claim" not in result

    def test_bare_html_comment_preserved(self):
        """Bare HTML comments (no backticks) preserved for Gate 14."""
        content = "Text <!-- claim: abc123 --> end"
        result = strip_visible_claim_markers(content)
        assert "<!-- claim: abc123 -->" in result


# ── TC-2200 R17-005: Clean /./ and /index/ from URLs ─────────────────────────

class TestCleanBadUrlPatterns:
    """TC-2200 R17-005: Clean /./ and /index/ from URLs."""

    def test_dot_slash_cleaned_in_absolute_url(self):
        content = "[License](https://docs.aspose.org/3d/python/./license/)"
        result = absolutize_links(content, "docs", "3d", "python")
        assert "/./" not in result

    def test_index_cleaned_from_url(self):
        content = "[Home](https://docs.aspose.org/3d/python/index/)"
        result = absolutize_links(content, "docs", "3d", "python")
        assert "/index/" not in result
        assert "https://docs.aspose.org/3d/python/)" in result

    def test_build_absolute_no_dot_slash(self):
        """_build_absolute should not produce /./ paths."""
        content = "[Test](/./ )"
        result = absolutize_links(content, "docs", "3d", "python")
        assert "/./" not in result

    def test_already_clean_url_unchanged(self):
        content = "[Docs](https://docs.aspose.org/3d/python/overview/)"
        result = absolutize_links(content, "docs", "3d", "python")
        assert "https://docs.aspose.org/3d/python/overview/)" in result
