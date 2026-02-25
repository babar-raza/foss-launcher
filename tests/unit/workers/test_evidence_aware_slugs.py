"""Tests for evidence-aware slug generation (TC-2480/2481/2481b).

Validates:
- Family keyword extraction from product slug
- Top format extraction from product_facts
- Evidence-aware slug derivation for KB how-to pages
- Topic category inference from titles
- Format scope inference
- Integration with load_and_merge_page_requirements()
"""

from __future__ import annotations

import pytest

from src.launch.workers.w4_ia_planner.worker import (
    _derive_evidence_aware_slug,
    _extract_family_keyword,
    _extract_top_formats,
    _extract_top_conversion_pair,
    _infer_topic_category,
    _infer_format_scope,
    load_and_merge_page_requirements,
)


# ── Family Keyword Extraction ────────────────────────────────────────────────

class TestExtractFamilyKeyword:
    def test_3d_family(self):
        assert _extract_family_keyword("3d") == "3d-models"

    def test_cells_family(self):
        assert _extract_family_keyword("cells") == "spreadsheets"

    def test_note_family(self):
        assert _extract_family_keyword("note") == "notebooks"

    def test_words_family(self):
        assert _extract_family_keyword("words") == "documents"

    def test_slides_family(self):
        assert _extract_family_keyword("slides") == "presentations"

    def test_imaging_family(self):
        assert _extract_family_keyword("imaging") == "images"

    def test_unknown_family(self):
        assert _extract_family_keyword("unknown-product") == "files"

    def test_case_insensitive(self):
        assert _extract_family_keyword("3D") == "3d-models"
        assert _extract_family_keyword("Cells") == "spreadsheets"


# ── Top Formats Extraction ───────────────────────────────────────────────────

class TestExtractTopFormats:
    def test_dict_format_entries(self):
        facts = {
            "supported_formats": [
                {"format": "FBX", "claim_ids": ["c1", "c2", "c3"]},
                {"format": "OBJ", "claim_ids": ["c4", "c5"]},
                {"format": "STL", "claim_ids": ["c6"]},
            ]
        }
        source, target = _extract_top_formats(facts)
        assert source == "fbx"
        assert target == "obj"

    def test_string_format_entries(self):
        facts = {"supported_formats": ["XLSX", "CSV", "PDF"]}
        source, target = _extract_top_formats(facts)
        # All equal evidence (1 each), sorted alphabetically
        assert source == "csv"
        assert target == "pdf"

    def test_empty_formats(self):
        source, target = _extract_top_formats({"supported_formats": []})
        assert source == ""
        assert target == "other"

    def test_single_format(self):
        facts = {"supported_formats": [{"format": "FBX", "claim_ids": ["c1"]}]}
        source, target = _extract_top_formats(facts)
        assert source == "fbx"
        assert target == "other"

    def test_no_formats_key(self):
        source, target = _extract_top_formats({})
        assert source == ""
        assert target == "other"


# ── Top Conversion Pair ──────────────────────────────────────────────────────

class TestExtractTopConversionPair:
    def test_valid_pair(self):
        facts = {"claim_groups": {"conversion_pairs": ["fbx", "obj", "stl", "glb"]}}
        pair = _extract_top_conversion_pair(facts)
        assert pair == ("FBX", "OBJ")

    def test_empty_pairs(self):
        facts = {"claim_groups": {"conversion_pairs": []}}
        assert _extract_top_conversion_pair(facts) == ("", "")

    def test_single_entry(self):
        facts = {"claim_groups": {"conversion_pairs": ["fbx"]}}
        assert _extract_top_conversion_pair(facts) == ("", "")

    def test_no_claim_groups(self):
        assert _extract_top_conversion_pair({}) == ("", "")


# ── Evidence-Aware Slug Derivation ───────────────────────────────────────────

