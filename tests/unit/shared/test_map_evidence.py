"""Tests for evidence mapping citation scoring (capability #4)."""
from __future__ import annotations

import pytest

from launcher.shared.map_evidence import (
    SOURCE_TYPE_WEIGHTS,
    infer_source_type,
    score_citation_quality,
)


class TestInferSourceType:
    def test_readme(self) -> None:
        assert infer_source_type("README.md") == "readme"

    def test_example(self) -> None:
        assert infer_source_type("examples/convert.py") == "example"

    def test_sample(self) -> None:
        assert infer_source_type("samples/demo.py") == "example"

    def test_test(self) -> None:
        assert infer_source_type("tests/test_main.py") == "test"

    def test_changelog(self) -> None:
        assert infer_source_type("CHANGELOG.md") == "changelog"

    def test_api_doc(self) -> None:
        assert infer_source_type("api/reference.md") == "api_doc"

    def test_generic(self) -> None:
        assert infer_source_type("docs/guide.md") == "generic_doc"

    def test_case_insensitive(self) -> None:
        assert infer_source_type("EXAMPLES/Demo.py") == "example"


class TestScoreCitationQuality:
    def test_no_citations(self) -> None:
        assert score_citation_quality([]) == 0.0

    def test_single_readme(self) -> None:
        citations = [{"path": "README.md"}]
        score = score_citation_quality(citations)
        assert score == SOURCE_TYPE_WEIGHTS["readme"]

    def test_explicit_source_type(self) -> None:
        citations = [{"source_type": "api_doc", "path": "whatever.md"}]
        score = score_citation_quality(citations)
        assert score == SOURCE_TYPE_WEIGHTS["api_doc"]

    def test_max_of_multiple(self) -> None:
        citations = [
            {"path": "README.md"},
            {"path": "examples/demo.py"},
            {"path": "docs/guide.md"},
        ]
        score = score_citation_quality(citations)
        assert score == SOURCE_TYPE_WEIGHTS["example"]  # 0.85 is highest

    def test_unknown_source(self) -> None:
        citations = [{"path": "random_file.bin"}]
        score = score_citation_quality(citations)
        assert score == SOURCE_TYPE_WEIGHTS["generic_doc"]

    def test_api_doc_highest(self) -> None:
        citations = [
            {"source_type": "api_doc"},
            {"source_type": "readme"},
            {"source_type": "test"},
        ]
        score = score_citation_quality(citations)
        assert score == SOURCE_TYPE_WEIGHTS["api_doc"]
