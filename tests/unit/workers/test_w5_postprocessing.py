"""TC-1404/TC-1502: Tests for W5 deterministic post-processing functions.

Tests cover the post-processing functions:
- TC-1404: _fix_inline_html_claim_markers, _close_unclosed_fences, _fix_collapsed_frontmatter, check_unfilled_tokens
- TC-1502: _strip_source_annotations, _strip_boilerplate_sentences, _fix_self_referential_links,
           _fix_prose_in_code_blocks, _strip_orphan_claim_markers, _fence_bare_commands
"""

import pytest

from launch.workers.w5_section_writer.worker import (
    _fix_inline_html_claim_markers,
    _close_unclosed_fences,
    _fix_code_fences,
    _fix_collapsed_frontmatter,
    check_unfilled_tokens,
    _strip_source_annotations,
    _strip_boilerplate_sentences,
    _strip_visible_claim_markers,
    _fix_self_referential_links,
    _fix_prose_in_code_blocks,
    _strip_orphan_claim_markers,
    _fence_bare_commands,
    _smart_truncate,
    _first_sentence_bullets,
    MAX_BULLET_LEN,
)


# ---------------------------------------------------------------------------
# _fix_inline_html_claim_markers
# ---------------------------------------------------------------------------

class TestFixInlineHtmlClaimMarkers:
    """Tests for _fix_inline_html_claim_markers."""

    def test_fix_inline_html_claim_markers_mid_sentence(self):
        """Verify inline HTML claim marker is moved to end of line."""
        content = "builds a unique vertex map .<!-- claim_id: ea12ad49-1234-5678-abcd-ef0123456789 -->."
        result = _fix_inline_html_claim_markers(content)
        # Marker should be at end, double period fixed
        assert "<!-- claim_id: ea12ad49-1234-5678-abcd-ef0123456789 -->" in result
        assert result.endswith("<!-- claim_id: ea12ad49-1234-5678-abcd-ef0123456789 -->")
        # Double period should be fixed
        assert ".." not in result

    def test_fix_inline_html_claim_markers_already_at_end(self):
        """Verify no change when marker is already at end of line."""
        content = "This is a complete sentence. <!-- claim_id: abcdef01-2345-6789-abcd-ef0123456789 -->"
        result = _fix_inline_html_claim_markers(content)
        # Should remain essentially the same (marker still at end)
        assert result.strip().endswith("<!-- claim_id: abcdef01-2345-6789-abcd-ef0123456789 -->")

    def test_fix_inline_html_claim_markers_double_period(self):
        """Verify double period '..' becomes single '.' after marker removal."""
        content = "Some text.<!-- claim_id: aa11bb22-3344-5566-7788-99aabbccddee -->. More text."
        result = _fix_inline_html_claim_markers(content)
        # The double period from "text." + "." should be collapsed
        assert ".." not in result
        assert "<!-- claim_id: aa11bb22-3344-5566-7788-99aabbccddee -->" in result

    def test_fix_inline_html_claim_markers_no_markers(self):
        """Verify content without HTML claim markers passes through unchanged."""
        content = "This is normal markdown content.\nWith multiple lines."
        result = _fix_inline_html_claim_markers(content)
        assert result == content

    def test_fix_inline_html_claim_markers_space_period(self):
        """Verify space-period ' .' is fixed to '.'."""
        content = "Some text <!-- claim_id: 1234abcd-5678-9012-3456-789012345678 --> . Rest."
        result = _fix_inline_html_claim_markers(content)
        # Space-period should be fixed
        assert " ." not in result.split("<!--")[0]

    def test_fix_inline_html_claim_markers_idempotent(self):
        """Verify running the function twice produces the same result."""
        content = "builds a unique vertex map .<!-- claim_id: ea12ad49-1234-5678-abcd-ef0123456789 -->."
        result1 = _fix_inline_html_claim_markers(content)
        result2 = _fix_inline_html_claim_markers(result1)
        assert result1 == result2

    def test_fix_inline_html_claim_markers_multiline(self):
        """Verify multi-line content is handled correctly."""
        content = (
            "Line one is fine.\n"
            "Line two has .<!-- claim_id: aaaa1111-2222-3333-4444-555566667777 -->. an issue.\n"
            "Line three is fine."
        )
        result = _fix_inline_html_claim_markers(content)
        lines = result.split('\n')
        assert len(lines) == 3
        assert lines[0] == "Line one is fine."
        assert lines[2] == "Line three is fine."
        # Line 2 should have marker at end
        assert lines[1].endswith("<!-- claim_id: aaaa1111-2222-3333-4444-555566667777 -->")


