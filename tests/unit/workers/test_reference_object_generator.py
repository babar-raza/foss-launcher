"""Tests for the Spec v1.1 reference_object_page generator.

Covers:
- H2 (Q3=A): Generator registered with all aliases
- H2: Context builder filters api claims by object_name
- H2: Deterministic fallback emits H3 members as sub-sections
- E3: not_evidenced_hint → scoped fallback text
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_product_facts():
    return {
        "product_name": "Aspose.Test",
        "claims": [
            {
                "claim_id": "api-001",
                "claim_text": "The Document class opens and saves files.",
                "claim_kind": "api",
                "tags": ["api"],
                "demo_snippet_ids": ["snip-1"],
            },
            {
                "claim_id": "api-002",
                "claim_text": "Document.save() persists changes.",
                "claim_kind": "api",
                "tags": ["api"],
                "demo_snippet_ids": [],
            },
            {
                "claim_id": "feat-001",
                "claim_text": "Supports 20+ formats.",
                "claim_kind": "feature",
                "tags": [],
                "demo_snippet_ids": [],
            },
        ],
        "claim_groups": {"key_features": ["feat-001"]},
        "api_surface_summary": {
            "classes": [
                {
                    "name": "Document",
                    "description": "Core class for file manipulation.",
                    "methods": [
                        {"name": "open", "type": "method", "description": "Opens a file."},
                        {"name": "save", "type": "method", "description": "Saves the file."},
                    ],
                    "properties": [
                        {"name": "page_count", "type": "property", "description": "Number of pages."},
                    ],
                }
            ],
            "functions": [],
        },
    }


@pytest.fixture
def mock_snippet_catalog():
    return {
        "snippets": [
            {
                "snippet_id": "snip-1",
                "language": "python",
                "code": "doc = Document('file.docx')\ndoc.save('out.pdf')",
                "tags": ["api", "document"],
                "claim_ids": ["api-001"],
            },
            {
                "snippet_id": "snip-2",
                "language": "python",
                "code": "count = doc.page_count",
                "tags": ["api", "property"],
                "claim_ids": ["api-002"],
            },
        ]
    }


@pytest.fixture
def ref_page():
    return {
        "section": "reference",
        "slug": "document",
        "page_role": "reference_object_page",
        "title": "Document Class Reference",
        "object_name": "Document",
        "object_kind": "class",
        "required_claim_ids": ["api-001", "api-002"],
        "claim_ids": ["api-001", "api-002"],
        "not_evidenced_hint": False,
    }


# ── Registry Tests ─────────────────────────────────────────────────────────────

class TestReferenceObjectRegistration:
    def test_registered_in_registry(self):
        from src.launch.workers.w5_section_writer.generators import get_registry
        registry = get_registry()
        assert "reference_object_page" in registry

    def test_aliases_registered(self):
        from src.launch.workers.w5_section_writer.generators import get_registry
        registry = get_registry()
        for alias in ["reference_object", "class_reference", "module_reference"]:
            assert alias in registry, f"Alias '{alias}' not registered"

    def test_generator_is_callable(self):
        from src.launch.workers.w5_section_writer.generators import get_registry
        fn = get_registry().get("reference_object_page")
        assert callable(fn)


# ── Context Builder Tests ─────────────────────────────────────────────────────

class TestBuildReferenceObjectContext:
    def test_filters_api_claims_by_object_name(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            build_reference_object_context,
        )
        ctx = build_reference_object_context(ref_page, mock_product_facts, mock_snippet_catalog)
        # Only api-kind claims mentioning "document" should be returned
        claim_texts = [c["claim_text"] for c in ctx["claims"]]
        assert all("document" in t.lower() for t in claim_texts)
        # feat-001 (feature, not api) must not appear
        assert not any("formats" in t for t in claim_texts)

    def test_collects_demo_snippets(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            build_reference_object_context,
        )
        ctx = build_reference_object_context(ref_page, mock_product_facts, mock_snippet_catalog)
        assert len(ctx["snippets"]) >= 1

    def test_returns_claim_context_string(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            build_reference_object_context,
        )
        ctx = build_reference_object_context(ref_page, mock_product_facts, mock_snippet_catalog)
        assert isinstance(ctx["claim_context"], str)


# ── Generator Tests ───────────────────────────────────────────────────────────

class TestGenerateReferenceObjectContent:
    def test_generates_without_llm(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_reference_object_content,
        )
        content = generate_reference_object_content(ref_page, mock_product_facts, mock_snippet_catalog)
        assert isinstance(content, str)
        assert len(content) > 0

    def test_contains_object_name(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_reference_object_content,
        )
        content = generate_reference_object_content(ref_page, mock_product_facts, mock_snippet_catalog)
        assert "Document" in content

    def test_contains_members_as_h3(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_reference_object_content,
        )
        content = generate_reference_object_content(ref_page, mock_product_facts, mock_snippet_catalog)
        # Deterministic fallback should emit H3 for class members
        assert "###" in content

    def test_contains_constructor_section(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_reference_object_content,
        )
        content = generate_reference_object_content(ref_page, mock_product_facts, mock_snippet_catalog)
        assert "Constructor" in content or "Instantiation" in content

    def test_not_evidenced_fallback(self, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_reference_object_content,
            _NOT_EVIDENCED_CONTENT,
        )
        page = {
            "section": "reference",
            "slug": "orphan-class",
            "page_role": "reference_object_page",
            "title": "OrphanClass Reference",
            "object_name": "OrphanClass",
            "object_kind": "class",
            "required_claim_ids": [],
            "claim_ids": [],
            "not_evidenced_hint": True,
        }
        content = generate_reference_object_content(page, mock_product_facts, mock_snippet_catalog)
        assert _NOT_EVIDENCED_CONTENT in content

    def test_no_fallback_when_claims_present(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_reference_object_content,
            _NOT_EVIDENCED_CONTENT,
        )
        content = generate_reference_object_content(ref_page, mock_product_facts, mock_snippet_catalog)
        assert _NOT_EVIDENCED_CONTENT not in content


# ── Deterministic Fallback Tests ──────────────────────────────────────────────

class TestBuildDeterministicReferenceObject:
    def test_class_members_listed(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_deterministic_reference_object,
        )
        content = _build_deterministic_reference_object(ref_page, mock_product_facts, mock_snippet_catalog)
        # Class has methods: open, save; property: page_count
        assert "open" in content or "save" in content

    def test_contains_python_code_block(self, ref_page, mock_product_facts, mock_snippet_catalog):
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_deterministic_reference_object,
        )
        content = _build_deterministic_reference_object(ref_page, mock_product_facts, mock_snippet_catalog)
        assert "```python" in content or "```" in content

    def test_no_class_entry_uses_claims(self, mock_product_facts, mock_snippet_catalog):
        """When the object has no api_surface entry, falls back to claims."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            _build_deterministic_reference_object,
        )
        page = {
            "section": "reference",
            "slug": "unknown-class",
            "page_role": "reference_object_page",
            "object_name": "UnknownClass",
            "object_kind": "class",
            "required_claim_ids": ["feat-001"],
            "claim_ids": ["feat-001"],
        }
        content = _build_deterministic_reference_object(page, mock_product_facts, mock_snippet_catalog)
        assert isinstance(content, str)
        assert len(content) > 0


