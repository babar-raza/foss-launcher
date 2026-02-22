"""Tests for Layer 1 LLM Response Validator (TC-2392).

Covers the 9 required test cases from the taskcard:
1. test_fence_balance_even          — even fence count → is_valid=True
2. test_fence_balance_odd           — odd fence count → error in errors list
3. test_frontmatter_contamination   — 4+ bare '---' lines → error
4. test_frontmatter_two_delimiters_ok — exactly 2 '---' lines → no error
5. test_truncation_detection        — response not ending with punct/fence → warning
6. test_min_length_fail             — content < 50 chars → error
7. test_enhance_prompt_for_retry    — error block injected into retry prompt
8. test_validation_duration_ms      — duration < 15ms on typical content
9. test_no_errors_no_enhancement    — valid result → enhance_prompt returns base unchanged
"""

import pytest

from launch.workers._shared.llm_response_validator import (
    ValidationResult,
    validate_llm_response,
    enhance_prompt_for_retry,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

# A well-formed markdown snippet used as baseline for "good" content.
GOOD_MARKDOWN = """\
## Introduction

This section explains how to convert PDF files to DOCX format using Aspose.Words for Python.
The API provides a simple one-call conversion method.

```python
import aspose.words as aw
doc = aw.Document("input.pdf")
doc.save("output.docx")
```

The example above loads a PDF and saves it as a Word document.
All formatting is preserved automatically.
"""


# ── Test 1: even fence count → is_valid=True ──────────────────────────────────

def test_fence_balance_even():
    """Even number of ``` markers (2) → no fence error, is_valid=True."""
    content = GOOD_MARKDOWN  # has exactly 2 ``` markers → balanced
    result = validate_llm_response(content, content_type="markdown")

    fence_errors = [e for e in result.errors if "fence" in e.lower() or "code block" in e.lower()]
    assert fence_errors == [], f"Expected no fence errors; got: {fence_errors}"
    assert result.is_valid, f"Expected is_valid=True; errors: {result.errors}"


# ── Test 2: odd fence count → error ──────────────────────────────────────────

def test_fence_balance_odd():
    """Odd number of ``` markers (3) → fence error, is_valid=False."""
    content = (
        "## Section\n\n"
        "Here is some code:\n\n"
        "```python\nprint('hello')\n"
        "```\n\n"
        "And another unclosed block:\n\n"
        "```python\nprint('world')\n"
        # intentionally missing closing ```
        "\nThis response is long enough to pass the minimum length check. "
        "Extra padding to exceed fifty characters easily."
    )
    result = validate_llm_response(content, content_type="markdown")

    assert not result.is_valid, "Expected is_valid=False for odd fence count"
    fence_errors = [e for e in result.errors if "fence" in e.lower() or "code block" in e.lower()]
    assert len(fence_errors) >= 1, f"Expected at least one fence error; got errors: {result.errors}"


# ── Test 3: frontmatter contamination (4+ --- lines) → error ─────────────────

def test_frontmatter_contamination():
    """Four bare '---' lines → frontmatter contamination error, is_valid=False."""
    content = (
        "---\n"
        "title: First Block\n"
        "---\n"
        "Some content here that makes the response long enough to pass length check.\n"
        "---\n"
        "title: Second Block\n"
        "---\n"
        "More content follows to make sure we have enough characters for the test.\n"
        "All done."
    )
    result = validate_llm_response(content, content_type="markdown")

    assert not result.is_valid, "Expected is_valid=False for frontmatter contamination"
    fm_errors = [e for e in result.errors if "frontmatter" in e.lower() or "---" in e]
    assert len(fm_errors) >= 1, f"Expected frontmatter error; got errors: {result.errors}"


# ── Test 4: exactly 2 '---' lines → no frontmatter error ─────────────────────

def test_frontmatter_two_delimiters_ok():
    """Exactly 2 bare '---' lines (one frontmatter block) → no frontmatter error."""
    content = (
        "---\n"
        "title: Valid Page\n"
        "---\n"
        "## Introduction\n\n"
        "This is the page body. It has enough content to pass the minimum length check.\n"
        "The frontmatter block above is perfectly valid and should not trigger an error."
    )
    result = validate_llm_response(content, content_type="markdown")

    fm_errors = [e for e in result.errors if "frontmatter" in e.lower()]
    assert fm_errors == [], f"Expected no frontmatter errors for 2 --- lines; got: {fm_errors}"


# ── Test 5: truncation → warning (not error) ─────────────────────────────────

def test_truncation_detection():
    """Response not ending with sentence-terminal punctuation → truncation warning."""
    # Ends with a letter mid-sentence, not with .!?`>
    content = (
        "## Getting Started\n\n"
        "To install the package, run the following command in your terminal and then configure"
    )
    result = validate_llm_response(content, content_type="markdown")

    trunc_warnings = [w for w in result.warnings if "truncat" in w.lower()]
    assert len(trunc_warnings) >= 1, (
        f"Expected a truncation warning; got warnings: {result.warnings}"
    )


# ── Test 6: content < 50 chars → error ────────────────────────────────────────

def test_min_length_fail():
    """Content shorter than 50 chars → minimum-length error, is_valid=False."""
    short_content = "Too short."  # 10 chars
    result = validate_llm_response(short_content, content_type="markdown")

    assert not result.is_valid, "Expected is_valid=False for content below minimum length"
    length_errors = [e for e in result.errors if "short" in e.lower() or "minimum" in e.lower()]
    assert len(length_errors) >= 1, f"Expected a length error; got errors: {result.errors}"


def test_keyword_response_none_is_valid():
    """'NONE' (4 chars) is valid — expected response from semantic hallucination checks."""
    result = validate_llm_response("NONE", content_type="markdown")
    assert result.is_valid, f"Expected 'NONE' to be valid; got errors: {result.errors}"


def test_keyword_response_yes_is_valid():
    """'Yes' and 'No' are valid one-word responses (semantic yes/no checks)."""
    for kw in ("YES", "NO", "PASS", "FAIL", "TRUE", "FALSE", "N/A"):
        result = validate_llm_response(kw, content_type="markdown")
        assert result.is_valid, f"Expected '{kw}' to be valid; got errors: {result.errors}"


def test_arbitrary_short_non_keyword_still_fails():
    """Short non-keyword responses still fail (e.g. 'Ok.' is not in the allow-list)."""
    result = validate_llm_response("Ok.", content_type="markdown")
    length_errors = [e for e in result.errors if "short" in e.lower() or "minimum" in e.lower()]
    assert len(length_errors) >= 1, f"Expected length error for 'Ok.'; got: {result.errors}"


# ── Test 7: enhance_prompt_for_retry injects error block ─────────────────────

def test_enhance_prompt_for_retry():
    """Error block from ValidationResult is injected into the retry prompt."""
    base_prompt = "Write a tutorial section about PDF conversion."
    validation_result = ValidationResult(
        is_valid=False,
        errors=[
            "Unbalanced code fences: 3 ``` markers found (must be even).",
            "Frontmatter contamination: 4 bare '---' lines found.",
        ],
        warnings=[],
        content_type="markdown",
        validation_duration_ms=1,
    )

    enhanced = enhance_prompt_for_retry(base_prompt, validation_result)

    assert base_prompt in enhanced, "Original prompt must be preserved in enhanced prompt"
    assert "Unbalanced code fences" in enhanced, "First error must appear in enhanced prompt"
    assert "Frontmatter contamination" in enhanced, "Second error must appear in enhanced prompt"
    # The enhancement block should come after the base prompt
    assert enhanced.index(base_prompt) < len(enhanced) - len(base_prompt), (
        "Enhancement context should be appended, not prepended to the base prompt"
    )


# ── Test 8: validation runs in < 15ms ────────────────────────────────────────

def test_validation_duration_ms():
    """validate_llm_response() completes in < 15ms on a typical 2000-char input."""
    # Build ~2000-char content
    paragraph = (
        "Aspose.Words for Python provides a powerful API for document conversion. "
        "You can convert between dozens of formats including PDF, DOCX, HTML, and more. "
    )
    content = "## Overview\n\n" + (paragraph * 14)[:2000]

    result = validate_llm_response(content, content_type="markdown")

    assert result.validation_duration_ms < 15, (
        f"Expected validation in < 15ms; took {result.validation_duration_ms}ms"
    )


# ── Test 9: no errors → enhance_prompt returns base unchanged ─────────────────

def test_no_errors_no_enhancement():
    """When ValidationResult.errors is empty, enhance_prompt returns base_prompt unchanged."""
    base_prompt = "Write a section about installation steps."
    valid_result = ValidationResult(
        is_valid=True,
        errors=[],
        warnings=["Response may be truncated"],  # warnings don't trigger enhancement
        content_type="markdown",
        validation_duration_ms=0,
    )

    returned = enhance_prompt_for_retry(base_prompt, valid_result)

    assert returned == base_prompt, (
        f"Expected base_prompt returned unchanged when no errors; got: {returned!r}"
    )