# ---------------------------------------------------------------------------
# _close_unclosed_fences
# ---------------------------------------------------------------------------

class TestCloseUnclosedFences:
    """Tests for _close_unclosed_fences."""

    def test_close_unclosed_fences_closes_open(self):
        """Verify unclosed fence gets a closing ``` appended."""
        content = "Some text.\n\n```python\ndef hello():\n    pass"
        result = _close_unclosed_fences(content)
        assert result.rstrip().endswith("```")
        # Count fences: should be 2 (opening + closing)
        fence_count = sum(1 for line in result.split('\n') if line.strip().startswith('```'))
        assert fence_count == 2

    def test_close_unclosed_fences_leaves_balanced(self):
        """Verify no change when fences are already balanced."""
        content = "Some text.\n\n```python\ndef hello():\n    pass\n```\n\nMore text."
        result = _close_unclosed_fences(content)
        assert result == content

    def test_close_unclosed_fences_empty_content(self):
        """Verify empty content passes through unchanged."""
        content = ""
        result = _close_unclosed_fences(content)
        assert result == content

    def test_close_unclosed_fences_no_fences(self):
        """Verify content without any fences passes through unchanged."""
        content = "Just normal text.\nWith multiple lines.\n"
        result = _close_unclosed_fences(content)
        assert result == content

    def test_close_unclosed_fences_multiple_balanced(self):
        """Verify multiple balanced fence pairs are left unchanged."""
        content = "```python\ncode1\n```\n\n```bash\ncode2\n```\n"
        result = _close_unclosed_fences(content)
        assert result == content

    def test_close_unclosed_fences_idempotent(self):
        """Verify running the function twice produces the same result."""
        content = "```python\ndef hello():\n    pass"
        result1 = _close_unclosed_fences(content)
        result2 = _close_unclosed_fences(result1)
        assert result1 == result2


# ---------------------------------------------------------------------------
# _fix_code_fences (TC-1662)
# ---------------------------------------------------------------------------

class TestFixCodeFences:
    """Tests for _fix_code_fences."""

    def test_fix_code_fences_orphaned_closing(self):
        """Verify orphaned closing fence is removed."""
        content = """## Example

Some text here.

```
Orphaned closing fence.
"""
        result = _fix_code_fences(content)
        # Should have 0 fences (orphaned closing removed)
        fence_count = sum(1 for line in result.split('\n') if line.strip().startswith('```'))
        assert fence_count == 0
        assert "Some text here." in result

    def test_fix_code_fences_pseudocode_conversion(self):
        """Test conversion of pseudocode blocks to python with comment."""
        content = """## Example

```pseudocode
for each file in directory:
    process(file)
```
"""
        result = _fix_code_fences(content)
        # Should not have pseudocode
        assert '```pseudocode' not in result
        # Should have python
        assert '```python' in result
        # TC-1807: Illustrative comment no longer injected
        # Should be properly closed
        fence_count = sum(1 for line in result.split('\n') if line.strip().startswith('```'))
        assert fence_count == 2  # Opening and closing

    def test_fix_code_fences_unclosed_at_end(self):
        """Verify unclosed fence at end gets closed."""
        content = """## Example

```python
def hello():
    pass"""
        result = _fix_code_fences(content)
        # Should auto-close
        assert result.rstrip().endswith("```")
        fence_count = sum(1 for line in result.split('\n') if line.strip().startswith('```'))
        assert fence_count == 2

    def test_fix_code_fences_balanced_unchanged(self):
        """Verify balanced fences pass through unchanged."""
        content = """## Example

```python
def hello():
    print("world")
```

Some text.
"""
        result = _fix_code_fences(content)
        # Content should be identical (already valid)
        assert result == content

    def test_fix_code_fences_pseudocode_case_insensitive(self):
        """Verify pseudocode detection is case-insensitive."""
        content = """```PSEUDOCODE
algorithm step 1
```"""
        result = _fix_code_fences(content)
        assert '```python' in result
        # TC-1807: Illustrative comment no longer injected
        assert '```PSEUDOCODE' not in result

    def test_fix_code_fences_idempotent(self):
        """Verify running the function twice produces the same result."""
        content = """```pseudocode
step 1
step 2
```"""
        result1 = _fix_code_fences(content)
        result2 = _fix_code_fences(result1)
        assert result1 == result2