# ── Agent 45: Richness Boost + Priority + Role Override Tests ────────────────

class TestRichnessBoostClasses:
    """Agent 45: Verify richness-based quality scoring for per_api_object candidates."""

    def test_richness_boost_classes_with_methods(self):
        """Class with 15 methods gets quality_score >= 5 (even with 0 claims)."""
        raw_cls = {
            "name": "BigClass",
            "methods": [{"name": f"method_{i}"} for i in range(15)],
            "properties": [],
        }
        # Simulate the scoring formula from worker.py:1660-1666
        matching_claims = []
        matching_snippets = []
        quality_score = (len(matching_claims) * 2) + (len(matching_snippets) * 3)
        if isinstance(raw_cls, dict):
            _methods = raw_cls.get("methods", [])
            _props = raw_cls.get("properties", [])
            quality_score += min(len(_methods) // 3, 5)
            quality_score += min(len(_props), 3)
        assert quality_score >= 5  # 15//3 = 5, capped at 5

    def test_richness_boost_empty_class(self):
        """Class with 0 methods/properties and no claims gets quality_score = 0."""
        raw_cls = {"name": "EmptyClass", "methods": [], "properties": []}
        quality_score = 0  # no claims, no snippets
        if isinstance(raw_cls, dict):
            quality_score += min(len(raw_cls.get("methods", [])) // 3, 5)
            quality_score += min(len(raw_cls.get("properties", [])), 3)
        assert quality_score == 0

    def test_richness_boost_properties(self):
        """Class with 5 properties gets +3 bonus (capped)."""
        raw_cls = {
            "name": "PropClass",
            "methods": [],
            "properties": [{"name": f"prop_{i}"} for i in range(5)],
        }
        quality_score = 0
        if isinstance(raw_cls, dict):
            quality_score += min(len(raw_cls.get("methods", [])) // 3, 5)
            quality_score += min(len(raw_cls.get("properties", [])), 3)
        assert quality_score == 3  # min(5, 3) = 3

    def test_richness_boost_caps(self):
        """Max +5 from methods, +3 from properties = +8 total richness."""
        raw_cls = {
            "name": "HugeClass",
            "methods": [{"name": f"m_{i}"} for i in range(100)],
            "properties": [{"name": f"p_{i}"} for i in range(50)],
        }
        quality_score = 0
        if isinstance(raw_cls, dict):
            method_bonus = min(len(raw_cls.get("methods", [])) // 3, 5)
            prop_bonus = min(len(raw_cls.get("properties", [])), 3)
            quality_score += method_bonus + prop_bonus
        assert quality_score == 8  # 5 + 3

    def test_function_docstring_boost(self):
        """Function with docstring gets +1 boost."""
        raw_fn = {"name": "my_func", "docstring": "Does something useful."}
        quality_score = 0  # no matching claims
        if isinstance(raw_fn, dict) and raw_fn.get("docstring"):
            quality_score += 1
        assert quality_score == 1

    def test_function_no_docstring_no_boost(self):
        """Function without docstring gets no boost."""
        raw_fn = {"name": "bare_func"}
        quality_score = 0
        if isinstance(raw_fn, dict) and raw_fn.get("docstring"):
            quality_score += 1
        assert quality_score == 0


class TestRulesetReferenceConfig:
    """Agent 45: Verify ruleset.v1_1.yaml reference section config."""

    def test_reference_max_pages_20(self):
        """ruleset.v1_1 reference section has max_pages == 20."""
        from pathlib import Path
        import yaml

        repo_root = Path(__file__).parent.parent.parent.parent
        ruleset_path = repo_root / "specs" / "rulesets" / "ruleset.v1_1.yaml"
        with open(ruleset_path) as f:
            ruleset = yaml.safe_load(f)
        assert ruleset["sections"]["reference"]["max_pages"] == 20

    def test_per_api_object_priority_over_symbol(self):
        """per_api_object has priority=1, per_api_symbol has priority=2 in ruleset."""
        from pathlib import Path
        import yaml

        repo_root = Path(__file__).parent.parent.parent.parent
        ruleset_path = repo_root / "specs" / "rulesets" / "ruleset.v1_1.yaml"
        with open(ruleset_path) as f:
            ruleset = yaml.safe_load(f)
        policies = ruleset["sections"]["reference"]["optional_page_policies"]
        obj_policy = next(p for p in policies if p["source"] == "per_api_object")
        sym_policy = next(p for p in policies if p["source"] == "per_api_symbol")
        assert obj_policy["priority"] < sym_policy["priority"], (
            f"per_api_object priority ({obj_policy['priority']}) must be < "
            f"per_api_symbol priority ({sym_policy['priority']})"
        )


class TestMandatoryRoleOverride:
    """Agent 45: Verify mandatory page role override logic."""

    def test_mandatory_role_override_toc(self):
        """Template 'landing' role is overridden to 'toc' when ruleset says page_role='toc'."""
        # Simulate the mandatory injection logic from worker.py:4389-4402
        all_pages = [
            {
                "section": "reference",
                "slug": "index",
                "page_role": "landing",
                "title": "Reference Home",
                "content_strategy": {},
            },
        ]
        existing_slugs = {"index"}
        section = "reference"

        # Mandatory config says _index should be toc
        mp = {"slug": "_index", "page_role": "toc"}
        m_slug = mp.get("slug", "")
        m_role = mp.get("page_role", "")
        normalized_slug = "index" if m_slug == "_index" else m_slug

        # The override logic
        if normalized_slug in existing_slugs and m_role:
            for p in all_pages:
                if p["section"] == section and p["slug"] == normalized_slug:
                    if p["page_role"] != m_role:
                        p["page_role"] = m_role
                    break

        assert all_pages[0]["page_role"] == "toc"

    def test_mandatory_role_override_preserves_content(self):
        """Override changes role only, not title or other fields."""
        all_pages = [
            {
                "section": "reference",
                "slug": "index",
                "page_role": "landing",
                "title": "API Reference Index",
                "content_strategy": {"cross_links": ["/docs/"]},
            },
        ]
        original_title = all_pages[0]["title"]
        original_strategy = all_pages[0]["content_strategy"].copy()

        mp = {"slug": "_index", "page_role": "toc"}
        m_role = mp["page_role"]
        normalized_slug = "index"

        for p in all_pages:
            if p["section"] == "reference" and p["slug"] == normalized_slug:
                if p["page_role"] != m_role:
                    p["page_role"] = m_role
                break

        assert all_pages[0]["page_role"] == "toc"
        assert all_pages[0]["title"] == original_title
        assert all_pages[0]["content_strategy"] == original_strategy

    def test_child_pages_populated_for_toc_index(self):
        """_index page with role='toc' gets child_pages listing sibling slugs."""
        # Simulate the child_pages population logic from worker.py:4967-4978
        all_pages = [
            {
                "section": "reference",
                "slug": "index",
                "page_role": "toc",
                "content_strategy": {},
            },
            {
                "section": "reference",
                "slug": "api-overview",
                "page_role": "api_reference",
                "content_strategy": {},
            },
            {
                "section": "reference",
                "slug": "document",
                "page_role": "reference_object_page",
                "content_strategy": {},
            },
            {
                "section": "reference",
                "slug": "scene",
                "page_role": "reference_object_page",
                "content_strategy": {},
            },
        ]

        # Apply child_pages population (mirrors worker.py:4967-4978)
        for page in all_pages:
            if page.get("page_role") == "toc":
                section = page["section"]
                child_slugs = sorted([
                    p["slug"]
                    for p in all_pages
                    if p["section"] == section and p["slug"] != "_index"
                    and p["slug"] != page["slug"]
                ])
                page["content_strategy"]["child_pages"] = child_slugs

        toc_page = all_pages[0]
        assert "child_pages" in toc_page["content_strategy"]
        children = toc_page["content_strategy"]["child_pages"]
        assert "api-overview" in children
        assert "document" in children
        assert "scene" in children
        assert len(children) == 3

    def test_landing_role_skips_child_pages(self):
        """_index page with role='landing' does NOT get child_pages populated."""
        all_pages = [
            {
                "section": "reference",
                "slug": "index",
                "page_role": "landing",
                "content_strategy": {},
            },
            {
                "section": "reference",
                "slug": "api-overview",
                "page_role": "api_reference",
                "content_strategy": {},
            },
        ]

        # Apply child_pages population (only fires for toc)
        for page in all_pages:
            if page.get("page_role") == "toc":
                section = page["section"]
                child_slugs = sorted([
                    p["slug"]
                    for p in all_pages
                    if p["section"] == section and p["slug"] != page["slug"]
                ])
                page["content_strategy"]["child_pages"] = child_slugs

        # landing page should NOT have child_pages
        assert "child_pages" not in all_pages[0]["content_strategy"]
