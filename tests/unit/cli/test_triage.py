"""Unit tests for the operator triage module (TC-2900).

Tests the core triage logic: summary building, issue ranking,
and recommendation engine.  All tests are fast (no network, no LLM).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from launch.cli.triage import (
    build_summary,
    load_validation_report,
    rank_issues,
    recommend_action,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_gate(name: str, ok: bool = True) -> Dict[str, Any]:
    return {"name": name, "ok": ok}


def _make_issue(
    gate: str,
    severity: str = "error",
    error_code: str = "",
    message: str = "test issue",
    path: str = "",
    line: int = 0,
) -> Dict[str, Any]:
    issue: Dict[str, Any] = {
        "issue_id": f"{gate}_{severity}_{error_code or 'nocode'}",
        "gate": gate,
        "severity": severity,
        "message": message,
        "status": "OPEN",
    }
    if error_code:
        issue["error_code"] = error_code
    if path or line:
        issue["location"] = {}
        if path:
            issue["location"]["path"] = path
        if line:
            issue["location"]["line"] = line
    return issue


def _make_report(
    gates: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    profile: str = "local",
    ok: bool | None = None,
) -> Dict[str, Any]:
    if ok is None:
        ok = all(g["ok"] for g in gates)
    return {
        "schema_version": "1.0",
        "ok": ok,
        "profile": profile,
        "gates": gates,
        "issues": issues,
    }


def _write_report(run_dir: Path, report: Dict[str, Any]) -> Path:
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    report_path = artifacts / "validation_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


# ── load_validation_report ─────────────────────────────────────────────────

class TestLoadValidationReport:
    def test_loads_report(self, tmp_path: Path) -> None:
        report = _make_report(
            gates=[_make_gate("gate_1_schema_validation")],
            issues=[],
        )
        _write_report(tmp_path, report)
        loaded = load_validation_report(tmp_path)
        assert loaded["schema_version"] == "1.0"
        assert loaded["ok"] is True

    def test_missing_report_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="validation_report.json"):
            load_validation_report(tmp_path)


# ── build_summary ──────────────────────────────────────────────────────────

class TestBuildSummary:
    def test_severity_counts(self) -> None:
        report = _make_report(
            gates=[
                _make_gate("g1", ok=True),
                _make_gate("g2", ok=False),
            ],
            issues=[
                _make_issue("g2", severity="error", error_code="E1"),
                _make_issue("g2", severity="error", error_code="E2"),
                _make_issue("g2", severity="warn"),
                _make_issue("g2", severity="info"),
                _make_issue("g2", severity="info"),
                _make_issue("g2", severity="info"),
            ],
        )
        summary = build_summary("test-run", report)
        assert summary["run_id"] == "test-run"
        assert summary["profile"] == "local"
        assert summary["total_gates"] == 2
        assert summary["failed_gates"] == 1
        assert summary["severity_counts"] == {
            "blocker": 0,
            "error": 2,
            "warn": 1,
            "info": 3,
        }

    def test_with_snapshot(self) -> None:
        report = _make_report(gates=[], issues=[])
        snapshot = {"run_state": "VALIDATING"}
        summary = build_summary("run-1", report, snapshot)
        assert summary["run_state"] == "VALIDATING"

    def test_without_snapshot(self) -> None:
        report = _make_report(gates=[], issues=[])
        summary = build_summary("run-1", report)
        assert summary["run_state"] is None


# ── rank_issues ────────────────────────────────────────────────────────────

class TestRankIssues:
    def test_top_n_limiting(self) -> None:
        issues = [_make_issue("g", severity="info", error_code=f"I{i}") for i in range(15)]
        report = _make_report(gates=[], issues=issues)
        ranked = rank_issues(report, top_n=10)
        assert len(ranked) == 10

    def test_all_critical_included(self) -> None:
        """All blockers/errors always appear, even if more than top_n."""
        issues = [
            _make_issue("g", severity="blocker", error_code=f"B{i}") for i in range(12)
        ]
        issues.append(_make_issue("g", severity="info"))
        report = _make_report(gates=[], issues=issues, ok=False)
        ranked = rank_issues(report, top_n=5)
        # All 12 blockers must be returned (exceeds top_n)
        assert len(ranked) == 12
        assert all(i["severity"] == "blocker" for i in ranked)

    def test_pads_with_warnings(self) -> None:
        issues = [
            _make_issue("g", severity="error", error_code="E1"),
            _make_issue("g", severity="warn"),
            _make_issue("g", severity="warn"),
            _make_issue("g", severity="info"),
        ]
        report = _make_report(gates=[], issues=issues, ok=False)
        ranked = rank_issues(report, top_n=3)
        # 1 error + 2 warns to fill up to 3
        assert len(ranked) == 3
        assert ranked[0]["severity"] == "error"
        assert ranked[1]["severity"] == "warn"
        assert ranked[2]["severity"] == "warn"


# ── recommend_action ───────────────────────────────────────────────────────

class TestRecommendAction:
    def test_truth_layer_missing_recommends_w2(self, tmp_path: Path) -> None:
        """Gate 0 failure -> recommend W2."""
        report = _make_report(
            gates=[_make_gate("gate_truth_layer_completeness", ok=False)],
            issues=[
                _make_issue(
                    "gate_truth_layer_completeness",
                    severity="error",
                    error_code="TRUTH_MISSING",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        assert any("--from-worker W2" in r["command"] for r in recs)

    def test_truth_facts_completeness_recommends_w2(self, tmp_path: Path) -> None:
        """Gate 40 failure -> recommend W2."""
        report = _make_report(
            gates=[_make_gate("gate_truth_facts_completeness", ok=False)],
            issues=[
                _make_issue(
                    "gate_truth_facts_completeness",
                    severity="error",
                    error_code="TRUTH_INCOMPLETE",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        assert any("--from-worker W2" in r["command"] for r in recs)

    def test_code_fence_api_recommends_w5(self, tmp_path: Path) -> None:
        """Gate 15b failure -> recommend W5."""
        report = _make_report(
            gates=[_make_gate("gate_15b_code_fence_api", ok=False)],
            issues=[
                _make_issue(
                    "gate_15b_code_fence_api",
                    severity="error",
                    error_code="CF-API-001",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        assert any("--from-worker W5" in r["command"] for r in recs)

    def test_scaffold_leak_recommends_w10(self, tmp_path: Path) -> None:
        """gate_scaffold_leak failure -> recommend W10."""
        report = _make_report(
            gates=[_make_gate("gate_scaffold_leak", ok=False)],
            issues=[
                _make_issue(
                    "gate_scaffold_leak",
                    severity="error",
                    error_code="SCAFFOLD_LEAK",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        assert any("--from-worker W10" in r["command"] for r in recs)

    def test_formatting_fq_recommends_w10(self, tmp_path: Path) -> None:
        """FQ-* error codes -> recommend W10."""
        report = _make_report(
            gates=[_make_gate("gate_17_formatting_quality", ok=False)],
            issues=[
                _make_issue(
                    "gate_17_formatting_quality",
                    severity="error",
                    error_code="FQ-1",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        assert any("--from-worker W10" in r["command"] for r in recs)

    def test_link_issues_recommend_w8(self, tmp_path: Path) -> None:
        """Link gate failure -> recommend W8."""
        report = _make_report(
            gates=[_make_gate("gate_5_cross_page_link_validity", ok=False)],
            issues=[
                _make_issue(
                    "gate_5_cross_page_link_validity",
                    severity="error",
                    error_code="BROKEN_LINK",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        assert any("--from-worker W8" in r["command"] for r in recs)

    def test_patch_issues_recommend_w8(self, tmp_path: Path) -> None:
        """Patch gate failure -> recommend W8."""
        report = _make_report(
            gates=[_make_gate("gate_12_patch_conflicts", ok=False)],
            issues=[
                _make_issue(
                    "gate_12_patch_conflicts",
                    severity="error",
                    error_code="PATCH_CONFLICT",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        assert any("--from-worker W8" in r["command"] for r in recs)

    def test_fallback_recommends_w9(self, tmp_path: Path) -> None:
        """No specific pattern -> recommend W9."""
        report = _make_report(
            gates=[_make_gate("gate_1_schema_validation", ok=True)],
            issues=[_make_issue("gate_1_schema_validation", severity="info")],
        )
        recs = recommend_action(tmp_path, report)
        assert len(recs) == 1
        assert "--from-worker W9" in recs[0]["command"]

    def test_multiple_recommendations(self, tmp_path: Path) -> None:
        """Multiple failures -> multiple recommendations in priority order."""
        report = _make_report(
            gates=[
                _make_gate("gate_truth_layer_completeness", ok=False),
                _make_gate("gate_15b_code_fence_api", ok=False),
                _make_gate("gate_scaffold_leak", ok=False),
            ],
            issues=[
                _make_issue("gate_truth_layer_completeness", severity="error",
                            error_code="TRUTH_MISSING"),
                _make_issue("gate_15b_code_fence_api", severity="error",
                            error_code="CF-API-001"),
                _make_issue("gate_scaffold_leak", severity="error",
                            error_code="SCAFFOLD_LEAK"),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        workers = [r["command"].split("--from-worker ")[-1] for r in recs]
        assert workers == ["W2", "W5", "W10"]

    def test_run_dir_in_command(self, tmp_path: Path) -> None:
        """Recommendation commands include the correct run_dir path."""
        report = _make_report(
            gates=[_make_gate("gate_truth_layer_completeness", ok=False)],
            issues=[],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        run_dir_str = str(tmp_path).replace("\\", "/")
        assert run_dir_str in recs[0]["command"]

    def test_warn_truth_issue_with_passing_gate_does_not_recommend_w2(
        self, tmp_path: Path
    ) -> None:
        """Regression TC-3120 F1: warn truth issue + passing truth gate => W10, not W2."""
        report = _make_report(
            gates=[
                _make_gate("gate_truth_layer_completeness", ok=True),
                _make_gate("gate_17_formatting_quality", ok=False),
            ],
            issues=[
                _make_issue(
                    "gate_truth_layer_completeness",
                    severity="warn",
                    error_code="TRUTH_WARN",
                ),
                _make_issue(
                    "gate_17_formatting_quality",
                    severity="error",
                    error_code="FQ-4",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        workers = [r["command"].split("--from-worker ")[-1] for r in recs]
        assert "W10" in workers, f"Expected W10 in recommendations, got: {workers}"
        assert "W2" not in workers, (
            f"W2 must NOT be recommended when truth gates pass (ok=True), got: {workers}"
        )

    def test_truth_gate_name_alone_does_not_trigger_w2(
        self, tmp_path: Path
    ) -> None:
        """Regression TC-3120 F1: truth gate name in issue with passing gate => no W2."""
        report = _make_report(
            gates=[
                _make_gate("gate_truth_layer_completeness", ok=True),
                _make_gate("gate_truth_facts_completeness", ok=True),
            ],
            issues=[
                _make_issue(
                    "gate_truth_layer_completeness",
                    severity="warn",
                    error_code="TRUTH_PARTIAL",
                ),
            ],
            ok=True,
        )
        recs = recommend_action(tmp_path, report)
        assert all("--from-worker W2" not in r["command"] for r in recs), (
            f"W2 must NOT appear when all truth gates pass, got: {recs}"
        )

    def test_kb_howto_structure_recommends_w10(self, tmp_path: Path) -> None:
        """TC-3213: gate_kb_howto_structure failure → recommend W10."""
        report = _make_report(
            gates=[_make_gate("gate_kb_howto_structure", ok=False)],
            issues=[
                _make_issue(
                    "gate_kb_howto_structure",
                    severity="error",
                    error_code="GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        workers = [r["command"].split("--from-worker ")[-1] for r in recs]
        assert "W10" in workers, f"Expected W10 for KB howto, got: {workers}"

    def test_kb_howto_error_code_recommends_w10(self, tmp_path: Path) -> None:
        """TC-3213: GATE_KB_HOWTO_* error code → recommend W10."""
        report = _make_report(
            gates=[_make_gate("gate_kb_howto_mandatory", ok=False)],
            issues=[
                _make_issue(
                    "gate_kb_howto_mandatory",
                    severity="error",
                    error_code="GATE_KB_HOWTO_MANDATORY_TOPIC_MISSING",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        workers = [r["command"].split("--from-worker ")[-1] for r in recs]
        assert "W10" in workers, f"Expected W10 for KB howto error code, got: {workers}"

    def test_g20_issues_recommend_w10(self, tmp_path: Path) -> None:
        """TC-3213: G20-005 error → recommend W10."""
        report = _make_report(
            gates=[_make_gate("gate_20_cross_page_consistency", ok=False)],
            issues=[
                _make_issue(
                    "gate_20_cross_page_consistency",
                    severity="error",
                    error_code="G20-005",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        workers = [r["command"].split("--from-worker ")[-1] for r in recs]
        assert "W10" in workers, f"Expected W10 for G20 issues, got: {workers}"

    def test_kb_howto_and_scaffold_both_route_to_single_w10(
        self, tmp_path: Path
    ) -> None:
        """TC-3213: KB howto + scaffold issues → single W10 recommendation (dedup)."""
        report = _make_report(
            gates=[
                _make_gate("gate_scaffold_leak", ok=False),
                _make_gate("gate_kb_howto_structure", ok=False),
            ],
            issues=[
                _make_issue("gate_scaffold_leak", "error", "SCAFFOLD_LEAK"),
                _make_issue(
                    "gate_kb_howto_structure",
                    "error",
                    "GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        workers = [r["command"].split("--from-worker ")[-1] for r in recs]
        # W10 should appear exactly once (dedup via seen_workers)
        assert workers.count("W10") == 1, (
            f"Expected exactly 1 W10 recommendation, got: {workers}"
        )


# ── TC-3580: load_validation_report fallback behaviour ───────────────────────


class TestValidateOutputFile:
    """Tests for TC-3580: W9 report preferred; .site.json fallback only."""

    def _write(self, artifacts: Path, filename: str, data: dict) -> Path:
        artifacts.mkdir(parents=True, exist_ok=True)
        p = artifacts / filename
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_w9_report_preferred_when_both_exist(self, tmp_path: Path) -> None:
        """When both validation_report.json and .site.json exist, W9 report wins."""
        arts = tmp_path / "artifacts"
        w9_data = _make_report(
            gates=[_make_gate("gate_w9", ok=True)],
            issues=[],
        )
        w9_data["_source"] = "w9"
        self._write(arts, "validation_report.json", w9_data)

        site_data = _make_report(gates=[], issues=[])
        site_data["_source"] = "site"
        self._write(arts, "validation_report.site.json", site_data)

        loaded = load_validation_report(tmp_path)
        assert loaded.get("_source") == "w9", "Expected W9 report to be loaded"

    def test_site_report_fallback_loads_when_w9_absent(self, tmp_path: Path) -> None:
        """When only .site.json exists, it is loaded as a fallback."""
        arts = tmp_path / "artifacts"
        site_data = _make_report(gates=[], issues=[])
        site_data["_source"] = "site"
        self._write(arts, "validation_report.site.json", site_data)

        loaded = load_validation_report(tmp_path)
        assert loaded.get("_source") == "site", "Expected site report to be loaded as fallback"

    def test_site_report_fallback_emits_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Fallback to .site.json emits a WARNING log."""
        import logging

        arts = tmp_path / "artifacts"
        site_data = _make_report(gates=[], issues=[])
        self._write(arts, "validation_report.site.json", site_data)

        with caplog.at_level(logging.WARNING, logger="launch.cli.triage"):
            load_validation_report(tmp_path)

        assert any("site.json" in r.message.lower() or "site report" in r.message.lower()
                   for r in caplog.records), (
            "Expected a WARNING about falling back to site report"
        )

    def test_missing_both_raises_file_not_found(self, tmp_path: Path) -> None:
        """When neither report exists, FileNotFoundError is raised."""
        (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
        with pytest.raises(FileNotFoundError, match="validation_report.json"):
            load_validation_report(tmp_path)


# ── TC-3600: Triage rule for gate_4_frontmatter_required_fields ──────────


class TestGate4FrontmatterTriageRule:
    """TC-3600: gate_4_frontmatter_required_fields issues should recommend W10."""

    def test_gate4_issue_recommends_w10(self, tmp_path: Path) -> None:
        """Report with gate_4_frontmatter_required_fields issue recommends W10."""
        report = _make_report(
            gates=[
                _make_gate("gate_4_frontmatter_required_fields", ok=False),
                _make_gate("gate_17_formatting_quality", ok=True),
            ],
            issues=[
                _make_issue(
                    "gate_4_frontmatter_required_fields",
                    "error",
                    "G4-001",
                    "Missing title in frontmatter",
                ),
            ],
        )
        recs = recommend_action(tmp_path, report)
        workers = [
            r["command"].split("--from-worker ")[-1].strip()
            for r in recs
        ]
        assert "W10" in workers
        # The reason should mention frontmatter
        w10_recs = [r for r in recs if "--from-worker W10" in r["command"]]
        assert any("rontmatter" in r["reason"] for r in w10_recs)

    def test_gate4_only_failing_does_not_get_w9_fallback(self, tmp_path: Path) -> None:
        """When only gate_4 is failing, triage should NOT fall back to W9."""
        report = _make_report(
            gates=[
                _make_gate("gate_4_frontmatter_required_fields", ok=False),
            ],
            issues=[
                _make_issue(
                    "gate_4_frontmatter_required_fields",
                    "error",
                    "G4-002",
                    "Missing layout field",
                ),
            ],
        )
        recs = recommend_action(tmp_path, report)
        # Should have W10 recommendation, not just W9 fallback
        assert len(recs) >= 1
        first_worker = recs[0]["command"].split("--from-worker ")[-1].strip()
        assert first_worker == "W10"


# ── TC-3614: Stable recommendation_id ────────────────────────────────────────


class TestRecommendationId:
    """TC-3614: Every recommendation must carry a stable 'id' field.

    The id is derived from the match function name + worker key, NOT from the
    human-readable reason label.  Rewording a label must NOT change the id.
    """

    def test_all_recommendations_have_id(self, tmp_path: Path) -> None:
        """Every recommendation returned by recommend_action has a non-empty 'id'."""
        report = _make_report(
            gates=[
                _make_gate("gate_truth_layer_completeness", ok=False),
                _make_gate("gate_15b_code_fence_api", ok=False),
                _make_gate("gate_scaffold_leak", ok=False),
            ],
            issues=[
                _make_issue("gate_truth_layer_completeness", "error", "TRUTH_MISSING"),
                _make_issue("gate_15b_code_fence_api", "error", "CF-001"),
                _make_issue("gate_scaffold_leak", "error", "SCAFFOLD"),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        for rec in recs:
            assert "id" in rec, f"Recommendation missing 'id': {rec}"
            assert rec["id"], f"Recommendation 'id' is empty: {rec}"

    def test_fallback_recommendation_has_id(self, tmp_path: Path) -> None:
        """Fallback W9 recommendation also has a stable 'id'."""
        # All gates pass — no specific pattern → fallback
        report = _make_report(
            gates=[_make_gate("gate_1_schema_validation", ok=True)],
            issues=[_make_issue("gate_1_schema_validation", severity="info")],
        )
        recs = recommend_action(tmp_path, report)
        assert len(recs) == 1
        assert recs[0]["id"] == "triage:fallback->W9"

    def test_recommendation_id_is_deterministic(self, tmp_path: Path) -> None:
        """Same failing gates always produce the same recommendation ids."""
        report = _make_report(
            gates=[_make_gate("gate_truth_layer_completeness", ok=False)],
            issues=[_make_issue("gate_truth_layer_completeness", "error", "TRUTH_MISSING")],
            ok=False,
        )
        recs1 = recommend_action(tmp_path, report)
        recs2 = recommend_action(tmp_path, report)
        ids1 = [r["id"] for r in recs1]
        ids2 = [r["id"] for r in recs2]
        assert ids1 == ids2, f"Recommendation ids are not deterministic: {ids1} vs {ids2}"

    def test_recommendation_id_independent_of_reason_wording(self, tmp_path: Path) -> None:
        """The 'id' field is derived from function name + worker, NOT from reason label.

        This is verified by inspecting the id format: it must start with 'triage:'
        and contain '->' separating the rule name from the worker key.
        It must NOT contain the label text verbatim.
        """
        report = _make_report(
            gates=[_make_gate("gate_truth_layer_completeness", ok=False)],
            issues=[_make_issue("gate_truth_layer_completeness", "error", "TRUTH_MISSING")],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        w2_recs = [r for r in recs if "--from-worker W2" in r["command"]]
        assert len(w2_recs) >= 1
        rec = w2_recs[0]
        # Format: "triage:<fn_name>->W2"
        assert rec["id"].startswith("triage:"), f"id must start with 'triage:': {rec['id']}"
        assert "->W2" in rec["id"], f"id must contain '->W2': {rec['id']}"
        # Must NOT just be the reason text
        assert rec["id"] != rec["reason"], "id must be independent of reason label"


# ── GAP-4 fix: REF_ routes to W5 (content generation) ─────────────────────


class TestRefCompletenessRoutesToW5:
    """REF_ issues require content generation — must route to W5, not W10."""

    def test_ref_missing_code_fence_routes_to_w5(self, tmp_path: Path) -> None:
        report = _make_report(
            gates=[_make_gate("gate_reference_completeness", ok=False)],
            issues=[
                _make_issue(
                    "gate_reference_completeness",
                    severity="error",
                    error_code="REF_MISSING_CODE_FENCE",
                ),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        w5_recs = [r for r in recs if "--from-worker W5" in r["command"]]
        assert len(w5_recs) >= 1, (
            f"Expected REF_ to route to W5, got: {[r['command'] for r in recs]}"
        )

    def test_w10_recommendations_have_distinct_ids_per_rule(self, tmp_path: Path) -> None:
        """Different triage rules for W10 produce different ids (dedup means only 1 W10 rec).

        Because seen_workers dedup fires, only the FIRST W10-matching rule produces
        a recommendation. Verify that this recommendation has a non-empty stable id.
        """
        report = _make_report(
            gates=[
                _make_gate("gate_scaffold_leak", ok=False),
                _make_gate("gate_kb_howto_structure", ok=False),
            ],
            issues=[
                _make_issue("gate_scaffold_leak", "error", "SCAFFOLD"),
                _make_issue("gate_kb_howto_structure", "error", "KB_HOWTO"),
            ],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        w10_recs = [r for r in recs if "--from-worker W10" in r["command"]]
        assert len(w10_recs) == 1, "Dedup: only one W10 recommendation expected"
        assert w10_recs[0]["id"].startswith("triage:")
        assert "->W10" in w10_recs[0]["id"]

    def test_rule_id_takes_priority_over_function_name(self, tmp_path: Path) -> None:
        """TC-3615: Emitted id uses rule_id slug, not the match function's __name__.

        The id must NOT contain the old '_match_' prefix that would appear if
        function names were used.
        """
        report = _make_report(
            gates=[_make_gate("gate_truth_layer_completeness", ok=False)],
            issues=[_make_issue("gate_truth_layer_completeness", "error", "TRUTH_MISSING")],
            ok=False,
        )
        recs = recommend_action(tmp_path, report)
        w2_recs = [r for r in recs if "--from-worker W2" in r["command"]]
        assert len(w2_recs) >= 1
        rec_id = w2_recs[0]["id"]
        # Must use frozen rule_id slug "truth", not function name "_match_truth"
        assert rec_id == "triage:truth->W2", (
            f"Expected 'triage:truth->W2' but got {rec_id!r}. "
            "TC-3615: rule_id slug must be used, not match.__name__."
        )
        assert "_match_" not in rec_id, (
            f"id must not contain '_match_' prefix (function name leaked): {rec_id!r}"
        )

    def test_renaming_match_function_does_not_change_id(self, tmp_path: Path) -> None:
        """TC-3615: Renaming the match function does NOT change the emitted id.

        Simulated by temporarily patching __name__ on the match function to a
        different value. The emitted id must still be the frozen rule_id slug.
        """
        from launch.cli import triage as _triage

        # Grab the scaffold rule's match fn and patch its __name__
        scaffold_rule = next(
            r for r in _triage._RECOMMENDATION_RULES
            if r.get("rule_id") == "scaffold_or_fmt"
        )
        original_name = scaffold_rule["match"].__name__
        scaffold_rule["match"].__name__ = "_RENAMED_MATCH_FN_DO_NOT_USE"
        try:
            report = _make_report(
                gates=[_make_gate("gate_scaffold_leak", ok=False)],
                issues=[_make_issue("gate_scaffold_leak", "error", "SCAFFOLD")],
                ok=False,
            )
            recs = recommend_action(tmp_path, report)
            w10_recs = [r for r in recs if "--from-worker W10" in r["command"]]
            assert len(w10_recs) >= 1
            rec_id = w10_recs[0]["id"]
            # Must still be the frozen slug, not the patched __name__
            assert rec_id == "triage:scaffold_or_fmt->W10", (
                f"Expected frozen slug but got {rec_id!r}. "
                "TC-3615: renaming the fn must NOT change the emitted id."
            )
            assert "_RENAMED_MATCH_FN_DO_NOT_USE" not in rec_id
        finally:
            scaffold_rule["match"].__name__ = original_name
