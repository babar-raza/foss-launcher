"""Tests for prose_scorer module (TC-PROSE-01 Phase 4)."""
from __future__ import annotations

from launcher.models.evaluation import Finding
from launcher.workers.evaluate.prose_scorer import compute_prose_score


def _f(check: str, severity: str) -> Finding:
    """Shortcut to create a Finding."""
    return Finding(check=check, message="test", severity=severity, location="slug")


class TestComputeProseScore:
    def test_no_findings_returns_100(self):
        assert compute_prose_score([]) == 100.0

    def test_non_prose_findings_ignored(self):
        findings = [
            _f("safety", "high"),
            _f("seo", "medium"),
            _f("frontmatter", "low"),
        ]
        assert compute_prose_score(findings) == 100.0

    def test_det_medium_penalty(self):
        findings = [_f("prose_lead", "medium")]
        assert compute_prose_score(findings) == 92.0  # 100 - 8

    def test_det_low_penalty(self):
        findings = [_f("paragraph_monotony", "low")]
        assert compute_prose_score(findings) == 98.0  # 100 - 2

    def test_llm_medium_penalty(self):
        findings = [_f("prose_quality", "medium")]
        assert compute_prose_score(findings) == 95.0  # 100 - 5

    def test_llm_low_penalty(self):
        findings = [_f("prose_quality", "low")]
        assert compute_prose_score(findings) == 99.0  # 100 - 1

    def test_multiple_findings_accumulate(self):
        findings = [
            _f("prose_lead", "medium"),       # -8
            _f("sentence_openings", "medium"),  # -8
            _f("heading_echo", "medium"),       # -8
            _f("prose_quality", "medium"),      # -5
        ]
        assert compute_prose_score(findings) == 71.0  # 100 - 29

    def test_floor_at_zero(self):
        findings = [_f("prose_lead", "medium")] * 20  # -160
        assert compute_prose_score(findings) == 0.0

    def test_mixed_prose_and_non_prose(self):
        findings = [
            _f("prose_lead", "medium"),   # -8
            _f("safety", "high"),          # ignored
            _f("low_specificity", "medium"),  # -8
            _f("seo", "medium"),           # ignored
        ]
        assert compute_prose_score(findings) == 84.0  # 100 - 16

    def test_all_prose_check_names_recognized(self):
        checks = [
            "prose_lead", "sentence_openings", "explanation_gap",
            "paragraph_monotony", "heading_echo", "low_specificity",
            "prose_quality",
        ]
        findings = [_f(c, "medium") for c in checks]
        # 6 deterministic × 8 + 1 LLM × 5 = 53
        assert compute_prose_score(findings) == 47.0
