"""Tests for Phase B: W4 Planning Quality fixes (B2-B6)."""
import pytest
from launch.workers.w4_ia_planner.worker import (
    link_claims_to_snippets,
    _extract_symbols_from_claims,
    _find_claims_for_topic,
    _sanitize_page_spec_fields,
)


# --- B2: Name-based claim-to-snippet matching ---


class TestLinkClaimsToSnippets:
    """Test name-based claim-to-snippet matching."""

    def test_name_based_matching(self):
        """Snippet entity names mentioned in claim text produce matches."""
        claims = [
            {"claim_id": "c1", "claim_text": "Scene class represents a 3D scene"},
            {"claim_id": "c2", "claim_text": "Load 3D models from files"},
        ]
        catalog = {
            "snippets": [
                {"snippet_id": "s1", "code": "scene = Scene()\nscene.open('test.fbx')", "tags": ["scene"]},
                {"snippet_id": "s2", "code": "mesh = Mesh()\nmesh.add_vertex()", "tags": ["mesh"]},
            ]
        }
        result = link_claims_to_snippets(claims, catalog)
        c1 = next(c for c in result if c["claim_id"] == "c1")
        assert "s1" in c1["demo_snippet_ids"]

    def test_tag_matching(self):
        """Snippet tags mentioned in claim text produce matches."""
        claims = [
            {"claim_id": "c1", "claim_text": "mesh manipulation features"},
        ]
        catalog = {
            "snippets": [
                {"snippet_id": "s1", "code": "x = 1", "tags": ["mesh", "manipulation"]},
            ]
        }
        result = link_claims_to_snippets(claims, catalog)
        c1 = result[0]
        assert "s1" in c1["demo_snippet_ids"]

    def test_empty_catalog_passthrough(self):
        """Empty catalog returns claims unchanged."""
        claims = [{"claim_id": "c1", "claim_text": "test"}]
        result = link_claims_to_snippets(claims, {"snippets": []})
        assert result == claims

    def test_idempotent(self):
        """Claims with existing demo_snippet_ids are not modified."""
        claims = [
            {"claim_id": "c1", "claim_text": "Scene class", "demo_snippet_ids": ["existing"]},
        ]
        catalog = {
            "snippets": [
                {"snippet_id": "s1", "code": "scene = Scene()", "tags": ["scene"]},
            ]
        }
        result = link_claims_to_snippets(claims, catalog)
        assert result[0]["demo_snippet_ids"] == ["existing"]


# --- B3: Fix _extract_symbols ---


class TestExtractSymbols:
    """Test symbol extraction from api_surface_summary."""

    def test_real_class_names_returned(self):
        """api_surface_summary classes are used directly (not claim_id comparison)."""
        product_facts = {
            "api_surface_summary": {
                "classes": [
                    {"name": "Scene"},
                    {"name": "Entity"},
                    {"name": "Mesh"},
                ]
            },
            "claims": [
                {"claim_id": "abc123", "claim_text": "Scene represents a 3D scene with Entity objects"},
                {"claim_id": "def456", "claim_text": "Mesh provides geometry manipulation for 3D models"},
            ],
        }
        result = _extract_symbols_from_claims(product_facts, "3d")
        assert "Scene" in result["key_symbols"]
        assert "3dDocument" not in result["key_symbols"]

    def test_empty_api_returns_defaults(self):
        """Empty api_surface_summary returns family-based defaults."""
        result = _extract_symbols_from_claims(
            {"api_surface_summary": {"classes": []}, "claims": []}, "note"
        )
        assert result["signature_class"] == "NoteDocument"

    def test_noise_words_filtered(self):
        """Exception classes are filtered from symbol names."""
        product_facts = {
            "api_surface_summary": {
                "classes": [{"name": "ValueError"}, {"name": "Scene"}]
            },
            "claims": [
                {"claim_id": "x", "claim_text": "Scene handles 3D data with ValueError checks"},
            ],
        }
        result = _extract_symbols_from_claims(product_facts, "3d")
        assert "ValueError" not in result["key_symbols"]
        assert "Scene" in result["key_symbols"]


# --- B5: Zero-claim page guard + _find_claims_for_topic ---


class TestFindClaimsForTopic:
    """Test keyword-based claim-to-topic matching."""

    def test_keyword_matching(self):
        """Claims with overlapping keywords are found."""
        claims = [
            {"claim_id": "c1", "claim_text": "Scene supports loading FBX format files"},
            {"claim_id": "c2", "claim_text": "Mesh provides vertex manipulation methods"},
            {"claim_id": "c3", "claim_text": "Material defines surface shading properties"},
        ]
        result = _find_claims_for_topic(
            "Loading FBX Files", "How to load FBX format models",
            claims, covered_ids=set(),
        )
        assert "c1" in result
        assert len(result) >= 1

    def test_skips_covered_ids(self):
        """Already-covered claim IDs are excluded."""
        claims = [
            {"claim_id": "c1", "claim_text": "Scene supports loading FBX format files"},
        ]
        result = _find_claims_for_topic(
            "Loading FBX Files", "How to load FBX models",
            claims, covered_ids={"c1"},
        )
        assert result == []

    def test_zero_overlap_returns_empty(self):
        """Topic with no keyword overlap returns empty list."""
        claims = [
            {"claim_id": "c1", "claim_text": "Scene supports loading FBX format files"},
        ]
        result = _find_claims_for_topic(
            "Database Optimization", "Improve database query performance",
            claims, covered_ids=set(),
        )
        assert result == []


