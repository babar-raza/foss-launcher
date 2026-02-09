"""Tests for W5.5 ContentReviewer LLM regeneration.

TC-1100-P5: W5.5 ContentReviewer Phase 5 - Tests
"""
import pytest
from pathlib import Path

from launch.workers.w5_5_content_reviewer.fixes.llm_regen import (
    spawn_enhancement_agents,
    build_enhancement_prompt,
)


class TestSpawnEnhancementAgents:
    """Test agent spawning logic.

    Testing: mocked
    """

    def test_offline_mode_skips(self, tmp_path):
        """Should skip all agents in offline mode.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "test"}
        ]
        run_config = {"offline_mode": True, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert len(result) == 1
        assert result[0]["status"] == "skipped"
        assert "Offline mode" in result[0]["error"]

    def test_review_disabled_skips(self, tmp_path):
        """Should skip when review_enabled is False.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "test"}
        ]
        run_config = {"offline_mode": False, "review_enabled": False}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert len(result) == 1
        assert result[0]["status"] == "skipped"
        assert "Review not enabled" in result[0]["error"]

    def test_no_llm_issues_skips(self, tmp_path):
        """Should skip when all issues are auto-fixable.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "warn",
             "auto_fixable": True, "message": "test"}
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert len(result) == 1
        assert result[0]["status"] == "skipped"
        assert "No issues requiring LLM" in result[0]["error"]

    def test_warn_severity_not_sent_to_llm(self, tmp_path):
        """Non-auto-fixable warns should NOT spawn agents (only error/blocker).

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "warn",
             "auto_fixable": False, "message": "test"}
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert len(result) == 1
        assert result[0]["status"] == "skipped"

    def test_spawns_content_enhancer(self, tmp_path):
        """Should spawn content enhancer for content quality errors.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "Poor readability"}
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert any(r["agent_type"] == "content_enhancer" for r in result)
        enhancer = [r for r in result if r["agent_type"] == "content_enhancer"][0]
        assert enhancer["status"] == "success"
        assert enhancer["issues_addressed"] == 1

    def test_spawns_technical_fixer(self, tmp_path):
        """Should spawn technical fixer for technical accuracy errors.

        Testing: mocked
        """
        issues = [
            {"check": "technical_accuracy.code_syntax", "severity": "error",
             "auto_fixable": False, "message": "Broken code"}
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert any(r["agent_type"] == "technical_fixer" for r in result)

    def test_spawns_usability_improver(self, tmp_path):
        """Should spawn usability improver for usability errors.

        Testing: mocked
        """
        issues = [
            {"check": "usability.navigation", "severity": "error",
             "auto_fixable": False, "message": "Missing TOC"}
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert any(r["agent_type"] == "usability_improver" for r in result)

    def test_multiple_dimensions_spawn_multiple_agents(self, tmp_path):
        """Should spawn separate agents for different dimensions.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "test"},
            {"check": "technical_accuracy.code_syntax", "severity": "blocker",
             "auto_fixable": False, "message": "test"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        agent_types = {r["agent_type"] for r in result}
        assert "content_enhancer" in agent_types
        assert "technical_fixer" in agent_types

    def test_backwards_compat_no_review_enabled_key(self, tmp_path):
        """Should handle missing review_enabled key (defaults to False).

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "test"}
        ]
        run_config = {}  # No review_enabled key
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert result[0]["status"] == "skipped"

    def test_blocker_severity_triggers_agent(self, tmp_path):
        """Blocker severity issues should trigger agent spawning.

        Testing: mocked
        """
        issues = [
            {"check": "usability.accessibility", "severity": "blocker",
             "auto_fixable": False, "message": "Critical accessibility issue"}
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        assert any(r["agent_type"] == "usability_improver" for r in result)

    def test_all_three_agents_spawned(self, tmp_path):
        """Should spawn all 3 agent types when issues span all dimensions.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "test"},
            {"check": "technical_accuracy.code_syntax", "severity": "error",
             "auto_fixable": False, "message": "test"},
            {"check": "usability.navigation", "severity": "blocker",
             "auto_fixable": False, "message": "test"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        agent_types = sorted(r["agent_type"] for r in result)
        assert agent_types == sorted(["content_enhancer", "technical_fixer", "usability_improver"])

    def test_issues_summary_in_result(self, tmp_path):
        """Agent results should include issues_summary with check/severity/message.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "Grade level too high"}
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        enhancer = [r for r in result if r["agent_type"] == "content_enhancer"][0]
        assert "issues_summary" in enhancer
        assert enhancer["issues_summary"][0]["message"] == "Grade level too high"


class TestBuildEnhancementPrompt:
    """Test prompt building."""

    def test_builds_prompt_with_issues(self):
        """Should build prompt containing issues."""
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "message": "Grade level too high", "location": {"line": 42}}
        ]
        prompt = build_enhancement_prompt(
            "content_enhancer", issues, "# Test Content", {"product_name": "Test"}
        )
        assert "Grade level too high" in prompt
        assert "Test Content" in prompt

    def test_builds_prompt_with_context(self):
        """Should include product context in prompt."""
        issues = [{"check": "test", "severity": "warn", "message": "t", "location": {}}]
        prompt = build_enhancement_prompt(
            "technical_fixer", issues, "# Doc", {"product_name": "Aspose.3D"}
        )
        assert "Aspose.3D" in prompt

    def test_caps_context_size(self):
        """Should cap context to prevent prompt overflow."""
        large_context = {"data": "x" * 10000}
        issues = [{"check": "test", "severity": "warn", "message": "t", "location": {}}]
        prompt = build_enhancement_prompt(
            "content_enhancer", issues, "# Doc", large_context
        )
        # Context is capped at 5000 chars in the source, so prompt should be bounded
        assert len(prompt) < 20000

    def test_includes_severity_in_prompt(self):
        """Should include severity level in issue listing."""
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "message": "Too complex", "location": {"line": 10}}
        ]
        prompt = build_enhancement_prompt(
            "content_enhancer", issues, "# Content", {}
        )
        assert "ERROR" in prompt

    def test_includes_line_number_in_prompt(self):
        """Should include line number in issue listing."""
        issues = [
            {"check": "content_quality.readability", "severity": "warn",
             "message": "Issue at line", "location": {"line": 55}}
        ]
        prompt = build_enhancement_prompt(
            "content_enhancer", issues, "# Content", {}
        )
        assert "55" in prompt

    def test_multiple_issues_all_listed(self):
        """Should list all issues in prompt."""
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "message": "Issue Alpha", "location": {"line": 1}},
            {"check": "content_quality.tone", "severity": "warn",
             "message": "Issue Beta", "location": {"line": 20}},
        ]
        prompt = build_enhancement_prompt(
            "content_enhancer", issues, "# Content", {}
        )
        assert "Issue Alpha" in prompt
        assert "Issue Beta" in prompt

    def test_fallback_template_used_when_no_agent_file(self):
        """Should use fallback template when agent file doesn't exist."""
        issues = [{"check": "test", "severity": "warn", "message": "t", "location": {}}]
        prompt = build_enhancement_prompt(
            "nonexistent_agent_type", issues, "# Content", {}
        )
        # Fallback template includes "Fix all listed issues"
        assert "Fix all listed issues" in prompt
