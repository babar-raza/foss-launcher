"""Agent 43: KB How-To Contract tests.

Validates the Spec v1.1 how-to article heading order, not-evidenced fallback,
format evidence injection, and code fence normalization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def product_facts_minimal() -> Dict[str, Any]:
    return {
        "product_name": "Aspose.3D FOSS for Python",
        "claims": [],
        "claim_groups": {},
        "supported_formats": [],
    }


@pytest.fixture
def product_facts_with_formats() -> Dict[str, Any]:
    return {
        "product_name": "Aspose.3D FOSS for Python",
        "claims": [],
        "claim_groups": {
            "conversion_pairs": [
                {"source": "OBJ", "target": "GLTF"},
            ],
        },
        "supported_formats": [
            {"format": "OBJ", "direction": "both"},
            {"format": "FBX", "direction": "import"},
            {"format": "STL", "direction": "both"},
            {"format": "GLTF", "direction": "unknown"},
        ],
    }


@pytest.fixture
def howto_page() -> Dict[str, Any]:
    return {
        "slug": "how-to-open-a-file",
        "title": "How to Open a File",
        "page_role": "howto_article",
        "section": "kb",
        "not_evidenced_hint": True,
        "required_claim_ids": [],
        "content_strategy": {},
    }


@pytest.fixture
def convert_page_no_evidence() -> Dict[str, Any]:
    return {
        "slug": "how-to-convert-formats",
        "title": "How to Convert Formats",
        "page_role": "howto_article",
        "section": "kb",
        "not_evidenced_hint": True,
        "required_claim_ids": [],
        "content_strategy": {
            "is_conversion_howto": True,
            "supported_formats": [],
            "conversion_pairs": [],
        },
    }


@pytest.fixture
def convert_page_with_evidence() -> Dict[str, Any]:
    return {
        "slug": "how-to-convert-formats",
        "title": "How to Convert Formats",
        "page_role": "howto_article",
        "section": "kb",
        "not_evidenced_hint": False,
        "required_claim_ids": ["abc123"],
        "content_strategy": {
            "is_conversion_howto": True,
            "supported_formats": [
                {"format": "OBJ", "direction": "both"},
                {"format": "FBX", "direction": "import"},
            ],
            "conversion_pairs": [
                {"source": "OBJ", "target": "GLTF"},
            ],
        },
    }


@pytest.fixture
def snippet_catalog_empty() -> Dict[str, Any]:
    return {"snippets": []}


# ---------------------------------------------------------------------------
# Not-evidenced fallback tests
# ---------------------------------------------------------------------------

_REQUIRED_HEADINGS = [
    "## Goal",
    "## When You'd Use This",
    "## Prerequisites",
    "## Steps",
    "Code Example",
    "## Common Mistakes",
    "## See Also",
]


class TestNotEvidencedHowto:
    """Tests for _build_not_evidenced_howto()."""

    def test_not_evidenced_has_all_headings(self, howto_page, product_facts_minimal):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_not_evidenced_howto,
        )

        content = _build_not_evidenced_howto(howto_page, product_facts_minimal)
        for heading in _REQUIRED_HEADINGS:
            assert heading in content, f"Missing heading: {heading}"

    def test_not_evidenced_code_fence_is_comments_only(self, howto_page, product_facts_minimal):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_not_evidenced_howto,
        )

        content = _build_not_evidenced_howto(howto_page, product_facts_minimal)
        # Extract code between fences
        fence_match = re.search(r"```python\n(.*?)```", content, re.DOTALL)
        assert fence_match, "Expected a python code fence"
        code_lines = fence_match.group(1).strip().split("\n")
        for line in code_lines:
            stripped = line.strip()
            if stripped:
                assert stripped.startswith("#"), f"Non-comment line in not-evidenced code: {stripped}"

    def test_not_evidenced_has_no_example_message(self, howto_page, product_facts_minimal):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_not_evidenced_howto,
        )

        content = _build_not_evidenced_howto(howto_page, product_facts_minimal)
        assert "No working example was found in this repository" in content

    def test_not_evidenced_conversion_no_formats(
        self, convert_page_no_evidence, product_facts_minimal
    ):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_not_evidenced_howto,
        )

        content = _build_not_evidenced_howto(convert_page_no_evidence, product_facts_minimal)
        assert "No format conversion evidence was found in this repository" in content


# ---------------------------------------------------------------------------
# Deterministic fallback tests
# ---------------------------------------------------------------------------


class TestDeterministicHowto:
    """Tests for _build_deterministic_howto_article()."""

    def test_deterministic_headings_match_contract(
        self, howto_page, product_facts_minimal, snippet_catalog_empty
    ):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_deterministic_howto_article,
        )

        content = _build_deterministic_howto_article(
            howto_page, product_facts_minimal, snippet_catalog_empty
        )
        assert "## Goal" in content
        assert "## Steps" in content
        assert "Code Example" in content
        assert "## See Also" in content
        # Old headings must NOT appear
        assert "## Step-by-Step Guide" not in content
        assert "## Related Resources" not in content

    def test_deterministic_conversion_with_formats(
        self, convert_page_with_evidence, product_facts_with_formats, snippet_catalog_empty
    ):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_deterministic_howto_article,
        )

        content = _build_deterministic_howto_article(
            convert_page_with_evidence, product_facts_with_formats, snippet_catalog_empty
        )
        # Must list evidenced formats
        assert "OBJ" in content
        assert "FBX" in content

    def test_deterministic_conversion_with_pairs(
        self, convert_page_with_evidence, product_facts_with_formats, snippet_catalog_empty
    ):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_deterministic_howto_article,
        )

        content = _build_deterministic_howto_article(
            convert_page_with_evidence, product_facts_with_formats, snippet_catalog_empty
        )
        # Code fence should reference the evidenced conversion pair
        assert "OBJ" in content
        assert "GLTF" in content

    def test_deterministic_conversion_no_evidence(
        self, convert_page_no_evidence, product_facts_minimal, snippet_catalog_empty
    ):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_deterministic_howto_article,
        )

        content = _build_deterministic_howto_article(
            convert_page_no_evidence, product_facts_minimal, snippet_catalog_empty
        )
        assert "No format conversion evidence was found in this repository" in content
        # Should still have a code fence (pseudo-code)
        assert "```python" in content


# ---------------------------------------------------------------------------
# Format evidence text builder tests
# ---------------------------------------------------------------------------


class TestFormatEvidenceTextBuilder:
    """Tests for _build_format_evidence_text()."""

    def test_format_evidence_text_builder_empty(self):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_format_evidence_text,
        )

        result = _build_format_evidence_text({})
        assert result == ""

    def test_format_evidence_text_builder_non_convert(self):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_format_evidence_text,
        )

        page = {"content_strategy": {"is_conversion_howto": False}}
        result = _build_format_evidence_text(page)
        assert result == ""

    def test_format_evidence_text_builder_with_data(self):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_format_evidence_text,
        )

        page = {
            "content_strategy": {
                "is_conversion_howto": True,
                "supported_formats": [
                    {"format": "OBJ", "direction": "both"},
                    {"format": "FBX", "direction": "import"},
                ],
                "conversion_pairs": [
                    {"source": "OBJ", "target": "GLTF"},
                ],
            }
        }
        result = _build_format_evidence_text(page)
        assert "OBJ (both)" in result
        assert "FBX (import)" in result
        assert "OBJ" in result and "GLTF" in result


# ---------------------------------------------------------------------------
# Code fence normalizer tests
# ---------------------------------------------------------------------------


class TestNormalizeHowtoCodeFences:
    """Tests for _normalize_howto_code_fences()."""

    def test_normalize_empty_code_heading(self):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _normalize_howto_code_fences,
        )

        content = "## Goal\n\nSome text.\n\n## Product Code Example\n\n## Common Mistakes\n"
        page = {"page_role": "howto_article", "title": "Open a File"}
        result = _normalize_howto_code_fences(content, page)
        assert "```python" in result
        assert "# Example code for" in result

    def test_normalize_preserves_existing_fence(self):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _normalize_howto_code_fences,
        )

        content = "## Product Code Example\n\n```python\nprint('hello')\n```\n\n## See Also\n"
        page = {"page_role": "howto_article"}
        result = _normalize_howto_code_fences(content, page)
        assert result.count("```python") == 1
        assert "print('hello')" in result

    def test_normalize_skips_non_howto(self):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _normalize_howto_code_fences,
        )

        content = "## Code Example\n\n## Next\n"
        page = {"page_role": "tutorial"}
        result = _normalize_howto_code_fences(content, page)
        assert result == content

    def test_normalize_h3_empty_code_heading(self):
        """Agent 43: LLM may emit H3 headings — normalizer must handle both H2 and H3."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _normalize_howto_code_fences,
        )

        content = "### Goal\n\nText.\n\n### Code Example\n\n### Common Mistakes\n"
        page = {"page_role": "howto_article", "title": "Open a File"}
        result = _normalize_howto_code_fences(content, page)
        assert "```python" in result
        assert "# Example code for" in result

    def test_placeholder_fence_has_pass_statement(self):
        """Placeholder fence must have a `pass` statement to survive collapse_duplicate_fence_openings."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _normalize_howto_code_fences,
        )

        content = "## Code Example\n\n## See Also\n"
        page = {"page_role": "howto_article", "title": "Open a File"}
        result = _normalize_howto_code_fences(content, page)
        assert "pass" in result, "Placeholder fence must contain 'pass' to survive sanitizer"

    def test_placeholder_fence_survives_sanitizer_pipeline(self):
        """Regression: collapse_duplicate_fence_openings was stripping comment-only fences."""
        from src.launch.workers._shared.content_sanitizer import (
            collapse_duplicate_fence_openings,
        )

        content = (
            "## Code Example\n\n"
            "```python\n"
            "# Example code for open a file\n"
            "# See documentation for a complete working example.\n"
            "pass\n"
            "```\n\n"
            "## See Also\n"
        )
        result = collapse_duplicate_fence_openings(content)
        assert "```python" in result, "Fence must survive collapse_duplicate_fence_openings"
        assert "pass" in result, "pass statement must survive"


# ---------------------------------------------------------------------------
# Section templates + W4 default headings contract tests
# ---------------------------------------------------------------------------


class TestHowtoContractAlignment:
    """Tests verifying section_templates.yaml and W4 headings match Agent 43 contract."""

    def test_section_templates_yaml_howto_updated(self):
        yaml_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "launch"
            / "workers"
            / "w5_section_writer"
            / "section_templates.yaml"
        )
        with open(yaml_path, encoding="utf-8") as f:
            templates = yaml.safe_load(f)
        howto = templates["howto_article"]
        assert sorted(howto["required_sections"]) == sorted([
            "goal", "when_to_use", "prerequisites", "steps", "code_example", "see_also",
        ])
        assert "common_mistakes" in howto.get("optional_sections", [])

    def test_default_headings_for_role_howto(self):
        from src.launch.workers.w4_ia_planner.worker import _default_headings_for_role

        headings = _default_headings_for_role("howto_article", {})
        assert "Goal" in headings
        assert "Steps" in headings
        assert "Code Example" in headings
        assert "See Also" in headings
        # Old headings must NOT appear
        assert "Step-by-Step Guide" not in headings
        assert "Related Links" not in headings
