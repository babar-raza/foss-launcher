"""Tests for TC-2434: W4 content policy engine."""
from __future__ import annotations
from launch.workers.w4_ia_planner.content_policy import (
    ContentPolicy,
    PolicyDecision,
    load_policy_config,
    DEFAULT_MIN_SCORE,
    _SCORE_NORMALIZATION_DIVISOR,
)


def _make_policy(min_score=0.5, dry_run=False):
    return ContentPolicy(min_score=min_score, dry_run_optional=dry_run)


def _candidate(slug, quality_score):
    return {"slug": slug, "quality_score": quality_score}


class TestPolicyEvaluation:
    def test_policy_accepts_high_score_candidate(self):
        policy = _make_policy(min_score=0.5)
        decision = policy.evaluate(_candidate("advanced-usage", 25), section="docs")
        assert decision.accepted is True
        assert abs(decision.normalized_score - (25 / 30.0)) < 1e-9
        assert decision.raw_score == 25.0
        assert decision.rejection_reason is None

    def test_policy_rejects_low_score_candidate(self):
        policy = _make_policy(min_score=0.5)
        decision = policy.evaluate(_candidate("low-quality", 3), section="docs")
        assert decision.accepted is False
        assert decision.normalized_score < 0.5
        assert decision.rejection_reason is not None
        assert "threshold" in decision.rejection_reason
    def test_policy_threshold_boundary_at_exact_min_score(self):
        policy = _make_policy(min_score=0.5)
        decision = policy.evaluate(_candidate("boundary-page", 15), section="kb")
        assert abs(decision.normalized_score - 0.5) < 1e-9
        assert decision.accepted is True
        assert decision.rejection_reason is None

    def test_score_clamped_at_1_0_for_very_high_raw(self):
        policy = _make_policy()
        decision = policy.evaluate(_candidate("big-page", 90), section="docs")
        assert decision.normalized_score == 1.0
        assert decision.accepted is True

    def test_zero_quality_score_candidate(self):
        policy = _make_policy(min_score=0.5)
        decision = policy.evaluate(_candidate("no-evidence", 0), section="blog")
        assert decision.normalized_score == 0.0
        assert decision.accepted is False

    def test_missing_quality_score_defaults_to_zero(self):
        policy = _make_policy(min_score=0.5)
        decision = policy.evaluate({"slug": "no-score-key"}, section="docs")
        assert decision.raw_score == 0.0
        assert decision.accepted is False

    def test_missing_slug_defaults_to_question_mark(self):
        policy = _make_policy()
        decision = policy.evaluate({"quality_score": 25}, section="docs")
        assert decision.candidate_slug == "?"

    def test_decisions_accumulate(self):
        policy = _make_policy()
        policy.evaluate(_candidate("page-a", 25), section="docs")
        policy.evaluate(_candidate("page-b", 3), section="docs")
        assert len(policy.decisions) == 2


class TestDryRunMode:
    def test_dry_run_marks_not_rejects(self):
        policy = _make_policy(min_score=0.5, dry_run=True)
        decision = policy.evaluate(_candidate("good-page", 25), section="docs")
        assert decision.accepted is True
        assert decision.is_dry_run is True

    def test_dry_run_false_is_default(self):
        policy = _make_policy(min_score=0.5, dry_run=False)
        decision = policy.evaluate(_candidate("page", 25), section="docs")
        assert decision.is_dry_run is False

    def test_dry_run_applies_to_all_decisions(self):
        policy = _make_policy(dry_run=True)
        policy.evaluate(_candidate("a", 25), section="docs")
        policy.evaluate(_candidate("b", 3), section="docs")
        assert all(d.is_dry_run for d in policy.decisions)