class TestDeriveEvidenceAwareSlug:
    def test_3d_open(self):
        slug = _derive_evidence_aware_slug("How to Open a File", "3d", {})
        assert slug == "how-to-load-3d-models-python"

    def test_3d_save(self):
        slug = _derive_evidence_aware_slug("How to Save a File", "3d", {})
        assert slug == "how-to-save-3d-models-python"

    def test_3d_fix(self):
        slug = _derive_evidence_aware_slug("How to Fix Common Errors", "3d", {})
        assert slug == "how-to-fix-3d-models-errors-python"

    def test_3d_performance(self):
        slug = _derive_evidence_aware_slug("How to Improve Performance", "3d", {})
        assert slug == "how-to-optimize-3d-models-python"

    def test_3d_convert_with_evidence(self):
        facts = {
            "claim_groups": {"conversion_pairs": ["fbx", "obj"]},
            "supported_formats": [
                {"format": "FBX", "claim_ids": ["c1"]},
                {"format": "OBJ", "claim_ids": ["c2"]},
            ],
        }
        slug = _derive_evidence_aware_slug("How to Convert Formats", "3d", facts)
        assert slug == "how-to-convert-fbx-to-obj-python"

    def test_cells_open(self):
        slug = _derive_evidence_aware_slug("How to Open a File", "cells", {})
        assert slug == "how-to-load-spreadsheets-python"

    def test_cells_convert_with_formats(self):
        facts = {
            "supported_formats": [
                {"format": "XLSX", "claim_ids": ["c1", "c2", "c3"]},
                {"format": "CSV", "claim_ids": ["c4", "c5"]},
            ],
        }
        slug = _derive_evidence_aware_slug("How to Convert Formats", "cells", facts)
        assert slug == "how-to-convert-xlsx-to-csv-python"

    def test_note_open(self):
        slug = _derive_evidence_aware_slug("How to Open a File", "note", {})
        assert slug == "how-to-load-notebooks-python"

    def test_no_intent_match_falls_back(self):
        """Unrecognized title falls back to _derive_semantic_slug."""
        slug = _derive_evidence_aware_slug("Some Random Title", "3d", {})
        # Falls back to _derive_semantic_slug behavior
        assert "random" in slug.lower() or "some" in slug.lower()

    def test_deterministic(self):
        """Same inputs produce same outputs."""
        facts = {"supported_formats": [{"format": "FBX", "claim_ids": ["c1"]}]}
        results = set()
        for _ in range(5):
            results.add(_derive_evidence_aware_slug("How to Open a File", "3d", facts))
        assert len(results) == 1

    def test_max_length_enforced(self):
        slug = _derive_evidence_aware_slug(
            "How to Open a File", "3d", {}, max_length=20
        )
        assert len(slug) <= 20


# ── Topic Category Inference ─────────────────────────────────────────────────

class TestInferTopicCategory:
    def test_open_maps_to_load_file(self):
        assert _infer_topic_category("How to Open a File") == "load_file"

    def test_load_maps_to_load_file(self):
        assert _infer_topic_category("How to Load 3D Models") == "load_file"

    def test_save_maps_to_save_file(self):
        assert _infer_topic_category("How to Save a File") == "save_file"

    def test_convert_maps_to_convert_formats(self):
        assert _infer_topic_category("How to Convert Formats") == "convert_formats"

    def test_fix_maps_to_troubleshoot(self):
        assert _infer_topic_category("How to Fix Common Errors") == "troubleshoot"

    def test_performance_maps_to_optimize(self):
        assert _infer_topic_category("How to Improve Performance") == "optimize_performance"

    def test_unknown_returns_empty(self):
        assert _infer_topic_category("Some Random Title") == ""

    def test_case_insensitive(self):
        assert _infer_topic_category("HOW TO OPEN A FILE") == "load_file"


# ── Format Scope Inference ───────────────────────────────────────────────────

class TestInferFormatScope:
    def test_convert_with_conversion_pair(self):
        facts = {"claim_groups": {"conversion_pairs": ["fbx", "obj"]}}
        result = _infer_format_scope("How to Convert Formats", facts, "3d")
        assert result == "FBX-to-OBJ"

    def test_convert_with_formats_fallback(self):
        facts = {
            "supported_formats": [
                {"format": "XLSX", "claim_ids": ["c1", "c2"]},
                {"format": "CSV", "claim_ids": ["c3"]},
            ]
        }
        result = _infer_format_scope("How to Convert Formats", facts, "cells")
        assert result == "XLSX-to-CSV"

    def test_non_convert_returns_empty(self):
        result = _infer_format_scope("How to Open a File", {}, "3d")
        assert result == ""

    def test_no_evidence_returns_empty(self):
        result = _infer_format_scope("How to Convert Formats", {}, "3d")
        assert result == ""


# ── Integration: load_and_merge with evidence-aware slugs ────────────────────

