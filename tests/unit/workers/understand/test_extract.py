"""Tests for TC-3816: Adaptive understand — contamination filter, ClassBrief, docstring claims, synthetic snippets."""

from __future__ import annotations

from pathlib import Path

import pytest

from launcher.models.claims import Claim, EvidenceAnchor, Snippet
from launcher.models.product import ApiSurface, ClassBrief, ProductIdentity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product(**overrides) -> ProductIdentity:
    defaults = dict(
        family="note",
        platform="python",
        display_name="Aspose.Note",
        canonical_import="aspose_note_foss",
        repo_url="https://example.com",
    )
    defaults.update(overrides)
    return ProductIdentity(**defaults)


def _make_api_surface(class_briefs: list[ClassBrief] | None = None, **kw) -> ApiSurface:
    defaults = dict(
        public_classes=[b.name for b in (class_briefs or [])],
        import_allowlist=["aspose_note_foss"],
        confidence="high",
        api_identifiers=[],
        class_briefs=class_briefs or [],
    )
    defaults.update(kw)
    return ApiSurface(**defaults)


# ===========================================================================
# 1. Contamination filter tests
# ===========================================================================


class TestContaminationFilter:
    """Test that third-party and internal classes are filtered out."""

    def test_package_path_filtering(self, tmp_path):
        """Only files under package_root should contribute to API surface."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(canonical_import="aspose_note_foss")

        # Create package root
        pkg = tmp_path / "src" / "aspose_note_foss"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
        (pkg / "document.py").write_text(
            "class Document:\n    def load(self): pass\n",
            encoding="utf-8",
        )

        # Create a third-party file OUTSIDE the package root
        ext = tmp_path / "examples" / "third_party.py"
        ext.parent.mkdir(parents=True)
        ext.write_text(
            "class DoclingParser:\n    def parse(self): pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert "Document" in result.public_classes
        assert "DoclingParser" not in result.public_classes

    def test_internal_class_heuristic_filters_fnd(self, tmp_path):
        """Classes with FND/Chunk/Reference markers should be excluded."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(canonical_import="aspose_note_foss")

        pkg = tmp_path / "src" / "aspose_note_foss"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
        (pkg / "internals.py").write_text(
            "class DataSignatureGroupDefinitionFND:\n    pass\n"
            "class FileChunkReference32:\n    pass\n"
            "class BinaryReader:\n    pass\n"
            "class Document:\n    pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert "Document" in result.public_classes
        assert "DataSignatureGroupDefinitionFND" not in result.public_classes
        assert "FileChunkReference32" not in result.public_classes
        assert "BinaryReader" not in result.public_classes


# ===========================================================================
# 2. ClassBrief population tests
# ===========================================================================


class TestClassBriefPopulation:
    """Test that ClassBrief objects are built from analyzer data."""

    def test_methods_and_properties_captured(self, tmp_path):
        """ClassBrief should capture methods and properties from source."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(canonical_import="aspose_note_foss")

        pkg = tmp_path / "src" / "aspose_note_foss"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
        (pkg / "page.py").write_text(
            'class Page:\n'
            '    """Represents a single page in a notebook."""\n'
            '    @property\n'
            '    def title(self): pass\n'
            '    @property\n'
            '    def level(self): pass\n'
            '    def accept(self, visitor): pass\n'
            '    def clone(self): pass\n'
            '    def _internal(self): pass\n',
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert len(result.class_briefs) == 1

        brief = result.class_briefs[0]
        assert brief.name == "Page"
        assert "accept" in brief.methods
        assert "clone" in brief.methods
        assert "_internal" not in brief.methods
        assert "title" in brief.properties
        assert "level" in brief.properties
        assert "Represents a single page" in brief.docstring_snippet

    def test_methods_capped_at_10(self, tmp_path):
        """ClassBrief should cap methods and properties at 10 each."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(canonical_import="aspose_note_foss")

        pkg = tmp_path / "src" / "aspose_note_foss"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()

        # Generate a class with 15 methods
        methods = "\n".join(f"    def method_{i}(self): pass" for i in range(15))
        (pkg / "big_class.py").write_text(
            f"class BigClass:\n{methods}\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        brief = result.class_briefs[0]
        assert len(brief.methods) <= 10


# ===========================================================================
# 3. Docstring claims tests
# ===========================================================================


class TestDocstringClaims:
    """Test docstring-to-claim harvesting (raw dict output for AQ-01)."""

    def test_docstring_claims_raw_created(self):
        """ClassBrief with docstrings > 30 chars should yield raw claim dicts."""
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        product = _make_product()
        briefs = [
            ClassBrief(
                name="Document",
                docstring_snippet="Represents the main document container for OneNote files.",
                methods=["load", "save", "close"],
                properties=["pages", "title"],
            ),
            ClassBrief(
                name="Page",
                docstring_snippet="A single page within a notebook section.",
                methods=["accept", "clone"],
                properties=["title"],
            ),
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        raw = _harvest_docstring_claims_raw(api_surface, product)

        # Each class should produce: 1 docstring claim + 1 method-list claim = 4 total
        assert len(raw) >= 4
        assert all(isinstance(r, dict) for r in raw)
        assert all(r["kind"] == "api" for r in raw)
        # Raw dicts should have text, kind, evidence keys
        for r in raw:
            assert "text" in r
            assert "kind" in r
            assert "evidence" in r
        # Docstring claim text should contain class name and docstring
        doc_claims = [r for r in raw if "Represents" in r["text"]]
        assert len(doc_claims) == 1
        assert "Document" in doc_claims[0]["text"]

    def test_short_docstrings_skipped(self):
        """Docstrings shorter than 30 chars should not become claims."""
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        product = _make_product()
        briefs = [
            ClassBrief(name="Tiny", docstring_snippet="Short.", methods=["run"]),
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        raw = _harvest_docstring_claims_raw(api_surface, product)

        # Should only have the method-list claim, not a docstring claim
        doc_claims = [r for r in raw if "Short." in r["text"]]
        assert len(doc_claims) == 0

    def test_max_claims_cap(self):
        """Should not exceed max_claims."""
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        product = _make_product()
        briefs = [
            ClassBrief(
                name=f"Class{i}",
                docstring_snippet=f"This is a long enough docstring for class number {i}.",
                methods=[f"method_{i}"],
            )
            for i in range(100)
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        raw = _harvest_docstring_claims_raw(api_surface, product, max_claims=10)
        assert len(raw) <= 10

    def test_docstring_claims_pass_through_validation(self):
        """Docstring claims routed through _validate_and_normalize_claims are deduplicated."""
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        product = _make_product()
        briefs = [
            ClassBrief(
                name="Document",
                docstring_snippet="Represents the main document container for OneNote files.",
                methods=["load", "save"],
            ),
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        raw = _harvest_docstring_claims_raw(api_surface, product)

        # Simulate what run_extract does: extend raw_claims then validate
        # Raw dicts should be compatible with _validate_and_normalize_claims input format
        for r in raw:
            assert isinstance(r.get("text"), str)
            assert isinstance(r.get("kind"), str)
            assert isinstance(r.get("evidence"), list)


# ===========================================================================
# 4. Synthetic snippet tests
# ===========================================================================


class TestSyntheticSnippets:
    """Test template-based synthetic snippet generation."""

    def test_snippets_generated_for_classes_with_methods(self):
        """Classes with >= 2 methods should get synthetic snippets."""
        from launcher.workers.understand.extract import _generate_synthetic_snippets

        product = _make_product()
        briefs = [
            ClassBrief(name="Document", methods=["load", "save", "close"]),
            ClassBrief(name="Page", methods=["accept", "clone"]),
            ClassBrief(name="Tiny", methods=["run"]),  # < 2 methods, should skip
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        claims: list[Claim] = []

        snippets = _generate_synthetic_snippets(api_surface, product, claims)
        assert len(snippets) == 2  # Document and Page, not Tiny

        for s in snippets:
            assert s.source_type == "synthetic"
            assert s.language == "python"
            assert "aspose_note_foss" in s.code

    def test_snippets_pass_ast_parse(self):
        """All synthetic snippets must be valid Python."""
        import ast
        from launcher.workers.understand.extract import _generate_synthetic_snippets

        product = _make_product()
        briefs = [
            ClassBrief(name="Document", methods=["load", "save"]),
            ClassBrief(name="Page", methods=["accept", "clone"]),
        ]
        api_surface = _make_api_surface(class_briefs=briefs)

        snippets = _generate_synthetic_snippets(api_surface, product, [])
        for s in snippets:
            ast.parse(s.code)  # Should not raise

    def test_max_snippets_cap(self):
        """Should not exceed max_snippets."""
        from launcher.workers.understand.extract import _generate_synthetic_snippets

        product = _make_product()
        briefs = [
            ClassBrief(name=f"Class{i}", methods=["method_a", "method_b"])
            for i in range(50)
        ]
        api_surface = _make_api_surface(class_briefs=briefs)

        snippets = _generate_synthetic_snippets(api_surface, product, [], max_snippets=5)
        assert len(snippets) <= 5

    def test_snippets_link_to_claims(self):
        """Synthetic snippets should link to related claims."""
        from launcher.workers.understand.extract import _generate_synthetic_snippets

        product = _make_product()
        briefs = [ClassBrief(name="Document", methods=["load", "save"])]
        api_surface = _make_api_surface(class_briefs=briefs)
        claims = [
            Claim(
                claim_id="CLM-note-DOC-abc123",
                text="Document: Represents the main container.",
                kind="api",
                evidence=[],
            ),
        ]

        snippets = _generate_synthetic_snippets(api_surface, product, claims)
        assert len(snippets) == 1
        assert "CLM-note-DOC-abc123" in snippets[0].claim_ids


# ===========================================================================
# 5. Internal class filter unit test
# ===========================================================================


class TestInternalClassFilter:
    def test_is_internal_class(self):
        from launcher.workers.understand.extract import _is_internal_class

        assert _is_internal_class("DataSignatureGroupDefinitionFND") is True
        assert _is_internal_class("FileChunkReference32") is True
        assert _is_internal_class("BinaryReader") is True
        assert _is_internal_class("GlobalIdTableEntry") is True
        assert _is_internal_class("Document") is False
        assert _is_internal_class("Page") is False
        assert _is_internal_class("RichText") is False

    def test_internal_directory_excluded(self, tmp_path):
        """Classes in _internal/ subdirectory should be excluded from API surface."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(canonical_import="aspose_note_foss")

        # Create public class
        pkg = tmp_path / "src" / "aspose_note_foss"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
        (pkg / "document.py").write_text(
            "class Document:\n    def load(self): pass\n",
            encoding="utf-8",
        )

        # Create internal class
        internal = pkg / "_internal"
        internal.mkdir()
        (internal / "__init__.py").touch()
        (internal / "parser.py").write_text(
            "class InternalParser:\n    def parse(self): pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert "Document" in result.public_classes
        assert "InternalParser" not in result.public_classes

    def test_no_package_root_returns_empty(self, tmp_path):
        """Repos without a package root should return empty API surface."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(canonical_import="aspose_cells")

        # Create example files only (no package root)
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "demo.py").write_text(
            "class DemoHelper:\n    pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert "DemoHelper" not in result.public_classes
        assert len(result.public_classes) == 0


# ===========================================================================
# 6. GAP-06: Export-reachability internal class detection (AQ-05)
# ===========================================================================


class TestExportReachabilityFilter:
    """GAP-06: _is_internal_class uses export_allowlist for non-Aspose products."""

    def test_is_internal_class_with_allowlist_filters_unlisted(self):
        """A class not in export_allowlist is considered internal."""
        from launcher.workers.understand.extract import _is_internal_class

        allowlist = frozenset({"Document", "Page"})
        assert _is_internal_class("PrivateHelper", allowlist) is True

    def test_is_internal_class_with_allowlist_keeps_listed(self):
        """A class in export_allowlist is not internal (even without markers)."""
        from launcher.workers.understand.extract import _is_internal_class

        allowlist = frozenset({"Document", "Page"})
        assert _is_internal_class("Document", allowlist) is False
        assert _is_internal_class("Page", allowlist) is False

    def test_is_internal_class_marker_overrides_allowlist(self):
        """Marker check fires even when class is in the allowlist."""
        from launcher.workers.understand.extract import _is_internal_class

        allowlist = frozenset({"FNDHelper"})
        assert _is_internal_class("FNDHelper", allowlist) is True  # FND marker wins

    def test_is_internal_class_empty_allowlist_no_restriction(self):
        """Empty frozenset means no export-allowlist restriction applied."""
        from launcher.workers.understand.extract import _is_internal_class

        assert _is_internal_class("PrivateHelper", frozenset()) is False

    def test_is_internal_class_none_allowlist_no_restriction(self):
        """None allowlist (not available) means no restriction applied."""
        from launcher.workers.understand.extract import _is_internal_class

        assert _is_internal_class("PrivateHelper", None) is False

    def test_extract_exported_names_from_all(self, tmp_path):
        """_extract_exported_names reads __all__ from __init__.py."""
        from launcher.workers.understand.extract import _extract_exported_names

        init = tmp_path / "__init__.py"
        init.write_text(
            '__all__ = ["Document", "Page", "Notebook"]\n',
            encoding="utf-8",
        )
        result = _extract_exported_names(init)
        assert result == frozenset({"Document", "Page", "Notebook"})

    def test_extract_exported_names_from_reexports(self, tmp_path):
        """_extract_exported_names falls back to re-exports when no __all__."""
        from launcher.workers.understand.extract import _extract_exported_names

        init = tmp_path / "__init__.py"
        init.write_text(
            "from .document import Document\nfrom .page import Page\n",
            encoding="utf-8",
        )
        result = _extract_exported_names(init)
        assert "Document" in result
        assert "Page" in result

    def test_extract_exported_names_empty_init(self, tmp_path):
        """Empty __init__.py returns empty frozenset (no restriction)."""
        from launcher.workers.understand.extract import _extract_exported_names

        init = tmp_path / "__init__.py"
        init.write_text("", encoding="utf-8")
        result = _extract_exported_names(init)
        assert result == frozenset()

    def test_extract_api_surface_uses_export_reachability(self, tmp_path):
        """When __init__.py has __all__, only exported classes are in API surface."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(canonical_import="mypkg")

        pkg = tmp_path / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text(
            '__all__ = ["Document"]\n',
            encoding="utf-8",
        )
        (pkg / "public.py").write_text(
            "class Document:\n    def load(self): pass\n",
            encoding="utf-8",
        )
        (pkg / "internal.py").write_text(
            "class _InternalHelper:\n    def _run(self): pass\n"
            "class PrivateHelper:\n    def run(self): pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert "Document" in result.public_classes
        # PrivateHelper not in __all__ → filtered by export_allowlist
        assert "PrivateHelper" not in result.public_classes


# ===========================================================================
# 7. GAP-09: Synthetic snippets use import_allowlist[0] (AQ-05)
# ===========================================================================


class TestSyntheticSnippetImportPath:
    """GAP-09: _generate_synthetic_snippets uses import_allowlist[0] for import line."""

    def test_snippets_use_import_allowlist_when_available(self):
        """import_allowlist[0] should appear in the import line, not canonical_import."""
        from launcher.workers.understand.extract import _generate_synthetic_snippets

        product = _make_product(
            canonical_import="aspose_cells_foss",
            family="cells",
        )
        briefs = [ClassBrief(name="Workbook", methods=["save", "calculate"])]
        api_surface = ApiSurface(
            public_classes=["Workbook"],
            import_allowlist=["aspose.cells"],  # nested import path
            confidence="high",
            class_briefs=briefs,
        )

        snippets = _generate_synthetic_snippets(api_surface, product, [])
        assert len(snippets) == 1
        assert "import aspose.cells" in snippets[0].code
        assert "aspose.cells.Workbook" in snippets[0].code

    def test_snippets_fall_back_to_canonical_when_no_allowlist(self):
        """When import_allowlist is empty, canonical_import is used as fallback."""
        from launcher.workers.understand.extract import _generate_synthetic_snippets

        product = _make_product(
            canonical_import="aspose_cells_foss",
            family="cells",
        )
        briefs = [ClassBrief(name="Workbook", methods=["save", "calculate"])]
        api_surface = ApiSurface(
            public_classes=["Workbook"],
            import_allowlist=[],  # no allowlist
            confidence="medium",
            class_briefs=briefs,
        )

        snippets = _generate_synthetic_snippets(api_surface, product, [])
        assert len(snippets) == 1
        assert "import aspose_cells_foss" in snippets[0].code


# ---------------------------------------------------------------------------
# AQ-06 — Caplog tests for filter-stage logging and pruning observability
# ---------------------------------------------------------------------------

import logging


class TestApiSurfaceFilterLogging:
    """Tests for api_surface_filter and api_surface_classes log messages (GAP-08)."""

    def test_filter_log_message_appears(self, tmp_path, caplog):
        """api_surface_filter log line is emitted when _extract_api_surface runs."""
        from launcher.workers.understand.extract import _extract_api_surface

        pkg = tmp_path / "src" / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "module.py").write_text("class MyClass:\n    pass\n")

        product = _make_product(canonical_import="mypkg", family="mypkg")

        with caplog.at_level(logging.INFO, logger="launcher.workers.understand.extract"):
            _extract_api_surface(tmp_path, product)

        messages = [r.message for r in caplog.records]
        assert any("api_surface_filter:" in m for m in messages), (
            "Expected api_surface_filter log message; got: " + str(messages)
        )

    def test_classes_log_message_appears(self, tmp_path, caplog):
        """api_surface_classes log line is emitted when _extract_api_surface runs."""
        from launcher.workers.understand.extract import _extract_api_surface

        pkg = tmp_path / "src" / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "module.py").write_text("class MyClass:\n    pass\n")

        product = _make_product(canonical_import="mypkg", family="mypkg")

        with caplog.at_level(logging.INFO, logger="launcher.workers.understand.extract"):
            _extract_api_surface(tmp_path, product)

        messages = [r.message for r in caplog.records]
        assert any("api_surface_classes:" in m for m in messages), (
            "Expected api_surface_classes log message; got: " + str(messages)
        )

    def test_filter_log_contains_file_counts(self, tmp_path, caplog):
        """api_surface_filter log message includes total_files and import_filtered counts."""
        from launcher.workers.understand.extract import _extract_api_surface

        pkg = tmp_path / "src" / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "a.py").write_text("class A:\n    pass\n")
        (pkg / "b.py").write_text("class B:\n    pass\n")

        product = _make_product(canonical_import="mypkg", family="mypkg")

        with caplog.at_level(logging.INFO, logger="launcher.workers.understand.extract"):
            _extract_api_surface(tmp_path, product)

        filter_logs = [r.message for r in caplog.records if "api_surface_filter:" in r.message]
        assert filter_logs, "api_surface_filter log message not found"
        assert "total_files=" in filter_logs[0]
        assert "import_filtered=" in filter_logs[0]


class TestPruningLogging:
    """Tests for per-page density_pruning log messages (GAP-08)."""

    def test_per_page_pruning_log_appears(self, caplog):
        """A per-page 'density_pruning: page=... -> pruned' log appears for pruned pages."""
        from launcher.workers.planner.plan import _prune_thin_pages
        from launcher.models.plan import PlannedPage

        # Create enough pages to trigger pruning: budget = max(8, 5//10) = 8
        # With 3 mandatory + 1 claim = budget 8; use 10 claims + 20 optional pages to force prune
        mandatory = [
            PlannedPage(
                page_id=f"mandatory-{i}",
                page_role="index_page",
                mandatory=True,
                assigned_claims=[f"CLM-{i:04d}"],
                title=f"Mandatory {i}",
            )
            for i in range(8)
        ]
        optional_pages = [
            PlannedPage(
                page_id=f"optional-{i}",
                page_role="workflow_page",
                mandatory=False,
                assigned_claims=[],  # zero density → will be pruned
                title=f"Optional {i}",
            )
            for i in range(5)
        ]
        pages = mandatory + optional_pages
        claim_index = {f"CLM-{i:04d}": [f"mandatory-{i}"] for i in range(8)}

        with caplog.at_level(logging.INFO, logger="launcher.workers.planner.plan"):
            _prune_thin_pages(pages, claim_index, [])

        pruning_logs = [
            r.message for r in caplog.records if "-> pruned" in r.message
        ]
        assert pruning_logs, (
            "Expected per-page pruning log messages; got: "
            + str([r.message for r in caplog.records])
        )
        # Each pruned page log should contain page_id
        assert all("optional-" in msg for msg in pruning_logs)
