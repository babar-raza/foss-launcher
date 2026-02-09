"""TC-970 / TC-981: Unit tests for W4 docs/products/reference/kb token generation.

Tests verify that generate_content_tokens() produces all required tokens
for documentation templates with deterministic values.

TC-981: Additional tests for product-specific token derivation from product_facts,
fill_template_placeholders claim assignment, and title leading space fix.
"""

import os
import pytest
from src.launch.workers.w4_ia_planner.worker import (
    generate_content_tokens,
    _extract_symbols_from_claims,
    fill_template_placeholders,
)


class TestDocsTokenGeneration:
    """Test token generation for docs section."""

    def test_generate_docs_tokens_all_present(self):
        """Verify all 97 required tokens are generated for docs section."""
        page_spec = {"slug": "getting-started"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
            locale="en"
        )

        # Verify critical enable flags present
        required_enable_flags = [
            "__FAQ_ENABLE__", "__OVERVIEW_ENABLE__", "__BODY_ENABLE__",
            "__SUPPORT_AND_LEARNING_ENABLE__", "__BACK_TO_TOP_ENABLE__",
            "__SUPPORT_ENABLE__", "__SINGLE_ENABLE__", "__TESTIMONIALS_ENABLE__",
            "__BUTTON_ENABLE__"
        ]
        for flag in required_enable_flags:
            assert flag in tokens, f"Missing enable flag: {flag}"
            assert tokens[flag] in ["true", "false"], f"Invalid boolean: {tokens[flag]}"

        # Verify head metadata present
        assert "__HEAD_TITLE__" in tokens
        assert "__HEAD_DESCRIPTION__" in tokens
        assert "Aspose.3d" in tokens["__HEAD_TITLE__"]

        # Verify page content tokens
        assert "__PAGE_TITLE__" in tokens
        assert "__PAGE_DESCRIPTION__" in tokens
        assert "__OVERVIEW_TITLE__" in tokens
        assert "__OVERVIEW_CONTENT__" in tokens

        # Verify body blocks
        assert "__BODY_BLOCK_TITLE_LEFT__" in tokens
        assert "__BODY_BLOCK_CONTENT_LEFT__" in tokens
        assert "__BODY_BLOCK_TITLE_RIGHT__" in tokens
        assert "__BODY_BLOCK_CONTENT_RIGHT__" in tokens

        # Verify code blocks
        assert "__BODY_BLOCK_GIST_HASH__" in tokens
        assert "__BODY_BLOCK_GIST_FILE__" in tokens
        assert len(tokens["__BODY_BLOCK_GIST_HASH__"]) == 12  # MD5 truncated
        assert "__SINGLE_GIST_HASH__" in tokens
        assert "__SINGLE_GIST_FILE__" in tokens
        assert "__CODESAMPLES__" in tokens

        # Verify FAQ
        assert "__FAQ_QUESTION__" in tokens
        assert "__FAQ_ANSWER__" in tokens

        # Verify plugin metadata
        assert "__PLUGIN_NAME__" in tokens
        assert "__PLUGIN_DESCRIPTION__" in tokens
        assert "__PLUGIN_PLATFORM__" in tokens
        assert "__CART_ID__" in tokens
        assert "__PRODUCT_NAME__" in tokens

        # Verify misc tokens
        assert "__TOKEN__" in tokens
        assert tokens["__TOKEN__"] == ""  # Empty string placeholder
        assert "__WEIGHT__" in tokens
        assert "__LOCALE__" in tokens
        assert "__SECTION_PATH__" in tokens
        assert "__UPPER_SNAKE__" in tokens

        # Verify all tokens from error message are present
        error_tokens = [
            "__FAQ_ENABLE__", "__HEAD_TITLE__", "__PAGE_TITLE__",
            "__SUPPORT_AND_LEARNING_ENABLE__", "__PLUGIN_NAME__",
            "__BODY_BLOCK_GIST_HASH__", "__OVERVIEW_TITLE__",
            "__BODY_BLOCK_GIST_FILE__", "__FAQ_ANSWER__", "__MORE_FORMATS_ENABLE__",
            "__OVERVIEW_CONTENT__", "__FAQ_QUESTION__", "__BODY_BLOCK_CONTENT_LEFT__",
            "__TOKEN__", "__SUBMENU_ENABLE__", "__OVERVIEW_ENABLE__",
            "__BODY_BLOCK_TITLE_LEFT__", "__HEAD_DESCRIPTION__",
            "__PLUGIN_DESCRIPTION__", "__CART_ID__", "__PAGE_DESCRIPTION__",
            "__BODY_BLOCK_CONTENT_RIGHT__", "__BACK_TO_TOP_ENABLE__",
            "__BODY_ENABLE__", "__PLUGIN_PLATFORM__", "__BODY_BLOCK_TITLE_RIGHT__"
        ]
        for token in error_tokens:
            assert token in tokens, f"Missing token from error list: {token}"
            # __TOKEN__ is intentionally empty (generic placeholder)
            # __PLUGIN_PLATFORM__ is intentionally empty (V2 platform layout removed)
            if token not in ("__TOKEN__", "__PLUGIN_PLATFORM__"):
                assert tokens[token] != "", f"Token has empty value: {token}"

    def test_docs_tokens_deterministic(self):
        """Verify docs token generation is deterministic."""
        page_spec = {"slug": "index"}

        tokens1 = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
        )

        tokens2 = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
        )

        # All tokens must match exactly
        assert tokens1 == tokens2, "Token generation is non-deterministic"

        # Verify gist hash is deterministic
        assert tokens1["__BODY_BLOCK_GIST_HASH__"] == tokens2["__BODY_BLOCK_GIST_HASH__"]

    def test_products_section_enables_more_formats(self):
        """Verify products section enables __MORE_FORMATS_ENABLE__."""
        page_spec = {"slug": "converter"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="products",
            family="3d",
        )

        assert tokens["__MORE_FORMATS_ENABLE__"] == "true"

    def test_docs_section_disables_more_formats(self):
        """Verify docs section disables __MORE_FORMATS_ENABLE__."""
        page_spec = {"slug": "guide"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
        )

        assert tokens["__MORE_FORMATS_ENABLE__"] == "false"

    def test_reference_section_enables_single(self):
        """Verify reference section enables __SINGLE_ENABLE__."""
        page_spec = {"slug": "scene-class"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="reference",
            family="3d",
        )

        assert tokens["__SINGLE_ENABLE__"] == "true"

    def test_docs_section_disables_single(self):
        """Verify docs section disables __SINGLE_ENABLE__."""
        page_spec = {"slug": "guide"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
        )

        assert tokens["__SINGLE_ENABLE__"] == "false"

    def test_kb_section_token_generation(self):
        """Verify kb section generates all required tokens."""
        page_spec = {"slug": "troubleshooting"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="kb",
            family="note",
        )

        # Verify section-specific content
        assert "Aspose.Note" in tokens["__PLUGIN_NAME__"]
        assert "__FAQ_ENABLE__" in tokens
        assert "__BODY_ENABLE__" in tokens
        assert tokens["__FAQ_ENABLE__"] == "true"
        assert tokens["__MORE_FORMATS_ENABLE__"] == "false"  # kb not products

    def test_slug_transformation_in_tokens(self):
        """Verify slug is properly transformed in token values."""
        page_spec = {"slug": "working-with-meshes"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
        )

        # Slug should be transformed to title case with spaces
        assert "Working With Meshes" in tokens["__PAGE_TITLE__"]
        assert "working_with_meshes" in tokens["__BODY_BLOCK_GIST_FILE__"]
        assert "WORKING_WITH_MESHES" in tokens["__UPPER_SNAKE__"]

    def test_locale_token_passthrough(self):
        """Verify locale parameter is passed through to __LOCALE__ token."""
        page_spec = {"slug": "index"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
            locale="fr"
        )

        assert tokens["__LOCALE__"] == "fr"

    def test_gist_hash_deterministic_per_context(self):
        """Verify gist hash is deterministic and unique per family/platform/slug."""
        page_spec1 = {"slug": "example1"}
        page_spec2 = {"slug": "example2"}

        tokens1 = generate_content_tokens(
            page_spec=page_spec1,
            section="docs",
            family="3d",
        )

        tokens2 = generate_content_tokens(
            page_spec=page_spec2,
            section="docs",
            family="3d",
        )

        # Different slugs should produce different hashes
        assert tokens1["__BODY_BLOCK_GIST_HASH__"] != tokens2["__BODY_BLOCK_GIST_HASH__"]

        # Same context should produce same hash
        tokens1_repeat = generate_content_tokens(
            page_spec=page_spec1,
            section="docs",
            family="3d",
        )
        assert tokens1["__BODY_BLOCK_GIST_HASH__"] == tokens1_repeat["__BODY_BLOCK_GIST_HASH__"]


