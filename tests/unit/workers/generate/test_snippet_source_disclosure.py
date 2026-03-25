"""TC-5165: Tests for snippet source provenance disclosure in _format_snippets()."""
from __future__ import annotations

import pytest

from launcher.workers.generate.section_prompt import _snippet_provenance_line, _format_snippets
from launcher.models.claims import Snippet


def _make_snippet(
    code: str = "obj.save('out.pdf')",
    language: str = "python",
    source_type: str = "extracted",
    source_file: str = "tests/test_core.py",
    claim_ids: list | None = None,
) -> Snippet:
    return Snippet(
        code=code,
        language=language,
        source_type=source_type,
        source_file=source_file,
        claim_ids=claim_ids or [],
    )


class TestSnippetProvenanceLine:
    def test_extracted_snippet_shows_source_file(self):
        s = _make_snippet(source_type="extracted", source_file="tests/test_core.py")
        assert _snippet_provenance_line(s) == "[Extracted from: tests/test_core.py]"

    def test_extracted_deep_path_shows_last_2(self):
        s = _make_snippet(source_type="extracted", source_file="a/b/c/d/test.py")
        assert _snippet_provenance_line(s) == "[Extracted from: d/test.py]"

    def test_generated_snippet_shows_warning(self):
        s = _make_snippet(source_type="generated", source_file="")
        line = _snippet_provenance_line(s)
        assert line.startswith("[Generated")
        assert "illustrative" in line

    def test_synthetic_snippet_shows_warning(self):
        s = _make_snippet(source_type="synthetic", source_file="")
        line = _snippet_provenance_line(s)
        assert line.startswith("[Generated")

    def test_empty_source_type_shows_warning(self):
        class _Duck:
            source_type = ""
            source_file = ""
        line = _snippet_provenance_line(_Duck())
        assert line.startswith("[Generated")

    def test_unknown_source_type_shows_source_label(self):
        class _Duck:
            source_type = "custom_type"
            source_file = ""
        assert _snippet_provenance_line(_Duck()) == "[Source: custom_type]"


class TestFormatSnippets:
    def test_provenance_line_precedes_fence(self):
        s = _make_snippet(source_type="extracted", source_file="src/lib.py")
        result = _format_snippets([s])
        lines = result.split("\n")
        assert lines[0] == "[Extracted from: src/lib.py]"
        assert lines[1].startswith("```")

    def test_generated_provenance_in_output(self):
        s = _make_snippet(source_type="generated", source_file="")
        result = _format_snippets([s])
        assert "[Generated" in result
        assert "```" in result

    def test_empty_list_returns_empty_string(self):
        assert _format_snippets([]) == ""