# ---------------------------------------------------------------------------
# _fix_collapsed_frontmatter
# ---------------------------------------------------------------------------

class TestFixCollapsedFrontmatter:
    """Tests for _fix_collapsed_frontmatter."""

    def test_fix_collapsed_frontmatter_splits(self):
        """Verify collapsed YAML frontmatter is split into separate lines."""
        content = '---\ntitle: "My Page" description: "A description" summary: "A summary"\n---\n\n# Content'
        result = _fix_collapsed_frontmatter(content)
        # Should have split the keys onto separate lines
        assert 'title: "My Page"' in result
        assert 'description: "A description"' in result
        assert 'summary: "A summary"' in result
        # Each key should be on its own line
        lines = result.split('\n')
        title_lines = [l for l in lines if 'title:' in l and 'page_title' not in l.lower()]
        desc_lines = [l for l in lines if 'description:' in l]
        assert len(title_lines) >= 1
        assert len(desc_lines) >= 1

    def test_fix_collapsed_frontmatter_noop(self):
        """Verify properly formatted YAML frontmatter is unchanged."""
        content = '---\ntitle: "My Page"\ndescription: "A description"\n---\n\n# Content'
        result = _fix_collapsed_frontmatter(content)
        assert result == content

    def test_fix_collapsed_frontmatter_no_frontmatter(self):
        """Verify content without frontmatter passes through unchanged."""
        content = "# Just a heading\n\nSome content."
        result = _fix_collapsed_frontmatter(content)
        assert result == content

    def test_fix_collapsed_frontmatter_idempotent(self):
        """Verify running the function twice produces the same result."""
        content = '---\ntitle: "My Page" description: "A description"\n---\n\n# Content'
        result1 = _fix_collapsed_frontmatter(content)
        result2 = _fix_collapsed_frontmatter(result1)
        assert result1 == result2

    def test_fix_collapsed_frontmatter_single_key(self):
        """Verify single-key frontmatter lines are not modified."""
        content = '---\ntitle: "My Page"\nlayout: default\n---\n\n# Content'
        result = _fix_collapsed_frontmatter(content)
        assert result == content


# ---------------------------------------------------------------------------
# check_unfilled_tokens (updated)
# ---------------------------------------------------------------------------

