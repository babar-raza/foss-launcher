"""Tests for check_unsourced_metrics — TC-EVAL-502."""
from __future__ import annotations

from launcher.workers.evaluate.checks.unsourced_metrics import check_unsourced_metrics


class TestUnsourcedMetricsCheck:
    def test_no_metrics_no_finding(self) -> None:
        content = "This library provides spreadsheet processing capabilities."
        findings = check_unsourced_metrics(content, "test/slug")
        assert findings == []

    def test_percentage_claim_without_evidence_flagged(self) -> None:
        content = "This approach is 40% faster than alternatives."
        findings = check_unsourced_metrics(content, "test/slug")
        assert len(findings) == 1
        assert "40%" in findings[0].message

    def test_percentage_claim_with_evidence_ok(self) -> None:
        content = (
            "This approach is 40% faster than alternatives. "
            "Based on benchmark results from our testing."
        )
        findings = check_unsourced_metrics(content, "test/slug")
        assert findings == []

    def test_time_claim_without_evidence_flagged(self) -> None:
        content = "Processing completes in 10ms faster latency."
        findings = check_unsourced_metrics(content, "test/slug")
        assert len(findings) == 1

    def test_memory_reduction_claim_flagged(self) -> None:
        content = "Achieves 38% memory reduction compared to alternatives."
        findings = check_unsourced_metrics(content, "test/slug")
        assert len(findings) == 1

    def test_multiple_claims_single_finding(self) -> None:
        content = "This is 40% faster and uses 20% less memory."
        findings = check_unsourced_metrics(content, "test/slug")
        assert len(findings) == 1  # single finding listing both claims

    def test_sourced_claim_not_flagged(self) -> None:
        content = (
            "According to documentation states, the library processes "
            "files 30% faster."
        )
        findings = check_unsourced_metrics(content, "test/slug")
        assert findings == []