class TestLoadAndMergeWithEvidence:
    def _make_ruleset_with_howto(self):
        return {
            "sections": {
                "kb": {
                    "mandatory_pages": [
                        {"title": "How to Open a File", "page_role": "howto_article"},
                        {"title": "How to Save a File", "page_role": "howto_article"},
                        {"title": "How to Convert Formats", "page_role": "howto_article"},
                        {"title": "How to Fix Common Errors", "page_role": "howto_article"},
                        {"title": "How to Improve Performance", "page_role": "howto_article"},
                    ],
                    "optional_page_policies": [],
                },
            },
        }

    def test_3d_slugs_evidence_aware(self):
        facts = {
            "claim_groups": {"conversion_pairs": ["fbx", "obj"]},
            "supported_formats": [
                {"format": "FBX", "claim_ids": ["c1"]},
                {"format": "OBJ", "claim_ids": ["c2"]},
            ],
        }
        merged = load_and_merge_page_requirements(
            self._make_ruleset_with_howto(), "3d", facts
        )
        slugs = [p["slug"] for p in merged["kb"]["mandatory_pages"]]
        assert "how-to-load-3d-models-python" in slugs
        assert "how-to-save-3d-models-python" in slugs
        assert "how-to-convert-fbx-to-obj-python" in slugs

    def test_cells_slugs_evidence_aware(self):
        facts = {
            "supported_formats": [
                {"format": "XLSX", "claim_ids": ["c1", "c2", "c3"]},
                {"format": "CSV", "claim_ids": ["c4", "c5"]},
            ],
        }
        merged = load_and_merge_page_requirements(
            self._make_ruleset_with_howto(), "cells", facts
        )
        slugs = [p["slug"] for p in merged["kb"]["mandatory_pages"]]
        assert "how-to-load-spreadsheets-python" in slugs
        assert "how-to-convert-xlsx-to-csv-python" in slugs

    def test_topic_category_populated(self):
        facts = {"supported_formats": []}
        merged = load_and_merge_page_requirements(
            self._make_ruleset_with_howto(), "3d", facts
        )
        pages = merged["kb"]["mandatory_pages"]
        categories = {p.get("topic_category") for p in pages if p.get("topic_category")}
        assert "load_file" in categories
        assert "save_file" in categories
        assert "convert_formats" in categories
        assert "troubleshoot" in categories
        assert "optimize_performance" in categories

    def test_format_scope_on_convert(self):
        facts = {"claim_groups": {"conversion_pairs": ["fbx", "obj"]}}
        merged = load_and_merge_page_requirements(
            self._make_ruleset_with_howto(), "3d", facts
        )
        convert_pages = [
            p for p in merged["kb"]["mandatory_pages"]
            if p.get("topic_category") == "convert_formats"
        ]
        assert len(convert_pages) == 1
        assert convert_pages[0].get("format_scope") == "FBX-to-OBJ"

    def test_no_product_facts_uses_semantic_slug(self):
        """Without product_facts, falls back to _derive_semantic_slug."""
        merged = load_and_merge_page_requirements(
            self._make_ruleset_with_howto(), "3d"
        )
        slugs = [p["slug"] for p in merged["kb"]["mandatory_pages"]]
        # Semantic slugs are generic (no family keyword)
        assert any("open" in s for s in slugs)

    def test_non_howto_uses_semantic_slug(self):
        """Non-howto pages use _derive_semantic_slug even with product_facts."""
        ruleset = {
            "sections": {
                "docs": {
                    "mandatory_pages": [
                        {"title": "Getting Started", "page_role": "getting_started"},
                    ],
                    "optional_page_policies": [],
                },
            },
        }
        facts = {"supported_formats": []}
        merged = load_and_merge_page_requirements(ruleset, "3d", facts)
        slug = merged["docs"]["mandatory_pages"][0]["slug"]
        assert slug == "getting-started"

    def test_deterministic_across_calls(self):
        facts = {"claim_groups": {"conversion_pairs": ["fbx", "obj"]}}
        results = []
        for _ in range(3):
            merged = load_and_merge_page_requirements(
                self._make_ruleset_with_howto(), "3d", facts
            )
            slugs = sorted(p["slug"] for p in merged["kb"]["mandatory_pages"])
            results.append(tuple(slugs))
        assert len(set(results)) == 1


# ── TC-2514: Registry backward compatibility ─────────────────────────────────