class TestCheckUnfilledTokens:
    """Tests for the updated check_unfilled_tokens function."""

    def test_check_unfilled_tokens_ignores_lowercase(self):
        """Verify __title__ (lowercase) is NOT flagged — only UPPERCASE tokens are real template tokens.

        LLM content may contain lowercase double-underscore patterns (e.g., __cause__,
        __title__) that are text artifacts, not template placeholders.
        """
        content = "Welcome to __title__ documentation. Root __cause__ analysis."
        result = check_unfilled_tokens(content)
        assert "__title__" not in result
        assert "__cause__" not in result

    def test_check_unfilled_tokens_ignores_dunders(self):
        """Verify Python dunder methods like __init__ are NOT flagged."""
        content = "Call `__init__` to create an instance. Use `__name__` for the module name."
        result = check_unfilled_tokens(content)
        assert "__init__" not in result
        assert "__name__" not in result
        assert len(result) == 0

    def test_check_unfilled_tokens_catches_uppercase(self):
        """Verify __PRODUCT_NAME__ (uppercase) is still caught."""
        content = "This is __PRODUCT_NAME__ documentation."
        result = check_unfilled_tokens(content)
        assert "__PRODUCT_NAME__" in result

    def test_check_unfilled_tokens_mixed(self):
        """Verify mixed content with both dunders and unfilled tokens.

        Only UPPERCASE tokens are real template placeholders. Lowercase
        patterns are LLM artifacts or Python references.
        """
        content = (
            "Use __init__ to start.\n"
            "The __PRODUCT_NAME__ library provides __page_title__ features.\n"
            "Check __repr__ for details."
        )
        result = check_unfilled_tokens(content)
        assert "__init__" not in result
        assert "__repr__" not in result
        assert "__PRODUCT_NAME__" in result
        assert "__page_title__" not in result  # lowercase = not a real token
        assert len(result) == 1

    def test_check_unfilled_tokens_empty(self):
        """Verify empty content returns empty list."""
        result = check_unfilled_tokens("")
        assert result == []

    def test_check_unfilled_tokens_no_tokens(self):
        """Verify content without any tokens returns empty list."""
        content = "This is normal markdown content without any special tokens."
        result = check_unfilled_tokens(content)
        assert result == []

    def test_check_unfilled_tokens_mixed_case_not_caught(self):
        """Verify mixed-case tokens like __Page_Title__ are NOT caught.

        Only all-uppercase tokens (__PAGE_TITLE__) are real template placeholders.
        """
        content = "The __Page_Title__ is shown here. But __PAGE_TITLE__ is a real token."
        result = check_unfilled_tokens(content)
        assert "__Page_Title__" not in result
        assert "__PAGE_TITLE__" in result


# ---------------------------------------------------------------------------
# TC-1502: New post-processing functions
# ---------------------------------------------------------------------------

class TestStripSourceAnnotations:
    """Tests for _strip_source_annotations."""

    def test_strip_source_annotations_removes_comments(self):
        """Verify <!-- source: ... --> comments are removed."""
        content = "Some text <!-- source: claim_abc123 --> more text"
        result = _strip_source_annotations(content)
        assert "<!-- source:" not in result
        assert "Some text" in result
        assert "more text" in result

    def test_strip_source_annotations_collapses_blanks(self):
        """Verify multiple blank lines are collapsed to 2."""
        content = "Line 1\n\n\n\n\nLine 2"
        result = _strip_source_annotations(content)
        assert result == "Line 1\n\nLine 2"

    def test_strip_source_annotations_multiple(self):
        """Verify multiple source annotations are all removed."""
        content = (
            "Text 1 <!-- source: abc -->\n"
            "Text 2 <!-- source: def -->\n"
            "Text 3"
        )
        result = _strip_source_annotations(content)
        assert "<!-- source:" not in result
        assert result.count("Text") == 3

    def test_strip_source_annotations_idempotent(self):
        """Verify running twice produces same result."""
        content = "Text <!-- source: xyz --> more"
        result1 = _strip_source_annotations(content)
        result2 = _strip_source_annotations(result1)
        assert result1 == result2


class TestStripBoilerplateSentences:
    """Tests for _strip_boilerplate_sentences."""

    def test_strip_boilerplate_removes_code_above(self):
        """Verify 'The code above performs...' is removed."""
        content = (
            "```python\n"
            "print('hello')\n"
            "```\n"
            "The code above performs the described operation.\n"
            "More text."
        )
        result = _strip_boilerplate_sentences(content)
        assert "The code above" not in result
        assert "More text" in result

    def test_strip_boilerplate_removes_this_section_covers(self):
        """Verify 'This section covers...' is removed."""
        content = (
            "## Features\n"
            "This section covers key features.\n"
            "Actual content here."
        )
        result = _strip_boilerplate_sentences(content)
        assert "This section covers" not in result
        assert "Actual content" in result

    def test_strip_boilerplate_preserves_in_code_blocks(self):
        """Verify boilerplate inside code blocks is preserved."""
        content = (
            "```python\n"
            "# This section covers the main loop\n"
            "pass\n"
            "```"
        )
        result = _strip_boilerplate_sentences(content)
        assert "This section covers" in result

    def test_strip_boilerplate_no_match(self):
        """Verify content without boilerplate passes through."""
        content = "This is normal content.\nWith multiple lines."
        result = _strip_boilerplate_sentences(content)
        assert result == content


