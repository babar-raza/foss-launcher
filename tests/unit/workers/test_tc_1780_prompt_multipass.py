"""Tests for TC-1780: PromptLoader, RichContext, and MultiPassOrchestrator.

Covers:
- PromptLoader: load(), validate_variables(), get_version(), load_with_fragments(), error handling
- RichContext: dataclass creation, to_prompt_vars(), build_rich_context()
- MultiPassOrchestrator: generate() 3-pass flow, deterministic fallback, hallucination detection
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from launch.prompts import PromptLoader, PromptResult, _parse_frontmatter
from launch.workers.w5_section_writer.rich_context import (
    RichContext,
    build_rich_context,
)
from launch.workers.w5_section_writer.multi_pass import (
    MultiPassOrchestrator,
    MultiPassResult,
    detect_hallucination_risk,
    _check_api_names,
    _check_claim_density,
    _check_code_blocks,
    _check_performance_claims,
)


# ---------------------------------------------------------------------------
# Helpers: temp prompt directory and mock LLM client
# ---------------------------------------------------------------------------

def _create_prompt_file(base: Path, name: str, content: str) -> Path:
    """Write a prompt template file under base directory."""
    path = base / f"{name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_prompt_dir(tmp_path: Path) -> Path:
    """Create a minimal prompt directory with system/page/fragment templates."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    # System prompt: content_architect
    _create_prompt_file(prompt_dir, "system/content_architect", """\
---
version: "1.0"
description: "Content architect for outline generation"
required_variables:
  - product_name
  - page_role
optional_variables:
  - primary_focus
  - depth_guidance
strategy:
  temperature: 0.0
  max_tokens: 2048
---
You are a content architect for {product_name}.
Page role: {page_role}
Focus: {primary_focus}
Depth: {depth_guidance}""")

    # System prompt: technical_writer
    _create_prompt_file(prompt_dir, "system/technical_writer", """\
---
version: "1.0"
description: "Technical writer for draft generation"
required_variables:
  - product_name
optional_variables:
  - audience
  - outline
strategy:
  temperature: 0.1
  max_tokens: 6144
---
Write content for {product_name}.
Audience: {audience}
Outline: {outline}""")

    # System prompt: content_editor
    _create_prompt_file(prompt_dir, "system/content_editor", """\
---
version: "1.0"
description: "Content editor for refinement"
required_variables:
  - product_name
optional_variables:
  - draft
  - cross_page_summaries
strategy:
  temperature: 0.3
  max_tokens: 4000
---
Refine the following draft for {product_name}.
Draft: {draft}
Context: {cross_page_summaries}""")

    # Page prompt: comprehensive_guide
    _create_prompt_file(prompt_dir, "pages/comprehensive_guide", """\
---
version: "2.0"
description: "Comprehensive guide page prompt"
required_variables:
  - product_name
  - audience
optional_variables:
  - tagline
strategy:
  temperature: 0.1
  max_tokens: 6144
---
Create a comprehensive guide for {product_name}.
Audience: {audience}
Tagline: {tagline}""")

    # Page prompt: default
    _create_prompt_file(prompt_dir, "pages/default", """\
---
version: "1.0"
description: "Default page prompt"
required_variables:
  - product_name
optional_variables: []
strategy:
  temperature: 0.3
---
Write a default page for {product_name}.""")

    # Fragment: anti_hallucination
    _create_prompt_file(prompt_dir, "fragments/anti_hallucination", """\
---
version: "1.0"
description: "Anti-hallucination rules"
required_variables: []
optional_variables: []
---
CRITICAL: Ground every statement with [claim: ID].""")

    # Fragment: product_context
    _create_prompt_file(prompt_dir, "fragments/product_context", """\
---
version: "1.0"
description: "Product context fragment"
required_variables: []
optional_variables: []
---
Product context for {product_name}.""")

    return prompt_dir


class MockLLMClient:
    """Mock LLM client for testing MultiPassOrchestrator."""

    def __init__(self, responses: Optional[List[str]] = None):
        self._responses = responses or []
        self._call_count = 0
        self.calls: List[Dict[str, Any]] = []

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        call_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self.calls.append({
            "messages": messages,
            "call_id": call_id,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format,
        })
        idx = self._call_count
        self._call_count += 1
        content = self._responses[idx] if idx < len(self._responses) else ""
        return {"content": content, "model": "mock", "usage": {}}


class MockRunConfig:
    """Mock run configuration."""

    def __init__(self, multi_pass_config: Optional[Dict] = None):
        self._mp_config = multi_pass_config or {}

    def get_multi_pass_config(self) -> Dict:
        return self._mp_config


