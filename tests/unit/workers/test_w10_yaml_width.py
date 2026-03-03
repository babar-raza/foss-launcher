"""Tests for TC-3628: write_frontmatter() yaml.dump width=inf fix.

Verifies that long description strings do NOT wrap as YAML plain-scalar
continuations, preventing the "  post" / "  article" frontmatter artifact
that causes Hugo and PyYAML parse failures.
"""

import yaml
import pytest
from launch.workers.w10_fixer.worker import write_frontmatter


class TestNoYamlWrapping:
    """write_frontmatter must not wrap long strings (TC-3628)."""

    def test_long_description_no_wrapping(self):
        """A description longer than 80 chars must not wrap to next line."""
        desc = (
            "Introducing cells for FOSS Python - Aspose.Cells FOSS for Python blog post"
        )
        fm = {"description": desc, "layout": "blog"}
        result = write_frontmatter(fm, "body\n")
        # The word 'post' must appear on the same line as 'description:'
        lines = result.split("\n")
        desc_line = next((l for l in lines if l.startswith("description:")), None)
        assert desc_line is not None, "description key not found"
        assert "post" in desc_line, (
            f"'post' split to next line — yaml.dump wrapping not disabled. "
            f"Got: {[l for l in lines if 'post' in l or 'description' in l]}"
        )

    def test_blog_post_ending_no_artifact(self):
        """Exact reproduction of the 'blog post' wrapping bug."""
        desc = "Introducing cells for FOSS Python - Aspose.Cells FOSS for Python blog post"
        fm = {"description": desc, "layout": "blog"}
        result = write_frontmatter(fm, "")
        # There must NOT be a line with only '  post'
        assert "\n  post\n" not in result, (
            "Found orphaned '  post' continuation line — yaml.dump width not set to inf"
        )

    def test_article_ending_no_artifact(self):
        """Exact reproduction of the '  article' wrapping bug in howto files."""
        desc = (
            "See the [Installation Guide](https://docs.aspose.org/cells/python/installation/) "
            "for setup instructions. Overview article"
        )
        fm = {"description": desc, "layout": "kb"}
        result = write_frontmatter(fm, "")
        assert "\n  article\n" not in result, (
            "Found orphaned '  article' continuation line"
        )

    def test_round_trip_parseable_by_pyyaml(self):
        """Output of write_frontmatter must be parseable by PyYAML."""
        import re
        desc = (
            "Aspose.Cells FOSS for Python provides a pure-Python API for reading "
            "and writing Excel spreadsheets without Microsoft Office dependencies"
        )
        fm = {"title": "Test Title", "description": desc, "layout": "kb",
              "permalink": "/cells/python/test/"}
        result = write_frontmatter(fm, "body content\n")
        # Extract YAML block
        match = re.match(r"^---\n(.*?)\n---\n", result, re.DOTALL)
        assert match is not None, "Could not find YAML frontmatter delimiters"
        parsed = yaml.safe_load(match.group(1))
        assert parsed["description"] == desc

    def test_short_description_unchanged(self):
        """Short descriptions must not be affected by width=inf."""
        fm = {"title": "Short Title", "layout": "docs", "permalink": "/test/"}
        result = write_frontmatter(fm, "content\n")
        assert "---\n" in result
        assert "layout: docs\n" in result

    def test_multiline_yaml_free_output(self):
        """No line should be a bare YAML continuation (2-space indent + word)."""
        import re
        desc = "Long " * 20 + "end"  # 105 chars
        fm = {"description": desc, "layout": "blog"}
        result = write_frontmatter(fm, "")
        # Bare YAML continuation lines look like '  word' at start of line inside frontmatter
        # Check no lines match this pattern within the --- ... --- block
        fm_match = re.match(r"^---\n(.*?)\n---", result, re.DOTALL)
        if fm_match:
            fm_content = fm_match.group(1)
            continuation_lines = [
                l for l in fm_content.splitlines()
                if re.match(r"^  \w", l) and not l.strip().startswith("-")
                and ":" not in l
            ]
            assert not continuation_lines, (
                f"Found YAML continuation lines: {continuation_lines}"
            )