class TestBlogTokensStillWork:
    """Verify TC-964 blog tokens still work after TC-970 changes."""

    def test_blog_tokens_unchanged(self):
        """Verify blog section still generates expected tokens from TC-964."""
        page_spec = {"slug": "release-notes"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="3d",
        )

        # Verify TC-964 blog tokens present
        required_blog_tokens = [
            "__TITLE__", "__SEO_TITLE__", "__DESCRIPTION__", "__SUMMARY__",
            "__AUTHOR__", "__DATE__", "__DRAFT__",
            "__BODY_INTRO__", "__BODY_OVERVIEW__", "__BODY_CODE_SAMPLES__",
            "__BODY_CONCLUSION__", "__BODY_PREREQUISITES__", "__BODY_STEPS__",
            "__BODY_KEY_TAKEAWAYS__", "__BODY_TROUBLESHOOTING__", "__BODY_NOTES__",
            "__BODY_SEE_ALSO__"
        ]

        for token in required_blog_tokens:
            assert token in tokens, f"Blog token missing: {token}"

        # Verify blog-specific behavior
        assert "Aspose.3d" in tokens["__TITLE__"]
        assert tokens["__DATE__"] == "2024-01-01"  # Deterministic date
        assert tokens["__DRAFT__"] == "false"

    def test_blog_section_no_docs_tokens(self):
        """Verify blog section does not generate docs-specific tokens."""
        page_spec = {"slug": "article"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="blog",
            family="3d",
        )

        # Docs-specific tokens should NOT be present for blog
        docs_specific_tokens = [
            "__FAQ_ENABLE__", "__OVERVIEW_ENABLE__", "__MORE_FORMATS_ENABLE__",
            "__BODY_BLOCK_GIST_HASH__", "__SINGLE_ENABLE__"
        ]

        for token in docs_specific_tokens:
            assert token not in tokens, f"Docs token should not be in blog: {token}"