class TestFixSelfReferentialLinks:
    """Tests for _fix_self_referential_links."""

    def test_fix_self_referential_removes_link(self):
        """Verify self-referential link is removed."""
        content = (
            "# Overview\n\n"
            "Content here.\n\n"
            "## See Also\n\n"
            "- [Overview](/3d/overview/)\n"
            "- [Getting Started](/3d/getting-started/)\n"
            "- [API Reference](/3d/reference/)\n"
        )
        result = _fix_self_referential_links(content, "/3d/overview/")
        assert "- [Overview](/3d/overview/)" not in result
        assert "- [Getting Started](/3d/getting-started/)" in result
        assert "- [API Reference](/3d/reference/)" in result

    def test_fix_self_referential_removes_section_if_few_links(self):
        """Verify See Also section removed if <2 links remain."""
        content = (
            "# Page\n\n"
            "## See Also\n\n"
            "- [Current Page](/docs/page/)\n"
        )
        result = _fix_self_referential_links(content, "/docs/page/")
        assert "## See Also" not in result

    def test_fix_self_referential_normalizes_urls(self):
        """Verify URL normalization (trailing slashes)."""
        content = (
            "## See Also\n\n"
            "- [Page](/docs/page)\n"
            "- [Other](/docs/other)\n"
            "- [Third](/docs/third)\n"
        )
        result = _fix_self_referential_links(content, "/docs/page")
        assert "- [Page](/docs/page)" not in result
        assert "- [Other](/docs/other)" in result
        assert "- [Third](/docs/third)" in result

    def test_fix_self_referential_no_page_url(self):
        """Verify no changes when page_url is empty."""
        content = "## See Also\n\n- [Link](/docs/link/)"
        result = _fix_self_referential_links(content, "")
        assert result == content


class TestFixProseInCodeBlocks:
    """Tests for _fix_prose_in_code_blocks."""

    def test_fix_prose_rescues_heading(self):
        """Verify prose heading inside code block is rescued."""
        content = (
            "```python\n"
            "def foo():\n"
            "    pass\n"
            "## Installation\n"
            "Run pip install.\n"
            "```"
        )
        result = _fix_prose_in_code_blocks(content)
        # Heading should be outside code block
        assert "```\n## Installation" in result or "```\n\n## Installation" in result

    def test_fix_prose_rescues_blockquote(self):
        """Verify blockquote inside code block is rescued."""
        content = (
            "```python\n"
            "code_here()\n"
            "> Note: This is important.\n"
            "```"
        )
        result = _fix_prose_in_code_blocks(content)
        # Blockquote should be outside fence
        assert result.count("```") >= 4  # Original open/close + new close/open

    def test_fix_prose_rescues_bold(self):
        """Verify bold text inside code block is rescued."""
        content = (
            "```python\n"
            "x = 1\n"
            "**Important**: Do not modify.\n"
            "```"
        )
        result = _fix_prose_in_code_blocks(content)
        # Bold should trigger fence close/reopen
        assert result.count("```") >= 4

    def test_fix_prose_no_prose(self):
        """Verify normal code blocks pass through."""
        content = (
            "```python\n"
            "def hello():\n"
            "    return 'world'\n"
            "```"
        )
        result = _fix_prose_in_code_blocks(content)
        assert result.count("```") == 2


