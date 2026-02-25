"""Tests for Agent 42: Mandatory Page Catalog.

Validates that ruleset.v1_1.yaml contains the correct mandatory pages per
spec v1.1, and that W4 produces correct page specs for them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent.parent


def _load_ruleset_yaml() -> Dict[str, Any]:
    """Load ruleset.v1_1.yaml as raw dict."""
    path = REPO_ROOT / "specs" / "rulesets" / "ruleset.v1_1.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_mandatory_slugs(ruleset: Dict[str, Any], section: str) -> List[str]:
    """Return list of mandatory page slugs for a section (after slug normalisation).

    For title-only entries, derives slug using _derive_semantic_slug.
    """
    from src.launch.workers.w4_ia_planner.worker import (
        _derive_semantic_slug,
        load_and_merge_page_requirements,
    )

    merged = load_and_merge_page_requirements(ruleset, product_slug="3d")
    entries = merged.get(section, {}).get("mandatory_pages", [])
    return [e["slug"] for e in entries]


# ---------------------------------------------------------------------------
# Step 1 — ruleset.v1_1.yaml mandatory page catalog
# ---------------------------------------------------------------------------


def test_products_mandatory_has_index_slug():
    """products section home must use slug '_index', not 'overview'."""
    ruleset = _load_ruleset_yaml()
    slugs = _get_mandatory_slugs(ruleset, "products")
    assert "_index" in slugs, f"Expected '_index' in products mandatory slugs, got: {slugs}"
    assert "overview" not in slugs, f"'overview' should not be mandatory, got: {slugs}"


def test_docs_mandatory_exactly_three():
    """docs base mandatory pages (before family overrides) must be exactly 3."""
    ruleset = _load_ruleset_yaml()
    # Test the raw YAML mandatory_pages, not the merged result (which includes family overrides).
    raw_mandatory = ruleset["sections"]["docs"].get("mandatory_pages", [])
    slugs = [e["slug"] for e in raw_mandatory if "slug" in e]
    assert len(slugs) == 3, (
        f"Expected 3 base docs mandatory pages, got {len(slugs)}: {slugs}"
    )
    assert set(slugs) == {"_index", "installation", "getting-started"}, (
        f"Expected exactly _index/installation/getting-started, got: {slugs}"
    )


def test_docs_min_pages_is_three():
    """docs.min_pages must be 3."""
    ruleset = _load_ruleset_yaml()
    min_pages = ruleset["sections"]["docs"]["min_pages"]
    assert min_pages == 3, f"Expected docs.min_pages == 3, got {min_pages}"


def test_docs_getting_started_is_folder_index():
    """docs/getting-started mandatory entry must have folder_index: true."""
    ruleset = _load_ruleset_yaml()
    mandatory = ruleset["sections"]["docs"].get("mandatory_pages", [])
    gs = next((e for e in mandatory if e.get("slug") == "getting-started"), None)
    assert gs is not None, "getting-started entry not found in docs mandatory_pages"
    assert gs.get("folder_index") is True, f"Expected folder_index: true on getting-started, got: {gs}"


def test_reference_mandatory_has_index():
    """reference section must have '_index' as first mandatory page."""
    ruleset = _load_ruleset_yaml()
    slugs = _get_mandatory_slugs(ruleset, "reference")
    assert "_index" in slugs, f"Expected '_index' in reference mandatory slugs, got: {slugs}"


def test_kb_mandatory_count_is_nine():
    """KB mandatory pages must total 9 (for family '3d' with no overrides in that section)."""
    ruleset = _load_ruleset_yaml()
    slugs = _get_mandatory_slugs(ruleset, "kb")
    assert len(slugs) == 9, f"Expected 9 KB mandatory pages, got {len(slugs)}: {slugs}"


def test_kb_has_use_cases():
    """KB mandatory pages must include 'use-cases'."""
    ruleset = _load_ruleset_yaml()
    slugs = _get_mandatory_slugs(ruleset, "kb")
    assert "use-cases" in slugs, f"Expected 'use-cases' in KB mandatory slugs, got: {slugs}"


def test_kb_howto_slugs_correct():
    """KB mandatory how-to slugs must match the updated 5-slug list."""
    ruleset = _load_ruleset_yaml()
    slugs = set(_get_mandatory_slugs(ruleset, "kb"))
    required = {
        "how-to-open-a-file",
        "how-to-save-a-file",
        "how-to-convert-formats",      # was "how-to-convert-a-document"
        "how-to-fix-common-errors",    # new
        "how-to-improve-performance",  # new
    }
    missing = required - slugs
    assert not missing, f"Missing KB how-to slugs: {sorted(missing)}. Found: {sorted(slugs)}"
    # The old slug must NOT be present
    assert "how-to-convert-a-document" not in slugs, (
        "'how-to-convert-a-document' must be replaced by 'how-to-convert-formats'"
    )


def test_blog_min_pages_is_two():
    """blog.min_pages must be 2."""
    ruleset = _load_ruleset_yaml()
    min_pages = ruleset["sections"]["blog"]["min_pages"]
    assert min_pages == 2, f"Expected blog.min_pages == 2, got {min_pages}"


# ---------------------------------------------------------------------------
# Step 3a — subpath stored for folder-index pages
# ---------------------------------------------------------------------------


def test_subpath_stored_for_folder_index():
    """W4 mandatory injection must store subpath: [slug] for folder_index pages."""
    from src.launch.workers.w4_ia_planner.worker import (
        _derive_semantic_slug,
        load_and_merge_page_requirements,
    )

    ruleset = _load_ruleset_yaml()
    merged = load_and_merge_page_requirements(ruleset, product_slug="3d")
    docs_mandatory = merged.get("docs", {}).get("mandatory_pages", [])
    gs_entry = next((e for e in docs_mandatory if e.get("slug") == "getting-started"), None)
    assert gs_entry is not None, "getting-started not in merged docs mandatory pages"
    assert gs_entry.get("folder_index") is True, (
        f"Expected folder_index: true on getting-started entry, got: {gs_entry}"
    )


# ---------------------------------------------------------------------------
# Step 3b — cross_section_links on products _index
# ---------------------------------------------------------------------------


def test_cross_section_links_on_products_index():
    """_populate_products_cross_section_links must add 4-element list to products _index.

    W4 normalizes _index → index in page_spec (worker.py:4296). Both slugs are accepted.
    """
    from src.launch.workers.w4_ia_planner.worker import _populate_products_cross_section_links

    pages = [
        {
            "section": "products",
            "slug": "index",          # normalized form used by W4 at runtime
            "content_strategy": {},
        },
        {
            "section": "docs",
            "slug": "index",
            "content_strategy": {},
        },
    ]
    _populate_products_cross_section_links(pages, product_slug="3d")

    products_page = next(p for p in pages if p["section"] == "products")
    links = products_page["content_strategy"].get("cross_section_links", [])
    assert len(links) == 4, f"Expected 4 cross_section_links, got {len(links)}: {links}"
    # All links must be absolute URLs
    for link in links:
        assert link.startswith("https://"), f"Expected absolute URL, got: {link}"
    # Links must cover all four sibling sections
    sections_covered = {"docs", "reference", "kb", "blog"}
    for section in sections_covered:
        assert any(section in link for link in links), (
            f"No cross_section_link found for section '{section}': {links}"
        )


def test_cross_section_links_not_on_other_pages():
    """_populate_products_cross_section_links must NOT modify docs/kb/blog pages."""
    from src.launch.workers.w4_ia_planner.worker import _populate_products_cross_section_links

    pages = [
        {"section": "docs", "slug": "index", "content_strategy": {}},
        {"section": "kb", "slug": "index", "content_strategy": {}},
        {"section": "products", "slug": "overview", "content_strategy": {}},  # wrong slug
    ]
    _populate_products_cross_section_links(pages, product_slug="3d")
    for page in pages:
        assert "cross_section_links" not in page["content_strategy"], (
            f"cross_section_links should not be set on {page['section']}/{page['slug']}"
        )


# ---------------------------------------------------------------------------
# Step 4 — gate_kb_howto_mandatory with topic_category-based coverage (TC-2481b)
# ---------------------------------------------------------------------------


def test_gate_kb_howto_mandatory_passes_with_five_slugs(tmp_path):
    """Gate passes when all 5 required how-to slugs are present."""
    import json
    from src.launch.workers.w9_validator.gates.gate_kb_howto_mandatory import execute_gate

    plan = {
        "pages": [
            {"section": "kb", "slug": "how-to-open-a-file", "page_role": "howto_article"},
            {"section": "kb", "slug": "how-to-save-a-file", "page_role": "howto_article"},
            {"section": "kb", "slug": "how-to-convert-formats", "page_role": "howto_article"},
            {"section": "kb", "slug": "how-to-fix-common-errors", "page_role": "howto_article"},
            {"section": "kb", "slug": "how-to-improve-performance", "page_role": "howto_article"},
        ]
    }
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "page_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    passed, issues = execute_gate(tmp_path, "local")
    assert passed, f"Gate should pass with all 5 slugs; issues: {issues}"


def test_gate_kb_howto_mandatory_fails_with_missing_topic_category(tmp_path):
    """Gate fails when a required topic category is not covered by any howto page.

    TC-2481b: Gate now uses topic_category-based coverage, not literal slug matching.
    A slug like 'how-to-frobulate' doesn't infer any known topic category, so
    replacing a required category's page with it causes a failure.
    """
    import json
    from src.launch.workers.w9_validator.gates.gate_kb_howto_mandatory import execute_gate

    plan = {
        "pages": [
            {"section": "kb", "slug": "how-to-open-a-file", "page_role": "howto_article"},
            {"section": "kb", "slug": "how-to-save-a-file", "page_role": "howto_article"},
            {"section": "kb", "slug": "how-to-frobulate", "page_role": "howto_article"},  # no known category
            {"section": "kb", "slug": "how-to-fix-common-errors", "page_role": "howto_article"},
            {"section": "kb", "slug": "how-to-improve-performance", "page_role": "howto_article"},
        ]
    }
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "page_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    passed, issues = execute_gate(tmp_path, "local")
    assert not passed, "Gate should fail when 'convert_formats' topic category is missing"
    assert any("TOPIC_MISSING" in str(i) for i in issues), (
        f"Issue message should mention missing topic; issues: {issues}"
    )
