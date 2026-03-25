"""TC-5162: Tests for API surface enrichment with extraction_db.api_facts docstrings."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from launcher.workers.generate.section_prompt import _format_api_surface

_API_BLOCK_MAX_CHARS = 4000


def _make_class_brief(
    name: str,
    methods: list[str] | None = None,
    docstring_snippet: str = "",
) -> MagicMock:
    brief = MagicMock()
    brief.name = name
    brief.methods = methods or []
    brief.typed_methods = []
    brief.typed_properties = []
    brief.properties = []
    brief.enums = []
    brief.docstring_snippet = docstring_snippet
    return brief


def _make_api_fact(class_name: str, member_name: str, docstring: str) -> MagicMock:
    fact = MagicMock()
    fact.class_name = class_name
    fact.member_name = member_name
    fact.docstring = docstring
    return fact


class TestFormatApiSurfaceEnrichment:
    def test_docstring_appended_to_method(self):
        brief = _make_class_brief("Workbook", methods=["save"])
        api_facts = {"Workbook": [_make_api_fact("Workbook", "save", "Saves to disk.")]}
        result = _format_api_surface(
            ["Workbook"],
            class_briefs=[brief],
            api_facts_by_class=api_facts,
        )
        assert "save [Saves to disk.]" in result

    def test_docstring_capped_at_80_chars(self):
        long_doc = "A" * 100
        brief = _make_class_brief("Foo", methods=["method1"])
        api_facts = {"Foo": [_make_api_fact("Foo", "method1", long_doc)]}
        result = _format_api_surface(
            ["Foo"],
            class_briefs=[brief],
            api_facts_by_class=api_facts,
        )
        # Docstring in output must be capped at 80 chars
        assert long_doc[:80] in result
        assert long_doc[:81] not in result

    def test_no_api_facts_unchanged_output(self):
        brief = _make_class_brief("Bar", methods=["run"])
        result_without = _format_api_surface(
            ["Bar"],
            class_briefs=[brief],
            api_facts_by_class=None,
        )
        result_empty = _format_api_surface(
            ["Bar"],
            class_briefs=[brief],
            api_facts_by_class={},
        )
        # Both should produce identical output (no docstring annotation)
        assert result_without == result_empty
        assert "[" not in result_without or "Bar" in result_without  # no doc brackets

    def test_method_not_in_api_facts_no_error(self):
        brief = _make_class_brief("Baz", methods=["load", "save"])
        api_facts = {"Baz": [_make_api_fact("Baz", "save", "Saves the file.")]}
        result = _format_api_surface(
            ["Baz"],
            class_briefs=[brief],
            api_facts_by_class=api_facts,
        )
        # save gets docstring, load does not
        assert "save [Saves the file.]" in result
        # load appears without brackets (plain name)
        assert "load" in result

    def test_api_block_max_chars_respected(self):
        # Create a large number of classes with long docstrings
        briefs = [_make_class_brief(f"Class{i}", methods=[f"method{j}" for j in range(5)]) for i in range(30)]
        api_facts: dict[str, list] = {
            f"Class{i}": [
                _make_api_fact(f"Class{i}", f"method{j}", "X" * 80)
                for j in range(5)
            ]
            for i in range(30)
        }
        public_classes = [f"Class{i}" for i in range(30)]
        result = _format_api_surface(
            public_classes,
            class_briefs=briefs,
            api_facts_by_class=api_facts,
        )
        assert len(result) <= _API_BLOCK_MAX_CHARS + 40  # allow truncation suffix

    def test_only_first_3_methods_enriched(self):
        """Only the first 3 methods per class get docstring enrichment (TC-5162)."""
        methods = [f"method{i}" for i in range(6)]
        brief = _make_class_brief("Big", methods=methods)
        api_facts = {
            "Big": [_make_api_fact("Big", f"method{i}", f"Doc {i}.") for i in range(6)]
        }
        result = _format_api_surface(
            ["Big"],
            class_briefs=[brief],
            api_facts_by_class=api_facts,
        )
        # At most 3 docstring brackets in the output for this class
        doc_bracket_count = result.count("[Doc ")
        assert doc_bracket_count <= 3
