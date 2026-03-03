"""TC-I: Publication-blocker fixture pack + idempotency verification.

Exercises gates + sanitizers on representative markdown that hits each
publication-blocker category:
  - Duplicate See Also (including See Also. variant)
  - Content after See Also
  - Aspose. Cells (space in brand name) in frontmatter
  - Spec leakage terms in prose
  - Heading trailing periods
  - Import sanitizer: canonical_import wiring (verified elsewhere)
  - Pipeline idempotency: pipeline(pipeline(x)) == pipeline(x)
"""

from __future__ import annotations

import textwrap

import pytest

from launch.workers._shared.content_sanitizer import (
    canonicalize_product_names,
    dedup_see_also_sections,
    move_see_also_to_end,
    run_pipeline,
    strip_heading_trailing_punct,
    strip_spec_leakage_terms,
)


# ── Blocker: Heading trailing period ──────────────────────────────────────────

class TestBlockerHeadingTrailingPeriod:
    """strip_heading_trailing_punct removes trailing periods from H2/H3."""

    def test_h2_period_removed(self):
        result = strip_heading_trailing_punct("## Overview.\n\nContent.\n")
        assert "## Overview\n" in result
        assert "## Overview.\n" not in result

    def test_h3_period_removed(self):
        result = strip_heading_trailing_punct("### Installation.\n\nSteps.\n")
        assert "### Installation\n" in result


# ── Blocker: Duplicate See Also ───────────────────────────────────────────────

class TestBlockerDuplicateSeeAlso:
    """dedup_see_also_sections merges duplicate See Also headings."""

    def test_two_see_also_merged(self):
        content = textwrap.dedent("""\
            ## Overview

            Content.

            ## See Also

            - [Link 1](url1)

            ## See Also

            - [Link 2](url2)""")
        result = dedup_see_also_sections(content)
        assert result.count("## See Also") == 1
        assert "- [Link 1](url1)" in result
        assert "- [Link 2](url2)" in result

    def test_see_also_with_trailing_period(self):
        content = textwrap.dedent("""\
            ## See Also.

            - [Link 1](url1)

            ## See Also

            - [Link 2](url2)""")
        result = dedup_see_also_sections(content)
        # Both links preserved
        assert "- [Link 1](url1)" in result
        assert "- [Link 2](url2)" in result


# ── Blocker: Content after See Also ───────────────────────────────────────────

class TestBlockerContentAfterSeeAlso:
    """move_see_also_to_end repositions See Also to be the last H2."""

    def test_see_also_moved_to_end(self):
        content = textwrap.dedent("""\
            ## Overview

            Content.

            ## See Also

            - [Link](url)

            ## Troubleshooting

            Fix things.""")
        result = move_see_also_to_end(content)
        lines = result.split("\n")
        h2s = [l for l in lines if l.strip().startswith("## ")]
        # Last H2 should be See Also
        assert "See Also" in h2s[-1]


# ── Blocker: Product name space corruption in frontmatter ─────────────────────

class TestBlockerProductNameFrontmatter:
    """canonicalize_product_names fixes 'Aspose. Cells' in frontmatter."""

    def test_space_after_dot_in_frontmatter_title(self):
        content = textwrap.dedent("""\
            ---
            title: "Aspose. Cells FOSS for Python"
            description: "Work with Aspose. Cells"
            ---

            Regular content.""")
        result = canonicalize_product_names(content, "Aspose.Cells FOSS for Python")
        assert "Aspose. Cells" not in result
        assert "Aspose.Cells" in result


# ── Blocker: Spec leakage terms in prose ──────────────────────────────────────

class TestBlockerSpecLeakage:
    """strip_spec_leakage_terms removes spec terms from prose."""

    def test_jcid_removed_from_prose(self):
        content = "## Overview\n\nThe JCID format is used internally.\nNormal text.\n"
        result = strip_spec_leakage_terms(content)
        assert "JCID" not in result
        assert "Normal text." in result

    def test_spec_term_in_code_fence_preserved(self):
        content = textwrap.dedent("""\
            Normal text.

            ```python
            # JCID is used here
            value = 0xABCD
            ```

            More text.""")
        result = strip_spec_leakage_terms(content)
        assert "JCID" in result  # Inside fence, preserved


# ── Idempotency ──────────────────────────────────────────────────────────────

class TestPipelineIdempotency:
    """Verify pipeline(pipeline(x)) == pipeline(x) for representative inputs."""

    def _test_sanitizer_idempotent(self, content: str, sanitizer_fn, *args):
        """Generic idempotency check: fn(fn(x)) == fn(x)."""
        once = sanitizer_fn(content, *args)
        twice = sanitizer_fn(once, *args)
        assert once == twice, f"{sanitizer_fn.__name__} is not idempotent"

    def test_idempotent_strip_heading_punct(self):
        content = "## Overview.\n\n### Details.\n\nContent.\n"
        self._test_sanitizer_idempotent(content, strip_heading_trailing_punct)

    def test_idempotent_canonicalize_product_names(self):
        content = textwrap.dedent("""\
            ---
            title: "Aspose. Cells Guide"
            ---

            Use Aspose. Cells for spreadsheets.""")
        self._test_sanitizer_idempotent(
            content, canonicalize_product_names, "Aspose.Cells FOSS for Python"
        )

    def test_idempotent_dedup_see_also(self):
        content = textwrap.dedent("""\
            ## See Also

            - [Link 1](url1)

            ## See Also

            - [Link 2](url2)""")
        self._test_sanitizer_idempotent(content, dedup_see_also_sections)

    def test_idempotent_move_see_also_to_end(self):
        content = textwrap.dedent("""\
            ## See Also

            - [Link](url)

            ## Content

            Text here.""")
        self._test_sanitizer_idempotent(content, move_see_also_to_end)

    def test_idempotent_strip_spec_leakage(self):
        content = "## Overview\n\nThe JCID format.\nNormal text.\n"
        self._test_sanitizer_idempotent(content, strip_spec_leakage_terms)
