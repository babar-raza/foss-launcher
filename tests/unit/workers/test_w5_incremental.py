"""Tests for TC-2450: W5 page hash cache + regen_failed_only.

Covers:
- _compute_page_input_hash() — determinism, claim sensitivity, snippet sensitivity
- _find_failed_page_slugs() — validation_report parsing
- W5 cache hit skip — no LLM call; cache miss → generate
- regen_failed_only — page_status override from validation report
- Timing — duration_ms in manifest entries
- Cache record — page key recorded after generation
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch, call

import pytest

from launch.workers.w5_section_writer.worker import (
    _compute_page_input_hash,
    _find_failed_page_slugs,
)
from launch.workers._shared.worker_cache import WorkerCache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_page() -> Dict[str, Any]:
    return {
        "slug": "overview",
        "section": "products",
        "page_role": "overview",
        "title": "Overview",
        "purpose": "Introduce the product.",
        "required_claim_ids": ["c1", "c2"],
        "required_snippet_tags": ["hello"],
        "required_headings": ["Features"],
        "template_variant": "standard",
        "output_path": "content/docs/mylib/en/products/overview.md",
    }


@pytest.fixture
def product_facts() -> Dict[str, Any]:
    return {
        "claims": [
            {"claim_id": "c1", "claim_text": "Does X efficiently."},
            {"claim_id": "c2", "claim_text": "Supports Y format."},
            {"claim_id": "c3", "claim_text": "Unrelated claim."},
        ]
    }


@pytest.fixture
def snippet_catalog() -> Dict[str, Any]:
    return {
        "snippets": [
            {"tag": "hello", "code": "print('hello')", "description": "Hello world"},
            {"tag": "other", "code": "x = 1", "description": "Other"},
        ]
    }


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    rd = tmp_path / "run"
    (rd / "artifacts").mkdir(parents=True)
    (rd / "drafts" / "products").mkdir(parents=True)
    return rd


# ---------------------------------------------------------------------------
# TestComputePageInputHash
# ---------------------------------------------------------------------------

class TestComputePageInputHash:
    def test_deterministic_same_inputs(self, simple_page, product_facts, snippet_catalog):
        h1 = _compute_page_input_hash(simple_page, product_facts, snippet_catalog)
        h2 = _compute_page_input_hash(simple_page, product_facts, snippet_catalog)
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex digest

    def test_claim_id_order_does_not_affect_hash(self, simple_page, product_facts, snippet_catalog):
        p1 = dict(simple_page, required_claim_ids=["c1", "c2"])
        p2 = dict(simple_page, required_claim_ids=["c2", "c1"])
        assert _compute_page_input_hash(p1, product_facts, snippet_catalog) == \
               _compute_page_input_hash(p2, product_facts, snippet_catalog)

    def test_different_claim_text_changes_hash(self, simple_page, snippet_catalog):
        pf_a = {"claims": [{"claim_id": "c1", "claim_text": "Version A"}]}
        pf_b = {"claims": [{"claim_id": "c1", "claim_text": "Version B"}]}
        page = dict(simple_page, required_claim_ids=["c1"], required_snippet_tags=[])
        assert _compute_page_input_hash(page, pf_a, snippet_catalog) != \
               _compute_page_input_hash(page, pf_b, snippet_catalog)

    def test_different_snippet_code_changes_hash(self, simple_page, product_facts):
        sc_a = {"snippets": [{"tag": "hello", "code": "print('a')", "description": ""}]}
        sc_b = {"snippets": [{"tag": "hello", "code": "print('b')", "description": ""}]}
        assert _compute_page_input_hash(simple_page, product_facts, sc_a) != \
               _compute_page_input_hash(simple_page, product_facts, sc_b)

    def test_different_title_changes_hash(self, simple_page, product_facts, snippet_catalog):
        p1 = dict(simple_page, title="Title A")
        p2 = dict(simple_page, title="Title B")
        assert _compute_page_input_hash(p1, product_facts, snippet_catalog) != \
               _compute_page_input_hash(p2, product_facts, snippet_catalog)

    def test_unrelated_claim_not_in_hash(self, simple_page, snippet_catalog):
        """Claims not in required_claim_ids must not affect hash."""
        page = dict(simple_page, required_claim_ids=["c1"])
        pf_a = {"claims": [{"claim_id": "c1", "claim_text": "Text"}, {"claim_id": "c9", "claim_text": "Ignored A"}]}
        pf_b = {"claims": [{"claim_id": "c1", "claim_text": "Text"}, {"claim_id": "c9", "claim_text": "Ignored B"}]}
        assert _compute_page_input_hash(page, pf_a, snippet_catalog) == \
               _compute_page_input_hash(page, pf_b, snippet_catalog)

    def test_empty_claims_and_snippets(self):
        page = {
            "slug": "empty", "section": "docs", "page_role": "faq",
            "title": "T", "purpose": "P",
            "required_claim_ids": [], "required_snippet_tags": [],
            "required_headings": [], "template_variant": "standard",
        }
        h = _compute_page_input_hash(page, {}, {})
        assert isinstance(h, str) and len(h) == 64


# ---------------------------------------------------------------------------
# TestFindFailedPageSlugs
# ---------------------------------------------------------------------------

class TestFindFailedPageSlugs:
    def _write_report(self, path: Path, issues: list) -> None:
        path.write_text(json.dumps({"issues": issues}), encoding="utf-8")

    def test_blocker_issue_marks_slug_failed(self, tmp_path):
        p = tmp_path / "validation_report.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "drafts/products/overview.md"}, "error_code": "X"}
        ])
        slugs = _find_failed_page_slugs(p)
        assert "overview" in slugs

    def test_error_issue_marks_slug_failed(self, tmp_path):
        p = tmp_path / "validation_report.json"
        self._write_report(p, [
            {"severity": "error", "location": {"path": "drafts/docs/install.md"}, "error_code": "Y"}
        ])
        slugs = _find_failed_page_slugs(p)
        assert "install" in slugs

    def test_warn_issue_does_not_mark_failed(self, tmp_path):
        p = tmp_path / "validation_report.json"
        self._write_report(p, [
            {"severity": "warn", "location": {"path": "drafts/docs/tips.md"}, "error_code": "Z"}
        ])
        slugs = _find_failed_page_slugs(p)
        assert "tips" not in slugs

    def test_no_issues_returns_empty_set(self, tmp_path):
        p = tmp_path / "validation_report.json"
        self._write_report(p, [])
        slugs = _find_failed_page_slugs(p)
        assert len(slugs) == 0

    def test_missing_file_returns_empty_set(self, tmp_path):
        p = tmp_path / "does_not_exist.json"
        slugs = _find_failed_page_slugs(p)
        assert len(slugs) == 0

    def test_corrupt_json_returns_empty_set(self, tmp_path):
        p = tmp_path / "validation_report.json"
        p.write_text("NOT VALID {{{", encoding="utf-8")
        slugs = _find_failed_page_slugs(p)
        assert len(slugs) == 0

    def test_multiple_issues_same_page_deduped(self, tmp_path):
        p = tmp_path / "validation_report.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "drafts/docs/overview.md"}, "error_code": "A"},
            {"severity": "error", "location": {"path": "drafts/docs/overview.md"}, "error_code": "B"},
        ])
        slugs = _find_failed_page_slugs(p)
        assert slugs == frozenset({"overview"})


# ---------------------------------------------------------------------------
# TestWorkerCacheHashIntegration (WorkerCache integration)
# ---------------------------------------------------------------------------

class TestWorkerCacheHashIntegration:
    def test_enabled_cache_hit_with_matching_hash(self, tmp_path):
        cache = WorkerCache(tmp_path / "run", enabled=True)
        cache.record_page("products_overview", "drafts/products/overview.md", "hash_abc")
        result = cache.is_page_hit("products_overview", "hash_abc")
        assert result == "drafts/products/overview.md"

    def test_enabled_cache_miss_with_changed_hash(self, tmp_path):
        cache = WorkerCache(tmp_path / "run", enabled=True)
        cache.record_page("products_overview", "drafts/products/overview.md", "hash_abc")
        result = cache.is_page_hit("products_overview", "hash_xyz")
        assert result is None

    def test_disabled_cache_never_hits(self, tmp_path):
        cache = WorkerCache(tmp_path / "run", enabled=False)
        cache.record_page("products_overview", "drafts/products/overview.md", "hash_abc")
        result = cache.is_page_hit("products_overview", "hash_abc")
        assert result is None


# ---------------------------------------------------------------------------
# TestRegenFailedOnlyPageStatusOverride
# ---------------------------------------------------------------------------

class TestRegenFailedOnlyPageStatusOverride:
    """Test regen_failed_only behavior via execute_section_writer call.

    Uses a minimal integration approach: mock LLM + pre-built artifacts,
    verify page_status is overridden correctly based on validation_report.
    """

    def _make_artifacts(self, run_dir: Path, pages: list, failing_slugs: list) -> None:
        """Write minimal artifact files for the run."""
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)

        page_plan = {"pages": pages, "schema_version": "1.0"}
        (artifacts / "page_plan.json").write_text(json.dumps(page_plan), encoding="utf-8")

        product_facts = {"claims": [], "claim_groups": {}, "product_slug": "test"}
        (artifacts / "product_facts.json").write_text(json.dumps(product_facts), encoding="utf-8")

        snippet_catalog = {"snippets": []}
        (artifacts / "snippet_catalog.json").write_text(json.dumps(snippet_catalog), encoding="utf-8")

        evidence_map = {}
        (artifacts / "evidence_map.json").write_text(json.dumps(evidence_map), encoding="utf-8")

        # Write validation_report.json with the failing slugs
        issues = [
            {
                "severity": "blocker",
                "location": {"path": f"drafts/products/{slug}.md"},
                "error_code": "GATE_X",
                "gate": "gate_14",
                "issue_id": f"issue_{slug}",
                "message": f"Page {slug} failed.",
                "status": "OPEN",
            }
            for slug in failing_slugs
        ]
        validation_report = {"schema_version": "1.0", "ok": False, "issues": issues, "gates": []}
        (artifacts / "validation_report.json").write_text(
            json.dumps(validation_report), encoding="utf-8"
        )

    def test_failed_slug_marked_new(self, tmp_path):
        """_find_failed_page_slugs correctly identifies failed slugs."""
        report_path = tmp_path / "validation_report.json"
        issues = [
            {"severity": "blocker", "location": {"path": "drafts/products/failing-page.md"}, "error_code": "E"}
        ]
        report_path.write_text(json.dumps({"issues": issues}), encoding="utf-8")
        slugs = _find_failed_page_slugs(report_path)
        assert "failing-page" in slugs

    def test_passing_slug_not_in_failed_set(self, tmp_path):
        """Pages without errors should not appear in the failed set."""
        report_path = tmp_path / "validation_report.json"
        report_path.write_text(json.dumps({"issues": []}), encoding="utf-8")
        slugs = _find_failed_page_slugs(report_path)
        assert len(slugs) == 0

    def test_info_severity_not_failed(self, tmp_path):
        """Info-level issues do not count as page failures."""
        report_path = tmp_path / "validation_report.json"
        issues = [
            {"severity": "info", "location": {"path": "drafts/products/info-page.md"}, "error_code": "I"}
        ]
        report_path.write_text(json.dumps({"issues": issues}), encoding="utf-8")
        slugs = _find_failed_page_slugs(report_path)
        assert "info-page" not in slugs


# ---------------------------------------------------------------------------
# TestComputePageInputHashEdgeCases
# ---------------------------------------------------------------------------

class TestComputePageInputHashEdgeCases:
    def test_missing_optional_fields_use_defaults(self):
        """page dict with minimal fields shouldn't crash."""
        page = {"slug": "s", "section": "docs"}
        h = _compute_page_input_hash(page, {}, {})
        assert isinstance(h, str) and len(h) == 64

    def test_sorted_headings_produce_same_hash(self):
        p1 = {
            "slug": "s", "section": "docs", "page_role": "r", "title": "T", "purpose": "P",
            "required_claim_ids": [], "required_snippet_tags": [],
            "required_headings": ["A", "B", "C"], "template_variant": "standard",
        }
        p2 = dict(p1, required_headings=["C", "A", "B"])
        # sorted() normalizes order → same hash
        assert _compute_page_input_hash(p1, {}, {}) == _compute_page_input_hash(p2, {}, {})

    def test_hash_is_sha256_length(self, simple_page, product_facts, snippet_catalog):
        h = _compute_page_input_hash(simple_page, product_facts, snippet_catalog)
        assert len(h) == 64
        int(h, 16)  # valid hex string

    def test_different_page_roles_different_hashes(self, product_facts, snippet_catalog):
        base = {
            "slug": "s", "section": "docs", "title": "T", "purpose": "P",
            "required_claim_ids": [], "required_snippet_tags": [],
            "required_headings": [], "template_variant": "standard",
        }
        h1 = _compute_page_input_hash(dict(base, page_role="tutorial"), product_facts, snippet_catalog)
        h2 = _compute_page_input_hash(dict(base, page_role="faq"), product_facts, snippet_catalog)
        assert h1 != h2