class TestStripOrphanClaimMarkers:
    """Tests for _strip_orphan_claim_markers."""

    def test_strip_orphan_html_marker(self):
        """Verify orphan HTML claim marker is removed (TC-1650 format)."""
        content = (
            "- Feature 1\n"
            "- <!-- claim: abc123 -->\n"
            "- Feature 2"
        )
        result = _strip_orphan_claim_markers(content)
        assert "- <!-- claim:" not in result
        assert "- Feature 1" in result
        assert "- Feature 2" in result

    def test_strip_orphan_bracket_marker(self):
        """Verify orphan <!-- claim: ... --> marker is removed."""
        content = (
            "- Item 1\n"
            "- <!-- claim: xyz789 -->\n"
            "- Item 2"
        )
        result = _strip_orphan_claim_markers(content)
        assert "- <!-- claim:" not in result
        assert "- Item 1" in result

    def test_strip_orphan_numbered(self):
        """Verify orphan numbered list marker is removed."""
        content = (
            "1. Step 1\n"
            "- 2. <!-- claim_id: def456 -->\n"
            "3. Step 3"
        )
        result = _strip_orphan_claim_markers(content)
        assert "- 2. <!--" not in result

    def test_strip_orphan_preserves_valid(self):
        """Verify valid claim markers with text are preserved."""
        content = "- Feature X <!-- claim_id: abc123 -->"
        result = _strip_orphan_claim_markers(content)
        assert "Feature X" in result
        assert "<!-- claim_id: abc123 -->" in result


class TestFenceBareCommands:
    """Tests for _fence_bare_commands."""

    def test_fence_bare_pip_install(self):
        """Verify bare pip install is wrapped in fence."""
        content = (
            "Install the package:\n\n"
            "pip install aspose-3d\n\n"
            "Then import it."
        )
        result = _fence_bare_commands(content)
        assert "```bash\npip install aspose-3d\n```" in result

    def test_fence_bare_python_command(self):
        """Verify bare python -m is wrapped."""
        content = "Run:\n\npython -m pytest\n\nDone."
        result = _fence_bare_commands(content)
        assert "```bash\npython -m pytest\n```" in result

    def test_fence_bare_npm_install(self):
        """Verify bare npm install is wrapped."""
        content = "Install:\n\nnpm install pkg\n\nContinue."
        result = _fence_bare_commands(content)
        assert "```bash\nnpm install pkg\n```" in result

    def test_fence_bare_preserves_existing(self):
        """Verify commands already in fences are unchanged."""
        content = (
            "```bash\n"
            "pip install pkg\n"
            "```"
        )
        result = _fence_bare_commands(content)
        # Should not add extra fences
        assert result.count("```bash") == 1

    def test_fence_bare_consecutive_commands(self):
        """Verify consecutive bare commands are grouped."""
        content = (
            "Run:\n\n"
            "pip install pkg1\n"
            "pip install pkg2\n\n"
            "Done."
        )
        result = _fence_bare_commands(content)
        # Should wrap both in one fence
        assert result.count("```bash") == 1
        assert "pip install pkg1" in result
        assert "pip install pkg2" in result


# ---------------------------------------------------------------------------
# _smart_truncate (TC-1660)
# ---------------------------------------------------------------------------

