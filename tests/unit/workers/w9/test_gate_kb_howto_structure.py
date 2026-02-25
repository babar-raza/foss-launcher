"""Tests for gate_kb_howto_structure (TC-2481b: dynamic slug discovery).

Validates KB how-to draft file existence, heading order, and FQ-1 absence.
Uses dynamic slug discovery from page_plan.json instead of hardcoded frozenset.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_kb_howto_structure import (
    execute_gate,
    _extract_h2_headings,
    _check_heading_order,
    _discover_howto_slugs,
    _HEADING_ORDER,
)

_FQ1_WARNING = "<!-- WARNING: fragmented-code detected (FQ-1) -->"

# Test slugs used across test cases
_TEST_SLUGS = [
    "how-to-load-3d-models-python",
    "how-to-save-3d-models-python",
    "how-to-convert-fbx-to-obj",
    "how-to-fix-common-3d-models-errors",
    "how-to-optimize-3d-models-performance",
]


@pytest.fixture
def tmp_run(tmp_path):
    (tmp_path / "artifacts").mkdir()
    return tmp_path


def _write_page_plan(run_dir: Path, slugs: list) -> None:
    """Write a page_plan.json with given KB how-to slugs."""
    pages = [
        {"section": "kb", "page_role": "howto_article", "slug": slug}
        for slug in slugs
    ]
    (run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps({"pages": pages}), encoding="utf-8"
    )


def _good_howto_content(product_name: str = "TestProduct") -> str:
    """Return well-structured KB how-to markdown content."""
    return f"""---
title: "How To Guide"
---

## Goal

This guide explains how to do something using {product_name}.

## When You'd Use This

Use this when you need to do something.

## Prerequisites

- {product_name} installed.
- Python 3.8+.

## Steps

1. Import the library.
2. Load data.
3. Process the data.

## {product_name} Code Example

```python
import test_product
data = test_product.load("input.dat")
result = test_product.process(data)
test_product.save(result, "output.dat")
```

## Common Mistakes

- Forgetting to install the library.

## See Also

- [Getting Started](../getting-started/)
- [FAQ](../faq/)
"""


def _write_kb_drafts(run_dir: Path, slugs=None, content_fn=None):
    """Write draft files for given slugs (defaults to _TEST_SLUGS)."""
    kb_dir = run_dir / "drafts" / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    if slugs is None:
        slugs = _TEST_SLUGS
    for slug in slugs:
        content = content_fn(slug) if content_fn else _good_howto_content()
        (kb_dir / f"{slug}.md").write_text(content, encoding="utf-8")


# ── Skips ────────────────────────────────────────────────────────────────────

class TestGateKbHowtoStructureSkips:
    def test_no_drafts_dir_skips(self, tmp_run):
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_no_page_plan_skips(self, tmp_run):
        """When drafts/kb/ exists but no page_plan.json, graceful skip."""
        kb_dir = tmp_run / "drafts" / "kb"
        kb_dir.mkdir(parents=True)
        (kb_dir / "how-to-test.md").write_text("# Test", encoding="utf-8")
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []


# ── Pass ─────────────────────────────────────────────────────────────────────

class TestGateKbHowtoStructurePass:
    def test_all_drafts_with_correct_headings(self, tmp_run):
        _write_page_plan(tmp_run, _TEST_SLUGS)
        _write_kb_drafts(tmp_run)
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert all(i["severity"] != "error" for i in issues)

    def test_extra_draft_files_allowed(self, tmp_run):
        _write_page_plan(tmp_run, _TEST_SLUGS)
        _write_kb_drafts(tmp_run)
        kb_dir = tmp_run / "drafts" / "kb"
        (kb_dir / "how-to-merge.md").write_text(
            _good_howto_content(), encoding="utf-8"
        )
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True


# ── Fail ─────────────────────────────────────────────────────────────────────

class TestGateKbHowtoStructureFail:
    def test_missing_draft_file_errors(self, tmp_run):
        """Write page_plan with 5 slugs but only 3 draft files -> error."""
        _write_page_plan(tmp_run, _TEST_SLUGS)
        _write_kb_drafts(tmp_run, slugs=_TEST_SLUGS[:3])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False
        assert any("DRAFT_MISSING" in i["error_code"] for i in issues)

    def test_wrong_heading_order_errors(self, tmp_run):
        bad_content = """---
title: "Bad Headings"
---

## See Also

- link

## Goal

Explanation.

## Steps

1. Step one.

## Prerequisites

- something

## TestProduct Code Example

