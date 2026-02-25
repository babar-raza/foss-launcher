"""Tests for slug collision detection and registry-based slug generation (TC-2515/2514/2516).

Validates:
- Slug collision detection within same section
- Slug collision tolerance across different sections
- W4 registry-based keyword resolution (family_capabilities)
- W4 fallback to hardcoded maps
- W6 format validation against registry
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from src.launch.workers.w4_ia_planner.worker import (
    _detect_slug_collisions,
    _derive_evidence_aware_slug,
    _load_family_capabilities,
)
from src.launch.workers.w6_seo_optimizer.worker import (
    _validate_slug_formats,
)


# ---------------------------------------------------------------------------
# TC-2515: Slug collision detection
# ---------------------------------------------------------------------------


class TestDetectSlugCollisions:
    """Tests for _detect_slug_collisions()."""

    def test_no_collisions_in_clean_plan(self):
        """Well-formed plan with unique slugs per section has zero collisions."""
        page_plan = {
            "pages": [
                {"slug": "getting-started", "section": "docs", "title": "Getting Started"},
                {"slug": "load-3d-models", "section": "kb", "title": "Load 3D Models"},
                {"slug": "save-3d-models", "section": "kb", "title": "Save 3D Models"},
                {"slug": "release-notes", "section": "blog", "title": "Release Notes"},
            ]
        }
        collisions = _detect_slug_collisions(page_plan)
        assert collisions == []

    def test_detects_duplicate_slugs(self):
        """Two pages with same slug in same section triggers collision."""
        page_plan = {
            "pages": [
                {"slug": "load-models", "section": "kb", "title": "Load Models (A)"},
                {"slug": "load-models", "section": "kb", "title": "Load Models (B)"},
                {"slug": "save-models", "section": "kb", "title": "Save Models"},
            ]
        }
        collisions = _detect_slug_collisions(page_plan)
        assert len(collisions) == 1
        assert collisions[0]["slug"] == "load-models"
        assert collisions[0]["section"] == "kb"
        assert sorted(collisions[0]["pages"]) == ["Load Models (A)", "Load Models (B)"]

    def test_different_sections_no_collision(self):
        """Same slug in different sections is acceptable (no collision)."""
        page_plan = {
            "pages": [
                {"slug": "getting-started", "section": "docs", "title": "Getting Started Docs"},
                {"slug": "getting-started", "section": "kb", "title": "Getting Started KB"},
            ]
        }
        collisions = _detect_slug_collisions(page_plan)
        assert collisions == []

    def test_empty_plan(self):
        """Empty plan has no collisions."""
        collisions = _detect_slug_collisions({"pages": []})
        assert collisions == []

    def test_no_pages_key(self):
        """Missing pages key is handled gracefully."""
        collisions = _detect_slug_collisions({})
        assert collisions == []

    def test_multiple_collisions_across_sections(self):
        """Multiple collisions across different sections are all reported."""
        page_plan = {
            "pages": [
                {"slug": "dup-a", "section": "docs", "title": "Dup A (1)"},
                {"slug": "dup-a", "section": "docs", "title": "Dup A (2)"},
                {"slug": "dup-b", "section": "kb", "title": "Dup B (1)"},
                {"slug": "dup-b", "section": "kb", "title": "Dup B (2)"},
                {"slug": "unique", "section": "blog", "title": "Unique"},
            ]
        }
        collisions = _detect_slug_collisions(page_plan)
        assert len(collisions) == 2
        sections = sorted(c["section"] for c in collisions)
        assert sections == ["docs", "kb"]

    def test_three_way_collision(self):
        """Three pages with same slug in same section reports all three."""
        page_plan = {
            "pages": [
                {"slug": "same-slug", "section": "kb", "title": "Page A"},
                {"slug": "same-slug", "section": "kb", "title": "Page B"},
                {"slug": "same-slug", "section": "kb", "title": "Page C"},
            ]
        }
        collisions = _detect_slug_collisions(page_plan)
        assert len(collisions) == 1
        assert len(collisions[0]["pages"]) == 3
        assert sorted(collisions[0]["pages"]) == ["Page A", "Page B", "Page C"]

    def test_pages_without_slug_ignored(self):
        """Pages missing slug field are skipped."""
        page_plan = {
            "pages": [
                {"section": "docs", "title": "No Slug Page"},
                {"slug": "", "section": "docs", "title": "Empty Slug"},
                {"slug": "valid", "section": "docs", "title": "Valid"},
            ]
        }
        collisions = _detect_slug_collisions(page_plan)
        assert collisions == []

    def test_collisions_sorted_deterministically(self):
        """Output is sorted by section, then slug for determinism."""
        page_plan = {
            "pages": [
                {"slug": "z-slug", "section": "kb", "title": "Z1"},
                {"slug": "z-slug", "section": "kb", "title": "Z2"},
                {"slug": "a-slug", "section": "docs", "title": "A1"},
                {"slug": "a-slug", "section": "docs", "title": "A2"},
            ]
        }
        collisions = _detect_slug_collisions(page_plan)
        assert len(collisions) == 2
        assert collisions[0]["section"] == "docs"
        assert collisions[0]["slug"] == "a-slug"
        assert collisions[1]["section"] == "kb"
        assert collisions[1]["slug"] == "z-slug"

    def test_subdomain_used_as_section_fallback(self):
        """When 'section' is absent, 'subdomain' is used as fallback."""
        page_plan = {
            "pages": [
                {"slug": "dup", "subdomain": "blog.aspose.org", "title": "Blog 1"},
                {"slug": "dup", "subdomain": "blog.aspose.org", "title": "Blog 2"},
            ]
        }
        collisions = _detect_slug_collisions(page_plan)
        assert len(collisions) == 1
        assert collisions[0]["section"] == "blog.aspose.org"


# ---------------------------------------------------------------------------
# TC-2514: W4 registry-based slug generation
# ---------------------------------------------------------------------------


class TestW4RegistryKeyword:
    """Tests for family_capabilities integration in _derive_evidence_aware_slug."""

    def test_w4_uses_registry_keyword(self):
        """When family_capabilities is provided, uses registry keyword."""
        caps = {"keyword": "custom-widgets"}
        slug = _derive_evidence_aware_slug(
            "How to Open a File", "unknown-product", {},
            family_capabilities=caps,
        )
        assert slug == "how-to-load-custom-widgets-python"

    def test_w4_falls_back_to_hardcoded(self):
        """When family_capabilities is absent, uses hardcoded map."""
        slug = _derive_evidence_aware_slug(
            "How to Open a File", "3d", {},
            family_capabilities=None,
        )
        assert slug == "how-to-load-3d-models-python"

    def test_w4_registry_conversion_pairs(self):
        """Registry conversion_pairs override product_facts extraction."""
        caps = {
            "keyword": "3d-models",
            "conversion_pairs": ["gltf", "usdz"],
            "supported_formats": ["GLTF", "USDZ", "FBX"],
        }
        # product_facts has different pairs
        facts = {"claim_groups": {"conversion_pairs": ["fbx", "obj"]}}
        slug = _derive_evidence_aware_slug(
            "How to Convert Formats", "3d", facts,
            family_capabilities=caps,
        )
        assert slug == "how-to-convert-gltf-to-usdz-python"

    def test_w4_registry_supported_formats_fallback(self):
        """When registry has no conversion_pairs, uses supported_formats."""
        caps = {
            "keyword": "3d-models",
            "conversion_pairs": [],
            "supported_formats": ["GLTF", "FBX"],
        }
        slug = _derive_evidence_aware_slug(
            "How to Convert Formats", "3d", {},
            family_capabilities=caps,
        )
        assert slug == "how-to-convert-gltf-to-fbx-python"

    def test_w4_registry_empty_keyword_falls_back(self):
        """Empty keyword in registry falls back to hardcoded map."""
        caps = {"keyword": ""}
        slug = _derive_evidence_aware_slug(
            "How to Open a File", "cells", {},
            family_capabilities=caps,
        )
        assert slug == "how-to-load-spreadsheets-python"

    def test_w4_registry_no_intent_match_falls_back(self):
        """Title without intent keyword falls back to semantic slug regardless of registry."""
        caps = {"keyword": "custom-widgets"}
        slug = _derive_evidence_aware_slug(
            "Some Random Title", "3d", {},
            family_capabilities=caps,
        )
        # Falls back to _derive_semantic_slug — no how-to prefix
        assert "random" in slug.lower() or "some" in slug.lower()


# ---------------------------------------------------------------------------
# TC-2514: _load_family_capabilities
# ---------------------------------------------------------------------------


class TestLoadFamilyCapabilities:
    """Tests for _load_family_capabilities file loading."""

    def test_loads_valid_file(self, tmp_path):
        """Valid family_capabilities.json is loaded successfully."""
        run_dir = tmp_path / "run"
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True)
        caps = {"keyword": "3d-models", "supported_formats": ["FBX", "OBJ"]}
        (artifacts_dir / "family_capabilities.json").write_text(
            json.dumps(caps), encoding="utf-8"
        )
        result = _load_family_capabilities(run_dir)
        assert result is not None
        assert result["keyword"] == "3d-models"

    def test_returns_none_when_missing(self, tmp_path):
        """Returns None when file does not exist."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        result = _load_family_capabilities(run_dir)
        assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path):
        """Returns None when file contains invalid JSON."""
        run_dir = tmp_path / "run"
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "family_capabilities.json").write_text(
            "not valid json", encoding="utf-8"
        )
        result = _load_family_capabilities(run_dir)
        assert result is None

    def test_returns_none_when_missing_keyword(self, tmp_path):
        """Returns None when JSON is valid but missing 'keyword' key."""
        run_dir = tmp_path / "run"
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "family_capabilities.json").write_text(
            json.dumps({"formats": ["FBX"]}), encoding="utf-8"
        )
        result = _load_family_capabilities(run_dir)
        assert result is None

    def test_returns_none_when_no_artifacts_dir(self, tmp_path):
        """Returns None when artifacts directory does not exist."""
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        result = _load_family_capabilities(run_dir)
        assert result is None


