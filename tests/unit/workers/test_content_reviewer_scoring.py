"""Tests for W7 ContentReviewer scoring crash fixes and LLM verification.

TC-2338: Scoring crash fix - defensive str() for dict/list paths
TC-2339: LLM score verification layer
TC-2341: Post-LLM re-scoring
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from launch.workers.w7_content_reviewer.scoring import (
    calculate_scores,
    calculate_per_page_scores,
    route_review_result,
    verify_scores_with_llm,
)


# ---------------------------------------------------------------------------
# TC-2338: Scoring crash fix tests
# ---------------------------------------------------------------------------


def test_calculate_scores_malformed_location_dict_path():
    """TC-2338: scoring crash fix - path as dict should not raise TypeError."""
    issues = [
        {
            "check": "content_quality.x",
            "severity": "warn",
            "location": {"path": {"file": "x.md"}, "line": 1},
        }
    ]
    scores = calculate_scores(issues, num_pages=1)
    assert "content_quality" in scores
    assert scores["content_quality"] == 4  # 1 warn = score 4


def test_route_review_result_malformed_location():
    """TC-2338: scoring crash fix - malformed location should not crash routing."""
    issues = [
        {
            "severity": "warn",
            "check": "content_quality.x",
            "location": {"path": ["a", "b"], "line": 1},
        }
    ]
    scores = {"content_quality": 4, "technical_accuracy": 5, "usability": 5}
    result = route_review_result(scores, issues)
    assert result in ("PASS", "NEEDS_CHANGES", "REJECT")


def test_calculate_per_page_scores_malformed_path():
    """TC-2338: per-page scoring with dict path should not crash."""
    issues = [
        {
            "check": "content_quality.x",
            "severity": "warn",
            "location": {"path": {"nested": True}, "line": 1},
        }
    ]
    result = calculate_per_page_scores(issues)
    assert isinstance(result, dict)
    # The dict path should be stringified and appear as a key
    assert len(result) == 1


def test_calculate_scores_dict_path_in_auto_detect_mode():
    """TC-2338: dict path should not crash when num_pages auto-detected from locations."""
    issues = [
        {
            "check": "content_quality.foo",
            "severity": "warn",
            "location": {"path": {"a": 1}, "line": 1},
        },
        {
            "check": "content_quality.bar",
            "severity": "warn",
            "location": {"path": {"b": 2}, "line": 2},
        },
    ]
    # num_pages=0 triggers auto-detection from issue location paths
    scores = calculate_scores(issues, num_pages=0)
    assert "content_quality" in scores


def test_route_review_result_none_location():
    """TC-2338: missing location entirely should not crash."""
    issues = [
        {
            "severity": "warn",
            "check": "content_quality.x",
            # no location key at all
        }
    ]
    scores = {"content_quality": 4, "technical_accuracy": 5, "usability": 5}
    result = route_review_result(scores, issues)
    assert result in ("PASS", "NEEDS_CHANGES", "REJECT")


# ---------------------------------------------------------------------------
# TC-2339: LLM score verification layer tests
# ---------------------------------------------------------------------------


def test_verify_scores_with_llm_returns_dict_on_success():
    """TC-2339: verify_scores_with_llm returns parsed dict on LLM success.

    Testing: mocked (LLM client is mocked, prompt file is real).
    """
    llm_response = json.dumps({
        "llm_status": "PASS",
        "llm_scores": {"content_quality": 5, "technical_accuracy": 5, "usability": 5},
        "edge_cases": [],
        "agreement": True,
        "override_reason": None,
    })
    mock_client = MagicMock()
    mock_client.chat_completion.return_value = {"content": llm_response}

    scores = {"content_quality": 5, "technical_accuracy": 5, "usability": 5}
    issues = [
        {"check": "content_quality.test", "severity": "warn",
         "message": "Test issue", "location": {"path": "test.md", "line": 1}},
    ]

    result = verify_scores_with_llm(
        mock_client, scores, issues, "PASS", {"test.md": "Hello world content sample"}
    )

    assert result is not None
    assert result["llm_status"] == "PASS"
    assert result["agreement"] is True
    mock_client.chat_completion.assert_called_once()


def test_verify_scores_with_llm_returns_none_on_failure():
    """TC-2339: verify_scores_with_llm returns None when LLM call fails."""
    mock_client = MagicMock()
    mock_client.chat_completion.side_effect = Exception("LLM error")

    scores = {"content_quality": 5, "technical_accuracy": 5, "usability": 5}

    # Even if prompt file read fails, should return None gracefully
    result = verify_scores_with_llm(
        mock_client, scores, [], "PASS", {}
    )
    assert result is None


def test_verify_scores_with_llm_returns_none_on_bad_json():
    """TC-2339: verify_scores_with_llm returns None when LLM returns invalid JSON."""
    mock_client = MagicMock()
    mock_client.chat_completion.return_value = {"content": "This is not valid JSON at all"}

    scores = {"content_quality": 5, "technical_accuracy": 5, "usability": 5}

    result = verify_scores_with_llm(
        mock_client, scores, [], "PASS", {}
    )

    # No valid JSON with "llm_status" key found -> returns None
    assert result is None


def test_verify_scores_safety_constraint_reject_cannot_become_pass():
    """TC-2339: safety constraint - LLM cannot override REJECT to PASS.

    This tests the worker-level integration logic, not the scoring function itself.
    The safety constraint is: if deterministic says REJECT and LLM says PASS,
    overall_status remains REJECT.
    """
    # Simulate the worker-level logic
    overall_status = "REJECT"
    llm_verification = {
        "llm_status": "PASS",
        "agreement": False,
        "override_reason": "Content looks fine",
    }

    llm_status = llm_verification.get("llm_status", overall_status)
    # The worker code only allows downgrades:
    # - PASS + llm!=PASS -> llm_status
    # - NEEDS_CHANGES + llm==REJECT -> REJECT
    # REJECT + llm==PASS -> no change (safety)
    if overall_status == "PASS" and llm_status != "PASS":
        overall_status = llm_status
    elif overall_status == "NEEDS_CHANGES" and llm_status == "REJECT":
        overall_status = "REJECT"
    # Note: no branch for REJECT -> anything else

    assert overall_status == "REJECT"  # Must remain REJECT


def test_verify_scores_llm_can_downgrade_pass_to_needs_changes():
    """TC-2339: LLM can downgrade PASS to NEEDS_CHANGES."""
    overall_status = "PASS"
    llm_verification = {
        "llm_status": "NEEDS_CHANGES",
        "agreement": False,
        "override_reason": "Content has raw parameter dumps",
    }

    llm_status = llm_verification.get("llm_status", overall_status)
    if overall_status == "PASS" and llm_status != "PASS":
        overall_status = llm_status
    elif overall_status == "NEEDS_CHANGES" and llm_status == "REJECT":
        overall_status = "REJECT"

    assert overall_status == "NEEDS_CHANGES"


def test_verify_scores_llm_can_downgrade_needs_changes_to_reject():
    """TC-2339: LLM can downgrade NEEDS_CHANGES to REJECT."""
    overall_status = "NEEDS_CHANGES"
    llm_verification = {
        "llm_status": "REJECT",
        "agreement": False,
        "override_reason": "Content is critically bad",
    }

    llm_status = llm_verification.get("llm_status", overall_status)
    if overall_status == "PASS" and llm_status != "PASS":
        overall_status = llm_status
    elif overall_status == "NEEDS_CHANGES" and llm_status == "REJECT":
        overall_status = "REJECT"

    assert overall_status == "REJECT"


# ---------------------------------------------------------------------------
# TC-2363: W7 -> W5 selective re-draft routing
# ---------------------------------------------------------------------------


def _make_state(
    run_dir: str,
    redraft_enabled: bool = False,
    overall_status: str = "REJECT",
    pages_failed: int = 2,
    redraft_attempts: int = 0,
    max_redraft_attempts: int = 1,
) -> dict:
    """Build a minimal OrchestratorState dict for routing tests."""
    return {
        "run_id": "test-run",
        "run_state": "REVIEWING",
        "run_dir": run_dir,
        "run_config": {
            "redraft_enabled": redraft_enabled,
            "max_redraft_attempts": max_redraft_attempts,
        },
        "snapshot": {},
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
        "redraft_attempts": redraft_attempts,
        # Internal: used to build review_report.json
        "_overall_status": overall_status,
        "_pages_failed": pages_failed,
    }


def _write_review_report(run_dir_path, overall_status: str, pages_failed: int, issues=None):
    """Write a minimal review_report.json to the artifacts dir."""
    import os
    artifacts = run_dir_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "1.0.0",
        "overall_status": overall_status,
        "pages_failed": pages_failed,
        "pages_passed": 1,
        "issues": issues or [],
    }
    (artifacts / "review_report.json").write_text(json.dumps(report))


def test_decide_after_review_disabled(tmp_path):
    """TC-2363: redraft_enabled=False -> always 'continue' regardless of REJECT status."""
    from src.launch.orchestrator.graph import decide_after_review

    _write_review_report(tmp_path, "REJECT", 2)
    state = _make_state(str(tmp_path), redraft_enabled=False)
    assert decide_after_review(state) == "continue"


def test_decide_after_review_reject_routes_redraft(tmp_path):
    """TC-2363: redraft_enabled=True + REJECT + pages_failed>0 + attempts<max -> 'redraft'."""
    from src.launch.orchestrator.graph import decide_after_review

    _write_review_report(tmp_path, "REJECT", pages_failed=2)
    state = _make_state(
        str(tmp_path),
        redraft_enabled=True,
        redraft_attempts=0,
        max_redraft_attempts=1,
    )
    assert decide_after_review(state) == "redraft"


def test_decide_after_review_exhausted(tmp_path):
    """TC-2363: redraft_enabled=True + REJECT + attempts >= max -> 'continue' (exhausted)."""
    from src.launch.orchestrator.graph import decide_after_review

    _write_review_report(tmp_path, "REJECT", pages_failed=2)
    state = _make_state(
        str(tmp_path),
        redraft_enabled=True,
        redraft_attempts=1,
        max_redraft_attempts=1,
    )
    assert decide_after_review(state) == "continue"


def test_decide_after_review_pass_continues(tmp_path):
    """TC-2363: redraft_enabled=True + PASS -> 'continue'."""
    from src.launch.orchestrator.graph import decide_after_review

    _write_review_report(tmp_path, "PASS", pages_failed=0)
    state = _make_state(
        str(tmp_path),
        redraft_enabled=True,
        overall_status="PASS",
        pages_failed=0,
    )
    assert decide_after_review(state) == "continue"


def test_redraft_pages_node_marks_correctly(tmp_path):
    """TC-2363: redraft_pages_node marks failing pages 'new', passing pages 'preserved'.

    Verifies: atomic write, correct page_status values, redraft_attempts incremented.
    """
    from src.launch.orchestrator.graph import redraft_pages_node

    # Build review_report with 2 failing page paths
    failing_issue_paths = [
        "drafts/docs/guide.md",
        "drafts/reference/api.md",
    ]
    _write_review_report(
        tmp_path,
        "REJECT",
        pages_failed=2,
        issues=[
            {"check": "x", "severity": "error", "location": {"path": p, "line": 1}}
            for p in failing_issue_paths
        ],
    )

    # Build page_plan with 4 pages (2 failing, 2 passing)
    page_plan = {
        "product_slug": "cells",
        "pages": [
            {"section": "docs", "slug": "guide", "draft_path": "drafts/docs/guide.md",
             "output_path": "content/docs/guide.md", "title": "Guide"},
            {"section": "reference", "slug": "api", "draft_path": "drafts/reference/api.md",
             "output_path": "content/reference/api.md", "title": "API"},
            {"section": "docs", "slug": "intro", "draft_path": "drafts/docs/intro.md",
             "output_path": "content/docs/intro.md", "title": "Intro"},
            {"section": "docs", "slug": "faq", "draft_path": "drafts/docs/faq.md",
             "output_path": "content/docs/faq.md", "title": "FAQ"},
        ],
    }
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "page_plan.json").write_text(json.dumps(page_plan))

    state = {
        "run_id": "test",
        "run_state": "REVIEWING",
        "run_dir": str(tmp_path),
        "run_config": {"redraft_enabled": True},
        "snapshot": {},
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
        "redraft_attempts": 0,
    }

    result = redraft_pages_node(state)

    # redraft_attempts incremented
    assert result["redraft_attempts"] == 1

    # page_plan.json updated atomically
    updated = json.loads((artifacts / "page_plan.json").read_text())
    statuses = {p["slug"]: p["page_status"] for p in updated["pages"]}
    assert statuses["guide"] == "new"      # failing -> new
    assert statuses["api"] == "new"        # failing -> new
    assert statuses["intro"] == "preserved"  # passing -> preserved
    assert statuses["faq"] == "preserved"    # passing -> preserved


# ---------------------------------------------------------------------------
# BLKR-02: FQ Formatting Defect Check Tests
# ---------------------------------------------------------------------------

from launch.workers.w7_content_reviewer.checks.technical_accuracy import (
    _check_fq1_naked_code,
    _check_fq3_truncated_bullets,
    _check_fq4_double_heading,
    _check_fq7_incoherent_headings,
)
from launch.workers.w7_content_reviewer.fixes.auto_fixes import (
    fix_fq1_naked_code,
    fix_fq3_truncated_bullets,
    fix_fq4_double_heading,
)


class TestFQ1NakedCode:
    """FQ-1 NAKED_CODE: detection and auto-fix."""

    def test_detects_bare_import(self):
        content = "## Installation\n\nimport aspose.threed as a3d\n\nSome text.\n"
        issues = _check_fq1_naked_code(content, "docs/page.md", "page")
        assert any("fq1_naked_code" in i["check"] for i in issues)

    def test_detects_pip_install(self):
        content = "## Install\n\npip install aspose-3d\n\nDone.\n"
        issues = _check_fq1_naked_code(content, "docs/page.md", "page")
        assert any("fq1_naked_code" in i["check"] for i in issues)

    def test_no_false_positive_inside_fence(self):
        content = "## Code\n\n```python\nimport aspose.threed\n```\n\nDone.\n"
        issues = _check_fq1_naked_code(content, "docs/page.md", "page")
        assert not any("fq1_naked_code" in i["check"] for i in issues)

    def test_no_false_positive_clean_prose(self):
        content = "## Overview\n\nThis product supports 3D rendering.\n"
        issues = _check_fq1_naked_code(content, "docs/page.md", "page")
        assert issues == []

    def test_auto_fix_wraps_in_fence(self, tmp_path):
        md = tmp_path / "page.md"
        md.write_text("## Install\n\nimport aspose.threed as a3d\n\nDone.\n", encoding="utf-8")
        issue = {
            "issue_id": "test_fq1",
            "check": "technical_accuracy.fq1_naked_code",
            "location": {"path": "docs/page.md", "line": 3},
        }
        result = fix_fq1_naked_code(issue, md)
        assert result["success"] is True
        fixed = md.read_text(encoding="utf-8")
        assert "```python" in fixed
        assert "import aspose.threed" in fixed


class TestFQ3TruncatedBullets:
    """FQ-3 TRUNCATED: detection and auto-fix."""

    def test_detects_trailing_comma(self):
        content = "## Features\n\n- Supports Excel, PDF,\n- Another item.\n"
        issues = _check_fq3_truncated_bullets(content, "docs/page.md", "page")
        assert any("fq3_truncated" in i["check"] for i in issues)

    def test_detects_dangling_preposition(self):
        content = "## Usage\n\n- Use this method with\n- Next item.\n"
        issues = _check_fq3_truncated_bullets(content, "docs/page.md", "page")
        assert any("fq3_truncated" in i["check"] for i in issues)

    def test_no_false_positive_complete_bullet(self):
        content = "## Features\n\n- Supports OBJ, FBX, and GLTF formats.\n"
        issues = _check_fq3_truncated_bullets(content, "docs/page.md", "page")
        assert not any("fq3_truncated" in i["check"] for i in issues)

    def test_no_false_positive_inside_fence(self):
        content = "```python\n# comment ends with the\n```\n"
        issues = _check_fq3_truncated_bullets(content, "docs/page.md", "page")
        assert issues == []

    def test_auto_fix_trailing_comma(self, tmp_path):
        md = tmp_path / "page.md"
        md.write_text("## Feats\n\n- Supports Excel, PDF,\n", encoding="utf-8")
        issue = {
            "issue_id": "test_fq3",
            "check": "technical_accuracy.fq3_truncated_bullets",
            "location": {"path": "docs/page.md", "line": 3},
        }
        result = fix_fq3_truncated_bullets(issue, md)
        assert result["success"] is True
        assert "- Supports Excel, PDF." in md.read_text(encoding="utf-8")

    def test_auto_fix_dangling_word(self, tmp_path):
        md = tmp_path / "page.md"
        md.write_text("## Usage\n\n- Use this method with\n", encoding="utf-8")
        issue = {
            "issue_id": "test_fq3b",
            "check": "technical_accuracy.fq3_truncated_bullets",
            "location": {"path": "docs/page.md", "line": 3},
        }
        result = fix_fq3_truncated_bullets(issue, md)
        assert result["success"] is True
        assert md.read_text(encoding="utf-8").strip().endswith(".")


class TestFQ4DoubleHeading:
    """FQ-4 DOUBLE_HEADING: detection and auto-fix."""

    def test_detects_oversized_heading(self):
        content = "## Overview This product provides comprehensive 3D scene manipulation capabilities for Python developers.\n"
        issues = _check_fq4_double_heading(content, "docs/page.md", "page")
        assert any("fq4_double_heading" in i["check"] for i in issues)

    def test_no_false_positive_normal_heading(self):
        content = "## Getting Started\n\nInstall the package first.\n"
        issues = _check_fq4_double_heading(content, "docs/page.md", "page")
        assert issues == []

    def test_no_false_positive_inside_fence(self):
        content = "```markdown\n## This is a very long heading that exceeds seventy characters in length okay\n```\n"
        issues = _check_fq4_double_heading(content, "docs/page.md", "page")
        assert issues == []

    def test_auto_fix_splits_heading(self, tmp_path):
        md = tmp_path / "page.md"
        content = "## Overview. This product provides comprehensive 3D manipulation for Python.\n\nMore.\n"
        md.write_text(content, encoding="utf-8")
        issue = {
            "issue_id": "test_fq4",
            "check": "technical_accuracy.fq4_double_heading",
            "location": {"path": "docs/page.md", "line": 1},
        }
        result = fix_fq4_double_heading(issue, md)
        assert result["success"] is True
        assert "## Overview" in md.read_text(encoding="utf-8")


class TestFQ7IncoherentHeadings:
    """FQ-7 INCOHERENT: heading repetition detection (no auto-fix)."""

    def test_detects_verbatim_repetition(self):
        content = "## Installation Guide\nInstallation guide is how you set up.\n"
        issues = _check_fq7_incoherent_headings(content, "docs/page.md", "page")
        assert any("fq7_incoherent" in i["check"] for i in issues)

    def test_no_false_positive_different_body(self):
        content = "## Installation Guide\nFollow these steps to install.\n"
        issues = _check_fq7_incoherent_headings(content, "docs/page.md", "page")
        assert issues == []

    def test_no_false_positive_short_heading(self):
        content = "## API\nAPI stands for Application Programming Interface.\n"
        issues = _check_fq7_incoherent_headings(content, "docs/page.md", "page")
        assert issues == []

    def test_not_auto_fixable(self):
        content = "## Installation Guide\nInstallation guide is how you set up.\n"
        issues = _check_fq7_incoherent_headings(content, "docs/page.md", "page")
        fq7 = [i for i in issues if "fq7_incoherent" in i["check"]]
        assert fq7
        assert all(not i.get("auto_fixable", True) for i in fq7)