class TestRegistryBackwardCompat:
    """Ensure registry path produces same results for known families (TC-2514)."""

    def test_registry_produces_same_slug_for_3d(self):
        """Registry with 3d keyword produces identical slug to hardcoded path."""
        # Hardcoded path
        slug_hardcoded = _derive_evidence_aware_slug("How to Open a File", "3d", {})
        # Registry path with equivalent keyword
        caps = {"keyword": "3d-models"}
        slug_registry = _derive_evidence_aware_slug(
            "How to Open a File", "3d", {},
            family_capabilities=caps,
        )
        assert slug_hardcoded == slug_registry

    def test_registry_produces_same_slug_for_cells_convert(self):
        """Registry with cells formats produces identical conversion slug."""
        facts = {
            "supported_formats": [
                {"format": "XLSX", "claim_ids": ["c1", "c2", "c3"]},
                {"format": "CSV", "claim_ids": ["c4", "c5"]},
            ],
        }
        slug_hardcoded = _derive_evidence_aware_slug(
            "How to Convert Formats", "cells", facts,
        )
        # Registry with equivalent data
        caps = {
            "keyword": "spreadsheets",
            "conversion_pairs": [],
            "supported_formats": ["XLSX", "CSV"],
        }
        slug_registry = _derive_evidence_aware_slug(
            "How to Convert Formats", "cells", facts,
            family_capabilities=caps,
        )
        assert slug_hardcoded == slug_registry


# ── TC-2604: Platform-Aware Slug Generation ─────────────────────────────────


class TestPlatformAwareSlugs:
    """Verify platform parameter is substituted into all slug templates."""

    def test_open_default_python(self):
        slug = _derive_evidence_aware_slug("How to Open a File", "3d", {})
        assert slug == "how-to-load-3d-models-python"

    def test_open_java(self):
        slug = _derive_evidence_aware_slug(
            "How to Open a File", "3d", {}, platform="java"
        )
        assert slug == "how-to-load-3d-models-java"

    def test_save_csharp(self):
        slug = _derive_evidence_aware_slug(
            "How to Save a File", "cells", {}, platform="csharp"
        )
        assert slug == "how-to-save-spreadsheets-csharp"

    def test_fix_javascript(self):
        slug = _derive_evidence_aware_slug(
            "How to Fix Errors", "note", {}, platform="javascript"
        )
        assert slug == "how-to-fix-notebooks-errors-javascript"

    def test_performance_python(self):
        slug = _derive_evidence_aware_slug(
            "How to Improve Performance", "cells", {}, platform="python"
        )
        assert slug == "how-to-optimize-spreadsheets-python"

    def test_convert_with_evidence_java(self):
        facts = {
            "claim_groups": {"conversion_pairs": ["fbx", "obj"]},
        }
        slug = _derive_evidence_aware_slug(
            "How to Convert Formats", "3d", facts, platform="java"
        )
        assert slug == "how-to-convert-fbx-to-obj-java"

    def test_convert_no_evidence_falls_back_to_family(self):
        """Convert without format evidence uses family_keyword fallback."""
        slug = _derive_evidence_aware_slug(
            "How to Convert Formats", "3d", {}, platform="python"
        )
        assert slug == "how-to-convert-3d-models-python"

    def test_convert_no_evidence_java(self):
        slug = _derive_evidence_aware_slug(
            "How to Convert Formats", "cells", {}, platform="java"
        )
        assert slug == "how-to-convert-spreadsheets-java"

    def test_platform_threaded_through_load_and_merge(self):
        """Platform parameter reaches slug generation via load_and_merge."""
        ruleset = {
            "sections": {
                "kb": {
                    "mandatory_pages": [
                        {"title": "How to Open a File", "page_role": "howto_article"},
                    ],
                    "optional_page_policies": [],
                },
            },
        }
        facts = {"supported_formats": []}
        merged = load_and_merge_page_requirements(
            ruleset, "3d", facts, platform="java"
        )
        slug = merged["kb"]["mandatory_pages"][0]["slug"]
        assert slug == "how-to-load-3d-models-java"

    def test_explicit_platform_param_overrides_default(self):
        """Passing platform explicitly overrides the default 'python'."""
        slug_py = _derive_evidence_aware_slug(
            "How to Open a File", "3d", {}
        )
        slug_go = _derive_evidence_aware_slug(
            "How to Open a File", "3d", {}, platform="go"
        )
        assert slug_py == "how-to-load-3d-models-python"
        assert slug_go == "how-to-load-3d-models-go"
        assert slug_py != slug_go