```python
pass
```
"""
        _write_page_plan(tmp_run, _TEST_SLUGS)
        _write_kb_drafts(tmp_run, content_fn=lambda _: bad_content)
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False
        assert any("HEADING_ORDER" in i["error_code"] for i in issues)

    def test_empty_draft_file_fails_heading_check(self, tmp_run):
        _write_page_plan(tmp_run, _TEST_SLUGS)
        _write_kb_drafts(tmp_run, content_fn=lambda _: "")
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False
        assert any("HEADING_ORDER" in i["error_code"] for i in issues)


# ── Warn (FQ-1) ─────────────────────────────────────────────────────────────

class TestGateKbHowtoStructureWarn:
    def test_fq1_warning_produces_warn_not_error(self, tmp_run):
        content_with_fq1 = _good_howto_content() + f"\n{_FQ1_WARNING}\n"
        _write_page_plan(tmp_run, _TEST_SLUGS)
        _write_kb_drafts(tmp_run, content_fn=lambda _: content_with_fq1)
        ok, issues = execute_gate(tmp_run, "local")
        # FQ-1 is warn-only -> gate still passes
        assert ok is True
        fq1_issues = [i for i in issues if "FQ1" in i["error_code"]]
        assert len(fq1_issues) > 0
        assert all(i["severity"] == "warn" for i in fq1_issues)


# ── Dynamic Slug Discovery ──────────────────────────────────────────────────

class TestDiscoverHowtoSlugs:
    def test_discovers_slugs_from_page_plan(self, tmp_run):
        _write_page_plan(tmp_run, ["how-to-load-3d-models-python", "how-to-save-files"])
        slugs = _discover_howto_slugs(tmp_run)
        assert slugs == {"how-to-load-3d-models-python", "how-to-save-files"}

    def test_ignores_non_howto_pages(self, tmp_run):
        pages = [
            {"section": "kb", "page_role": "howto_article", "slug": "how-to-load"},
            {"section": "kb", "page_role": "faq", "slug": "faq-page"},
            {"section": "docs", "page_role": "howto_article", "slug": "docs-howto"},
        ]
        (tmp_run / "artifacts" / "page_plan.json").write_text(
            json.dumps({"pages": pages}), encoding="utf-8"
        )
        slugs = _discover_howto_slugs(tmp_run)
        assert slugs == {"how-to-load"}

    def test_empty_when_no_page_plan(self, tmp_run):
        slugs = _discover_howto_slugs(tmp_run)
        assert slugs == set()


# ── Helpers ──────────────────────────────────────────────────────────────────

class TestHelpers:
    def test_extract_h2_headings(self):
        content = "## Goal\ntext\n## Steps\nmore\n### Substep\n## See Also\n"
        headings = _extract_h2_headings(content)
        assert headings == ["goal", "steps", "substep", "see also"]

    def test_extract_h2_matches_h3_too(self):
        """H3 headings are included since W5 may emit H3 for sections."""
        content = "### Also Section\n## Real H2\n"
        headings = _extract_h2_headings(content)
        assert headings == ["also section", "real h2"]

    def test_extract_h2_ignores_h4(self):
        content = "#### Not section\n## Real H2\n"
        headings = _extract_h2_headings(content)
        assert headings == ["real h2"]

    def test_heading_order_correct(self):
        headings = [
            "goal",
            "when you'd use this",
            "prerequisites",
            "steps",
            "testproduct code example",
            "common mistakes",
            "see also",
        ]
        violations = _check_heading_order(headings, "test-slug")
        assert violations == []

    def test_heading_order_reversed(self):
        headings = ["see also", "steps", "goal"]
        violations = _check_heading_order(headings, "test-slug")
        assert len(violations) > 0

    def test_heading_order_missing_heading(self):
        headings = ["goal", "steps", "see also"]
        violations = _check_heading_order(headings, "test-slug")
        assert any("prerequisites" in v for v in violations)
        assert any("code example" in v for v in violations)

    def test_code_example_substring_match_product_name(self):
        """Product-prefixed 'X Code Example' matches 'code example' via substring."""
        headings = [
            "aspose.3d foss for python goal",
            "prerequisites",
            "aspose.3d foss for python steps",
            "aspose.3d foss for python code example",
            "see also",
        ]
        violations = _check_heading_order(headings, "test-slug")
        assert violations == []

    def test_code_example_substring_match(self):
        """'testproduct code example' should match 'code example' in order check."""
        headings = [
            "goal",
            "prerequisites",
            "steps",
            "testproduct code example",
            "see also",
        ]
        violations = _check_heading_order(headings, "test-slug")
        assert violations == []
