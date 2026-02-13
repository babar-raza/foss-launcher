"""Tests for W5.5 ContentReviewer LLM regeneration.

TC-1100-P5: W5.5 ContentReviewer Phase 5 - Tests
"""
import pytest
from pathlib import Path

from launch.workers.w5_5_content_reviewer.fixes.llm_regen import (
    spawn_enhancement_agents,
    build_enhancement_prompt,
    _format_api_surface,
    _format_snippets,
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
        """Should handle missing review_enabled key (defaults to True as of schema v1.2).

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "test"}
        ]
        run_config = {}  # No review_enabled key - defaults to True
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        # Should spawn agents (not skip) since review_enabled defaults to True
        assert result[0]["status"] == "success"
        assert result[0]["agent_type"] == "content_enhancer"

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


class TestFactualVerifierRouting:
    """Tests for TC-1406: factual verifier agent routing.

    Testing: mocked
    """

    def test_semantic_issues_route_to_factual_verifier(self, tmp_path):
        """Verify semantic_accuracy issues route to factual_verifier agent.

        Testing: mocked
        """
        issues = [
            {"check": "semantic_accuracy.api_hallucination", "severity": "error",
             "auto_fixable": False, "message": "Unknown method Scene.exportToFbx()"},
            {"check": "technical_accuracy.api_reference", "severity": "error",
             "auto_fixable": False, "message": "Other issue"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        agent_types = {r["agent_type"] for r in result}
        assert "factual_verifier" in agent_types
        verifier = [r for r in result if r["agent_type"] == "factual_verifier"][0]
        assert verifier["status"] == "success"
        assert verifier["issues_addressed"] == 1  # Only the semantic issue

    def test_no_semantic_issues_no_factual_verifier(self, tmp_path):
        """Verify factual_verifier not spawned without semantic issues.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "Hard to read"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        agent_types = {r["agent_type"] for r in result}
        assert "factual_verifier" not in agent_types

    def test_semantic_and_other_issues_spawn_multiple_agents(self, tmp_path):
        """Verify semantic issues spawn factual_verifier alongside other agents.

        Testing: mocked
        """
        issues = [
            {"check": "semantic_accuracy.licensing_accuracy", "severity": "error",
             "auto_fixable": False, "message": "Commercial license language"},
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "Grade level too high"},
            {"check": "usability.navigation", "severity": "error",
             "auto_fixable": False, "message": "Missing TOC"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        agent_types = {r["agent_type"] for r in result}
        assert "factual_verifier" in agent_types
        assert "content_enhancer" in agent_types
        assert "usability_improver" in agent_types

    def test_factual_verifier_includes_context(self, tmp_path):
        """Verify factual_verifier result includes api_surface and snippets context.

        Testing: mocked
        """
        issues = [
            {"check": "semantic_accuracy.api_hallucination", "severity": "error",
             "auto_fixable": False, "message": "Hallucinated API"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        verifier = [r for r in result if r["agent_type"] == "factual_verifier"][0]
        assert "context" in verifier
        assert "api_surface" in verifier["context"]
        assert "snippets" in verifier["context"]

    def test_factual_verifier_loads_artifacts(self, tmp_path):
        """Verify factual_verifier loads product_facts and snippet_catalog from run_dir.

        Testing: mocked
        """
        # Create artifacts directory with test data
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        import json
        (artifacts_dir / "product_facts.json").write_text(json.dumps({
            "api_surface_summary": {
                "classes": [{"name": "Scene", "methods": ["save", "load", "open"]}],
                "functions": [],
            }
        }), encoding="utf-8")
        (artifacts_dir / "snippet_catalog.json").write_text(json.dumps({
            "snippets": [{"description": "Load 3D scene", "content": "scene = Scene()"}]
        }), encoding="utf-8")

        issues = [
            {"check": "semantic_accuracy.api_hallucination", "severity": "error",
             "auto_fixable": False, "message": "Unknown method"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        verifier = [r for r in result if r["agent_type"] == "factual_verifier"][0]
        assert "Scene" in verifier["context"]["api_surface"]
        assert "Load 3D scene" in verifier["context"]["snippets"]

    def test_factual_verifier_content_relevance_routes(self, tmp_path):
        """Verify content_relevance semantic issues route to factual_verifier.

        Testing: mocked
        """
        issues = [
            {"check": "semantic_accuracy.content_relevance", "severity": "error",
             "auto_fixable": False, "message": "Content discusses unrelated product"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        agent_types = {r["agent_type"] for r in result}
        assert "factual_verifier" in agent_types

    def test_all_four_agents_spawned(self, tmp_path):
        """Should spawn all 4 agent types when issues span all dimensions.

        Testing: mocked
        """
        issues = [
            {"check": "content_quality.readability", "severity": "error",
             "auto_fixable": False, "message": "test"},
            {"check": "technical_accuracy.code_syntax", "severity": "error",
             "auto_fixable": False, "message": "test"},
            {"check": "usability.navigation", "severity": "blocker",
             "auto_fixable": False, "message": "test"},
            {"check": "semantic_accuracy.api_hallucination", "severity": "error",
             "auto_fixable": False, "message": "test"},
        ]
        run_config = {"offline_mode": False, "review_enabled": True}
        result = spawn_enhancement_agents(issues, tmp_path, run_config)
        agent_types = sorted(r["agent_type"] for r in result)
        assert agent_types == sorted([
            "content_enhancer", "technical_fixer",
            "usability_improver", "factual_verifier",
        ])


class TestFormatApiSurface:
    """Tests for TC-1406: _format_api_surface helper.

    Testing: mocked
    """

    def test_format_api_surface_with_classes(self):
        """Verify API surface formatting with classes and methods."""
        pf = {
            "api_surface_summary": {
                "classes": [{"name": "Scene", "methods": ["save", "load"]}],
                "functions": [],
            }
        }
        result = _format_api_surface(pf)
        assert "Scene" in result
        assert "save" in result
        assert "load" in result

    def test_format_api_surface_with_functions(self):
        """Verify API surface formatting with standalone functions."""
        pf = {
            "api_surface_summary": {
                "classes": [],
                "functions": [{"name": "convert_file"}, {"name": "merge_documents"}],
            }
        }
        result = _format_api_surface(pf)
        assert "convert_file()" in result
        assert "merge_documents()" in result

    def test_format_api_surface_class_without_methods(self):
        """Verify class without methods still shows class name."""
        pf = {
            "api_surface_summary": {
                "classes": [{"name": "License", "methods": []}],
                "functions": [],
            }
        }
        result = _format_api_surface(pf)
        assert "License" in result

    def test_format_api_surface_empty(self):
        """Verify empty API surface returns fallback message."""
        result = _format_api_surface({})
        assert "No API surface available" in result

    def test_format_api_surface_empty_summary(self):
        """Verify empty api_surface_summary returns fallback message."""
        pf = {"api_surface_summary": {"classes": [], "functions": []}}
        result = _format_api_surface(pf)
        assert "No API surface available" in result

    def test_format_api_surface_caps_methods_at_10(self):
        """Verify methods list is capped at 10 per class."""
        methods = [f"method_{i}" for i in range(20)]
        pf = {
            "api_surface_summary": {
                "classes": [{"name": "BigClass", "methods": methods}],
                "functions": [],
            }
        }
        result = _format_api_surface(pf)
        assert "method_9" in result
        assert "method_10" not in result

    def test_format_api_surface_multiple_classes(self):
        """Verify multiple classes are all listed."""
        pf = {
            "api_surface_summary": {
                "classes": [
                    {"name": "Scene", "methods": ["save"]},
                    {"name": "Node", "methods": ["add_child"]},
                ],
                "functions": [],
            }
        }
        result = _format_api_surface(pf)
        assert "Scene" in result
        assert "Node" in result


class TestFormatSnippets:
    """Tests for TC-1406: _format_snippets helper.

    Testing: mocked
    """

    def test_format_snippets_with_content(self):
        """Verify snippet formatting with description and content."""
        sc = {"snippets": [{"description": "Load scene", "content": "scene = Scene()"}]}
        result = _format_snippets(sc)
        assert "Load scene" in result
        assert "Scene()" in result

    def test_format_snippets_with_code_key(self):
        """Verify snippets using 'code' key instead of 'content'."""
        sc = {"snippets": [{"description": "Save file", "code": "doc.save('out.pdf')"}]}
        result = _format_snippets(sc)
        assert "Save file" in result
        assert "doc.save" in result

    def test_format_snippets_with_file_path_fallback(self):
        """Verify snippets fall back to file_path when no description."""
        sc = {"snippets": [{"file_path": "examples/demo.py", "content": "print('hello')"}]}
        result = _format_snippets(sc)
        assert "examples/demo.py" in result

    def test_format_snippets_empty(self):
        """Verify empty snippets returns fallback message."""
        result = _format_snippets({})
        assert "No snippets available" in result

    def test_format_snippets_empty_list(self):
        """Verify empty snippets list returns fallback message."""
        result = _format_snippets({"snippets": []})
        assert "No snippets available" in result

    def test_format_snippets_caps_at_20(self):
        """Verify snippets list is capped at 20."""
        snippets = [
            {"description": f"Snippet {i}", "content": f"code_{i}()"}
            for i in range(30)
        ]
        sc = {"snippets": snippets}
        result = _format_snippets(sc)
        assert "Snippet 19" in result
        assert "Snippet 20" not in result

    def test_format_snippets_truncates_long_code(self):
        """Verify individual snippet code is truncated at 500 chars."""
        long_code = "x" * 1000
        sc = {"snippets": [{"description": "Long snippet", "content": long_code}]}
        result = _format_snippets(sc)
        # The code block should be at most 500 chars of 'x'
        code_block_content = result.split("```\n")[1].split("\n```")[0]
        assert len(code_block_content) == 500

    def test_format_snippets_skips_no_code(self):
        """Verify snippets without code/content are skipped."""
        sc = {"snippets": [
            {"description": "No code snippet"},
            {"description": "Has code", "content": "real_code()"},
        ]}
        result = _format_snippets(sc)
        assert "No code snippet" not in result
        assert "Has code" in result