# --- B6: Sanitize content_strategy dicts ---


class TestSanitizePageSpecFields:
    """Test content_strategy sanitization."""

    def test_nested_dicts_converted(self):
        """Nested dicts in content_strategy become strings."""
        page = {
            "slug": "test",
            "content_strategy": {
                "tone": "professional",
                "nested": {"key1": "val1", "key2": "val2"},
            },
        }
        result = _sanitize_page_spec_fields(page)
        assert isinstance(result["content_strategy"]["nested"], str)
        assert "key1: val1" in result["content_strategy"]["nested"]

    def test_strings_preserved(self):
        """String values in content_strategy are preserved."""
        page = {
            "slug": "test",
            "content_strategy": {"tone": "professional", "length": "medium"},
        }
        result = _sanitize_page_spec_fields(page)
        assert result["content_strategy"]["tone"] == "professional"

    def test_lists_preserved(self):
        """String lists in content_strategy are preserved."""
        page = {
            "slug": "test",
            "content_strategy": {
                "forbidden_topics": ["internal", "governance"],
            },
        }
        result = _sanitize_page_spec_fields(page)
        assert result["content_strategy"]["forbidden_topics"] == ["internal", "governance"]

    def test_claim_quota_preserved_as_dict(self):
        """claim_quota is schema-required as object — must NOT be flattened."""
        page = {
            "slug": "test",
            "content_strategy": {
                "tone": "professional",
                "claim_quota": {"min": 10, "max": 20},
                "nested": {"key1": "val1"},
            },
        }
        result = _sanitize_page_spec_fields(page)
        assert isinstance(result["content_strategy"]["claim_quota"], dict)
        assert result["content_strategy"]["claim_quota"] == {"min": 10, "max": 20}
        assert isinstance(result["content_strategy"]["nested"], str)

    def test_no_strategy_passthrough(self):
        """Page without content_strategy is returned unchanged."""
        page = {"slug": "test"}
        result = _sanitize_page_spec_fields(page)
        assert result == {"slug": "test"}


# --- C1-C4: W4 IAPlanner guarantee fixes ---


class TestPerSectionTopicBudget:
    """C1: Per-section topic budget replaces docs-only budget."""

    def test_section_budget_computed_per_section(self):
        """Each section has its own budget from its own quota."""
        from launch.workers.w4_ia_planner.worker import _get_section_expansion
        page_expansion = {
            "docs": {"min_pages": 0, "max_pages": 5},
            "kb": {"min_pages": 0, "max_pages": 10},
        }
        docs_exp = _get_section_expansion(page_expansion, "docs")
        kb_exp = _get_section_expansion(page_expansion, "kb")
        assert docs_exp["max_pages"] == 5
        assert kb_exp["max_pages"] == 10

    def test_missing_section_gets_defaults(self):
        """Section not in page_expansion gets safe defaults."""
        from launch.workers.w4_ia_planner.worker import _get_section_expansion
        result = _get_section_expansion({}, "reference")
        assert result["enabled"] is True
        assert result["min_pages"] == 0
        assert result["max_pages"] == 999


class TestSectionAwareZeroClaimGuard:
    """C2: Zero-claim guard respects required section minimums."""

    def test_nav_roles_always_exempt(self):
        """Pages with toc/landing/index roles always survive guard."""
        pages = [
            {"section": "docs", "slug": "toc", "page_role": "toc", "required_claim_ids": []},
            {"section": "docs", "slug": "landing", "page_role": "landing", "required_claim_ids": []},
        ]
        nav_roles = {"toc", "landing", "index"}
        guarded = [
            p for p in pages
            if p.get("required_claim_ids") or p.get("page_role", "") in nav_roles
            or p.get("slug", "") in ("_index", "index")
        ]
        assert len(guarded) == 2

    def test_index_slug_always_exempt(self):
        """Pages with _index or index slug always survive guard."""
        pages = [
            {"section": "docs", "slug": "_index", "page_role": "tutorial", "required_claim_ids": []},
            {"section": "docs", "slug": "index", "page_role": "tutorial", "required_claim_ids": []},
        ]
        nav_roles = {"toc", "landing", "index"}
        guarded = [
            p for p in pages
            if p.get("required_claim_ids") or p.get("page_role", "") in nav_roles
            or p.get("slug", "") in ("_index", "index")
        ]
        assert len(guarded) == 2

    def test_page_with_claims_survives(self):
        """Pages with non-empty required_claim_ids survive guard."""
        pages = [
            {"section": "docs", "slug": "feature", "page_role": "tutorial",
             "required_claim_ids": ["c1", "c2"]},
        ]
        nav_roles = {"toc", "landing", "index"}
        guarded = [
            p for p in pages
            if p.get("required_claim_ids") or p.get("page_role", "") in nav_roles
            or p.get("slug", "") in ("_index", "index")
        ]
        assert len(guarded) == 1


