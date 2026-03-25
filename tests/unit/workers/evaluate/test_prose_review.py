"""Tests for prose_review module (TC-PROSE-01 Phase 3)."""
from __future__ import annotations

import json

import pytest

from launcher.models.evaluation import Finding
from launcher.workers.evaluate.prose_review import (
    _cap_severity,
    _parse_prose_response,
)


class TestCapSeverity:
    def test_medium_passes_through(self):
        assert _cap_severity("medium") == "medium"

    def test_low_passes_through(self):
        assert _cap_severity("low") == "low"

    def test_high_capped_to_medium(self):
        assert _cap_severity("high") == "medium"

    def test_critical_capped_to_medium(self):
        assert _cap_severity("critical") == "medium"

    def test_unknown_becomes_medium(self):
        assert _cap_severity("bogus") == "medium"

    def test_case_insensitive(self):
        assert _cap_severity("HIGH") == "medium"
        assert _cap_severity("Critical") == "medium"


class TestParseProseResponse:
    def test_valid_json_parsed(self):
        data = {
            "prose_findings": [
                {
                    "check": "prose_quality",
                    "message": "Opening restates the heading",
                    "severity": "medium",
                    "confidence": 0.8,
                    "location": "## Overview",
                },
            ]
        }
        findings = _parse_prose_response(json.dumps(data), "test-slug")
        assert len(findings) == 1
        assert findings[0].check == "prose_quality"
        assert findings[0].severity == "medium"
        assert findings[0].location == "## Overview"

    def test_high_severity_capped_to_medium(self):
        data = {
            "prose_findings": [
                {
                    "check": "prose_quality",
                    "message": "Bad opening",
                    "severity": "high",
                    "confidence": 0.9,
                },
            ]
        }
        findings = _parse_prose_response(json.dumps(data), "test-slug")
        assert len(findings) == 1
        assert findings[0].severity == "medium"

    def test_low_confidence_filtered(self):
        data = {
            "prose_findings": [
                {
                    "check": "prose_quality",
                    "message": "Maybe bad?",
                    "severity": "medium",
                    "confidence": 0.3,
                },
            ]
        }
        findings = _parse_prose_response(json.dumps(data), "test-slug")
        assert len(findings) == 0

    def test_wrong_check_name_discarded(self):
        data = {
            "prose_findings": [
                {
                    "check": "invented_check",
                    "message": "Something",
                    "severity": "medium",
                    "confidence": 0.9,
                },
            ]
        }
        findings = _parse_prose_response(json.dumps(data), "test-slug")
        assert len(findings) == 0

    def test_invalid_json_returns_empty(self):
        findings = _parse_prose_response("not json at all {{{", "test-slug")
        assert findings == []

    def test_json_in_markdown_fences(self):
        data = {
            "prose_findings": [
                {
                    "check": "prose_quality",
                    "message": "Test",
                    "severity": "medium",
                    "confidence": 0.7,
                },
            ]
        }
        raw = f"```json\n{json.dumps(data)}\n```"
        findings = _parse_prose_response(raw, "test-slug")
        assert len(findings) == 1

    def test_empty_prose_findings(self):
        data = {"prose_findings": []}
        findings = _parse_prose_response(json.dumps(data), "test-slug")
        assert findings == []

    def test_missing_confidence_defaults_to_zero(self):
        data = {
            "prose_findings": [
                {
                    "check": "prose_quality",
                    "message": "No confidence field",
                    "severity": "medium",
                    # no confidence key
                },
            ]
        }
        findings = _parse_prose_response(json.dumps(data), "test-slug")
        assert len(findings) == 0  # 0.0 < 0.5 threshold

    def test_slug_used_when_no_location(self):
        data = {
            "prose_findings": [
                {
                    "check": "prose_quality",
                    "message": "Test",
                    "severity": "medium",
                    "confidence": 0.8,
                },
            ]
        }
        findings = _parse_prose_response(json.dumps(data), "my-slug")
        assert findings[0].location == "my-slug"

    def test_multiple_findings(self):
        data = {
            "prose_findings": [
                {"check": "prose_quality", "message": "A", "severity": "medium", "confidence": 0.7},
                {"check": "prose_quality", "message": "B", "severity": "low", "confidence": 0.6},
                {"check": "prose_quality", "message": "C", "severity": "high", "confidence": 0.9},
            ]
        }
        findings = _parse_prose_response(json.dumps(data), "slug")
        assert len(findings) == 3
        severities = {f.severity for f in findings}
        assert "high" not in severities  # all capped
