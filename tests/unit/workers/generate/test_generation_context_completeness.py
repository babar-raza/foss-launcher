"""TC-4319: GenerationContext completeness enforcement tests.

Verifies that:
1. PlannerWorker includes product_evidence in GenerationContext (TC-4318 fix)
2. _make_understand_from_context() round-trips ProductEvidence correctly
3. Empty product_evidence_dict falls through to empty ProductEvidence() (backward compat)
4. _validate_understand_namespace() warns when product_evidence is empty
"""
from __future__ import annotations

import logging
import pytest
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_install_recipe(cmd: str = "pip install testlib"):
    from launcher.models.understanding import InstallRecipe
    return InstallRecipe(install_command=cmd, package_name="testlib")


def _make_limitation(feature: str, constraint: str):
    from launcher.models.understanding import LimitationEntry
    return LimitationEntry(feature=feature, constraint=constraint)


def _make_product_evidence(limitations=None, install_recipe=None):
    from launcher.models.understanding import ProductEvidence
    return ProductEvidence(
        limitations=limitations or [],
        install_recipe=install_recipe,
        capabilities=[{"text": "Converts XLSX to PDF"}],
        input_formats=["XLSX", "CSV"],
        output_formats=["PDF", "HTML"],
    )


def _make_generation_context(product_evidence_dict: dict):
    from launcher.models.plan import GenerationContext
    return GenerationContext(
        claims=[],
        snippets=[],
        product={},
        richness_tier="B",
        api_surface={},
        product_evidence=product_evidence_dict,
    )


# ---------------------------------------------------------------------------
# TC1: GenerationContext model accepts and stores product_evidence
# ---------------------------------------------------------------------------

class TestGenerationContextModel:
    """TC-4318: GenerationContext model has product_evidence field."""

    def test_product_evidence_field_exists_with_default(self):
        """GenerationContext has product_evidence field defaulting to empty dict."""
        from launcher.models.plan import GenerationContext
        gc = GenerationContext()
        assert hasattr(gc, "product_evidence")
        assert gc.product_evidence == {}

    def test_product_evidence_field_stores_serialized_dict(self):
        """GenerationContext stores a serialized ProductEvidence dict."""
        pe = _make_product_evidence(
            limitations=[_make_limitation("FBX export", "not supported")],
            install_recipe=_make_install_recipe("pip install testlib"),
        )
        pe_dict = pe.model_dump(mode="json")
        gc = _make_generation_context(pe_dict)
        assert gc.product_evidence != {}
        assert gc.product_evidence.get("limitations") is not None
        assert len(gc.product_evidence["limitations"]) == 1
        assert gc.product_evidence["limitations"][0]["feature"] == "FBX export"

    def test_product_evidence_backward_compat_empty_dict(self):
        """Pre-TC-4318 bundles with no product_evidence field load cleanly."""
        from launcher.models.plan import GenerationContext
        # Simulate loading a pre-TC-4318 bundle that lacks product_evidence
        gc = GenerationContext.model_validate({
            "claims": [],
            "snippets": [],
            "product": {},
            "richness_tier": "B",
            "api_surface": {},
            # product_evidence intentionally absent
        })
        assert gc.product_evidence == {}


# ---------------------------------------------------------------------------
# TC2: _make_understand_from_context() round-trips ProductEvidence
# ---------------------------------------------------------------------------

