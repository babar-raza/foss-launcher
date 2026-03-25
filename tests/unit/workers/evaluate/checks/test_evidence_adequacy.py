"""TC-5164: Tests for the evidence_adequacy check."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.evidence_adequacy import check_evidence_adequacy


class _Page:
    def __init__(self, page_role: str = "overview", slug: str = "overview"):
        self.page_role = page_role
        self.slug = slug


class TestCheckEvidenceAdequacy:
    def test_emits_finding_when_insufficient(self):
        page = _Page(page_role="reference", slug="ref-page")
        pei = {"reference": {"evidence_sufficient": False, "missing": ["no_snippets"]}}
        result = check_evidence_adequacy(page, pei)
        assert len(result) == 1
        assert result[0]["check"] == "evidence_adequacy"
        assert "no_snippets" in result[0]["message"]

    def test_no_finding_when_sufficient(self):
        page = _Page(page_role="overview")
        pei = {"overview": {"evidence_sufficient": True, "missing": []}}
        result = check_evidence_adequacy(page, pei)
        assert result == []

    def test_no_finding_when_index_empty(self):
        page = _Page(page_role="overview")
        result = check_evidence_adequacy(page, {})
        assert result == []

    def test_no_finding_when_role_absent(self):
        page = _Page(page_role="faq")
        pei = {"overview": {"evidence_sufficient": False, "missing": []}}
        result = check_evidence_adequacy(page, pei)
        assert result == []

    def test_missing_list_capped_at_3(self):
        page = _Page(page_role="guide")
        pei = {"guide": {
            "evidence_sufficient": False,
            "missing": ["sig1", "sig2", "sig3", "sig4", "sig5", "sig6", "sig7", "sig8", "sig9", "sig10"],
        }}
        result = check_evidence_adequacy(page, pei)
        assert len(result) == 1
        msg = result[0]["message"]
        # Only first 3 items should appear
        assert "sig1" in msg
        assert "sig2" in msg
        assert "sig3" in msg
        assert "sig4" not in msg

    def test_handles_dict_score(self):
        page = _Page(page_role="quickstart")
        pei = {"quickstart": {"evidence_sufficient": False, "missing": ["no_claims"]}}
        result = check_evidence_adequacy(page, pei)
        assert len(result) == 1
        assert result[0]["severity"] == "medium"

    def test_handles_object_score(self):
        class _Score:
            evidence_sufficient = False
            missing = ["low_snippet_count"]

        page = _Page(page_role="tutorial")
        pei = {"tutorial": _Score()}
        result = check_evidence_adequacy(page, pei)
        assert len(result) == 1
        assert "low_snippet_count" in result[0]["message"]

    def test_finding_severity_is_medium(self):
        page = _Page(page_role="reference")
        pei = {"reference": {"evidence_sufficient": False, "missing": []}}
        result = check_evidence_adequacy(page, pei)
        assert result[0]["severity"] == "medium"

    def test_finding_location_is_slug(self):
        page = _Page(page_role="reference", slug="ref-slug")
        pei = {"reference": {"evidence_sufficient": False, "missing": []}}
        result = check_evidence_adequacy(page, pei)
        assert result[0]["location"] == "ref-slug"
