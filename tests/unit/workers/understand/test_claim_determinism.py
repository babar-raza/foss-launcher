"""TC-UND-211: Tests for claim foundation — sort stability, fallback confidence, evidence expansion, CDN-01.

Covers:
- 1a: _build_api_facts sort determinism + _build_verified_facts_block sort+cap
- 1b: deterministic_fallback confidence = 0.60
- 1c: harvest_evidence_claims produces diversified claims from ExtractionDatabase
- 1d: CDN-01 detection (no LLM-origin claims → evidence claims sole source)
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from launcher.workers.understand.extract._validation import CONFIDENCE_BY_SOURCE, _SOURCE_PRIORITY


# ── 1b: Fallback confidence architecture ──────────────────────────────


class TestFallbackConfidence:
    """TC-UND-211 Phase 1b: deterministic_fallback source exists and survives U-2."""

    def test_deterministic_fallback_in_confidence_map(self):
        assert "deterministic_fallback" in CONFIDENCE_BY_SOURCE

    def test_deterministic_fallback_confidence_is_060(self):
        assert CONFIDENCE_BY_SOURCE["deterministic_fallback"] == 0.60

    def test_deterministic_fallback_survives_u2(self):
        """U-2 threshold is 0.5; deterministic_fallback@0.60 must survive."""
        assert CONFIDENCE_BY_SOURCE["deterministic_fallback"] >= 0.5

    def test_deterministic_fallback_in_source_priority(self):
        assert "deterministic_fallback" in _SOURCE_PRIORITY

    def test_no_dead_zone_between_sources(self):
        """No source should have confidence in the 0.36–0.49 range (dead zone)."""
        for source, conf in CONFIDENCE_BY_SOURCE.items():
            assert conf <= 0.35 or conf >= 0.50, (
                f"{source}={conf} is in the dead zone [0.36, 0.49]"
            )


# ── 1c: harvest_evidence_claims ───────────────────────────────────────


def _make_product(family="cells", platform="python", display_name="Aspose.Cells FOSS for Python"):
    return SimpleNamespace(family=family, platform=platform, display_name=display_name)


def _make_class_brief(name, docstring_snippet="", methods=None, typed_methods=None, typed_properties=None, properties=None, enums=None):
    return SimpleNamespace(
        name=name,
        docstring_snippet=docstring_snippet,
        methods=methods or [],
        typed_methods=typed_methods or [],
        typed_properties=typed_properties or [],
        properties=properties or [],
        enums=enums or [],
    )


def _make_api_surface(class_briefs=None, format_matrix=None):
    return SimpleNamespace(
        class_briefs=class_briefs or [],
        public_classes=[b.name for b in (class_briefs or [])],
        import_allowlist=[],
        format_matrix=format_matrix or [],
    )


def _make_format_fact(name, ext="", can_import=False, can_export=False, source_file=""):
    return SimpleNamespace(
        fact_id=f"FF-test-{name}",
        format_name=name,
        extension=ext,
        can_import=can_import,
        can_export=can_export,
        confidence=0.85,
        evidence_source="enum_declaration",
        source_file=source_file,
    )


def _make_snippet_fact(op_label, code="x = 1", demo_class="", in_fmt="", out_fmt="", source_file="test.py"):
    import hashlib
    h = hashlib.sha256(code.encode()).hexdigest()[:6]
    return SimpleNamespace(
        fact_id=f"SF-test-{op_label}-{h}",
        code=code,
        language="python",
        operation_label=op_label,
        input_format=in_fmt,
        output_format=out_fmt,
        demonstrates_class=demo_class,
        demonstrates_methods=[],
        source_file=source_file,
        source_lines=(1, 10),
        syntax_valid=True,
        confidence=0.9,
    )


def _make_limitation_fact(feature, constraint, source_file=""):
    import hashlib
    h = hashlib.md5(f"{feature}:{constraint}".encode(), usedforsecurity=False).hexdigest()[:6]
    return SimpleNamespace(
        fact_id=f"LF-test-{h}",
        feature=feature,
        constraint=constraint,
        status="warning",
        source_file=source_file,
        source_line=0,
        confidence=0.8,
    )


def _make_install_recipe(cmd="pip install aspose-cells-foss", pkg="aspose-cells-foss"):
    return SimpleNamespace(install_command=cmd, package_name=pkg)


def _make_extraction_db(format_facts=None, snippet_facts=None, limitation_facts=None, install_recipe=None):
    return SimpleNamespace(
        api_facts=[],
        format_facts=format_facts or [],
        snippet_facts=snippet_facts or [],
        limitation_facts=limitation_facts or [],
        install_recipe=install_recipe,
    )


class TestHarvestEvidenceClaims:
    """TC-UND-211 Phase 1c: evidence→claim expansion from ExtractionDatabase."""

    def _harvest(self, **kwargs):
        from launcher.workers.understand.extract._deterministic import harvest_evidence_claims
        return harvest_evidence_claims(**kwargs)

    def test_class_brief_claims_produced(self):
        briefs = [
            _make_class_brief("Workbook", "Represents a spreadsheet workbook with sheets and cells"),
            _make_class_brief("Worksheet", "A single sheet within a workbook"),
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        db = _make_extraction_db()
        product = _make_product()

        claims = self._harvest(api_surface=api_surface, extraction_db=db, product=product)
        api_claims = [c for c in claims if c["kind"] == "api"]
        assert len(api_claims) >= 2
        texts = [c["text"] for c in api_claims]
        assert any("Workbook" in t for t in texts)
        assert any("Worksheet" in t for t in texts)

    def test_class_brief_without_docstring_still_produces_claim(self):
        briefs = [_make_class_brief("Workbook")]
        api_surface = _make_api_surface(class_briefs=briefs)
        db = _make_extraction_db()
        product = _make_product()

        claims = self._harvest(api_surface=api_surface, extraction_db=db, product=product)
        assert len(claims) >= 1
        assert "Workbook" in claims[0]["text"]

    def test_format_claims_produced(self):
        ffs = [
            _make_format_fact("XLSX", ".xlsx", can_import=True, can_export=True),
            _make_format_fact("CSV", ".csv", can_import=True, can_export=True),
        ]
        api_surface = _make_api_surface()
        db = _make_extraction_db(format_facts=ffs)
        product = _make_product()

        claims = self._harvest(api_surface=api_surface, extraction_db=db, product=product)
        fmt_claims = [c for c in claims if c["kind"] == "format"]
        assert len(fmt_claims) == 2
        assert any("XLSX" in c["text"] for c in fmt_claims)
        assert any("reading and writing" in c["text"] for c in fmt_claims)

    def test_format_claim_import_only(self):
        ffs = [_make_format_fact("ODS", ".ods", can_import=True, can_export=False)]
        db = _make_extraction_db(format_facts=ffs)
        claims = self._harvest(
            api_surface=_make_api_surface(), extraction_db=db, product=_make_product(),
        )
        fmt_claims = [c for c in claims if c["kind"] == "format"]
        assert len(fmt_claims) == 1
        assert "reading" in fmt_claims[0]["text"]
        assert "writing" not in fmt_claims[0]["text"]

    def test_snippet_convert_claims(self):
        sfs = [_make_snippet_fact("convert", code="wb.save('out.csv')", in_fmt="XLSX", out_fmt="CSV")]
        db = _make_extraction_db(snippet_facts=sfs)
        claims = self._harvest(
            api_surface=_make_api_surface(), extraction_db=db, product=_make_product(),
        )
        wf_claims = [c for c in claims if c["kind"] == "workflow"]
        assert len(wf_claims) == 1
        assert "XLSX" in wf_claims[0]["text"]
        assert "CSV" in wf_claims[0]["text"]

    def test_snippet_other_skipped(self):
        """Snippets with op_label='other' and no demo class are skipped."""
        sfs = [_make_snippet_fact("other", code="x = 1")]
        db = _make_extraction_db(snippet_facts=sfs)
        claims = self._harvest(
            api_surface=_make_api_surface(), extraction_db=db, product=_make_product(),
        )
        # No snippet claims — 'other' with no class is skipped
        snippet_claims = [c for c in claims if c["kind"] in ("workflow", "example")]
        assert len(snippet_claims) == 0

    def test_limitation_claims_produced(self):
        lfs = [_make_limitation_fact("Threading", "Not thread-safe for concurrent writes")]
        db = _make_extraction_db(limitation_facts=lfs)
        claims = self._harvest(
            api_surface=_make_api_surface(), extraction_db=db, product=_make_product(),
        )
        ts_claims = [c for c in claims if c["kind"] == "troubleshoot"]
        assert len(ts_claims) == 1
        assert "Threading" in ts_claims[0]["text"]

    def test_install_recipe_claim(self):
        recipe = _make_install_recipe()
        db = _make_extraction_db()
        claims = self._harvest(
            api_surface=_make_api_surface(), extraction_db=db, product=_make_product(),
            install_recipe=recipe,
        )
        install_claims = [c for c in claims if c["kind"] == "install"]
        assert len(install_claims) == 1
        assert "pip install" in install_claims[0]["text"]

    def test_all_claims_are_deterministic_source(self):
        briefs = [_make_class_brief("Workbook", "A workbook represents a spreadsheet")]
        ffs = [_make_format_fact("CSV", ".csv", can_import=True, can_export=True)]
        lfs = [_make_limitation_fact("Threading", "Not thread-safe")]
        recipe = _make_install_recipe()
        sfs = [_make_snippet_fact("save_file", out_fmt="CSV")]
        db = _make_extraction_db(format_facts=ffs, snippet_facts=sfs, limitation_facts=lfs)
        api_surface = _make_api_surface(class_briefs=briefs)

        claims = self._harvest(
            api_surface=api_surface, extraction_db=db, product=_make_product(),
            install_recipe=recipe,
        )
        for c in claims:
            assert c["claim_source"] == "deterministic", f"claim {c['text'][:50]} has wrong source"

    def test_kind_diversification(self):
        """Evidence claims must produce at least 3 different kinds."""
        briefs = [_make_class_brief("Workbook", "Represents a spreadsheet workbook")]
        ffs = [_make_format_fact("CSV", ".csv", can_import=True, can_export=True)]
        lfs = [_make_limitation_fact("Threading", "Not thread-safe")]
        recipe = _make_install_recipe()
        sfs = [_make_snippet_fact("save_file", out_fmt="CSV")]
        db = _make_extraction_db(format_facts=ffs, snippet_facts=sfs, limitation_facts=lfs)

        claims = self._harvest(
            api_surface=_make_api_surface(class_briefs=briefs), extraction_db=db,
            product=_make_product(), install_recipe=recipe,
        )
        kinds = {c["kind"] for c in claims}
        assert len(kinds) >= 3, f"Expected ≥3 kinds, got {kinds}"

    def test_deterministic_order_across_runs(self):
        """Claims must be produced in the same order regardless of input order."""
        briefs_a = [
            _make_class_brief("Zebra", "Z class docs here"),
            _make_class_brief("Alpha", "A class docs here"),
        ]
        briefs_b = [
            _make_class_brief("Alpha", "A class docs here"),
            _make_class_brief("Zebra", "Z class docs here"),
        ]
        db = _make_extraction_db()
        product = _make_product()

        claims_a = self._harvest(
            api_surface=_make_api_surface(class_briefs=briefs_a), extraction_db=db, product=product,
        )
        claims_b = self._harvest(
            api_surface=_make_api_surface(class_briefs=briefs_b), extraction_db=db, product=product,
        )
        texts_a = [c["text"] for c in claims_a]
        texts_b = [c["text"] for c in claims_b]
        assert texts_a == texts_b, "Claim order should be deterministic regardless of input order"

    def test_claim_ids_use_ev_prefix(self):
        briefs = [_make_class_brief("Workbook", "Represents a workbook")]
        db = _make_extraction_db()
        claims = self._harvest(
            api_surface=_make_api_surface(class_briefs=briefs), extraction_db=db, product=_make_product(),
        )
        for c in claims:
            assert c["claim_id"].startswith("ev_"), f"Expected ev_ prefix, got {c['claim_id']}"