class TestMakeUnderstandFromContext:
    """TC-4318: _make_understand_from_context() deserializes product_evidence."""

    def test_limitations_round_trip(self):
        """ProductEvidence.limitations survive serialization/deserialization."""
        from launcher.workers.generate.worker import _make_understand_from_context

        pe = _make_product_evidence(
            limitations=[
                _make_limitation("FBX export", "not supported"),
                _make_limitation("async API", "experimental"),
            ],
        )
        pe_dict = pe.model_dump(mode="json")

        ns = _make_understand_from_context(
            claims=[], snippets=[], product=None, richness_tier_str="B",
            product_evidence_dict=pe_dict,
        )

        assert ns.product_evidence is not None
        lims = ns.product_evidence.limitations
        assert len(lims) == 2
        assert lims[0].feature == "FBX export"
        assert lims[1].constraint == "experimental"

    def test_install_recipe_round_trip(self):
        """ProductEvidence.install_recipe survives serialization/deserialization."""
        from launcher.workers.generate.worker import _make_understand_from_context

        pe = _make_product_evidence(
            install_recipe=_make_install_recipe("pip install testlib==1.2.3"),
        )
        pe_dict = pe.model_dump(mode="json")

        ns = _make_understand_from_context(
            claims=[], snippets=[], product=None, richness_tier_str="B",
            product_evidence_dict=pe_dict,
        )

        assert ns.product_evidence.install_recipe is not None
        assert ns.product_evidence.install_recipe.install_command == "pip install testlib==1.2.3"

    def test_format_lists_round_trip(self):
        """input_formats and output_formats survive the round trip."""
        from launcher.workers.generate.worker import _make_understand_from_context

        pe = _make_product_evidence()
        pe_dict = pe.model_dump(mode="json")

        ns = _make_understand_from_context(
            claims=[], snippets=[], product=None, richness_tier_str="B",
            product_evidence_dict=pe_dict,
        )

        assert "XLSX" in ns.product_evidence.input_formats
        assert "PDF" in ns.product_evidence.output_formats

    def test_empty_dict_falls_through_to_empty_product_evidence(self):
        """Empty product_evidence_dict yields ProductEvidence() with all defaults."""
        from launcher.workers.generate.worker import _make_understand_from_context
        from launcher.models.understanding import ProductEvidence

        ns = _make_understand_from_context(
            claims=[], snippets=[], product=None, richness_tier_str="B",
            product_evidence_dict={},
        )

        assert ns.product_evidence is not None
        assert ns.product_evidence.limitations == []
        assert ns.product_evidence.install_recipe is None

    def test_none_dict_falls_through_to_empty_product_evidence(self):
        """None product_evidence_dict yields ProductEvidence() with all defaults."""
        from launcher.workers.generate.worker import _make_understand_from_context

        ns = _make_understand_from_context(
            claims=[], snippets=[], product=None, richness_tier_str="B",
            product_evidence_dict=None,
        )

        assert ns.product_evidence.limitations == []

    def test_malformed_dict_falls_through_with_warning(self, caplog):
        """Malformed product_evidence_dict falls back to empty and logs WARNING."""
        from launcher.workers.generate.worker import _make_understand_from_context

        malformed = {"limitations": "this_should_be_a_list_not_a_string"}

        with caplog.at_level(logging.WARNING, logger="launcher"):
            ns = _make_understand_from_context(
                claims=[], snippets=[], product=None, richness_tier_str="B",
                product_evidence_dict=malformed,
            )

        assert ns.product_evidence.limitations == []
        assert any("TC-4318" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# TC4: _validate_understand_namespace() logs WARNING for empty product_evidence
# ---------------------------------------------------------------------------

class TestValidateUnderstandNamespace:
    """TC-4319: _validate_understand_namespace() observability checks."""

    def test_warns_when_product_evidence_is_empty(self, caplog):
        """WARNING is emitted when product_evidence has no non-default fields."""
        from launcher.workers.generate.worker import _validate_understand_namespace
        from launcher.models.understanding import ProductEvidence

        ns = SimpleNamespace(product_evidence=ProductEvidence(), extraction_db=None)

        with caplog.at_level(logging.WARNING, logger="launcher"):
            _validate_understand_namespace(ns, "test_source")

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1
        assert any("TC-4319" in r.message for r in warning_records)
        assert any("product_evidence" in r.message for r in warning_records)

    def test_no_warning_when_product_evidence_is_populated(self, caplog):
        """No WARNING when product_evidence has real evidence."""
        from launcher.workers.generate.worker import _validate_understand_namespace

        pe = _make_product_evidence(
            limitations=[_make_limitation("FBX", "not supported")],
        )
        ns = SimpleNamespace(product_evidence=pe, extraction_db=None)

        with caplog.at_level(logging.WARNING, logger="launcher"):
            _validate_understand_namespace(ns, "test_source")

        warning_records = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "product_evidence" in r.message
        ]
        assert len(warning_records) == 0

    def test_debug_when_extraction_db_is_none(self, caplog):
        """DEBUG is logged (not WARNING) when extraction_db is None."""
        from launcher.workers.generate.worker import _validate_understand_namespace

        pe = _make_product_evidence(
            limitations=[_make_limitation("FBX", "not supported")],
        )
        ns = SimpleNamespace(product_evidence=pe, extraction_db=None)

        with caplog.at_level(logging.DEBUG, logger="launcher"):
            _validate_understand_namespace(ns, "test_source")

        debug_records = [
            r for r in caplog.records
            if r.levelno == logging.DEBUG and "extraction_db" in r.message
        ]
        assert len(debug_records) >= 1

    def test_no_exception_when_product_evidence_attr_missing(self):
        """_validate_understand_namespace() never raises even on missing attributes."""
        from launcher.workers.generate.worker import _validate_understand_namespace

        ns = SimpleNamespace()  # No product_evidence attribute at all
        # Should not raise
        _validate_understand_namespace(ns, "test_source")


