"""Unit tests for W2 workflow and example enrichment.

Tests comprehensive coverage of enrich_workflow() and enrich_example()
functions including step ordering, complexity determination, time estimation,
description extraction, and audience level inference.

Spec: specs/03_product_facts_and_evidence.md (Workflow enrichment)
Spec: specs/05_example_curation.md (Example enrichment)
"""

from __future__ import annotations

import pytest
from pathlib import Path

from launch.workers.w2_facts_builder.enrich_workflows import (
    enrich_workflow,
    _determine_complexity,
    _estimate_time,
    _order_workflow_steps,
    _extract_step_name,
    _prettify_workflow_name,
    _generate_workflow_description,
    _get_snippet_tags,
)
from launch.workers.w2_facts_builder.enrich_examples import (
    enrich_example,
    _extract_description_from_code,
    _analyze_code_complexity,
    _infer_audience_level,
)


class TestWorkflowEnrichment:
    """Tests for enrich_workflow() function and helpers."""

    def test_enrich_workflow_step_ordering_install_first(self):
        """Test that install steps come first in ordering."""
        claims = [
            {"claim_id": "c1", "claim_text": "Use the advanced features"},
            {"claim_id": "c2", "claim_text": "Install via pip install package"},
            {"claim_id": "c3", "claim_text": "Configure the settings file"},
        ]

        result = enrich_workflow("installation", ["c1", "c2", "c3"], claims, [])

        steps = result.get("steps", [])
        assert len(steps) == 3
        assert steps[0]["claim_id"] == "c2"  # Install step
        assert steps[1]["claim_id"] == "c3"  # Config step
        assert steps[2]["claim_id"] == "c1"  # Advanced step

    def test_enrich_workflow_complexity_simple_1_2_steps(self):
        """Test that workflows with 1-2 steps are marked as 'simple'."""
        claims = [
            {"claim_id": "c1", "claim_text": "Step one"},
            {"claim_id": "c2", "claim_text": "Step two"},
        ]

        result = enrich_workflow("quick_start", ["c1", "c2"], claims, [])

        assert result["complexity"] == "simple"

    def test_enrich_workflow_complexity_moderate_3_5_steps(self):
        """Test that workflows with 3-5 steps are marked as 'moderate'."""
        claims = [
            {"claim_id": f"c{i}", "claim_text": f"Step {i}"} for i in range(5)
        ]
        claim_ids = [f"c{i}" for i in range(5)]

        result = enrich_workflow("setup", claim_ids, claims, [])

        assert result["complexity"] == "moderate"

    def test_enrich_workflow_complexity_complex_6plus_steps(self):
        """Test that workflows with 6+ steps are marked as 'complex'."""
        claims = [
            {"claim_id": f"c{i}", "claim_text": f"Step {i}"} for i in range(10)
        ]
        claim_ids = [f"c{i}" for i in range(10)]

        result = enrich_workflow("advanced", claim_ids, claims, [])

        assert result["complexity"] == "complex"

    def test_enrich_workflow_time_estimation_scales_with_steps(self):
        """Test that estimated time increases with step count."""
        # 2 steps
        claims_2 = [{"claim_id": f"c{i}", "claim_text": f"Step {i}"} for i in range(2)]
        result_2 = enrich_workflow("test", ["c0", "c1"], claims_2, [])

        # 10 steps
        claims_10 = [
            {"claim_id": f"c{i}", "claim_text": f"Step {i}"} for i in range(10)
        ]
        result_10 = enrich_workflow("test", [f"c{i}" for i in range(10)], claims_10, [])

        assert result_10["estimated_time_minutes"] > result_2["estimated_time_minutes"]

    def test_enrich_workflow_time_estimation_install_base(self):
        """Test that install workflows have lower base time (5 min)."""
        claims = [{"claim_id": "c1", "claim_text": "Install the package"}]

        result = enrich_workflow("installation", ["c1"], claims, [])

        # Install base: 5, plus 0 additional (1 step)
        assert result["estimated_time_minutes"] == 5

    def test_enrich_workflow_time_estimation_config_base(self):
        """Test that configuration workflows have medium base time (10 min)."""
        claims = [{"claim_id": "c1", "claim_text": "Configure the settings"}]

        result = enrich_workflow("configuration", ["c1"], claims, [])

        # Config base: 10, plus 0 additional (1 step)
        assert result["estimated_time_minutes"] == 10

    def test_enrich_workflow_step_ordering_full_sequence(self):
        """Test full step ordering: install → setup → config → basic → advanced."""
        claims = [
            {"claim_id": "c1", "claim_text": "Advanced custom configuration"},
            {"claim_id": "c2", "claim_text": "Basic usage example"},
            {"claim_id": "c3", "claim_text": "Install the package"},
            {"claim_id": "c4", "claim_text": "Initialize the project"},
            {"claim_id": "c5", "claim_text": "Configure settings"},
        ]
        claim_ids = ["c1", "c2", "c3", "c4", "c5"]

        result = enrich_workflow("complete", claim_ids, claims, [])
        steps = result["steps"]

        # Verify order
        assert steps[0]["claim_id"] == "c3"  # Install
        assert steps[1]["claim_id"] == "c4"  # Initialize (setup)
        assert steps[2]["claim_id"] == "c5"  # Configure
        assert steps[3]["claim_id"] == "c2"  # Basic
        assert steps[4]["claim_id"] == "c1"  # Advanced

    def test_enrich_workflow_generates_workflow_id(self):
        """Test that workflow_id is generated from tag."""
        claims = [{"claim_id": "c1", "claim_text": "Test"}]

        result = enrich_workflow("my_workflow", ["c1"], claims, [])

        assert result["workflow_id"] == "wf_my_workflow"
        assert result["workflow_tag"] == "my_workflow"

    def test_enrich_workflow_empty_claims(self):
        """Test handling of empty claim list."""
        result = enrich_workflow("empty", [], [], [])

        assert result["workflow_id"] == "wf_empty"
        assert result["steps"] == []
        assert result["complexity"] == "simple"
        assert result["estimated_time_minutes"] == 15  # Default base

    def test_enrich_workflow_snippet_matching(self):
        """Test that snippets are matched to claims by tag overlap."""
        claims = [
            {"claim_id": "c1", "claim_text": "Install the package"},
        ]
        snippets = [
            {"snippet_id": "s1", "tags": ["install", "quickstart"]},
            {"snippet_id": "s2", "tags": ["config"]},
        ]

        result = enrich_workflow("installation", ["c1"], claims, snippets)

        steps = result["steps"]
        assert steps[0]["snippet_id"] == "s1"  # Matched by 'install' tag

    def test_enrich_workflow_prettify_name(self):
        """Test that workflow names are prettified correctly."""
        result = enrich_workflow("quick_start", [], [], [])

        assert result["name"] == "Quick Start"
        assert result["title"] == "Quick Start"

    def test_enrich_workflow_description_templates(self):
        """Test that known workflow tags get template descriptions."""
        result_install = enrich_workflow("installation", [], [], [])
        result_quickstart = enrich_workflow("quickstart", [], [], [])
        result_config = enrich_workflow("configuration", [], [], [])

        assert "Install and set up" in result_install["description"]
        assert "Get started" in result_quickstart["description"]
        assert "Configure product settings" in result_config["description"]

    def test_enrich_workflow_snippet_tags_mapping(self):
        """Test that snippet tags are mapped from workflow tag."""
        result_install = enrich_workflow("installation", [], [], [])
        result_quickstart = enrich_workflow("quickstart", [], [], [])

        assert result_install["snippet_tags"] == ["install"]
        assert result_quickstart["snippet_tags"] == ["quickstart", "getting-started"]

    def test_determine_complexity_boundary_cases(self):
        """Test complexity determination at boundary thresholds."""
        # 1 step: simple
        assert _determine_complexity([{"claim_id": "c1"}]) == "simple"
        # 2 steps: simple
        assert _determine_complexity([{"claim_id": f"c{i}"} for i in range(2)]) == "simple"
        # 3 steps: moderate
        assert _determine_complexity([{"claim_id": f"c{i}"} for i in range(3)]) == "moderate"
        # 5 steps: moderate
        assert _determine_complexity([{"claim_id": f"c{i}"} for i in range(5)]) == "moderate"
        # 6 steps: complex
        assert _determine_complexity([{"claim_id": f"c{i}"} for i in range(6)]) == "complex"

    def test_extract_step_name_truncation(self):
        """Test that long step names are truncated to 60 chars."""
        long_text = "A" * 100
        result = _extract_step_name(long_text)

        assert len(result) == 60
        assert result.endswith("...")

    def test_prettify_workflow_name_handles_underscores_and_hyphens(self):
        """Test that prettify handles underscores and hyphens."""
        assert _prettify_workflow_name("quick_start") == "Quick Start"
        assert _prettify_workflow_name("end-to-end") == "End To End"
        assert _prettify_workflow_name("quick-start_guide") == "Quick Start Guide"