class TestTokenValueFormats:
    """Test token value formats and constraints."""

    def test_enable_flags_are_strings(self):
        """Verify enable flags are string 'true'/'false' not booleans."""
        page_spec = {"slug": "test"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
        )

        enable_flags = [k for k in tokens.keys() if k.endswith("_ENABLE__")]
        for flag in enable_flags:
            assert isinstance(tokens[flag], str), f"{flag} should be string"
            assert tokens[flag] in ["true", "false"], f"{flag} has invalid value"

    def test_gist_hash_format(self):
        """Verify gist hash is 12-character hex string."""
        page_spec = {"slug": "test"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
        )

        gist_hash = tokens["__BODY_BLOCK_GIST_HASH__"]
        assert len(gist_hash) == 12, "Gist hash should be 12 characters"
        assert all(c in "0123456789abcdef" for c in gist_hash), "Gist hash should be hex"

    def test_no_empty_values_for_critical_tokens(self):
        """Verify critical tokens have non-empty values."""
        page_spec = {"slug": "test"}
        tokens = generate_content_tokens(
            page_spec=page_spec,
            section="docs",
            family="3d",
        )

        critical_tokens = [
            "__HEAD_TITLE__", "__PAGE_TITLE__", "__OVERVIEW_CONTENT__",
            "__PLUGIN_NAME__", "__CART_ID__"
        ]

        for token in critical_tokens:
            assert tokens[token] != "", f"{token} should not be empty"
            assert len(tokens[token]) > 0, f"{token} should have content"




# --- TC-981 Tests -----------------------------------------------------------


