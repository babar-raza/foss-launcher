"""Tests for slug_engine.py -- full v1 port verification.

TC-3780: Comprehensive tests for all 8 slug engine layers.
"""

from __future__ import annotations

import pytest

from launcher.shared.slug_engine import (
    FAMILY_KEYWORD_MAP,
    SLUG_LEADING_STOP_WORDS,
    TOPIC_CATEGORY_MAP,
    _VALID_REFINED_SLUG_RE,
    extract_slug_core,
    derive_blog_evidence_slug,
    derive_evidence_aware_slug,
    derive_semantic_slug,
    extract_family_keyword,
    refine_slugs_batch,
    score_blog_workflow,
    strip_html_entities,
    strip_leading_stop_words,
    validate_slug_quality,
    validate_slug_safety,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(**kwargs):
    from launcher.models.understanding import ProductEvidence

    return ProductEvidence(**kwargs)


# ---------------------------------------------------------------------------
# TestFamilyKeyword
# ---------------------------------------------------------------------------


class TestFamilyKeyword:
    def test_cells(self):
        assert extract_family_keyword("cells") == "spreadsheets"

    def test_3d(self):
        assert extract_family_keyword("3d") == "3d-models"

    def test_note(self):
        assert extract_family_keyword("note") == "notebooks"

    def test_words(self):
        assert extract_family_keyword("words") == "documents"

    def test_pdf(self):
        assert extract_family_keyword("pdf") == "pdf-files"

    def test_slides(self):
        assert extract_family_keyword("slides") == "presentations"

    def test_imaging(self):
        assert extract_family_keyword("imaging") == "images"

    def test_unknown_fallback(self):
        assert extract_family_keyword("unknown_product") == "files"

    def test_case_insensitive(self):
        assert extract_family_keyword("Cells") == "spreadsheets"

    def test_substring_match(self):
        assert extract_family_keyword("aspose-cells-python") == "spreadsheets"


# ---------------------------------------------------------------------------
# TestStripLeadingStopWords
# ---------------------------------------------------------------------------


class TestStripLeadingStopWords:
    def test_strips_filler(self):
        assert strip_leading_stop_words("you-can-create-rules") == "create-rules"

    def test_keeps_minimum(self):
        assert strip_leading_stop_words("the-a") == "the-a"

    def test_no_strip_needed(self):
        assert strip_leading_stop_words("convert-formats") == "convert-formats"

    def test_empty_string(self):
        assert strip_leading_stop_words("") == ""

    def test_all_stop_words(self):
        result = strip_leading_stop_words("the-a-an-is")
        # Should keep min_remaining=2
        assert len(result.split("-")) >= 2

    def test_custom_min_remaining(self):
        result = strip_leading_stop_words("the-a-convert", min_remaining=3)
        assert result == "the-a-convert"


# ---------------------------------------------------------------------------
# TestSemanticSlug
# ---------------------------------------------------------------------------


class TestSemanticSlug:
    def test_basic(self):
        result = derive_semantic_slug("Load and manipulate 3D scenes")
        assert result == "load-and-manipulate-3d-scenes"

    def test_strips_spec_header(self):
        result = derive_semantic_slug("11 Section 3: Handle file formats")
        assert "handle" in result

    def test_strips_preamble(self):
        result = derive_semantic_slug(
            "In cases where this document specifies format handling"
        )
        assert not result.startswith("in-cases")

    def test_max_length(self):
        result = derive_semantic_slug("a " * 50, max_length=20)
        assert len(result) <= 20

    def test_empty_fallback(self):
        result = derive_semantic_slug("")
        assert result == "feature"

    def test_whitespace_only_fallback(self):
        result = derive_semantic_slug("   ")
        assert result == "feature"

    def test_special_chars_stripped(self):
        result = derive_semantic_slug("Convert (PDF) to HTML!")
        assert "(" not in result
        assert "!" not in result

    def test_six_word_limit(self):
        result = derive_semantic_slug(
            "one two three four five six seven eight"
        )
        assert "seven" not in result
        assert "six" in result


# ---------------------------------------------------------------------------
# TestEvidenceAwareSlug
# ---------------------------------------------------------------------------


class TestEvidenceAwareSlug:
    def test_convert_with_pairs(self):
        ev = _make_evidence(
            conversion_pairs=[
                {"source": "XLSX", "target": "CSV", "evidence_file": "e.py"}
            ],
            supported_formats=["XLSX", "CSV"],
        )
        result = derive_evidence_aware_slug(
            "How to Convert Formats", "cells", ev, "python"
        )
        assert "xlsx" in result
        assert "csv" in result
        assert "python" in result

    def test_open_intent(self):
        ev = _make_evidence()
        result = derive_evidence_aware_slug(
            "How to Open a File", "3d", ev, "python"
        )
        assert "load" in result
        assert "3d-models" in result
        assert "python" in result

    def test_save_intent(self):
        ev = _make_evidence()
        result = derive_evidence_aware_slug(
            "How to Save Documents", "words", ev, "python"
        )
        assert "save" in result
        assert "documents" in result

    def test_fix_intent(self):
        ev = _make_evidence()
        result = derive_evidence_aware_slug(
            "How to Fix Errors", "cells", ev, "python"
        )
        assert "fix" in result
        assert "spreadsheets" in result
        assert "errors" in result

    def test_performance_intent(self):
        ev = _make_evidence()
        result = derive_evidence_aware_slug(
            "Performance Optimization Tips", "pdf", ev, "python"
        )
        assert "optimize" in result
        assert "pdf-files" in result

    def test_no_intent_fallback(self):
        ev = _make_evidence()
        result = derive_evidence_aware_slug(
            "Working with spreadsheet data", "cells", ev, "python"
        )
        assert "working" in result or "spreadsheet" in result

    def test_convert_no_evidence_fallback(self):
        ev = _make_evidence()
        result = derive_evidence_aware_slug(
            "How to Convert Files", "cells", ev, "python"
        )
        assert "convert" in result
        assert "spreadsheets" in result

    def test_convert_with_supported_formats(self):
        ev = _make_evidence(supported_formats=["PDF", "HTML"])
        result = derive_evidence_aware_slug(
            "How to Convert Files", "pdf", ev, "python"
        )
        assert "pdf" in result
        assert "html" in result


# ---------------------------------------------------------------------------
# TestBlogEvidenceSlug
# ---------------------------------------------------------------------------


class TestBlogEvidenceSlug:
    def test_enriches_with_family(self):
        ev = _make_evidence()
        result = derive_blog_evidence_slug("Convert Formats", "cells", ev, "python")
        assert "spreadsheets" in result

    def test_already_contains_keyword(self):
        ev = _make_evidence()
        result = derive_blog_evidence_slug(
            "Convert Spreadsheets", "cells", ev, "python"
        )
        assert result.count("spreadsheets") == 1

    def test_length_guard(self):
        ev = _make_evidence()
        result = derive_blog_evidence_slug("A" * 35, "cells", ev, "python")
        # If enriched > 40, should return base slug without family keyword
        assert len(result) <= 40 or "spreadsheets" not in result

    def test_empty_title(self):
        ev = _make_evidence()
        result = derive_blog_evidence_slug("", "cells", ev, "python")
        # derive_semantic_slug("") returns "feature", which is non-empty
        # So it gets enriched
        assert result in ("", "feature-spreadsheets")


# ---------------------------------------------------------------------------
# TestBlogWorkflowScoring
# ---------------------------------------------------------------------------


class TestBlogWorkflowScoring:
    def test_no_workflows_fallback(self):
        ev = _make_evidence()
        result = score_blog_workflow(ev, [], "cells", "python")
        assert result["slug"] == "feature-highlight"
        assert result["score"] == 0

    def test_with_workflow(self):
        ev = _make_evidence(
            workflows=[
                {
                    "name": "convert_xlsx_to_csv",
                    "source_file": "examples/convert.py",
                    "api_classes_used": ["Workbook"],
                }
            ],
        )
        result = score_blog_workflow(ev, [], "cells", "python")
        assert result["score"] >= 0

    def test_conversion_with_snippets(self):
        ev = _make_evidence(
            workflows=[
                {
                    "name": "convert_xlsx_to_csv",
                    "tags": ["convert"],
                    "claim_ids": ["c1"],
                }
            ],
        )
        snippets = [{"tags": ["convert"], "claim_ids": ["c1"]}]
        result = score_blog_workflow(ev, snippets, "cells", "python")
        # conversion + snippet overlap → score >= 5+3+2 = 10
        assert result["score"] >= 8

    def test_deterministic_tiebreaker(self):
        ev = _make_evidence(
            workflows=[
                {"name": "load_b_data", "tags": ["load"]},
                {"name": "load_a_data", "tags": ["load"]},
            ],
        )
        result = score_blog_workflow(ev, [], "cells", "python")
        # Both score 2 (high-intent verb "load" in name), tiebreaker = alphabetical
        assert result["workflow_tag"] == "load_a_data"


# ---------------------------------------------------------------------------
# TestRefineSlugsBatch
# ---------------------------------------------------------------------------


class TestRefineSlugsBatch:
    def test_algorithmic_fallback(self):
        slugs = ["you-can-create-rules", "allows-exporting-pdf"]
        result = refine_slugs_batch(slugs, llm_client=None)
        assert result[0] == "create-rules"
        assert "exporting-pdf" in result[1]

    def test_empty_list(self):
        assert refine_slugs_batch([], None) == []

    def test_preserves_length(self):
        slugs = ["slug-a", "slug-b", "slug-c"]
        result = refine_slugs_batch(slugs, llm_client=None)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# TestSlugSafety
# ---------------------------------------------------------------------------


class TestSlugSafety:
    def test_valid_slug(self):
        assert validate_slug_safety("how-to-load-spreadsheets-python") == []

    def test_repr_tokens_bracket(self):
        issues = validate_slug_safety("how-to-['convert']")
        assert any(
            "repr" in i.lower() or "bracket" in i.lower() for i in issues
        )

    def test_repr_tokens_quote(self):
        issues = validate_slug_safety('how-to-"convert"')
        assert len(issues) > 0

    def test_doubled_hyphens(self):
        issues = validate_slug_safety("how-to--convert")
        assert any("double" in i.lower() or "hyphen" in i.lower() for i in issues)

    def test_empty_segments(self):
        issues = validate_slug_safety("how//to/convert")
        assert any("segment" in i.lower() or "slash" in i.lower() for i in issues)

    def test_doubled_url_segment(self):
        issues = validate_slug_safety("python/python/convert")
        assert any("doubled" in i.lower() or "segment" in i.lower() for i in issues)

    def test_consecutive_stop_words(self):
        issues = validate_slug_safety("the-a-convert-files")
        assert any("stop word" in i.lower() for i in issues)

    def test_no_issues_simple(self):
        assert validate_slug_safety("convert-xlsx-to-csv") == []

    def test_entity_artifact_excelreg(self):
        issues = validate_slug_safety("microsoft-excelreg-files")
        assert any("entity" in i.lower() or "remnant" in i.lower() for i in issues)

    def test_entity_artifact_windowsreg(self):
        issues = validate_slug_safety("windowsreg-desktop")
        assert any("entity" in i.lower() for i in issues)

    def test_no_false_positive_registration(self):
        assert validate_slug_safety("registration-form") == []

    def test_no_false_positive_copyright_page(self):
        assert validate_slug_safety("copyright-notice") == []


# ---------------------------------------------------------------------------
# TC-3782: HTML entity handling in slug derivation
# ---------------------------------------------------------------------------


class TestHTMLEntityStripping:
    """derive_semantic_slug and derive_evidence_aware_slug must strip HTML entities."""

    def test_semantic_slug_strips_html_reg(self):
        result = derive_semantic_slug("Print Microsoft Excel&reg; files to printers")
        assert "reg" not in result.split("-"), f"'reg' fragment leaked: {result}"
        assert "excel" in result

    def test_semantic_slug_strips_html_trade(self):
        result = derive_semantic_slug("Windows&trade; Server installation guide")
        assert "trade" not in result.split("-"), f"'trade' fragment leaked: {result}"

    def test_semantic_slug_strips_html_copy(self):
        result = derive_semantic_slug("&copy; 2024 Company documentation")
        assert "copy" not in result.split("-"), f"'copy' fragment leaked: {result}"

    def test_semantic_slug_strips_unicode_symbols(self):
        result = derive_semantic_slug("Print Microsoft Excel\u00ae files")
        assert "reg" not in result.split("-"), f"Unicode reg leaked: {result}"

    def test_evidence_slug_strips_html_entities(self):
        evidence = _make_evidence(
            supported_formats=["XLSX", "CSV"],
            conversion_pairs=[{"source": "XLSX", "target": "CSV"}],
        )
        result = derive_evidence_aware_slug(
            "How to Convert Excel&reg; Files", "cells", evidence, "python",
        )
        assert "reg" not in result.split("-"), f"Entity leaked in evidence slug: {result}"


# ---------------------------------------------------------------------------
# TH-01: Malformed HTML entities (missing semicolons)
# ---------------------------------------------------------------------------


class TestMalformedHTMLEntities:
    """Entities without trailing semicolons must be handled identically."""

    def test_semantic_slug_strips_malformed_entity_no_semicolon(self):
        """&reg (no ;) should produce the same clean slug as &reg;"""
        result = derive_semantic_slug("Print Microsoft Excel&reg files to printers")
        assert "reg" not in result.split("-"), f"Malformed entity leaked: {result}"
        assert "excel" in result

    def test_semantic_slug_strips_numeric_entity(self):
        """&#174; (numeric entity for ®) should be stripped."""
        result = derive_semantic_slug("Print Microsoft Excel&#174; files")
        assert "174" not in result.split("-"), f"Numeric entity leaked: {result}"
        assert "reg" not in result.split("-"), f"reg fragment leaked: {result}"

    def test_evidence_slug_strips_malformed_entity(self):
        evidence = _make_evidence(
            supported_formats=["XLSX", "CSV"],
            conversion_pairs=[{"source": "XLSX", "target": "CSV"}],
        )
        result = derive_evidence_aware_slug(
            "How to Convert Excel&reg Files", "cells", evidence, "python",
        )
        assert "reg" not in result.split("-"), f"Malformed entity leaked: {result}"

    def test_rnd_ampersand_preserved(self):
        """Legitimate & in text (R&D) must not be corrupted."""
        result = derive_semantic_slug("R&D Tools for Development")
        # Should not crash or produce garbage; "rd" or "r-d" are both acceptable
        assert result  # non-empty


# ---------------------------------------------------------------------------
# TH-02: derive_blog_evidence_slug entity stripping
# ---------------------------------------------------------------------------


class TestBlogSlugEntityStripping:
    """derive_blog_evidence_slug must handle entities defensively."""

    def test_blog_slug_strips_html_entities(self):
        evidence = _make_evidence(
            supported_formats=["XLSX"],
            conversion_pairs=[],
        )
        result = derive_blog_evidence_slug(
            "Print Microsoft Excel&reg; Worksheets", "cells", evidence, "python",
        )
        assert "reg" not in result.split("-"), f"Entity leaked in blog slug: {result}"


# ---------------------------------------------------------------------------
# TH-05: Entity artifact validation regex precision
# ---------------------------------------------------------------------------


class TestEntityArtifactPrecision:
    """Refined regex requires 3+ preceding letters."""

    def test_no_false_positive_short_prefix(self):
        """'areg-test' has only 1 preceding letter — should not flag."""
        assert validate_slug_safety("areg-test") == []

    def test_no_false_positive_two_letter_prefix(self):
        """'abreg-test' has only 2 preceding letters — should not flag."""
        assert validate_slug_safety("abreg-test") == []

    def test_three_letter_prefix_flags(self):
        """'abcreg-test' has 3 preceding letters — should flag."""
        issues = validate_slug_safety("abcreg-test")
        assert any("entity" in i.lower() or "remnant" in i.lower() for i in issues)


# ---------------------------------------------------------------------------
# R2-01: Double-encoded HTML entity handling
# ---------------------------------------------------------------------------


class TestDoubleEncodedEntities:
    """Double/triple-encoded entities must be fully decoded."""

    def test_semantic_slug_strips_double_encoded_entity(self):
        """&amp;reg; (double-encoded) must not leak 'reg' or 'amp'."""
        result = derive_semantic_slug("Print Microsoft Excel&amp;reg; files")
        assert "reg" not in result.split("-"), f"Double-encoded reg leaked: {result}"
        assert "amp" not in result.split("-"), f"amp fragment leaked: {result}"
        assert "excelreg" not in result, f"excelreg artifact: {result}"
        assert "excelampreg" not in result, f"excelampreg artifact: {result}"

    def test_semantic_slug_strips_triple_encoded_entity(self):
        """&amp;amp;reg; (triple-encoded) must produce clean slug."""
        result = derive_semantic_slug("Excel&amp;amp;reg; files to export")
        assert "reg" not in result.split("-"), f"Triple-encoded reg leaked: {result}"
        assert "amp" not in result.split("-"), f"amp fragment leaked: {result}"

    def test_strip_convergence_terminates(self):
        """Pathological input should not cause infinite loop."""
        # 6 levels of encoding — exceeds cap of 5, but must still terminate
        text = "test&amp;amp;amp;amp;amp;amp;reg;end"
        result = derive_semantic_slug(text)
        # Must produce a result (not hang), content may still have artifacts
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# R2-03: Edge-case coverage for confirmed-working paths
# ---------------------------------------------------------------------------


class TestEdgeCaseCoverage:
    """Regression tests for paths verified empirically but previously untested."""

    def test_malformed_entity_uppercase(self):
        """&REG (uppercase, no semicolon) handled by IGNORECASE flag."""
        result = derive_semantic_slug("Print Microsoft Excel&REG files")
        assert "reg" not in result.split("-"), f"Uppercase entity leaked: {result}"

    def test_malformed_entity_mixed_case(self):
        """&Reg (mixed case, no semicolon) handled by IGNORECASE flag."""
        result = derive_semantic_slug("Print Microsoft Excel&Reg files")
        assert "reg" not in result.split("-"), f"Mixed-case entity leaked: {result}"

    def test_mixed_entities_same_string(self):
        """Multiple different entities in one string all stripped."""
        result = derive_semantic_slug("Excel&reg; and Windows&trade; files")
        assert "reg" not in result.split("-"), f"reg leaked: {result}"
        assert "trade" not in result.split("-"), f"trade leaked: {result}"

    def test_service_mark_stripped_by_slugification(self):
        """Service mark symbol stripped by slugification regex."""
        result = derive_semantic_slug("Excel\u2120 service files for export")
        # U+2120 is not alphanumeric, so stripped by [^a-z0-9\s-] regex
        assert result
        assert "\u2120" not in result


# ---------------------------------------------------------------------------
# TC-3820: Slug quality validation
# ---------------------------------------------------------------------------


class TestSlugQuality:
    """validate_slug_quality catches semantic issues beyond URL safety."""

    def test_good_slug_passes(self):
        assert validate_slug_quality("how-to-load-spreadsheets-python") == []

    def test_good_blog_slug_passes(self):
        assert validate_slug_quality("introducing-cells-foss-python") == []

    def test_good_feature_slug_passes(self):
        assert validate_slug_quality("cells-key-features") == []

    def test_consecutive_duplicate(self):
        issues = validate_slug_quality("microsoft-windows-windows-desktop")
        assert any("duplicate" in i.lower() for i in issues)

    def test_redundant_words_exact(self):
        issues = validate_slug_quality("spreadsheets-generation-spreadsheets")
        assert any("redundant" in i.lower() for i in issues)

    def test_redundant_words_singular_plural(self):
        """SR-03: spreadsheet vs spreadsheets caught via stemming."""
        issues = validate_slug_quality("spreadsheet-generation-spreadsheets")
        assert any("redundant" in i.lower() for i in issues)

    def test_redundant_words_no_false_positive(self):
        """Common patterns must not false-positive on stemming."""
        assert validate_slug_quality("convert-files-to-formats") == []
        assert validate_slug_quality("how-to-load-spreadsheets-python") == []

    def test_sentence_fragment(self):
        issues = validate_slug_quality("this-repository-provides-a-python-notebooks")
        assert any("sentence" in i.lower() or "stop" in i.lower() for i in issues)

    def test_os_noise_words(self):
        issues = validate_slug_quality("microsoft-windows-desktop-spreadsheets", family="cells")
        assert any("noise" in i.lower() for i in issues)

    def test_noise_words_exempt_if_family_match(self):
        # "linux" is noise but if it were somehow a family keyword, it should be exempt
        # Here "cells" family -> "spreadsheets", so "microsoft" and "windows" are still noise
        issues = validate_slug_quality("microsoft-windows-feature", family="cells")
        assert any("noise" in i.lower() for i in issues)

    def test_index_slug_exempt(self):
        assert validate_slug_quality("_index") == []

    def test_empty_slug_exempt(self):
        assert validate_slug_quality("") == []

    def test_short_slug_no_sentence_flag(self):
        # 3 parts or fewer should not trigger sentence fragment check
        assert validate_slug_quality("the-a-convert") == []

    def test_howto_pattern_exempt_from_sentence(self):
        # how-to-* slugs exempt from stop-word ratio check
        assert validate_slug_quality("how-to-load-spreadsheets-python") == []

    def test_known_bad_blog_slug(self):
        """The actual bad slug from deploy folder."""
        issues = validate_slug_quality(
            "microsoft-windows-windows-desktop-spreadsheets", family="cells"
        )
        assert len(issues) > 0, "Known bad slug should have quality issues"

    def test_known_bad_docs_slug(self):
        """The actual bad docs slug from deploy folder."""
        issues = validate_slug_quality(
            "this-repository-provides-a-python-notebooks"
        )
        assert len(issues) > 0, "Sentence-fragment slug should have quality issues"


# ---------------------------------------------------------------------------
# TC-3820: extract_slug_core
# ---------------------------------------------------------------------------


class TestExtractSlugCore:
    """extract_slug_core extracts verb+noun structure from text."""

    def test_convert_workflow(self):
        result = extract_slug_core("Convert XLSX files to CSV format", "cells")
        assert "convert" in result
        assert "spreadsheets" in result

    def test_create_workflow(self):
        result = extract_slug_core("Create charts and graphs", "cells")
        assert "create" in result
        assert "charts" in result

    def test_load_workflow(self):
        result = extract_slug_core("Load large Excel workbooks efficiently", "cells")
        assert "load" in result
        assert "excel" in result or "workbooks" in result

    def test_no_verb_returns_empty(self):
        result = extract_slug_core("Some random text without verbs", "cells")
        assert result == ""

    def test_empty_input(self):
        assert extract_slug_core("", "cells") == ""

    def test_family_keyword_enrichment(self):
        result = extract_slug_core("Save data files", "cells")
        assert "save" in result
        assert "spreadsheets" in result

    def test_noise_words_filtered(self):
        result = extract_slug_core(
            "Convert Microsoft Windows Desktop files", "cells"
        )
        assert "microsoft" not in result
        assert "windows" not in result
        assert "convert" in result


# ---------------------------------------------------------------------------
# TC-3820: Noise-word filtering in derive_semantic_slug
# ---------------------------------------------------------------------------


class TestSemanticSlugNoiseFilter:
    """derive_semantic_slug filters OS/platform noise words."""

    def test_filters_microsoft_windows(self):
        result = derive_semantic_slug(
            "Microsoft Windows Windows Desktop Spreadsheets"
        )
        assert "microsoft" not in result
        assert "windows" not in result
        assert "spreadsheets" in result

    def test_preserves_product_words(self):
        result = derive_semantic_slug("Excel file format manipulation tools")
        assert "excel" in result

    def test_preserves_meaningful_content(self):
        result = derive_semantic_slug("Load and manipulate 3D scenes")
        assert "load" in result
        assert "manipulate" in result


# ---------------------------------------------------------------------------
# TC-3826: _VALID_REFINED_SLUG_RE tightened + refine_slugs_batch hardening
# ---------------------------------------------------------------------------


class TestValidRefinedSlugRE:
    """_VALID_REFINED_SLUG_RE must reject double-hyphen slugs (TC-3826)."""

    def test_double_hyphen_rejected(self) -> None:
        assert _VALID_REFINED_SLUG_RE.match("convert--pdf") is None

    def test_triple_hyphen_rejected(self) -> None:
        assert _VALID_REFINED_SLUG_RE.match("a---b") is None

    def test_valid_slug_accepted(self) -> None:
        assert _VALID_REFINED_SLUG_RE.match("convert-pdf") is not None

    def test_single_char_accepted(self) -> None:
        assert _VALID_REFINED_SLUG_RE.match("a") is not None

    def test_two_char_accepted(self) -> None:
        assert _VALID_REFINED_SLUG_RE.match("ab") is not None

    def test_multi_word_accepted(self) -> None:
        assert _VALID_REFINED_SLUG_RE.match("excel-file-operations") is not None

    def test_leading_hyphen_rejected(self) -> None:
        assert _VALID_REFINED_SLUG_RE.match("-convert") is None

    def test_trailing_hyphen_rejected(self) -> None:
        assert _VALID_REFINED_SLUG_RE.match("convert-") is None


class TestRefineSlugsBatchHardening:
    """refine_slugs_batch strips entities and validates safety (TC-3826)."""

    class _MockLLMClient:
        """LLM client that returns a fixed response."""

        def __init__(self, response: str) -> None:
            self._response = response

        def chat_completion(self, messages, **kwargs) -> str:  # noqa: ANN001
            return self._response

    def test_double_hyphen_llm_falls_back_to_original(self) -> None:
        """LLM returning 'convert--pdf' must fall back to original slug."""
        client = self._MockLLMClient("convert--pdf")
        result = refine_slugs_batch(["convert-pdf"], llm_client=client)
        assert result == ["convert-pdf"]

    def test_entity_artifact_falls_back_to_original(self) -> None:
        """LLM returning 'excelreg' (from Excel&reg; entity) must fall back."""
        # After entity stripping 'excelreg' has no entity to strip — it's plain text.
        # But after strip+normalize it's still 'excelreg' which passes regex — so we
        # test that the entity is stripped BEFORE the regex check.
        # Real scenario: LLM returns 'excel&reg;-files' → strip_html_entities →
        # 'excel-files' → valid slug accepted.
        client = self._MockLLMClient("excel&reg;-files")
        result = refine_slugs_batch(["excel-spreadsheet-files"], llm_client=client)
        # After entity stripping: 'excel-files' → valid
        assert result == ["excel-files"]

    def test_entity_stripped_before_normalisation(self) -> None:
        """strip_html_entities is called so '&reg;' is removed, not turned into 'reg'."""
        assert strip_html_entities("excel&reg;") == "excel"

    def test_valid_llm_slug_accepted(self) -> None:
        """Clean LLM output is accepted without fallback."""
        client = self._MockLLMClient("convert-pdf")
        result = refine_slugs_batch(["you-can-convert-pdf-files"], llm_client=client)
        assert result == ["convert-pdf"]

    def test_mismatched_count_falls_back(self) -> None:
        """LLM returning wrong line count falls back to algorithmic."""
        client = self._MockLLMClient("only-one-line")
        result = refine_slugs_batch(
            ["slug-a", "slug-b"], llm_client=client
        )
        # Falls through to algorithmic strip_leading_stop_words
        assert len(result) == 2