# ---------------------------------------------------------------------------
# TC-5161: Evidence quality note injection in build_section_prompt
# ---------------------------------------------------------------------------


def _make_product_identity(display_name: str = "TestLib", platform: str = "python"):
    from launcher.models.product import ProductIdentity
    return ProductIdentity(
        family="testlib",
        platform=platform,
        display_name=display_name,
        canonical_import="testlib",
        repo_url="https://github.com/example/testlib",
    )


def _make_planned_page(page_role: str = "overview"):
    from launcher.models.plan import PlannedPage
    return PlannedPage(
        page_id="test-page",
        title="Test Page",
        page_role=page_role,
        assigned_claims=[],
        assigned_snippets=[],
        frontmatter={},
    )


def _make_skeleton_section():
    from launcher.shared.page_skeletons import SkeletonSection
    return SkeletonSection(
        heading="Introduction",
        content_hint="Describe the product.",
        level=2,
        required=True,
        min_words=100,
        max_words=300,
    )


class TestTC5161EvidenceQualityNote:
    """TC-5161: EVIDENCE QUALITY NOTE is injected when evidence_sufficient=False."""

    def _call_bsp(self, evidence_score):
        from launcher.workers.generate.section_prompt import build_section_prompt
        return build_section_prompt(
            _make_skeleton_section(), 0, 1,
            _make_planned_page(page_role="overview"),
            _make_product_identity(),
            claims=[],
            snippets=[],
            evidence_score=evidence_score,
        )

    def test_evidence_note_injected_when_insufficient(self):
        """evidence_score with evidence_sufficient=False → prompt contains EVIDENCE QUALITY NOTE."""
        result = self._call_bsp({"evidence_sufficient": False, "missing": ["no_snippets"]})
        assert "EVIDENCE QUALITY NOTE" in result
        # SR-01: note must appear before STRICT RULES (template-based, not prepended after)
        assert result.index("EVIDENCE QUALITY NOTE") < result.index("STRICT RULES:")

    def test_evidence_note_no_attribute_error_on_duck_typed_page(self):
        """SR-03: evidence note must not raise AttributeError when page has no page_role attr."""
        from types import SimpleNamespace
        from launcher.workers.generate.section_prompt import build_section_prompt
        page = SimpleNamespace(
            page_id="t", title="T", assigned_claims=[], assigned_snippets=[],
            frontmatter={}, claim_saturation=1.0, code_evidence_sparse=False,
            richness_tier="B",
        )
        result = build_section_prompt(
            _make_skeleton_section(), 0, 1,
            page,  # type: ignore[arg-type]
            _make_product_identity(),
            claims=[], snippets=[],
            evidence_score={"evidence_sufficient": False, "missing": ["x"]},
        )
        assert "EVIDENCE QUALITY NOTE" in result
        assert "unknown" in result  # fallback page_role value from getattr guard

    def test_no_evidence_note_when_sufficient(self):
        """evidence_sufficient=True → no EVIDENCE QUALITY NOTE in prompt."""
        result = self._call_bsp({"evidence_sufficient": True, "missing": []})
        assert "EVIDENCE QUALITY NOTE" not in result

    def test_no_evidence_note_when_none(self):
        """evidence_score=None → no EVIDENCE QUALITY NOTE (backward compat)."""
        result = self._call_bsp(None)
        assert "EVIDENCE QUALITY NOTE" not in result

    def test_evidence_note_capped_missing_at_3(self):
        """10 items in missing → only first 3 shown in note."""
        missing = ["sig1", "sig2", "sig3", "sig4", "sig5", "sig6", "sig7", "sig8", "sig9", "sig10"]
        result = self._call_bsp({"evidence_sufficient": False, "missing": missing})
        assert "sig1" in result
        assert "sig2" in result
        assert "sig3" in result
        assert "sig4" not in result