class TestExtractSymbolsFromClaims:
    """TC-981: Test _extract_symbols_from_claims helper."""

    def _make_product_facts_with_api(self):
        """Create product_facts with API claims."""
        return {
            "api_surface_summary": {
                "classes": ["claim_api_1", "claim_api_2"],
                "functions": [],
            },
            "claims": [
                {
                    "claim_id": "claim_api_1",
                    "claim_kind": "api",
                    "claim_text": (
                        "Implemented **Scene**, **Node**, **Entity** classes. "
                        "Also uses GlobalTransform for coordinate handling."
                    ),
                },
                {
                    "claim_id": "claim_api_2",
                    "claim_kind": "api",
                    "claim_text": (
                        "**Material** provides PhongMaterial. "
                        "**Scene** is the root container."
                    ),
                },
                {
                    "claim_id": "claim_other",
                    "claim_kind": "feature",
                    "claim_text": "Supports OBJ and STL.",
                },
            ],
            "claim_groups": {"key_features": ["claim_other"]},
        }

    def test_returns_dict_with_expected_keys(self):
        """Result must have all expected keys."""
        result = _extract_symbols_from_claims(None, "note")
        assert "key_symbols" in result
        assert "popular_classes" in result
        assert "signature_class" in result
        assert "entry_point" in result

    def test_none_product_facts_returns_family_defaults(self):
        """None product_facts uses family-based fallback."""
        result = _extract_symbols_from_claims(None, "note")
        assert result["signature_class"] == "NoteDocument"
        assert "NoteDocument" in result["key_symbols"]
        assert "NotePage" in result["key_symbols"]

    def test_empty_product_facts_returns_defaults(self):
        """Empty dict uses family-based fallback."""
        result = _extract_symbols_from_claims({}, "pdf")
        assert result["signature_class"] == "PdfDocument"

    def test_no_api_classes_returns_defaults(self):
        """No api classes falls back to family."""
        pf = {"api_surface_summary": {"classes": []}, "claims": []}
        result = _extract_symbols_from_claims(pf, "cells")
        assert result["signature_class"] == "CellsDocument"

    def test_extracts_bold_class_names(self):
        """Bold class names should be extracted."""
        pf = self._make_product_facts_with_api()
        result = _extract_symbols_from_claims(pf, "3d")
        assert "Scene" in result["key_symbols"]

    def test_most_frequent_is_signature(self):
        """Most frequent class is signature_class."""
        pf = self._make_product_facts_with_api()
        result = _extract_symbols_from_claims(pf, "3d")
        assert result["signature_class"] == "Scene"

    def test_noise_words_filtered(self):
        """Exception names like NotImplementedError filtered out."""
        pf = {
            "api_surface_summary": {"classes": ["c1"]},
            "claims": [{
                "claim_id": "c1",
                "claim_kind": "api",
                "claim_text": "Raises **NotImplementedError** for **Widget**",
            }],
        }
        result = _extract_symbols_from_claims(pf, "test")
        assert "NotImplementedError" not in result["key_symbols"]
        assert "Widget" in result["key_symbols"]

    def test_deterministic_output(self):
        """Same input produces identical output."""
        pf = self._make_product_facts_with_api()
        r1 = _extract_symbols_from_claims(pf, "3d")
        r2 = _extract_symbols_from_claims(pf, "3d")
        assert r1 == r2

class TestGenerateContentTokensWithProductFacts:
    """TC-981: Test product-specific token generation."""

    def _make_product_facts(self):
        return {
            "api_surface_summary": {"classes": ["c1"], "functions": []},
            "claims": [{
                "claim_id": "c1",
                "claim_kind": "api",
                "claim_text": "The **Document** class is the main entry point. **Page** handles content.",
            }],
            "claim_groups": {"key_features": ["c1"]},
        }

    def test_product_facts_none_backward_compatible(self):
        """Calling without product_facts should still work."""
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="3d",
        )
        assert "__BODY_KEY_SYMBOLS__" in tokens
        assert tokens["__BODY_KEY_SYMBOLS__"] != ""

    def test_product_facts_changes_api_tokens(self):
        """With product_facts, tokens should reflect product classes."""
        pf = self._make_product_facts()
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="note",
            product_facts=pf,
        )
        assert "Document" in tokens["__BODY_KEY_SYMBOLS__"]
        assert "Document" in tokens["__BODY_SIGNATURE__"]

    def test_no_hardcoded_scene_for_note(self):
        """Note product must NOT contain Scene class name."""
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="note",
            product_facts=None,
        )
        assert "Scene" not in tokens["__BODY_KEY_SYMBOLS__"]
        assert "NoteDocument" in tokens["__BODY_KEY_SYMBOLS__"]

    def test_signature_uses_extracted_class(self):
        """__BODY_SIGNATURE__ should use the extracted class."""
        pf = self._make_product_facts()
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="reference",
            family="note",
            product_facts=pf,
        )
        assert "class Document" in tokens["__BODY_SIGNATURE__"]

    def test_returns_uses_extracted_class(self):
        """__BODY_RETURNS__ should reference the extracted class."""
        pf = self._make_product_facts()
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="note",
            product_facts=pf,
        )
        assert "Document" in tokens["__BODY_RETURNS__"]

    def test_deterministic_with_product_facts(self):
        """Token generation with product_facts must be deterministic."""
        pf = self._make_product_facts()
        t1 = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="3d",
            product_facts=pf,
        )
        t2 = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="3d",
            product_facts=pf,
        )
        assert t1 == t2


