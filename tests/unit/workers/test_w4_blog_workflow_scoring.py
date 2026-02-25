"""Agent 44: Blog feature-highlight workflow scoring tests.

Validates:
1. score_blog_workflow() returns deterministic results
2. Conversion workflows with snippets score highest (+5+3+2=10)
3. Workflows with snippets but no conversion score +3(+2)
4. Fallback slug when no workflows or all score 0
5. Slug pattern is verb-object (via _derive_semantic_slug)
6. Same inputs always produce same output (PYTHONHASHSEED=0)
7. Ruleset mandates 2 blog pages (blog + feature_blog)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_product_facts() -> Dict[str, Any]:
    return {"workflows": [], "claim_groups": {}, "supported_formats": []}


@pytest.fixture
def empty_snippet_catalog() -> Dict[str, Any]:
    return {"snippets": []}


@pytest.fixture
def pf_with_conversion_workflow() -> Dict[str, Any]:
    return {
        "workflows": [
            {
                "workflow_tag": "format_conversion",
                "title": "Convert OBJ to GLTF",
                "claim_ids": ["c1", "c2"],
                "snippet_tags": ["conversion"],
            },
            {
                "workflow_tag": "quickstart",
                "title": "Quick Start",
                "claim_ids": ["c3"],
                "snippet_tags": ["quickstart"],
            },
        ],
        "claim_groups": {"conversion_pairs": [{"source": "OBJ", "target": "GLTF"}]},
        "supported_formats": [
            {"format": "OBJ", "direction": "both"},
            {"format": "GLTF", "direction": "unknown"},
        ],
    }


@pytest.fixture
def sc_with_tags() -> Dict[str, Any]:
    return {
        "snippets": [
            {"snippet_id": "s1", "tags": ["conversion", "example"], "claim_ids": []},
            {"snippet_id": "s2", "tags": ["quickstart"], "claim_ids": []},
        ]
    }


# ---------------------------------------------------------------------------
# TestScoreBlogWorkflow
# ---------------------------------------------------------------------------


class TestScoreBlogWorkflow:
    """Tests for score_blog_workflow() deterministic scoring."""

    def test_fallback_when_no_workflows(self, empty_product_facts, empty_snippet_catalog):
        """Returns 'feature-highlight' fallback when workflows list is empty."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        result = score_blog_workflow(empty_product_facts, empty_snippet_catalog)
        assert result["slug"] == "feature-highlight"
        assert result["score"] == 0
        assert result["workflow_tag"] == ""

    def test_fallback_when_all_score_zero(self, empty_snippet_catalog):
        """Returns fallback when no workflow has snippet evidence."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        pf = {
            "workflows": [
                {
                    "workflow_tag": "installation",
                    "title": "Installation",
                    "claim_ids": ["c1"],
                    "snippet_tags": [],
                },
            ],
            "claim_groups": {},
            "supported_formats": [],
        }
        result = score_blog_workflow(pf, empty_snippet_catalog)
        assert result["slug"] == "feature-highlight"
        assert result["score"] == 0

    def test_conversion_with_snippets_scores_10(self, pf_with_conversion_workflow, sc_with_tags):
        """Conversion workflow with matching snippets gets +5+3+2=10."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        result = score_blog_workflow(pf_with_conversion_workflow, sc_with_tags)
        assert result["workflow_tag"] == "format_conversion"
        assert result["score"] == 10  # +5 conversion+snippet, +3 has snippet, +2 "convert" verb

    def test_snippet_via_claim_overlap(self):
        """Workflow scores via claim_ids overlap with snippet claim_ids."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        pf = {
            "workflows": [
                {
                    "workflow_tag": "render_scene",
                    "title": "Render 3D Scene",
                    "claim_ids": ["c1", "c2"],
                    "snippet_tags": [],
                },
            ],
            "claim_groups": {},
            "supported_formats": [],
        }
        sc = {"snippets": [{"snippet_id": "s1", "tags": ["example"], "claim_ids": ["c1"]}]}
        result = score_blog_workflow(pf, sc)
        assert result["workflow_tag"] == "render_scene"
        assert result["score"] == 5  # +3 snippet overlap + +2 "render" verb

    def test_deterministic_same_inputs(self, pf_with_conversion_workflow, sc_with_tags):
        """Same inputs always produce the same result."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        results = [
            score_blog_workflow(pf_with_conversion_workflow, sc_with_tags) for _ in range(5)
        ]
        assert all(r["slug"] == results[0]["slug"] for r in results)
        assert all(r["workflow_tag"] == results[0]["workflow_tag"] for r in results)
        assert all(r["score"] == results[0]["score"] for r in results)

    def test_tiebreak_alphabetical(self):
        """When scores are equal, lower workflow_tag wins (alphabetical)."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        pf = {
            "workflows": [
                {
                    "workflow_tag": "zz_workflow",
                    "title": "ZZ Workflow",
                    "claim_ids": ["c1"],
                    "snippet_tags": ["tag1"],
                },
                {
                    "workflow_tag": "aa_workflow",
                    "title": "AA Workflow",
                    "claim_ids": ["c2"],
                    "snippet_tags": ["tag2"],
                },
            ],
            "claim_groups": {},
            "supported_formats": [],
        }
        sc = {"snippets": [{"snippet_id": "s1", "tags": ["tag1", "tag2"], "claim_ids": []}]}
        result = score_blog_workflow(pf, sc)
        assert result["workflow_tag"] == "aa_workflow"

    def test_slug_uses_derive_semantic_slug(self, pf_with_conversion_workflow, sc_with_tags):
        """Slug is derived via _derive_semantic_slug — lowercase, hyphenated, <= 40 chars."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        result = score_blog_workflow(pf_with_conversion_workflow, sc_with_tags)
        slug = result["slug"]
        assert slug == slug.lower()
        assert " " not in slug
        assert len(slug) <= 40

    def test_high_intent_verb_boost(self):
        """Workflow title with high-intent verb gets +2 bonus."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        pf = {
            "workflows": [
                {
                    "workflow_tag": "create_spreadsheet",
                    "title": "Create Spreadsheet Documents",
                    "claim_ids": ["c1"],
                    "snippet_tags": ["create"],
                },
            ],
            "claim_groups": {},
            "supported_formats": [],
        }
        sc = {"snippets": [{"snippet_id": "s1", "tags": ["create"], "claim_ids": []}]}
        result = score_blog_workflow(pf, sc)
        # +3 snippet match + +2 "create" verb = 5
        assert result["score"] == 5
        assert "create" in result["slug"]


# ---------------------------------------------------------------------------
# TestRulesetBlogMandatory
# ---------------------------------------------------------------------------


class TestRulesetBlogMandatory:
    """Integration: ruleset.v1_1.yaml mandates 2 blog pages."""

    def test_ruleset_mandates_two_blog_pages(self):
        """Blog section has 2 mandatory pages with roles blog + feature_blog."""
        ruleset_path = (
            Path(__file__).parent.parent.parent.parent / "specs" / "rulesets" / "ruleset.v1_1.yaml"
        )
        if not ruleset_path.exists():
            pytest.skip("ruleset.v1_1.yaml not found")
        ruleset = yaml.safe_load(ruleset_path.read_text(encoding="utf-8"))
        blog_cfg = ruleset.get("sections", {}).get("blog", {})
        mandatory = blog_cfg.get("mandatory_pages", [])
        roles = sorted(mp.get("page_role", "") for mp in mandatory)
        assert "blog" in roles
        assert "feature_blog" in roles
        assert len(mandatory) >= 2
        assert blog_cfg.get("min_pages", 0) >= 2


# ---------------------------------------------------------------------------
# TC-2607: _derive_blog_evidence_slug
# ---------------------------------------------------------------------------


class TestDeriveBlogEvidenceSlug:
    """Tests for _derive_blog_evidence_slug() family keyword enrichment."""

    def test_enriches_with_family_keyword(self):
        """Base slug is enriched with family keyword when not already present."""
        from src.launch.workers.w4_ia_planner.worker import _derive_blog_evidence_slug

        slug = _derive_blog_evidence_slug(
            "Convert OBJ to GLTF", "3d", {},
        )
        assert "3d-models" in slug
        assert slug.startswith("convert-")

    def test_no_enrichment_when_keyword_already_present(self):
        """No double-enrichment when base slug already contains family keyword."""
        from src.launch.workers.w4_ia_planner.worker import _derive_blog_evidence_slug

        slug = _derive_blog_evidence_slug(
            "Load 3D Models Scene", "3d", {},
        )
        # Should NOT produce "load-3d-models-scene-3d-models"
        assert slug.count("3d-models") == 1

    def test_length_guard_prevents_overflow(self):
        """Enrichment is skipped when it would exceed 40 chars."""
        from src.launch.workers.w4_ia_planner.worker import _derive_blog_evidence_slug

        slug = _derive_blog_evidence_slug(
            "Convert Spreadsheet Documents Between Multiple Formats", "cells", {},
        )
        assert len(slug) <= 40

    def test_empty_title_still_enriches(self):
        """Empty title still produces enriched slug from semantic fallback."""
        from src.launch.workers.w4_ia_planner.worker import _derive_blog_evidence_slug

        slug = _derive_blog_evidence_slug("", "3d", {})
        # _derive_semantic_slug("") returns "feature"; enriched to "feature-3d-models"
        assert "3d-models" in slug

    def test_registry_override_keyword(self):
        """family_capabilities keyword overrides hardcoded map."""
        from src.launch.workers.w4_ia_planner.worker import _derive_blog_evidence_slug

        slug = _derive_blog_evidence_slug(
            "Convert Formats", "3d", {},
            family_capabilities={"keyword": "meshes"},
        )
        assert "meshes" in slug

    def test_cells_family(self):
        """Cells product slug produces spreadsheets keyword."""
        from src.launch.workers.w4_ia_planner.worker import _derive_blog_evidence_slug

        slug = _derive_blog_evidence_slug(
            "Create Reports", "cells", {},
        )
        assert "spreadsheets" in slug

    def test_note_family(self):
        """Note product slug produces notebooks keyword."""
        from src.launch.workers.w4_ia_planner.worker import _derive_blog_evidence_slug

        slug = _derive_blog_evidence_slug(
            "Extract Data", "note", {},
        )
        assert "notebooks" in slug

    def test_unknown_family_fallback(self):
        """Unknown family uses 'files' fallback."""
        from src.launch.workers.w4_ia_planner.worker import _derive_blog_evidence_slug

        slug = _derive_blog_evidence_slug(
            "Process Data", "barcode", {},
        )
        assert "files" in slug

    def test_backward_compat_no_product_slug(self):
        """score_blog_workflow without product_slug uses old codepath."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        pf = {
            "workflows": [
                {
                    "workflow_tag": "render_scene",
                    "title": "Render 3D Scene",
                    "claim_ids": ["c1"],
                    "snippet_tags": ["render"],
                },
            ],
            "claim_groups": {},
            "supported_formats": [],
        }
        sc = {"snippets": [{"snippet_id": "s1", "tags": ["render"], "claim_ids": []}]}
        result = score_blog_workflow(pf, sc)
        # Without product_slug, should still produce a valid slug via _derive_semantic_slug
        assert result["slug"]
        assert result["score"] > 0

    def test_score_blog_with_product_slug_enriches(self):
        """score_blog_workflow with product_slug produces enriched slug."""
        from src.launch.workers.w4_ia_planner.worker import score_blog_workflow

        pf = {
            "workflows": [
                {
                    "workflow_tag": "format_conversion",
                    "title": "Convert OBJ to GLTF",
                    "claim_ids": ["c1"],
                    "snippet_tags": ["conversion"],
                },
            ],
            "claim_groups": {},
            "supported_formats": [],
        }
        sc = {"snippets": [{"snippet_id": "s1", "tags": ["conversion"], "claim_ids": []}]}
        result = score_blog_workflow(pf, sc, product_slug="3d")
        assert "3d-models" in result["slug"]
        assert result["score"] > 0