def _make_rich_context(**overrides) -> RichContext:
    """Create a RichContext with sensible defaults, accepting overrides."""
    defaults = dict(
        product_name="Aspose.3D",
        tagline="3D file processing library",
        short_description="Process 3D files in Python.",
        audience="Python developers",
        license_info="MIT",
        page_role="comprehensive_guide",
        primary_focus="Getting started with 3D file processing",
        seo_keywords=["3d", "python", "aspose"],
        depth_guidance="Rich depth: 800+ words",
        page_claims=[
            {"claim_id": "c1", "claim_text": "Supports FBX format", "claim_kind": "feature"},
            {"claim_id": "c2", "claim_text": "Mesh creation API", "claim_kind": "feature"},
        ],
        workflows=[
            {"workflow_id": "wf1", "title": "Load and Save", "steps": ["open", "modify", "save"]},
        ],
        relevant_snippets=[
            {"snippet_id": "s1", "description": "Load FBX file", "code": "scene = Scene()\nscene.open('test.fbx')"},
        ],
        code_understanding={
            "classes": [{"name": "Scene"}, {"name": "Mesh"}],
            "functions": [{"name": "open"}, {"name": "save"}],
            "modules": [{"name": "aspose.threed"}],
        },
        sibling_pages=[{"slug": "tutorial", "title": "Tutorial"}],
        cross_page_summaries={"tutorial": "Tutorial page summary"},
        forbidden_topics=["pricing"],
        required_headings=["Overview", "Getting Started"],
        claim_quota={"feature": 5, "install": 2},
    )
    defaults.update(overrides)
    return RichContext(**defaults)


# ===========================================================================
# PART 1: PromptLoader Tests
# ===========================================================================

class TestPromptLoaderLoad:
    """Tests for PromptLoader.load()."""

    def test_load_basic_prompt(self, tmp_path: Path):
        """Load a prompt template and verify rendered text."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load("system/content_architect",
                             product_name="Aspose.3D",
                             page_role="comprehensive_guide")
        assert isinstance(result, PromptResult)
        assert "Aspose.3D" in result.text
        assert "comprehensive_guide" in result.text

    def test_load_returns_metadata(self, tmp_path: Path):
        """Metadata from frontmatter is parsed correctly."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load("system/content_architect",
                             product_name="X", page_role="guide")
        assert result.metadata["version"] == "1.0"
        assert result.metadata["description"] == "Content architect for outline generation"

    def test_load_returns_strategy(self, tmp_path: Path):
        """Strategy from frontmatter is extracted."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load("system/content_architect",
                             product_name="X", page_role="guide")
        assert result.strategy["temperature"] == 0.0
        assert result.strategy["max_tokens"] == 2048

    def test_load_fills_optional_variables(self, tmp_path: Path):
        """Optional variables are filled when provided."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load("system/content_architect",
                             product_name="X", page_role="guide",
                             primary_focus="3D Rendering")
        assert "3D Rendering" in result.text

    def test_load_missing_optional_uses_empty_string(self, tmp_path: Path):
        """Missing optional variables become empty strings."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load("system/content_architect",
                             product_name="X", page_role="guide")
        # primary_focus not provided, placeholder replaced with ""
        assert "{primary_focus}" not in result.text

    def test_load_caches_template(self, tmp_path: Path):
        """Second load uses cache (no re-read)."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        r1 = loader.load("system/content_architect",
                          product_name="A", page_role="x")
        r2 = loader.load("system/content_architect",
                          product_name="B", page_role="y")
        assert r1.version == r2.version  # Same hash from same template
        assert "A" in r1.text
        assert "B" in r2.text

    def test_load_missing_template_raises(self, tmp_path: Path):
        """FileNotFoundError when template doesn't exist."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        with pytest.raises(FileNotFoundError, match="not found"):
            loader.load("nonexistent/template")

    def test_load_name_stored_in_result(self, tmp_path: Path):
        """PromptResult.name is set to the prompt name."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load("system/content_architect",
                             product_name="X", page_role="guide")
        assert result.name == "system/content_architect"

    def test_load_with_list_variable(self, tmp_path: Path):
        """List values are stringified before substitution."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load("system/content_architect",
                             product_name="X", page_role="guide",
                             primary_focus=["step1", "step2"])
        assert "step1" in result.text
        assert "step2" in result.text

    def test_load_with_none_variable(self, tmp_path: Path):
        """None values become empty strings."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load("system/content_architect",
                             product_name="X", page_role="guide",
                             primary_focus=None)
        assert "{primary_focus}" not in result.text