class TestSmartTruncate:
    """Tests for _smart_truncate (TC-1660).

    Testing: mocked (Test 1: LLM path with mock)
    Testing: deterministic (Test 2-5: deterministic fallback paths)
    """

    def test_smart_truncate_passthrough_short_text(self):
        """Verify short text passes through unchanged."""
        text = "This is short text."
        result = _smart_truncate(text, max_len=200)
        assert result == text

    def test_smart_truncate_llm_success(self):
        """Verify LLM summarization is used when available.

        Testing: mocked
        """
        # Mock LLM client that returns valid summary
        class MockLLM:
            def generate(self, prompt, max_tokens=100, temperature=0.3):
                return "Short summary."

        text = "This is a very long text that needs to be truncated. " * 10
        llm_client = MockLLM()
        result = _smart_truncate(text, max_len=50, llm_client=llm_client)

        # Should use LLM summary
        assert result == "Short summary."
        assert len(result) <= 50

    def test_smart_truncate_llm_failure_fallback(self):
        """Verify fallback to sentence-boundary when LLM fails.

        Testing: mocked
        """
        # Mock LLM client that raises exception
        class MockLLM:
            def generate(self, prompt, max_tokens=100, temperature=0.3):
                raise Exception("LLM unavailable")

        text = "First sentence here. Second sentence here. Third sentence here."
        llm_client = MockLLM()
        result = _smart_truncate(text, max_len=40, llm_client=llm_client)

        # Should fall back to sentence-boundary truncation
        # max_len=40 fits only first sentence (20 chars)
        assert result == "First sentence here."
        assert len(result) <= 40
        assert not result.endswith("...")

    def test_smart_truncate_sentence_boundary(self):
        """Verify sentence-boundary truncation preserves complete sentences."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = _smart_truncate(text, max_len=35, llm_client=None)

        # Should include complete sentences only
        assert result == "First sentence. Second sentence."
        assert not result.endswith("...")
        assert len(result) <= 50

    def test_smart_truncate_word_boundary_last_resort(self):
        """Verify word-boundary truncation when no sentence fits."""
        # Very long single sentence without periods
        text = "This is a very long sentence without any punctuation marks that goes on and on"
        result = _smart_truncate(text, max_len=30, llm_client=None)

        # Should truncate at word boundary (not mid-word)
        assert not result.endswith("...")
        assert len(result) <= 30
        # Should not cut mid-word
        words = result.split()
        assert all(word.isalpha() or word[-1] in ".,!?" for word in words)

    def test_smart_truncate_handles_multiple_punctuation(self):
        """Verify truncation works with multiple punctuation types."""
        text = "Question one? Answer here! Statement next. More text here."
        result = _smart_truncate(text, max_len=35, llm_client=None)

        # Should include complete sentences
        assert result in [
            "Question one? Answer here!",
            "Question one?",
        ]
        assert not result.endswith("...")

    def test_smart_truncate_deterministic(self):
        """Verify deterministic behavior (no LLM = same output every time)."""
        text = "Sentence one. Sentence two. Sentence three."
        result1 = _smart_truncate(text, max_len=30, llm_client=None)
        result2 = _smart_truncate(text, max_len=30, llm_client=None)

        assert result1 == result2
        assert not result1.endswith("...")


# ---------------------------------------------------------------------------
# _first_sentence_bullets (TC-1661)
# ---------------------------------------------------------------------------

class TestFirstSentenceBullets:
    """Tests for _first_sentence_bullets (TC-1661).

    TC-1661: Ensure bracket claim markers are converted to HTML comments
    before sentence extraction to prevent broken markers at boundaries.
    """

    def test_first_sentence_bullets_converts_bracket_markers(self):
        """TC-1661: Ensure bracket markers converted to HTML comments before sentence extraction."""
        # Long bullet with bracket marker at end (must exceed MAX_BULLET_LEN=170)
        long_text = "This is a very long feature description that explains the functionality in great detail and provides comprehensive information about the capabilities. It has multiple additional sentences that make it even longer. [claim: feat_001]"
        bullet = f"- {long_text}"

        # Verify bullet exceeds threshold
        assert len(bullet.lstrip()) > MAX_BULLET_LEN

        # Should convert marker and extract first sentence
        result = _first_sentence_bullets(bullet)

        # Verify:
        # 1. Bracket marker converted to HTML comment
        assert "[claim:" not in result
        assert "<!-- claim: feat_001 -->" in result

        # 2. First sentence extracted (not full text)
        assert "multiple additional sentences" not in result
        assert "very long feature description" in result

        # 3. Marker preserved at end
        assert result.strip().endswith("<!-- claim: feat_001 -->")

    def test_first_sentence_bullets_html_comment_preserved(self):
        """Verify HTML comment markers are preserved correctly."""
        # Long bullet exceeding MAX_BULLET_LEN with HTML comment marker
        long_text = "This feature provides advanced capabilities and comprehensive functionality that enables users to perform complex operations efficiently. Additional details follow with more information. <!-- claim: feat_002 -->"
        bullet = f"- {long_text}"

        # Verify exceeds threshold
        assert len(bullet.lstrip()) > MAX_BULLET_LEN

        result = _first_sentence_bullets(bullet)

        # Verify HTML comment format preserved
        assert "<!-- claim: feat_002 -->" in result
        assert "[claim:" not in result

        # First sentence extracted
        assert "Additional details" not in result
        assert "advanced capabilities" in result

    def test_first_sentence_bullets_short_text_unchanged(self):
        """Verify short bullets pass through unchanged."""
        bullet = "- Short text [claim: abc]"
        result = _first_sentence_bullets(bullet)

        # Should convert marker but not truncate (too short)
        assert "<!-- claim: abc -->" in result
        assert "Short text" in result

    def test_first_sentence_bullets_no_marker(self):
        """Verify bullets without markers work correctly."""
        # Long bullet exceeding MAX_BULLET_LEN without claim marker
        long_text = "This is a very long bullet point that exceeds the maximum length threshold and provides detailed information about various features. It should be truncated at sentence boundary."
        bullet = f"- {long_text}"

        # Verify exceeds threshold
        assert len(bullet.lstrip()) > MAX_BULLET_LEN

        result = _first_sentence_bullets(bullet)

        # Should extract first sentence
        assert "maximum length threshold" in result
        assert "sentence boundary" not in result

    def test_first_sentence_bullets_multiple_bullets(self):
        """Verify multiple bullets are processed correctly."""
        content = (
            "- Short bullet [claim: a1]\n"
            "- This is a very long bullet point that definitely needs truncation because it contains extensive comprehensive details. Additional second sentence here. Third sentence too. [claim: a2]\n"
            "- Another short one [claim: a3]"
        )

        result = _first_sentence_bullets(content)

        # All bracket markers should be converted
        assert "[claim:" not in result
        assert result.count("<!-- claim:") == 3

        # Long bullet should be truncated (second and third sentences removed)
        assert "Additional second sentence" not in result
        assert "Third sentence" not in result
        assert "very long bullet" in result

    def test_first_sentence_bullets_idempotent(self):
        """Verify running twice produces same result."""
        # Long bullet exceeding MAX_BULLET_LEN
        bullet = "- Long text with extensive details about features and comprehensive information that definitely exceeds the required threshold for truncation. More text follows here with additional content. [claim: xyz]"

        # Verify exceeds threshold
        assert len(bullet.lstrip()) > MAX_BULLET_LEN

        result1 = _first_sentence_bullets(bullet)
        result2 = _first_sentence_bullets(result1)

        assert result1 == result2
        assert "[claim:" not in result1


# ---------------------------------------------------------------------------
# _strip_visible_claim_markers (Round 11.5 Fix 2)
# ---------------------------------------------------------------------------

class TestStripVisibleClaimMarkers:
    """Tests for _strip_visible_claim_markers()."""

    def test_strips_bracket_claim_markers(self):
        """Verify visible [claim: id] markers are stripped from body text."""
        content = "This is a feature [claim: abc123def456]. More text."
        result = _strip_visible_claim_markers(content)
        assert "[claim:" not in result
        assert "This is a feature" in result
        assert "More text" in result

    def test_strips_html_comment_markers(self):
        """Verify HTML comment claim markers ARE stripped (pipeline cleanup)."""
        content = "Feature text.\n<!-- claim: abc123 -->\nMore text."
        result = _strip_visible_claim_markers(content)
        assert "<!-- claim: abc123 -->" not in result
        assert "Feature text." in result
        assert "More text." in result

    def test_strips_multiple_markers(self):
        """Verify multiple visible markers in same content are all stripped."""
        content = (
            "First point [claim: aaa111].\n"
            "Second point [claim: bbb222].\n"
            "Third point [claim: ccc333]."
        )
        result = _strip_visible_claim_markers(content)
        assert "[claim:" not in result
        assert "First point" in result
        assert "Second point" in result
        assert "Third point" in result

    def test_handles_markers_with_hyphens(self):
        """Verify claim markers with hyphens (UUID format) are stripped."""
        content = "Text [claim: abc-123-def-456]."
        result = _strip_visible_claim_markers(content)
        assert "[claim:" not in result
        assert "Text" in result

    def test_no_double_spaces_after_stripping(self):
        """Verify no double spaces remain after marker removal."""
        content = "Feature text [claim: abc123] continues here."
        result = _strip_visible_claim_markers(content)
        assert "  " not in result