class TestLoadPolicyConfig:
    def test_load_policy_config_no_key_returns_none(self):
        result = load_policy_config({})
        assert result is None

    def test_load_policy_config_null_key_returns_none(self):
        result = load_policy_config({"policy": None})
        assert result is None
    def test_load_policy_config_empty_key_uses_defaults(self):
        result = load_policy_config({"policy": {}})
        assert result is not None
        assert result.min_score == DEFAULT_MIN_SCORE
        assert result.dry_run_optional is False

    def test_load_policy_config_custom_min_score(self):
        result = load_policy_config({"policy": {"optional_content_min_score": 0.7}})
        assert result is not None
        assert abs(result.min_score - 0.7) < 1e-9

    def test_load_policy_config_dry_run_true(self):
        result = load_policy_config({"policy": {"dry_run_optional": True}})
        assert result is not None
        assert result.dry_run_optional is True

    def test_load_policy_config_full_config(self):
        result = load_policy_config({
            "policy": {
                "optional_content_min_score": 0.8,
                "dry_run_optional": True,
            }
        })
        assert result is not None
        assert abs(result.min_score - 0.8) < 1e-9
        assert result.dry_run_optional is True


class TestToArtifact:
    def test_to_artifact_schema_structure(self):
        policy = _make_policy(min_score=0.5)
        policy.evaluate(_candidate("a", 25), section="docs")
        policy.evaluate(_candidate("b", 3), section="docs")
        artifact = policy.to_artifact()
        assert "schema_version" in artifact
        assert artifact["schema_version"] == "1.0"
        assert "policy" in artifact
        assert "summary" in artifact
        assert "decisions" in artifact

    def test_to_artifact_summary_counts(self):
        policy = _make_policy(min_score=0.5)
        policy.evaluate(_candidate("a", 25), section="docs")
        policy.evaluate(_candidate("b", 3), section="docs")
        policy.evaluate(_candidate("c", 15), section="docs")
        artifact = policy.to_artifact()
        assert artifact["summary"]["total_candidates"] == 3
        assert artifact["summary"]["accepted"] == 2
        assert artifact["summary"]["rejected"] == 1
    def test_to_artifact_decisions_sorted_by_section_slug(self):
        policy = _make_policy()
        policy.evaluate(_candidate("zebra", 20), section="docs")
        policy.evaluate(_candidate("alpha", 20), section="kb")
        policy.evaluate(_candidate("beta", 20), section="docs")
        artifact = policy.to_artifact()
        decisions = artifact["decisions"]
        slugs_sections = [(d["section"], d["slug"]) for d in decisions]
        assert slugs_sections == sorted(slugs_sections)

    def test_to_artifact_decisions_fields(self):
        policy = _make_policy(min_score=0.5)
        policy.evaluate(_candidate("page-x", 25), section="docs")
        artifact = policy.to_artifact()
        d = artifact["decisions"][0]
        assert "slug" in d
        assert "section" in d
        assert "normalized_score" in d
        assert "accepted" in d
        assert "rejection_reason" in d
        assert "is_dry_run" in d

    def test_to_artifact_normalized_score_rounded(self):
        policy = _make_policy()
        policy.evaluate(_candidate("p", 10), section="docs")
        artifact = policy.to_artifact()
        score = artifact["decisions"][0]["normalized_score"]
        assert score == 0.3333

    def test_to_artifact_rejection_reason_null_for_accepted(self):
        policy = _make_policy(min_score=0.5)
        policy.evaluate(_candidate("good", 25), section="docs")
        artifact = policy.to_artifact()
        assert artifact["decisions"][0]["rejection_reason"] is None

    def test_to_artifact_empty_decisions(self):
        policy = _make_policy()
        artifact = policy.to_artifact()
        assert artifact["summary"]["total_candidates"] == 0
        assert artifact["summary"]["accepted"] == 0
        assert artifact["summary"]["rejected"] == 0
        assert artifact["decisions"] == []

    def test_to_artifact_policy_config_reflected(self):
        policy = ContentPolicy(min_score=0.75, dry_run_optional=True)
        artifact = policy.to_artifact()
        assert artifact["policy"]["optional_content_min_score"] == 0.75
        assert artifact["policy"]["dry_run_optional"] is True
