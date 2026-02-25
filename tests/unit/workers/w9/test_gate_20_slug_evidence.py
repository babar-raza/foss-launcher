"""Tests for G20-008 slug-evidence consistency check (TC-2613).

Validates:
- Format tokens in slugs are cross-checked against product_facts.supported_formats
- Common slug words (stopwords) are not flagged
- Known format tokens pass silently
- Unknown format tokens produce info-level issues
- Empty supported_formats produces no issues
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
    _check_slug_evidence_consistency,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def product_facts_3d() -> Dict[str, Any]:
    return {
        "supported_formats": [
            {"format": "FBX", "claim_ids": ["c1"]},
            {"format": "OBJ", "claim_ids": ["c2"]},
            {"format": "GLTF", "claim_ids": ["c3"]},
        ]
    }


@pytest.fixture
def product_facts_cells() -> Dict[str, Any]:
    return {
        "supported_formats": ["XLSX", "CSV", "PDF", "ODS"]
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSlugEvidenceConsistency:
    """Tests for _check_slug_evidence_consistency()."""

    def test_no_issues_for_evidenced_formats(self, product_facts_3d):
        """Slugs with known format tokens produce no issues."""
        page_plan = {
            "pages": [
                {"slug": "how-to-convert-fbx-to-obj", "section": "kb"},
                {"slug": "how-to-load-gltf", "section": "kb"},
            ]
        }
        issues = _check_slug_evidence_consistency(page_plan, product_facts_3d)
        assert issues == []

    def test_flags_unknown_format_token(self, product_facts_3d):
        """Unknown format tokens produce info-level issues."""
        page_plan = {
            "pages": [
                {"slug": "how-to-convert-abc-to-xyz", "section": "kb"},
            ]
        }
        issues = _check_slug_evidence_consistency(page_plan, product_facts_3d)
        # "abc" and "xyz" are not in supported_formats
        assert len(issues) >= 2
        assert all(i["severity"] == "info" for i in issues)
        assert all(i["error_code"] == "G20-008" for i in issues)
        tokens_flagged = {i["message"].split("'")[1] for i in issues}
        assert "abc" in tokens_flagged
        assert "xyz" in tokens_flagged

    def test_stopwords_not_flagged(self, product_facts_3d):
        """Common slug words (how, to, python, etc.) are not flagged."""
        page_plan = {
            "pages": [
                {"slug": "how-to-load-models-python", "section": "kb"},
            ]
        }
        issues = _check_slug_evidence_consistency(page_plan, product_facts_3d)
        assert issues == []

    def test_empty_formats_no_issues(self):
        """When supported_formats is empty, no issues are produced."""
        page_plan = {
            "pages": [
                {"slug": "how-to-convert-abc-to-xyz", "section": "kb"},
            ]
        }
        issues = _check_slug_evidence_consistency(page_plan, {"supported_formats": []})
        assert issues == []

    def test_no_formats_key_no_issues(self):
        """When supported_formats key is absent, no issues are produced."""
        page_plan = {
            "pages": [
                {"slug": "how-to-convert-abc-to-xyz", "section": "kb"},
            ]
        }
        issues = _check_slug_evidence_consistency(page_plan, {})
        assert issues == []

    def test_mixed_known_and_unknown(self, product_facts_3d):
        """Only unknown tokens are flagged; known ones pass."""
        page_plan = {
            "pages": [
                {"slug": "how-to-convert-fbx-to-xyz", "section": "kb"},
            ]
        }
        issues = _check_slug_evidence_consistency(page_plan, product_facts_3d)
        assert len(issues) == 1
        assert "xyz" in issues[0]["message"]
        # fbx should NOT be flagged
        assert "fbx" not in issues[0]["message"].lower() or "xyz" in issues[0]["message"]

    def test_string_format_list(self, product_facts_cells):
        """Handles supported_formats as list of strings."""
        page_plan = {
            "pages": [
                {"slug": "how-to-convert-xlsx-to-csv", "section": "kb"},
            ]
        }
        issues = _check_slug_evidence_consistency(page_plan, product_facts_cells)
        assert issues == []

    def test_info_severity_does_not_fail_gate(self, product_facts_3d):
        """G20-008 issues are info-level and should not fail the gate."""
        page_plan = {
            "pages": [
                {"slug": "convert-abc-to-def", "section": "kb"},
            ]
        }
        issues = _check_slug_evidence_consistency(page_plan, product_facts_3d)
        assert all(i["severity"] == "info" for i in issues)
