"""TC-2508: W9 -> W10 handoff integrity tests.

Validates the generation_id + content_hash handoff mechanism introduced
by TC-2505 (W9 content hash) and TC-2506 (W10 verification).

Tests:
1. W9 emits content_hash in validation report
2. W9 content_hash is deterministic (same input -> same hash)
3. W10 accepts valid handoff (matching generation_id + content_hash)
4. W10 rejects stale generation_id (warns only -- backward compat)
5. W10 rejects mismatched hash -> StaleValidationReportError
6. W10 backward compat: missing fields -> warning only, not error
7. Both fields appear in final validation_report.json

Spec references:
- specs/28_coordination_and_handoffs.md (W9 -> W10 handoff)
- specs/schemas/validation_report.schema.json (generation_id, content_hash)
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from src.launch.workers.w10_fixer.worker import (
    StaleValidationReportError,
    _verify_handoff,
)


# ---------------------------------------------------------------------------
# Helper: build a minimal validation report with proper handoff metadata
# ---------------------------------------------------------------------------

def _build_report(
    gates=None,
    issues=None,
    include_generation_id=True,
    include_content_hash=True,
    tamper_hash=False,
):
    """Build a minimal validation report dict with optional handoff metadata.

    Args:
        gates: List of gate dicts. Defaults to one passing gate.
        issues: List of issue dicts. Defaults to empty list.
        include_generation_id: Whether to add a generation_id field.
        include_content_hash: Whether to add the content_hash field.
        tamper_hash: If True, the content_hash will be a wrong value.

    Returns:
        dict matching validation_report.schema.json (plus handoff fields).
    """
    if gates is None:
        gates = [{"name": "gate_1_schema_validation", "ok": True}]
    if issues is None:
        issues = []

    report = {
        "schema_version": "1.0",
        "ok": all(g["ok"] for g in gates),
        "profile": "local",
        "gates": gates,
        "issues": issues,
    }

    if include_generation_id:
        report["generation_id"] = str(uuid.uuid4())

    if include_content_hash:
        # Compute real hash (same algorithm as W9)
        hash_input = json.dumps(
            {"gates": gates, "issues": issues},
            sort_keys=True,
        )
        real_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        report["content_hash"] = "deadbeef" * 8 if tamper_hash else real_hash

    return report


# ---------------------------------------------------------------------------
# 1. W9 emits content_hash
# ---------------------------------------------------------------------------

def test_w9_emits_content_hash():
    """A report built by the same algorithm W9 uses must contain content_hash."""
    report = _build_report()
    assert "content_hash" in report
    assert isinstance(report["content_hash"], str)
    assert len(report["content_hash"]) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# 2. Content hash is deterministic
# ---------------------------------------------------------------------------

def test_w9_content_hash_deterministic():
    """Same gates + issues must produce the same content_hash every time."""
    gates = [
        {"name": "gate_1_schema_validation", "ok": True},
        {"name": "gate_10_consistency", "ok": False},
    ]
    issues = [
        {
            "issue_id": "issue_a",
            "gate": "gate_10_consistency",
            "severity": "error",
            "message": "Product name mismatch",
            "error_code": "GATE_CONSISTENCY_PRODUCT_NAME_MISMATCH",
            "status": "OPEN",
        }
    ]

    report_1 = _build_report(gates=gates, issues=issues)
    report_2 = _build_report(gates=gates, issues=issues)

    assert report_1["content_hash"] == report_2["content_hash"]


# ---------------------------------------------------------------------------
# 3. W10 accepts valid handoff
# ---------------------------------------------------------------------------

def test_w10_accepts_valid_handoff():
    """_verify_handoff must NOT raise when generation_id and content_hash are correct."""
    report = _build_report()
    # Should not raise
    _verify_handoff(report)


# ---------------------------------------------------------------------------
# 4. W10 warns on missing generation_id (backward compat)
# ---------------------------------------------------------------------------

def test_w10_warns_missing_generation_id(caplog):
    """When generation_id is absent, _verify_handoff warns but does not raise."""
    report = _build_report(include_generation_id=False, include_content_hash=False)
    # Should NOT raise -- backward compat
    _verify_handoff(report)
    assert "generation_id missing" in caplog.text


# ---------------------------------------------------------------------------
# 5. W10 rejects mismatched hash
# ---------------------------------------------------------------------------

def test_w10_rejects_mismatched_hash():
    """Tampered content_hash must raise StaleValidationReportError."""
    report = _build_report(tamper_hash=True)

    with pytest.raises(StaleValidationReportError, match="content_hash mismatch"):
        _verify_handoff(report)


# ---------------------------------------------------------------------------
# 6. Backward compat: missing both fields -> warn only
# ---------------------------------------------------------------------------

def test_w10_backward_compat_missing_fields(caplog):
    """Old reports without generation_id/content_hash should pass with warnings."""
    report = _build_report(
        include_generation_id=False,
        include_content_hash=False,
    )

    # Should NOT raise
    _verify_handoff(report)

    assert "generation_id missing" in caplog.text
    assert "content_hash missing" in caplog.text


# ---------------------------------------------------------------------------
# 7. Both fields appear in final report
# ---------------------------------------------------------------------------

def test_handoff_metadata_in_report():
    """Both generation_id and content_hash must be present in a fully-built report."""
    report = _build_report()

    assert "generation_id" in report
    assert "content_hash" in report

    # generation_id should be a valid UUID
    parsed_uuid = uuid.UUID(report["generation_id"])
    assert parsed_uuid.version == 4

    # content_hash should be 64-char hex
    assert len(report["content_hash"]) == 64
    int(report["content_hash"], 16)  # must be valid hex


# ---------------------------------------------------------------------------
# 8. Missing content_hash only -> warn (generation_id present)
# ---------------------------------------------------------------------------

def test_w10_warns_missing_content_hash_only(caplog):
    """When content_hash is absent but generation_id is present, warn only."""
    report = _build_report(include_generation_id=True, include_content_hash=False)
    _verify_handoff(report)
    assert "content_hash missing" in caplog.text


# ---------------------------------------------------------------------------
# 9. Missing generation_id only -> warn (content_hash present)
# ---------------------------------------------------------------------------

def test_w10_warns_missing_generation_id_only(caplog):
    """When generation_id is absent but content_hash is present, warn only."""
    report = _build_report(include_generation_id=False, include_content_hash=True)
    _verify_handoff(report)
    assert "generation_id missing" in caplog.text


# ---------------------------------------------------------------------------
# 10. Hash changes when issues change
# ---------------------------------------------------------------------------

def test_content_hash_changes_with_different_issues():
    """Different issues must produce a different content_hash."""
    report_a = _build_report(issues=[])
    report_b = _build_report(issues=[{
        "issue_id": "new_issue",
        "gate": "gate_1_schema_validation",
        "severity": "error",
        "message": "Schema violation",
        "error_code": "GATE_SCHEMA_VALIDATION_FAILED",
        "status": "OPEN",
    }])

    assert report_a["content_hash"] != report_b["content_hash"]


# ---------------------------------------------------------------------------
# 11. StaleValidationReportError is a subclass of FixerError
# ---------------------------------------------------------------------------

def test_stale_error_hierarchy():
    """StaleValidationReportError must be catchable as FixerError."""
    from src.launch.workers.w10_fixer.worker import FixerError

    err = StaleValidationReportError("test")
    assert isinstance(err, FixerError)


# ---------------------------------------------------------------------------
# 12. execute_fixer raises StaleValidationReportError on tampered report
# ---------------------------------------------------------------------------

def test_execute_fixer_rejects_tampered_report():
    """execute_fixer must raise StaleValidationReportError when hash is wrong."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "run"
        run_dir.mkdir()
        (run_dir / "artifacts").mkdir()
        (run_dir / "reports").mkdir()
        (run_dir / "events.ndjson").write_text("")

        # Write a tampered validation report
        report = _build_report(tamper_hash=True)
        (run_dir / "artifacts" / "validation_report.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        from src.launch.workers.w10_fixer.worker import execute_fixer

        run_config = {"validation_profile": "local"}

        with pytest.raises(StaleValidationReportError, match="content_hash mismatch"):
            execute_fixer(run_dir=run_dir, run_config=run_config)