class TestGenerateContentTokensWithProductFacts:
    """TC-981: Test product-specific token generation."""

    def _make_product_facts(self):
        return {
            "api_surface_summary": {"classes": ["c1"], "functions": []},
            "claims": [{
                "claim_id": "c1",
                "claim_kind": "api",
                "claim_text": "The **Document** class is the entry point. **Page** handles content.",
            }],
            "claim_groups": {"key_features": ["c1"]},
        }

    def test_product_facts_none_backward_compatible(self):
        """Calling without product_facts still works."""
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="3d",
        )
        assert "__BODY_KEY_SYMBOLS__" in tokens
        assert tokens["__BODY_KEY_SYMBOLS__"] != ""

    def test_product_facts_changes_api_tokens(self):
        """With product_facts, tokens reflect product classes."""
        pf = self._make_product_facts()
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="note",
            product_facts=pf,
        )
        assert "Document" in tokens["__BODY_KEY_SYMBOLS__"]
        assert "Document" in tokens["__BODY_SIGNATURE__"]

    def test_no_hardcoded_scene_for_note(self):
        """Note product must NOT contain Scene class name."""
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="docs",
            family="note",
            product_facts=None,
        )
        assert "Scene" not in tokens["__BODY_KEY_SYMBOLS__"]
        assert "NoteDocument" in tokens["__BODY_KEY_SYMBOLS__"]

    def test_signature_uses_extracted_class(self):
        """__BODY_SIGNATURE__ uses the extracted class."""
        pf = self._make_product_facts()
        tokens = generate_content_tokens(
            page_spec={"slug": "test"},
            section="reference",
            family="note",
            product_facts=pf,
        )
        assert "class Document" in tokens["__BODY_SIGNATURE__"]

    def test_deterministic_with_product_facts(self):
        """Token generation with product_facts is deterministic."""
        pf = self._make_product_facts()
        kw = dict(page_spec={"slug": "test"}, section="docs", family="3d", product_facts=pf)
        t1 = generate_content_tokens(**kw)
        t2 = generate_content_tokens(**kw)
        assert t1 == t2