class TestExampleEnrichment:
    """Tests for enrich_example() function and helpers."""

    def test_enrich_example_description_from_triple_double_docstring(self, tmp_path):
        """Test description extraction from triple-double-quoted docstring."""
        example_file = tmp_path / "example.py"
        example_file.write_text(
            '''
"""
This example demonstrates how to use the feature.
It shows basic usage patterns.
"""

def main():
    pass
'''
        )

        example_info = {
            "example_id": "ex1",
            "title": "Example",
            "path": "example.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert "demonstrates how to use the feature" in result["description"]

    def test_enrich_example_description_from_triple_single_docstring(self, tmp_path):
        """Test description extraction from triple-single-quoted docstring."""
        example_file = tmp_path / "example.py"
        example_file.write_text(
            """
'''Example showing basic operations.'''

print("test")
"""
        )

        example_info = {
            "example_id": "ex1",
            "title": "Example",
            "path": "example.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert "showing basic operations" in result["description"]

    def test_enrich_example_description_from_comment(self, tmp_path):
        """Test description extraction from single-line comment."""
        example_file = tmp_path / "example.py"
        example_file.write_text(
            """
# This is a comment describing the example

print("test")
"""
        )

        example_info = {
            "example_id": "ex1",
            "title": "Example",
            "path": "example.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert "comment describing the example" in result["description"]

    def test_enrich_example_audience_level_beginner(self, tmp_path):
        """Test that short examples with 'beginner' keywords are marked beginner."""
        example_file = tmp_path / "getting_started.py"
        example_file.write_text(
            '''
"""Getting started with the library."""

print("Hello World")
'''
        )

        example_info = {
            "example_id": "ex1",
            "title": "Getting Started",
            "path": "getting_started.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["audience_level"] == "beginner"

    def test_enrich_example_audience_level_advanced(self, tmp_path):
        """Test that examples with 'advanced' keywords are marked advanced."""
        example_file = tmp_path / "advanced.py"
        example_file.write_text(
            '''
"""Advanced custom configuration and optimization."""

# Complex code
'''
            + "\n".join([f"line_{i} = complex_operation()" for i in range(50)])
        )

        example_info = {
            "example_id": "ex1",
            "title": "Advanced",
            "path": "advanced.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["audience_level"] == "advanced"

    def test_enrich_example_audience_level_intermediate(self, tmp_path):
        """Test that moderate complexity examples default to intermediate."""
        example_file = tmp_path / "moderate.py"
        example_file.write_text(
            '''
"""Standard example showing common patterns."""

'''
            + "\n".join([f"line_{i} = operation()" for i in range(80)])
        )

        example_info = {
            "example_id": "ex1",
            "title": "Moderate",
            "path": "moderate.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["audience_level"] == "intermediate"

    def test_enrich_example_complexity_trivial(self, tmp_path):
        """Test that short code (<10 LOC) is marked trivial."""
        example_file = tmp_path / "trivial.py"
        example_file.write_text(
            '''
def hello():
    print("Hello")

hello()
'''
        )

        example_info = {
            "example_id": "ex1",
            "title": "Trivial",
            "path": "trivial.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["complexity"] == "trivial"

    def test_enrich_example_complexity_simple(self, tmp_path):
        """Test that code <50 LOC is marked simple."""
        example_file = tmp_path / "simple.py"
        example_file.write_text("\n".join([f"line_{i} = value" for i in range(30)]))

        example_info = {
            "example_id": "ex1",
            "title": "Simple",
            "path": "simple.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["complexity"] == "simple"

    def test_enrich_example_complexity_moderate(self, tmp_path):
        """Test that code <200 LOC is marked moderate."""
        example_file = tmp_path / "moderate.py"
        example_file.write_text("\n".join([f"line_{i} = value" for i in range(100)]))

        example_info = {
            "example_id": "ex1",
            "title": "Moderate",
            "path": "moderate.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["complexity"] == "moderate"

    def test_enrich_example_complexity_complex(self, tmp_path):
        """Test that code >=200 LOC is marked complex."""
        example_file = tmp_path / "complex.py"
        example_file.write_text("\n".join([f"line_{i} = value" for i in range(250)]))

        example_info = {
            "example_id": "ex1",
            "title": "Complex",
            "path": "complex.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["complexity"] == "complex"

    def test_enrich_example_preserves_original_fields(self, tmp_path):
        """Test that original fields (example_id, title, tags) are preserved."""
        example_file = tmp_path / "test.py"
        example_file.write_text("print('test')")

        example_info = {
            "example_id": "ex_12345",
            "title": "Test Example",
            "path": "test.py",
            "tags": ["tag1", "tag2"],
            "primary_snippet_id": "snippet_999",
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["example_id"] == "ex_12345"
        assert result["title"] == "Test Example"
        assert result["tags"] == ["tag1", "tag2"]
        assert result["primary_snippet_id"] == "snippet_999"

    def test_enrich_example_fallback_description(self, tmp_path):
        """Test fallback description when no docstring present."""
        example_file = tmp_path / "test.py"
        example_file.write_text("print('no docstring')")

        example_info = {
            "example_id": "ex1",
            "title": "Test",
            "path": "test.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert "demonstrating product usage" in result["description"].lower()

    def test_enrich_example_missing_file(self, tmp_path):
        """Test graceful handling when example file doesn't exist."""
        example_info = {
            "example_id": "ex1",
            "title": "Missing",
            "path": "nonexistent.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        # Should return with fallback values
        assert result["example_id"] == "ex1"
        assert result["complexity"] == "trivial"
        assert result["audience_level"] == "beginner"
        assert "demonstrating product usage" in result["description"]

    def test_enrich_example_file_path_field(self, tmp_path):
        """Test that file_path is set correctly in output."""
        example_file = tmp_path / "test.py"
        example_file.write_text("print('test')")

        example_info = {
            "example_id": "ex1",
            "title": "Test",
            "path": "test.py",
            "tags": [],
        }

        result = enrich_example(example_info, tmp_path, [])

        assert result["file_path"] == "test.py"

    def test_analyze_code_complexity_ignores_comments_and_blank_lines(self):
        """Test that complexity analysis ignores comments and blank lines."""
        content = """
# Comment 1
# Comment 2

line1 = value1
line2 = value2
# Another comment
line3 = value3
"""
        result = _analyze_code_complexity(content)

        # Only 3 non-comment lines: trivial
        assert result == "trivial"

    def test_extract_description_multiline_docstring(self):
        """Test that only first line of multiline docstring is extracted."""
        content = '''
"""
First line of docstring.
Second line of docstring.
Third line of docstring.
"""
'''
        result = _extract_description_from_code(content)

        assert result == "First line of docstring."

    def test_infer_audience_level_keyword_priority(self):
        """Test that description keywords override complexity for audience."""
        # Simple complexity but 'advanced' in description → advanced
        assert _infer_audience_level("simple", "advanced techniques") == "advanced"

        # Complex complexity but 'beginner' in description → beginner
        assert _infer_audience_level("simple", "beginner tutorial") == "beginner"

        # Moderate complexity, no keywords → intermediate
        assert _infer_audience_level("moderate", "example code") == "intermediate"