class TestPromptLoaderValidateVariables:
    """Tests for PromptLoader.validate_variables()."""

    def test_all_required_present_returns_empty(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        missing = loader.validate_variables(
            "system/content_architect",
            {"product_name": "X", "page_role": "guide"},
        )
        assert missing == []

    def test_missing_required_returns_names(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        missing = loader.validate_variables(
            "system/content_architect",
            {"product_name": "X"},
        )
        assert "page_role" in missing

    def test_extra_keys_are_ignored(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        missing = loader.validate_variables(
            "system/content_architect",
            {"product_name": "X", "page_role": "guide", "extra_key": "val"},
        )
        assert missing == []

    def test_no_required_variables_returns_empty(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        missing = loader.validate_variables(
            "fragments/anti_hallucination",
            {},
        )
        assert missing == []


class TestPromptLoaderGetVersion:
    """Tests for PromptLoader.get_version()."""

    def test_returns_8_char_hex(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        version = loader.get_version("system/content_architect")
        assert len(version) == 8
        assert all(c in "0123456789abcdef" for c in version)

    def test_same_content_same_version(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        v1 = loader.get_version("system/content_architect")
        v2 = loader.get_version("system/content_architect")
        assert v1 == v2

    def test_different_content_different_version(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        v1 = loader.get_version("system/content_architect")
        v2 = loader.get_version("pages/comprehensive_guide")
        assert v1 != v2


class TestPromptLoaderLoadWithFragments:
    """Tests for PromptLoader.load_with_fragments()."""

    def test_fragment_appended_to_body(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load_with_fragments(
            "system/technical_writer",
            ["fragments/anti_hallucination"],
            product_name="Aspose.3D",
        )
        assert "Ground every statement" in result.text
        assert "Aspose.3D" in result.text

    def test_multiple_fragments_appended(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load_with_fragments(
            "system/technical_writer",
            ["fragments/anti_hallucination", "fragments/product_context"],
            product_name="Aspose.3D",
        )
        assert "Ground every statement" in result.text
        assert "Product context" in result.text

    def test_missing_fragment_is_skipped(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load_with_fragments(
            "system/technical_writer",
            ["fragments/nonexistent"],
            product_name="Aspose.3D",
        )
        # Should still render the main template without error
        assert "Aspose.3D" in result.text

    def test_empty_fragments_list(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load_with_fragments(
            "system/technical_writer",
            [],
            product_name="X",
        )
        assert "X" in result.text

    def test_fragment_variables_substituted(self, tmp_path: Path):
        """Variables in fragment body are also substituted."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        result = loader.load_with_fragments(
            "system/technical_writer",
            ["fragments/product_context"],
            product_name="Aspose.Cells",
        )
        assert "Product context for Aspose.Cells" in result.text


class TestParseFrontmatter:
    """Tests for _parse_frontmatter()."""

    def test_no_frontmatter(self):
        metadata, body = _parse_frontmatter("Just a body, no frontmatter.")
        assert metadata == {}
        assert "Just a body" in body

    def test_valid_frontmatter(self):
        raw = "---\nversion: 1.0\ndescription: test\n---\nBody text here."
        metadata, body = _parse_frontmatter(raw)
        assert "version" in metadata
        assert body == "Body text here."

    def test_unclosed_frontmatter(self):
        raw = "---\nversion: 1.0\nNo closing delimiter"
        metadata, body = _parse_frontmatter(raw)
        # Unclosed frontmatter: entire text returned as body
        assert metadata == {}


# ===========================================================================
# PART 2: RichContext Tests
# ===========================================================================

class TestRichContextDataclass:
    """Tests for RichContext dataclass creation and defaults."""

    def test_defaults_are_empty(self):
        ctx = RichContext()
        assert ctx.product_name == ""
        assert ctx.page_claims == []
        assert ctx.code_understanding == {}
        assert ctx.forbidden_topics == []
        assert ctx.claim_quota == {}

    def test_full_creation(self):
        ctx = _make_rich_context()
        assert ctx.product_name == "Aspose.3D"
        assert len(ctx.page_claims) == 2
        assert ctx.page_claims[0]["claim_id"] == "c1"
        assert len(ctx.seo_keywords) == 3
        assert ctx.required_headings == ["Overview", "Getting Started"]


class TestRichContextToPromptVars:
    """Tests for RichContext.to_prompt_vars()."""

    def test_returns_dict_of_strings(self):
        ctx = _make_rich_context()
        pv = ctx.to_prompt_vars()
        assert isinstance(pv, dict)
        for key, val in pv.items():
            assert isinstance(val, str), f"Key '{key}' is {type(val)}, not str"

    def test_product_profile_fields(self):
        ctx = _make_rich_context()
        pv = ctx.to_prompt_vars()
        assert pv["product_name"] == "Aspose.3D"
        assert pv["tagline"] == "3D file processing library"
        assert pv["audience"] == "Python developers"

    def test_seo_keywords_joined(self):
        ctx = _make_rich_context(seo_keywords=["fast", "python", "3d"])
        pv = ctx.to_prompt_vars()
        assert pv["seo_keywords"] == "fast, python, 3d"

    def test_empty_claims_returns_none_string(self):
        ctx = _make_rich_context(page_claims=[])
        pv = ctx.to_prompt_vars()
        assert pv["page_claims"] == "None"

    def test_claims_formatted(self):
        ctx = _make_rich_context()
        pv = ctx.to_prompt_vars()
        assert "[c1]" in pv["page_claims"]
        assert "Supports FBX format" in pv["page_claims"]

    def test_workflows_formatted(self):
        ctx = _make_rich_context()
        pv = ctx.to_prompt_vars()
        assert "[wf1]" in pv["workflows"]
        assert "3 steps" in pv["workflows"]

    def test_snippets_formatted(self):
        ctx = _make_rich_context()
        pv = ctx.to_prompt_vars()
        assert "[s1]" in pv["relevant_snippets"]

    def test_code_understanding_formatted(self):
        ctx = _make_rich_context()
        pv = ctx.to_prompt_vars()
        assert "Classes: 2" in pv["code_understanding"]
        assert "Functions: 2" in pv["code_understanding"]

    def test_sibling_pages_formatted(self):
        ctx = _make_rich_context()
        pv = ctx.to_prompt_vars()
        assert "tutorial" in pv["sibling_pages"]

    def test_forbidden_topics_formatted(self):
        ctx = _make_rich_context(forbidden_topics=["pricing", "internal"])
        pv = ctx.to_prompt_vars()
        assert "- pricing" in pv["forbidden_topics"]
        assert "- internal" in pv["forbidden_topics"]

    def test_claim_quota_formatted(self):
        ctx = _make_rich_context(claim_quota={"feature": 5})
        pv = ctx.to_prompt_vars()
        assert "feature: 5" in pv["claim_quota"]

    def test_empty_optional_fields_return_none_string(self):
        ctx = RichContext()
        pv = ctx.to_prompt_vars()
        assert pv["workflows"] == "None"
        assert pv["relevant_snippets"] == "None"
        assert pv["code_understanding"] == "None"
        assert pv["sibling_pages"] == "None"
        assert pv["forbidden_topics"] == "None"
        assert pv["claim_quota"] == "None"
        assert pv["cross_page_summaries"] == "None"

    def test_cross_page_summaries_formatted(self):
        ctx = _make_rich_context(cross_page_summaries={"overview": "Summary of overview"})
        pv = ctx.to_prompt_vars()
        assert "[overview]" in pv["cross_page_summaries"]
        assert "Summary of overview" in pv["cross_page_summaries"]

    def test_api_surface_formatted(self):
        ctx = _make_rich_context(api_surface={"classes": 2, "functions": 2, "modules": 1})
        pv = ctx.to_prompt_vars()
        assert "classes: 2" in pv["api_surface"]
        assert "functions: 2" in pv["api_surface"]


class TestBuildRichContext:
    """Tests for build_rich_context()."""

    def _make_product_facts(self) -> Dict:
        return {
            "product_name": "Aspose.3D",
            "positioning": {
                "tagline": "3D library",
                "value_proposition": "Process 3D files",
                "audience": "Python devs",
            },
            "metadata": {"license": "MIT"},
            "claims": [
                {"claim_id": "c1", "claim_text": "FBX support", "claim_kind": "feature"},
                {"claim_id": "c2", "claim_text": "OBJ export", "claim_kind": "feature"},
            ],
            "workflows": [
                {"workflow_id": "wf1", "title": "Load model", "steps": ["open", "save"]},
            ],
        }

    def _make_page(self) -> Dict:
        return {
            "slug": "getting-started",
            "title": "Getting Started",
            "page_role": "comprehensive_guide",
            "primary_focus": "Introduction",
            "seo_keywords": ["3d", "python"],
            "claim_ids": ["c1"],
            "workflow_ids": ["wf1"],
            "snippet_ids": ["s1"],
            "section_path": "docs/getting-started",
            "forbidden_topics": ["pricing"],
            "required_headings": ["Overview"],
            "claim_quota": {"feature": 3},
        }

    def _make_snippet_catalog(self) -> Dict:
        return {
            "snippets": [
                {"snippet_id": "s1", "description": "Load file", "code": "scene.open('x.fbx')"},
            ],
        }

    def test_product_profile_populated(self):
        ctx = build_rich_context(
            page=self._make_page(),
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
        )
        assert ctx.product_name == "Aspose.3D"
        assert ctx.tagline == "3D library"
        assert ctx.audience == "Python devs"
        assert ctx.license_info == "MIT"

    def test_page_metadata_populated(self):
        ctx = build_rich_context(
            page=self._make_page(),
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
        )
        assert ctx.page_role == "comprehensive_guide"
        assert ctx.primary_focus == "Introduction"
        assert ctx.seo_keywords == ["3d", "python"]
        assert "800+" in ctx.depth_guidance  # comprehensive_guide -> rich depth

    def test_claims_extracted_by_id(self):
        ctx = build_rich_context(
            page=self._make_page(),
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
        )
        assert len(ctx.page_claims) == 1
        assert ctx.page_claims[0]["claim_id"] == "c1"

    def test_workflows_extracted(self):
        ctx = build_rich_context(
            page=self._make_page(),
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
        )
        assert len(ctx.workflows) == 1
        assert ctx.workflows[0]["workflow_id"] == "wf1"

    def test_snippets_extracted(self):
        ctx = build_rich_context(
            page=self._make_page(),
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
        )
        assert len(ctx.relevant_snippets) == 1
        assert ctx.relevant_snippets[0]["snippet_id"] == "s1"

    def test_constraints_populated(self):
        ctx = build_rich_context(
            page=self._make_page(),
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
        )
        assert ctx.forbidden_topics == ["pricing"]
        assert ctx.required_headings == ["Overview"]
        assert ctx.claim_quota == {"feature": 3}

    def test_sibling_pages_extracted(self):
        page = self._make_page()
        page_plan = {
            "pages": [
                {"slug": "getting-started", "title": "Getting Started",
                 "section_path": "docs/getting-started"},
                {"slug": "tutorial", "title": "Tutorial",
                 "section_path": "docs/getting-started"},
                {"slug": "api-ref", "title": "API Reference",
                 "section_path": "docs/api"},
            ],
        }
        ctx = build_rich_context(
            page=page,
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            page_plan=page_plan,
        )
        assert len(ctx.sibling_pages) == 1
        assert ctx.sibling_pages[0]["slug"] == "tutorial"

    def test_empty_product_facts(self):
        """build_rich_context handles empty product_facts gracefully."""
        ctx = build_rich_context(
            page={"slug": "x"},
            product_facts={},
            snippet_catalog={},
        )
        assert ctx.product_name == ""
        assert ctx.page_claims == []
        assert ctx.workflows == []

    def test_depth_guidance_for_tutorial(self):
        page = {"page_role": "tutorial"}
        ctx = build_rich_context(
            page=page, product_facts={}, snippet_catalog={},
        )
        assert "Step-by-step" in ctx.depth_guidance

    def test_depth_guidance_for_faq(self):
        page = {"page_role": "faq"}
        ctx = build_rich_context(
            page=page, product_facts={}, snippet_catalog={},
        )
        assert "Concise answers" in ctx.depth_guidance

    def test_depth_guidance_for_unknown_role(self):
        page = {"page_role": "some_new_role"}
        ctx = build_rich_context(
            page=page, product_facts={}, snippet_catalog={},
        )
        assert "Standard" in ctx.depth_guidance

    def test_evidence_map_enriches_claims(self):
        page = self._make_page()
        evidence_map = {"c1": {"source": "readme.md", "line": 42}}
        ctx = build_rich_context(
            page=page,
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            evidence_map=evidence_map,
        )
        assert "evidence" in ctx.page_claims[0]
        assert ctx.page_claims[0]["evidence"]["source"] == "readme.md"

    def test_code_understanding_passed_through(self):
        code_understanding = {
            "classes": [{"name": "Scene"}],
            "functions": [{"name": "open"}],
            "modules": [],
        }
        ctx = build_rich_context(
            page=self._make_page(),
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            code_understanding=code_understanding,
        )
        assert ctx.code_understanding == code_understanding
        assert ctx.api_surface["classes"] == 1
        assert ctx.api_surface["functions"] == 1


# ===========================================================================
# PART 3: MultiPassOrchestrator Tests
# ===========================================================================

class TestMultiPassOrchestratorGenerate:
    """Tests for MultiPassOrchestrator.generate() 3-pass flow."""

    def _make_orchestrator(self, tmp_path: Path, responses: List[str],
                           mp_config: Optional[Dict] = None) -> MultiPassOrchestrator:
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        llm = MockLLMClient(responses)
        run_config = MockRunConfig(mp_config or {})
        return MultiPassOrchestrator(llm, loader, run_config)

    def _make_page(self) -> Dict:
        return {"slug": "getting-started", "title": "Getting Started"}

    def _valid_outline_json(self) -> str:
        return json.dumps({
            "sections": [
                {"heading": "Overview", "claim_ids": ["c1"]},
                {"heading": "Details", "claim_ids": ["c2"]},
            ]
        })

    def _valid_draft(self) -> str:
        return (
            "## Overview\n\n"
            "Aspose.3D supports FBX format [claim: c1] for seamless 3D file processing. "
            + " ".join(["This is detailed content."] * 40) + "\n\n"
            "## Details\n\n"
            "[claim: c2] Mesh creation API enables complex geometries. "
            + " ".join(["More content here."] * 40)
        )

    def _valid_refined(self) -> str:
        return (
            "## Overview\n\n"
            "Aspose.3D supports FBX format [claim: c1] for seamless 3D file processing. "
            + " ".join(["This is refined content."] * 40) + "\n\n"
            "## Details\n\n"
            "[claim: c2] Mesh creation API with improved flow. "
            + " ".join(["More refined content."] * 40)
        )

    def test_full_3_pass_generation(self, tmp_path: Path):
        """Full 3-pass: outline -> draft -> refine."""
        orch = self._make_orchestrator(tmp_path, [
            self._valid_outline_json(),  # Pass 1: outline
            self._valid_draft(),         # Pass 2: draft
            self._valid_refined(),       # Pass 3: refine
        ])
        ctx = _make_rich_context()
        result = orch.generate(self._make_page(), ctx)

        assert isinstance(result, MultiPassResult)
        assert result.success is True
        assert result.pass_used == 3
        assert "[claim: c1]" in result.content

    def test_outline_failure_uses_deterministic_outline(self, tmp_path: Path):
        """When LLM outline fails, deterministic outline is used for draft."""
        orch = self._make_orchestrator(tmp_path, [
            "NOT VALID JSON",            # Pass 1: outline fails
            self._valid_draft(),         # Pass 2: draft (uses deterministic outline)
            self._valid_refined(),       # Pass 3: refine
        ])
        ctx = _make_rich_context()
        result = orch.generate(self._make_page(), ctx)

        assert result.success is True
        assert result.outline is not None
        assert "sections" in result.outline

    def test_draft_failure_returns_deterministic_fallback(self, tmp_path: Path):
        """When draft validation fails, deterministic fallback is used."""
        orch = self._make_orchestrator(tmp_path, [
            self._valid_outline_json(),  # Pass 1: outline
            "",                          # Pass 2: empty draft -> validation fail
        ])
        ctx = _make_rich_context()
        result = orch.generate(self._make_page(), ctx)

        assert result.success is False
        assert result.pass_used == 0
        # Fallback content should include HTML comment claim markers (not visible bracket format)
        assert "<!-- claim:" in result.content

    def test_thin_page_skips_refinement(self, tmp_path: Path):
        """Pages under 200 words skip pass 3 refinement."""
        # Must pass draft validation: 50+ words and 1+ claim marker, but < 200 words
        short_draft = "[claim: c1] This is a short page with content. " + " ".join(["word"] * 55)
        orch = self._make_orchestrator(tmp_path, [
            self._valid_outline_json(),
            short_draft,
        ], mp_config={"skip_refine_for_thin_pages": True})
        ctx = _make_rich_context()
        result = orch.generate(self._make_page(), ctx)

        assert result.pass_used == 2
        assert result.success is True

    def test_refinement_validation_failure_keeps_draft(self, tmp_path: Path):
        """When refinement drops too many claim markers, draft is kept."""
        orch = self._make_orchestrator(tmp_path, [
            self._valid_outline_json(),
            self._valid_draft(),
            "",  # Empty refinement -> validation fails
        ])
        ctx = _make_rich_context()
        result = orch.generate(self._make_page(), ctx)

        # refinement failed, so draft is kept
        assert result.pass_used == 3
        assert "[claim: c1]" in result.content

    def test_llm_called_with_correct_temperatures(self, tmp_path: Path):
        """Verify LLM called with correct temperatures for each pass."""
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        llm = MockLLMClient([
            self._valid_outline_json(),
            self._valid_draft(),
            self._valid_refined(),
        ])
        run_config = MockRunConfig({})
        orch = MultiPassOrchestrator(llm, loader, run_config)
        ctx = _make_rich_context()
        orch.generate(self._make_page(), ctx)

        # Pass 1: outline at 0.3, Pass 2: draft at 0.1 (I-3: reduced for determinism), Pass 3: refine at 0.3
        assert llm.calls[0]["temperature"] == 0.3
        assert llm.calls[1]["temperature"] == 0.1
        assert llm.calls[2]["temperature"] == 0.3

    def test_cross_page_summaries_updated(self, tmp_path: Path):
        """After generation, cross_page_summaries dict is updated."""
        orch = self._make_orchestrator(tmp_path, [
            self._valid_outline_json(),
            self._valid_draft(),
            self._valid_refined(),
        ])
        ctx = _make_rich_context()
        orch.generate(self._make_page(), ctx)

        assert "getting-started" in orch.cross_page_summaries


class TestMultiPassDeterministicOutline:
    """Tests for deterministic outline fallback."""

    def test_uses_required_headings(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        orch = MultiPassOrchestrator(MockLLMClient(), loader, MockRunConfig())

        ctx = _make_rich_context(required_headings=["Intro", "Setup", "Usage"])
        page = {"slug": "test"}

        outline = orch._deterministic_outline(page, ctx)
        headings = [s["heading"] for s in outline["sections"]]
        assert headings == ["Intro", "Setup", "Usage"]

    def test_tutorial_default_sections(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        orch = MultiPassOrchestrator(MockLLMClient(), loader, MockRunConfig())

        ctx = _make_rich_context(page_role="tutorial", required_headings=[])
        outline = orch._deterministic_outline({"slug": "t"}, ctx)
        headings = [s["heading"] for s in outline["sections"]]
        assert "Introduction" in headings
        assert "Step-by-Step Guide" in headings

    def test_claims_distributed_across_sections(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        orch = MultiPassOrchestrator(MockLLMClient(), loader, MockRunConfig())

        claims = [
            {"claim_id": f"c{i}", "claim_text": f"Claim {i}", "claim_kind": "feature"}
            for i in range(6)
        ]
        ctx = _make_rich_context(
            page_claims=claims,
            required_headings=["A", "B", "C"],
        )
        outline = orch._deterministic_outline({"slug": "t"}, ctx)
        all_ids = []
        for section in outline["sections"]:
            all_ids.extend(section["claim_ids"])
        assert sorted(all_ids) == ["c0", "c1", "c2", "c3", "c4", "c5"]


class TestMultiPassDeterministicFallback:
    """Tests for deterministic fallback content generation."""

    def test_fallback_includes_title(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        orch = MultiPassOrchestrator(MockLLMClient(), loader, MockRunConfig())

        ctx = _make_rich_context()
        page = {"slug": "overview", "title": "Product Overview"}
        content = orch._deterministic_fallback(page, ctx)
        assert "# Product Overview" in content

    def test_fallback_includes_claim_markers(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        orch = MultiPassOrchestrator(MockLLMClient(), loader, MockRunConfig())

        ctx = _make_rich_context()
        page = {"slug": "overview", "title": "Overview"}
        content = orch._deterministic_fallback(page, ctx)
        # Fallback uses HTML comment format (not visible bracket format)
        assert "<!-- claim: c1 -->" in content
        assert "<!-- claim: c2 -->" in content

    def test_fallback_uses_required_headings(self, tmp_path: Path):
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        orch = MultiPassOrchestrator(MockLLMClient(), loader, MockRunConfig())

        ctx = _make_rich_context(required_headings=["Features", "API"])
        page = {"slug": "x", "title": "X"}
        content = orch._deterministic_fallback(page, ctx)
        assert "## Features" in content
        assert "## API" in content


# ===========================================================================
# PART 4: Hallucination Detection Tests
# ===========================================================================

class TestDetectHallucinationRisk:
    """Tests for detect_hallucination_risk() and its sub-functions."""

    def test_clean_content_returns_no_risks(self):
        """Content with claim markers, known APIs, and matched snippets returns no risks."""
        ctx = _make_rich_context()
        content = (
            "## Overview\n\n"
            "The Scene() class provides [claim: c1] 3D file support. "
            + " ".join(["Content."] * 30) + "\n"
            "[claim: c2] Additional feature.\n"
            "```python\nscene = Scene()\nscene.open('test.fbx')\n```"
        )
        risks = detect_hallucination_risk(content, ctx)
        high_risks = [r for r in risks if r["level"] == "HIGH"]
        assert len(high_risks) == 0

    def test_api_names_not_in_whitelist(self):
        """Unknown API names raise MEDIUM risk."""
        ctx = _make_rich_context()
        content = "Use FakeAPI() and UnknownClass() to process [claim: c1] files. " * 20
        risks = _check_api_names(content, ctx)
        assert len(risks) > 0
        assert risks[0]["layer"] == 2
        assert risks[0]["level"] == "MEDIUM"

    def test_api_names_in_whitelist_no_risk(self):
        """Known API names produce no risk."""
        ctx = _make_rich_context()
        content = "Use Scene() and Mesh() to process files."
        risks = _check_api_names(content, ctx)
        assert len(risks) == 0

    def test_code_block_low_similarity(self):
        """Code block with no matching snippet raises HIGH risk."""
        ctx = _make_rich_context()
        content = (
            "Some text [claim: c1] here.\n"
            "```python\n"
            "import completely_unrelated_library\n"
            "x = completely_unrelated_library.do_something_entirely_new()\n"
            "print(x.result_value)\n"
            "```\n"
        )
        risks = _check_code_blocks(content, ctx)
        assert any(r["level"] == "HIGH" for r in risks)
        assert any(r["layer"] == 3 for r in risks)

    def test_code_block_high_similarity_no_risk(self):
        """Code block matching a snippet does not raise risk."""
        ctx = _make_rich_context()
        content = (
            "```python\n"
            "scene = Scene()\n"
            "scene.open('test.fbx')\n"
            "```\n"
        )
        risks = _check_code_blocks(content, ctx)
        high_risks = [r for r in risks if r["level"] == "HIGH"]
        assert len(high_risks) == 0

    def test_no_code_blocks_no_risk(self):
        """Content without code blocks produces no code provenance risk."""
        ctx = _make_rich_context()
        risks = _check_code_blocks("Plain text only [claim: c1].", ctx)
        assert len(risks) == 0

    def test_low_claim_density_risk(self):
        """Content with too few claim markers for word count raises MEDIUM risk."""
        # 300 words with only 1 claim marker -> density < 1.0 per 150 words
        content = "[claim: c1] " + " ".join(["word"] * 300)
        risks = _check_claim_density(content)
        assert len(risks) == 1
        assert risks[0]["layer"] == 4
        assert risks[0]["level"] == "MEDIUM"

    def test_high_claim_density_no_risk(self):
        """Content with sufficient claim markers raises no density risk."""
        # ~150 words with 2 claim markers -> density >= 1.0
        content = "[claim: c1] " + " ".join(["word"] * 70) + " [claim: c2] " + " ".join(["word"] * 70)
        risks = _check_claim_density(content)
        assert len(risks) == 0

    def test_empty_content_no_density_risk(self):
        """Empty content returns no density risk (no division by zero)."""
        risks = _check_claim_density("")
        assert len(risks) == 0

    def test_performance_claim_without_marker(self):
        """Performance keywords without claim markers raise MEDIUM risk."""
        content = "This library is extremely fast and efficient. It optimizes everything."
        risks = _check_performance_claims(content)
        assert len(risks) > 0
        assert risks[0]["layer"] == 7

    def test_performance_claim_with_marker_no_risk(self):
        """Performance keywords with claim markers produce no risk."""
        content = "[claim: c1] This library is extremely fast and efficient."
        risks = _check_performance_claims(content)
        assert len(risks) == 0

    def test_no_performance_keywords_no_risk(self):
        """Content without performance keywords produces no risk."""
        content = "This library reads and writes files."
        risks = _check_performance_claims(content)
        assert len(risks) == 0

    def test_high_risk_in_generate_triggers_fallback(self, tmp_path: Path):
        """High hallucination risk during generate() triggers deterministic fallback."""
        # Create code block with zero similarity to any snippet -> HIGH risk
        bad_draft = (
            "[claim: c1] Some text. " * 20 + "\n\n"
            "```python\n"
            "import completely_unrelated_xyz\n"
            "abc_xyz = completely_unrelated_xyz.magic_wand()\n"
            "print(abc_xyz.something_entirely_fabricated)\n"
            "```\n"
        )
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        outline_json = json.dumps({
            "sections": [{"heading": "Intro", "claim_ids": ["c1"]}]
        })
        llm = MockLLMClient([outline_json, bad_draft])
        run_config = MockRunConfig({})
        orch = MultiPassOrchestrator(llm, loader, run_config)
        ctx = _make_rich_context()

        result = orch.generate({"slug": "test", "title": "Test"}, ctx)
        assert result.success is False
        assert any(r["level"] == "HIGH" for r in result.risks)


class TestMultiPassValidation:
    """Tests for outline, draft, and refinement validation."""

    def _make_orchestrator(self, tmp_path: Path) -> MultiPassOrchestrator:
        prompt_dir = _make_prompt_dir(tmp_path)
        loader = PromptLoader(str(prompt_dir))
        return MultiPassOrchestrator(MockLLMClient(), loader, MockRunConfig())

    def test_validate_outline_valid(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        outline = {
            "sections": [
                {"heading": "A", "claim_ids": ["c1"]},
            ]
        }
        assert orch._validate_outline(outline, {}) is True

    def test_validate_outline_none(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        assert orch._validate_outline(None, {}) is False

    def test_validate_outline_missing_sections(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        assert orch._validate_outline({"no_sections": []}, {}) is False

    def test_validate_outline_missing_heading(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        outline = {"sections": [{"claim_ids": ["c1"]}]}
        assert orch._validate_outline(outline, {}) is False

    def test_validate_outline_missing_claim_ids(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        outline = {"sections": [{"heading": "A"}]}
        assert orch._validate_outline(outline, {}) is False

    def test_validate_draft_valid(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        draft = "[claim: c1] " + " ".join(["word"] * 60)
        assert orch._validate_draft(draft, {}) is True

    def test_validate_draft_empty(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        assert orch._validate_draft("", {}) is False

    def test_validate_draft_too_short(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        assert orch._validate_draft("[claim: c1] short", {}) is False

    def test_validate_draft_no_claim_markers(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        draft = " ".join(["word"] * 60)
        assert orch._validate_draft(draft, {}) is False

    def test_validate_refinement_valid(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        draft = "[claim: c1] " + " ".join(["word"] * 100)
        refined = "[claim: c1] " + " ".join(["word"] * 100)
        assert orch._validate_refinement(draft, refined) is True

    def test_validate_refinement_empty(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        assert orch._validate_refinement("x", "") is False

    def test_validate_refinement_lost_claims(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        draft = "[claim: c1] [claim: c2] [claim: c3] [claim: c4] [claim: c5] " + " ".join(["word"] * 100)
        # Refined has 0 claim markers -> below 90% of 5
        refined = " ".join(["word"] * 100)
        assert orch._validate_refinement(draft, refined) is False

    def test_validate_refinement_word_count_drop(self, tmp_path: Path):
        orch = self._make_orchestrator(tmp_path)
        draft = "[claim: c1] " + " ".join(["word"] * 200)
        refined = "[claim: c1] " + " ".join(["word"] * 10)  # ~5% of original
        assert orch._validate_refinement(draft, refined) is False


# ===========================================================================
# PART 5: PromptLoader with real prompt templates
# ===========================================================================

class TestPromptLoaderRealTemplates:
    """Tests using the actual prompts in src/launch/prompts/."""

    REAL_PROMPT_DIR = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "src", "launch", "prompts"
    )

    @pytest.fixture(autouse=True)
    def _check_real_dir(self):
        """Skip these tests if real prompt directory doesn't exist."""
        if not os.path.isdir(self.REAL_PROMPT_DIR):
            pytest.skip("Real prompt directory not found")

    def test_list_prompts_returns_entries(self):
        loader = PromptLoader(self.REAL_PROMPT_DIR)
        prompts = loader.list_prompts()
        assert len(prompts) > 0
        # Should contain at least some known templates
        names = set(prompts)
        assert "system/content_architect" in names or any(
            "content_architect" in p for p in prompts
        )

    def test_list_prompts_by_category(self):
        loader = PromptLoader(self.REAL_PROMPT_DIR)
        pages = loader.list_prompts(category="pages")
        assert len(pages) > 0
        for p in pages:
            assert p.startswith("pages/")

    def test_load_real_content_architect(self):
        loader = PromptLoader(self.REAL_PROMPT_DIR)
        result = loader.load(
            "system/content_architect",
            product_name="Aspose.3D",
            page_role="comprehensive_guide",
            enriched_claims="[c1] FBX support",
        )
        assert "Aspose.3D" in result.text
        assert result.version
        assert result.strategy.get("temperature") is not None

    def test_load_real_anti_hallucination_fragment(self):
        loader = PromptLoader(self.REAL_PROMPT_DIR)
        result = loader.load_with_fragments(
            "system/technical_writer",
            ["fragments/anti_hallucination"],
            product_name="Test",
            outline_json="{}",
            enriched_claims="none",
        )
        assert "claim" in result.text.lower()