class TestFillTemplatePlaceholdersClaimAssignment:
    """TC-981: Test fill_template_placeholders assigns claims."""

    def _find_template(self):
        """Find an actual template file with Hugo frontmatter for testing."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))))
        template_dir = os.path.join(repo_root, "specs", "templates")
        for root, dirs, files in os.walk(template_dir):
            for f in sorted(files):
                if f.endswith(".md") and f != "README.md":
                    fpath = os.path.join(root, f)
                    with open(fpath, "r", encoding="utf-8") as fh:
                        if fh.read(3) == "---":
                            return {"slug": "index", "template_path": fpath, "variant": "minimal"}
        return None

    def _make_product_facts(self):
        return {
            "claims": [
                {"claim_id": "kf1", "claim_kind": "feature", "claim_text": "Feature A"},
                {"claim_id": "kf2", "claim_kind": "feature", "claim_text": "Feature B"},
                {"claim_id": "is1", "claim_kind": "install", "claim_text": "Install via pip"},
                {"claim_id": "lm1", "claim_kind": "limitation", "claim_text": "Limitation 1"},
            ],
            "claim_groups": {"key_features": ["kf1", "kf2"], "install_steps": ["is1"], "limitations": ["lm1"]},
            "api_surface_summary": {"classes": [], "functions": []},
        }

    def test_template_pages_get_claim_ids(self):
        """Template pages should have non-empty required_claim_ids."""
        template = self._find_template()
        if template is None:
            pytest.skip("No template files found")
        pf = self._make_product_facts()
        page_spec = fill_template_placeholders(
            template=template, section="docs", product_slug="test",
            locale="en", subdomain="docs.aspose.org", product_facts=pf,
        )
        assert len(page_spec["required_claim_ids"]) > 0

    def test_template_pages_claim_ids_sorted(self):
        """Template page claim IDs must be sorted."""
        template = self._find_template()
        if template is None:
            pytest.skip("No template files found")
        pf = self._make_product_facts()
        page_spec = fill_template_placeholders(
            template=template, section="docs", product_slug="test",
            locale="en", subdomain="docs.aspose.org", product_facts=pf,
        )
        ids = page_spec["required_claim_ids"]
        assert ids == sorted(ids)

    def test_no_product_facts_gives_empty_claims(self):
        """Without product_facts, required_claim_ids should be empty."""
        template = self._find_template()
        if template is None:
            pytest.skip("No template files found")
        page_spec = fill_template_placeholders(
            template=template, section="docs", product_slug="test",
            locale="en", subdomain="docs.aspose.org",
        )
        assert page_spec["required_claim_ids"] == []

    def test_kb_section_assigns_install_and_limitation_claims(self):
        """KB section pulls from install_steps + limitations (like docs and blog)."""
        template = self._find_template()
        if template is None:
            pytest.skip("No template files found")
        pf = self._make_product_facts()
        page_spec = fill_template_placeholders(
            template=template, section="kb", product_slug="test",
            locale="en", subdomain="kb.aspose.org", product_facts=pf,
        )
        ids = page_spec["required_claim_ids"]
        # KB uses install_steps + limitations combined
        assert "lm1" in ids
        assert "is1" in ids


class TestTitleLeadingSpaceFix:
    """TC-981 RC-5: Verify title has no leading space."""

    def test_empty_product_name_no_leading_space(self):
        """When product_name is empty, no leading space."""
        from src.launch.workers.w4_ia_planner.worker import plan_pages_for_section
        product_facts = {
            "product_name": "",
            "claims": [{"claim_id": "c1", "claim_kind": "feature", "claim_text": "Test"}],
            "claim_groups": {"key_features": ["c1"], "install_steps": []},
            "workflows": [],
        }
        pages = plan_pages_for_section(
            section="products", launch_tier="minimal", product_facts=product_facts,
            snippet_catalog={"snippets": []}, product_slug="note",
        )
        assert len(pages) == 1
        title = pages[0]["title"]
        assert not title.startswith(" ")
        assert "Aspose.Note" in title

    def test_whitespace_product_name_no_leading_space(self):
        """When product_name is only whitespace, no leading space."""
        from src.launch.workers.w4_ia_planner.worker import plan_pages_for_section
        product_facts = {
            "product_name": "   ",
            "claims": [{"claim_id": "c1", "claim_kind": "feature", "claim_text": "Test"}],
            "claim_groups": {"key_features": ["c1"], "install_steps": []},
            "workflows": [],
        }
        pages = plan_pages_for_section(
            section="products", launch_tier="minimal", product_facts=product_facts,
            snippet_catalog={"snippets": []}, product_slug="cells",
        )
        title = pages[0]["title"]
        assert not title.startswith(" ")
        assert "Aspose.Cells" in title

    def test_valid_product_name_preserved(self):
        """When product_name is valid, it is used."""
        from src.launch.workers.w4_ia_planner.worker import plan_pages_for_section
        product_facts = {
            "product_name": "Aspose.3D for Python",
            "claims": [{"claim_id": "c1", "claim_kind": "feature", "claim_text": "Test"}],
            "claim_groups": {"key_features": ["c1"], "install_steps": []},
            "workflows": [],
        }
        pages = plan_pages_for_section(
            section="products", launch_tier="minimal", product_facts=product_facts,
            snippet_catalog={"snippets": []}, product_slug="3d",
        )
        title = pages[0]["title"]
        assert title == "Aspose.3D for Python Overview"
