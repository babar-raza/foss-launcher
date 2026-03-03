"""Tests for TC-3682: See Also dedup and position sanitizers."""

from __future__ import annotations

import textwrap

import pytest

from launch.workers._shared.content_sanitizer import (
    dedup_see_also_sections,
    move_see_also_to_end,
)


# ── dedup_see_also_sections ──────────────────────────────────────────────────

class TestDedupSeeAlsoSections:
    """Tests for dedup_see_also_sections()."""

    def test_no_see_also_unchanged(self):
        content = "## Overview\n\nSome content.\n"
        assert dedup_see_also_sections(content) == content

    def test_single_see_also_unchanged(self):
        content = textwrap.dedent("""\
            ## Overview

            Content.

            ## See Also

            - [Link 1](url1)
            - [Link 2](url2)""")
        assert dedup_see_also_sections(content) == content

    def test_duplicate_see_also_merged(self):
        content = textwrap.dedent("""\
            ## Overview

            Content.

            ## See Also

            - [Link 1](url1)

            ## More Content

            Some text.

            ## See Also

            - [Link 2](url2)""")
        result = dedup_see_also_sections(content)
        # Should have exactly one ## See Also
        assert result.count("## See Also") == 1
        # Both links should be present
        assert "- [Link 1](url1)" in result
        assert "- [Link 2](url2)" in result

    def test_case_insensitive_detection(self):
        """'## See also' (lowercase a) should be detected."""
        content = textwrap.dedent("""\
            ## See also

            - [Link 1](url1)

            ## Content

            Text.

            ## See Also

            - [Link 2](url2)""")
        result = dedup_see_also_sections(content)
        # Only one See Also variant should remain
        see_also_count = len([
            l for l in result.split("\n")
            if l.strip().lower().startswith("## see also")
        ])
        assert see_also_count == 1

    def test_punctuation_variant_detected(self):
        """'## See Also.' (with trailing period) should be detected."""
        content = textwrap.dedent("""\
            ## See Also.

            - [Link 1](url1)

            ## See Also

            - [Link 2](url2)""")
        result = dedup_see_also_sections(content)
        assert "- [Link 1](url1)" in result
        assert "- [Link 2](url2)" in result

    def test_links_deduped(self):
        """Duplicate links across sections should appear only once."""
        content = textwrap.dedent("""\
            ## See Also

            - [Same Link](url1)

            ## See Also

            - [Same Link](url1)
            - [New Link](url2)""")
        result = dedup_see_also_sections(content)
        assert result.count("- [Same Link](url1)") == 1
        assert "- [New Link](url2)" in result

    def test_code_fence_protection(self):
        """See Also inside code fence should not trigger dedup."""
        content = textwrap.dedent("""\
            ## See Also

            - [Link 1](url1)

            ```markdown
            ## See Also

            - [Fake Link](fake)
            ```""")
        # The code fence one should NOT be treated as a heading
        result = dedup_see_also_sections(content)
        assert "- [Fake Link](fake)" in result  # still inside fence

    def test_idempotent(self):
        content = textwrap.dedent("""\
            ## See Also

            - [Link 1](url1)

            ## See Also

            - [Link 2](url2)""")
        once = dedup_see_also_sections(content)
        twice = dedup_see_also_sections(once)
        assert once == twice


# ── move_see_also_to_end ─────────────────────────────────────────────────────

class TestMoveSeeAlsoToEnd:
    """Tests for move_see_also_to_end()."""

    def test_already_last_unchanged(self):
        content = textwrap.dedent("""\
            ## Overview

            Content.

            ## See Also

            - [Link](url)""")
        assert move_see_also_to_end(content) == content

    def test_no_see_also_unchanged(self):
        content = "## Overview\n\nContent.\n\n## Another\n\nMore.\n"
        assert move_see_also_to_end(content) == content

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
        # Find positions of H2 headings
        h2s = [(i, l) for i, l in enumerate(lines) if l.strip().startswith("## ")]
        # Last H2 should be See Also
        assert "See Also" in h2s[-1][1]
        # Troubleshooting should come before See Also
        assert "Troubleshooting" in h2s[-2][1]

    def test_see_also_content_preserved(self):
        """All See Also links should be preserved after move."""
        content = textwrap.dedent("""\
            ## See Also

            - [Link 1](url1)
            - [Link 2](url2)

            ## Content

            Text here.""")
        result = move_see_also_to_end(content)
        assert "- [Link 1](url1)" in result
        assert "- [Link 2](url2)" in result

    def test_idempotent(self):
        content = textwrap.dedent("""\
            ## See Also

            - [Link](url)

            ## Content

            Text.""")
        once = move_see_also_to_end(content)
        twice = move_see_also_to_end(once)
        assert once == twice