# ---------------------------------------------------------------------------
# TC-2516: W6 registry-validated format check
# ---------------------------------------------------------------------------


class TestW6ValidateSlugFormats:
    """Tests for _validate_slug_formats in W6."""

    def test_w6_validates_format_in_slug(self):
        """W6 warns when slug contains a format not in registry."""
        caps = {"supported_formats": ["FBX", "OBJ"]}
        warnings = _validate_slug_formats("how-to-convert-xyz-to-abc", caps)
        # xyz and abc are not in supported formats
        assert len(warnings) >= 1
        assert any("xyz" in w for w in warnings)
        assert any("abc" in w for w in warnings)

    def test_w6_no_warning_for_known_formats(self):
        """No warning when slug only contains known formats."""
        caps = {"supported_formats": ["FBX", "OBJ"]}
        warnings = _validate_slug_formats("how-to-convert-fbx-to-obj", caps)
        assert warnings == []

    def test_w6_no_registry_no_warnings(self):
        """No warnings when registry is absent."""
        warnings = _validate_slug_formats("how-to-convert-xyz-to-abc", None)
        assert warnings == []

    def test_w6_empty_formats_no_warnings(self):
        """No warnings when supported_formats is empty."""
        caps = {"supported_formats": []}
        warnings = _validate_slug_formats("how-to-convert-xyz-to-abc", caps)
        assert warnings == []

    def test_w6_stopwords_not_flagged(self):
        """Common slug words (how, to, python, etc.) are not flagged as formats."""
        caps = {"supported_formats": ["FBX"]}
        warnings = _validate_slug_formats("how-to-load-files-python", caps)
        assert warnings == []

    def test_w6_mixed_known_and_unknown(self):
        """Only unknown formats are flagged."""
        caps = {"supported_formats": ["FBX", "OBJ"]}
        warnings = _validate_slug_formats("how-to-convert-fbx-to-xyz", caps)
        assert len(warnings) == 1
        assert "token=xyz" in warnings[0]
        # fbx should NOT appear as a flagged token
        assert not any("token=fbx" in w for w in warnings)