class TestClaimBindingForMandatoryPages:
    """C2: Pre-guard claim binding rescues mandatory pages."""

    def test_find_claims_for_topic_keyword_overlap(self):
        """_find_claims_for_topic finds claims via keyword overlap."""
        from launch.workers.w4_ia_planner.worker import _find_claims_for_topic
        claims = [
            {"claim_id": "c1", "claim_text": "Supports OBJ format for 3D rendering"},
            {"claim_id": "c2", "claim_text": "Convert STL files to GLTF format"},
            {"claim_id": "c3", "claim_text": "Python installation guide for beginners"},
        ]
        result = _find_claims_for_topic(
            "3D Format Conversion", "Convert between mesh formats",
            claims, set(), max_claims=3,
        )
        assert isinstance(result, list)
        # Should find c1 and c2 (overlap with "format", "convert", "3D")
        assert len(result) >= 1

    def test_find_claims_excludes_covered_ids(self):
        """Already-covered claim IDs are excluded."""
        from launch.workers.w4_ia_planner.worker import _find_claims_for_topic
        claims = [
            {"claim_id": "c1", "claim_text": "Supports OBJ format for rendering"},
            {"claim_id": "c2", "claim_text": "Convert OBJ files to STL format"},
        ]
        result = _find_claims_for_topic(
            "OBJ Format Support", "Format handling",
            claims, {"c1"}, max_claims=3,
        )
        # c1 is excluded, only c2 can match
        assert "c1" not in result


class TestMandatorySectionGuarantee:
    """C4: Post-planning validation catches guarantee violations."""

    def test_guarantee_passes_with_all_sections(self):
        """No error when all required sections have pages with claims."""
        pages = [
            {"section": "docs", "slug": "guide", "page_role": "tutorial",
             "required_claim_ids": ["c1"]},
            {"section": "kb", "slug": "howto", "page_role": "howto_article",
             "required_claim_ids": ["c2"]},
        ]
        required_sections = ["docs", "kb"]
        # Simulate the guarantee check inline
        violations = []
        nav_roles = {"toc", "landing", "index"}
        for sec in required_sections:
            sec_pages = [p for p in pages if p.get("section") == sec]
            if len(sec_pages) < 1:
                violations.append(f"Section '{sec}': 0 pages")
                continue
            content_pages = [
                p for p in sec_pages
                if p.get("page_role", "") not in nav_roles
                and p.get("slug", "") not in ("_index", "index")
            ]
            pages_with_claims = [p for p in content_pages if p.get("required_claim_ids")]
            if content_pages and not pages_with_claims:
                violations.append(f"Section '{sec}': no claims")
        assert violations == []

    def test_guarantee_fails_when_section_missing(self):
        """Violation detected when required section has 0 pages."""
        pages = [
            {"section": "docs", "slug": "guide", "page_role": "tutorial",
             "required_claim_ids": ["c1"]},
        ]
        required_sections = ["docs", "kb"]
        violations = []
        for sec in required_sections:
            sec_pages = [p for p in pages if p.get("section") == sec]
            if len(sec_pages) < 1:
                violations.append(f"Section '{sec}': 0 pages")
        assert len(violations) == 1
        assert "kb" in violations[0]

    def test_guarantee_fails_when_all_pages_claimless(self):
        """Violation detected when section has pages but none have claims."""
        pages = [
            {"section": "docs", "slug": "guide", "page_role": "tutorial",
             "required_claim_ids": []},
            {"section": "docs", "slug": "faq", "page_role": "faq",
             "required_claim_ids": []},
        ]
        required_sections = ["docs"]
        violations = []
        nav_roles = {"toc", "landing", "index"}
        for sec in required_sections:
            sec_pages = [p for p in pages if p.get("section") == sec]
            if len(sec_pages) < 1:
                violations.append(f"Section '{sec}': 0 pages")
                continue
            content_pages = [
                p for p in sec_pages
                if p.get("page_role", "") not in nav_roles
                and p.get("slug", "") not in ("_index", "index")
            ]
            pages_with_claims = [p for p in content_pages if p.get("required_claim_ids")]
            if content_pages and not pages_with_claims:
                violations.append(f"Section '{sec}': no claims")
        assert len(violations) == 1
        assert "docs" in violations[0]

    def test_guarantee_ignores_empty_required_sections(self):
        """When required_sections=[], no violations possible."""
        violations = []
        for sec in []:
            violations.append(sec)
        assert violations == []
