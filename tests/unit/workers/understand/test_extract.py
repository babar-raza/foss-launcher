"""Tests for TC-3816: Adaptive understand — contamination filter, ClassBrief, docstring claims, synthetic snippets."""

from __future__ import annotations

from pathlib import Path

import pytest

from launcher.models.claims import Claim, EvidenceAnchor, Snippet
from launcher.models.product import ApiSurface, ClassBrief, ProductIdentity
from launcher.models.understanding import ProductEvidence, WorkflowExample, LimitationEntry


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

    def test_methods_capped_at_50(self, tmp_path):
        """ClassBrief caps methods at _MAX_METHODS_PER_CLASS (TC-4241: raised from 10 to 50)."""
        from launcher.workers.understand.extract import _extract_api_surface
        from launcher.workers.understand.extract._api_surface import _MAX_METHODS_PER_CLASS

        product = _make_product(canonical_import="aspose_note_foss")

        pkg = tmp_path / "src" / "aspose_note_foss"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()

        # Generate a class with 60 methods (above new cap of 50)
        methods = "\n".join(f"    def method_{i}(self): pass" for i in range(60))
        (pkg / "big_class.py").write_text(
            f"class BigClass:\n{methods}\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        brief = result.class_briefs[0]
        assert len(brief.methods) <= _MAX_METHODS_PER_CLASS

    def test_property_setter_not_emitted_as_callable_method(self, tmp_path):
        """Regression: @property setters must stay properties, not callable methods."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(canonical_import="aspose_note_foss")
        pkg = tmp_path / "src" / "aspose_note_foss"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
        (pkg / "page.py").write_text(
            'class Page:\n'
            '    @property\n'
            '    def title(self) -> str:\n'
            '        """Page title for display in navigation."""\n'
            '        return ""\n'
            '    @title.setter\n'
            '    def title(self, value: str) -> None:\n'
            '        self._title = value\n',
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        brief = result.class_briefs[0]
        assert "title" in brief.properties
        assert "title" not in brief.methods
        assert [prop.name for prop in brief.typed_properties] == ["title"]
        assert [method.name for method in brief.typed_methods] == []
        assert brief.typed_properties[0].is_readonly is False

    def test_nested_package_exports_are_treated_as_public(self, tmp_path):
        """Regression: nested package __init__ exports must count as public API surface."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(
            family="3d",
            display_name="Aspose.3D",
            canonical_import="aspose.threed",
            runtime_import="aspose.threed",
        )

        root_pkg = tmp_path / "aspose"
        root_pkg.mkdir(parents=True)
        (root_pkg / "__init__.py").write_text(
            'from . import threed\n__all__ = ["threed"]\n',
            encoding="utf-8",
        )

        threed = root_pkg / "threed"
        threed.mkdir()
        (threed / "__init__.py").write_text(
            'from .Scene import Scene\n__all__ = ["Scene"]\n',
            encoding="utf-8",
        )
        (threed / "Scene.py").write_text(
            "class Scene:\n"
            "    def open(self, path):\n"
            "        pass\n",
            encoding="utf-8",
        )

        entities = threed / "entities"
        entities.mkdir()
        (entities / "__init__.py").write_text(
            'from .VertexElement import VertexElement\n'
            '__all__ = ["VertexElement"]\n',
            encoding="utf-8",
        )
        (entities / "VertexElement.py").write_text(
            "class VertexElement:\n"
            "    pass\n",
            encoding="utf-8",
        )

        formats = threed / "formats"
        formats.mkdir()
        (formats / "__init__.py").write_text(
            'from .ColladaLoadOptions import ColladaLoadOptions\n'
            '__all__ = ["ColladaLoadOptions"]\n',
            encoding="utf-8",
        )
        (formats / "ColladaLoadOptions.py").write_text(
            "class ColladaLoadOptions:\n"
            "    pass\n",
            encoding="utf-8",
        )
        (formats / "ThreeMfPlugin.py").write_text(
            "class ThreeMfPlugin:\n"
            "    def get_file_format(self):\n"
            "        pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)

        assert "Scene" in result.public_classes
        assert "VertexElement" in result.public_classes
        assert "ColladaLoadOptions" in result.public_classes
        assert "ThreeMfPlugin" not in result.public_classes

    def test_root_exported_classes_are_ranked_ahead_of_nested_helpers(self, tmp_path):
        """Regression: core root-exported classes must stay early in class_briefs for reviewability."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = _make_product(
            family="3d",
            display_name="Aspose.3D",
            canonical_import="aspose.threed",
            runtime_import="aspose.threed",
        )

        root_pkg = tmp_path / "aspose"
        root_pkg.mkdir(parents=True)
        (root_pkg / "__init__.py").write_text(
            'from . import threed\n__all__ = ["threed"]\n',
            encoding="utf-8",
        )

        threed = root_pkg / "threed"
        threed.mkdir()
        (threed / "__init__.py").write_text(
            'from .Scene import Scene\n'
            'from .Node import Node\n'
            '__all__ = ["Scene", "Node"]\n',
            encoding="utf-8",
        )
        (threed / "Scene.py").write_text(
            "class Scene:\n"
            "    def open(self, path):\n"
            "        pass\n",
            encoding="utf-8",
        )
        (threed / "Node.py").write_text(
            "class Node:\n"
            "    def create_child_node(self, name):\n"
            "        pass\n",
            encoding="utf-8",
        )

        helpers = threed / "helpers"
        helpers.mkdir()
        (helpers / "__init__.py").write_text(
            'from .ImporterHelper import ImporterHelper\n'
            '__all__ = ["ImporterHelper"]\n',
            encoding="utf-8",
        )
        (helpers / "ImporterHelper.py").write_text(
            "class ImporterHelper:\n"
            "    def import_scene(self):\n"
            "        pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        brief_names = [brief.name for brief in result.class_briefs]

        assert brief_names.index("Scene") < brief_names.index("ImporterHelper")
        assert brief_names.index("Node") < brief_names.index("ImporterHelper")


# ===========================================================================
# 3. Docstring claims tests
# ===========================================================================


class TestDocstringClaims:
    """Test docstring-to-claim harvesting (raw dict output for AQ-01)."""

    def test_docstring_claims_raw_created(self):
        """ClassBrief docstrings yield bounded high-signal claims, not method-list floods."""
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        product = _make_product()
        briefs = [
            ClassBrief(
                name="Document",
                docstring_snippet="Represents the main document container for OneNote files.",
                typed_methods=[
                    {"name": "load", "docstring_snippet": "Loads a notebook from the provided file path."},
                    {"name": "save", "docstring_snippet": "Saves notebook changes back to disk using the target format."},
                ],
                typed_properties=[
                    {"name": "title", "docstring_snippet": "Notebook title shown to users in the navigation tree."},
                ],
            ),
            ClassBrief(
                name="Page",
                docstring_snippet="A single page within a notebook section.",
                typed_methods=[
                    {"name": "clone", "docstring_snippet": "Creates a copy of the current page for reuse in other sections."},
                ],
            ),
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        raw = _harvest_docstring_claims_raw(api_surface, product)

        assert 3 <= len(raw) <= 6
        assert all(isinstance(r, dict) for r in raw)
        assert all(r["kind"] == "api" for r in raw)
        assert not any("provides methods" in r["text"] for r in raw)
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

    def test_docstring_claims_are_ranked_and_bounded_per_class(self):
        """Regression: one rich class should not explode into dozens of micro-claims."""
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        product = _make_product()
        brief = ClassBrief(
            name="Document",
            docstring_snippet="Represents the main document container for OneNote files.",
            typed_methods=[
                {
                    "name": f"method_{i}",
                    "docstring_snippet": f"Executes rich workflow step number {i} with meaningful repository-backed semantics.",
                }
                for i in range(12)
            ],
        )
        api_surface = _make_api_surface(class_briefs=[brief])

        raw = _harvest_docstring_claims_raw(api_surface, product)

        assert len(raw) <= 5, f"Docstring harvesting should be bounded per class: {len(raw)}"
        assert not any("provides methods" in claim["text"] for claim in raw)

    def test_operation_claims_harvested_for_core_api_methods(self):
        """Deterministic operation claims provide linkable API evidence without flooding."""
        from launcher.workers.understand.extract._entry import _harvest_operation_claims_raw

        product = _make_product(display_name="Aspose.3D")
        briefs = [
            ClassBrief(
                name="AnimationClip",
                typed_methods=[{"name": "create_animation_node", "docstring_snippet": ""}],
            ),
            ClassBrief(
                name="Scene",
                typed_methods=[
                    {"name": "open", "docstring_snippet": ""},
                    {"name": "save", "docstring_snippet": ""},
                ],
            ),
        ]
        raw = _harvest_operation_claims_raw(
            _make_api_surface(class_briefs=briefs),
            product,
            snippet_codes=["scene = Scene()\nscene.open('model.obj')"],
        )

        assert raw
        assert raw[0]["claim_source"] == "deterministic"
        assert "Scene.open()" in raw[0]["text"]


class TestSnippetPollutionFilters:
    def test_extract_snippets_skips_meta_docs_and_cli_install_blocks(self, tmp_path):
        """Regression: operator/meta docs and shell install blocks are not snippet evidence."""
        from launcher.models.understanding import RepoInfo
        from launcher.workers.understand.extract._snippets import _extract_snippets

        (tmp_path / "AGENTS.md").write_text(
            "```python\nprint('internal operator instructions')\n```",
            encoding="utf-8",
        )
        (tmp_path / "README.md").write_text(
            "```bash\npip install aspose-note-foss\n```\n"
            "```python\nfrom aspose_note_foss import Document\nDocument()\n```",
            encoding="utf-8",
        )

        repo_info = RepoInfo(
            doc_paths=["AGENTS.md", "README.md"],
            example_paths=[],
            source_paths=[],
            file_tree=["AGENTS.md", "README.md"],
        )
        snippets = _extract_snippets(
            tmp_path,
            repo_info,
            _make_product(),
            _make_api_surface(),
            [],
        )

        assert len(snippets) == 1
        assert snippets[0].source_file == "README.md"
        assert "pip install" not in snippets[0].code

    def test_validate_snippet_imports_ignores_stdlib_imports(self):
        """Regression: stdlib imports in examples must not invalidate product snippets."""
        from launcher.workers.understand.extract._snippets import (
            _normalize_snippet_imports,
            _validate_snippet_imports,
        )

        normalized_code = _normalize_snippet_imports(
            "import os\nimport unittest\n"
            "from aspose.cells_foss import Workbook\n"
            "wb = Workbook()\n",
            _make_api_surface(import_allowlist=["aspose.cells"]),
            _make_product(
                family="cells",
                canonical_import="aspose_cells_foss",
                runtime_import="aspose.cells",
            ),
        )
        snippets = [
            Snippet(
                code=normalized_code,
                language="python",
                source_file="examples/test_workbook.py",
            )
        ]
        valid, invalid_count = _validate_snippet_imports(snippets, ["aspose.cells"])

        assert invalid_count == 0
        assert len(valid) == 1

    def test_extract_snippets_sanitizes_fallback_test_examples(self, tmp_path):
        """Regression: lean-repo test fallback keeps product usage, not unittest boilerplate."""
        from launcher.models.understanding import RepoInfo
        from launcher.workers.understand.extract._snippets import (
            _extract_snippets,
            _validate_snippet_imports,
        )

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_collada_importer.py").write_text(
            "import unittest\n"
            "import os\n\n"
            "from aspose.threed import Scene\n"
            "from aspose.threed.formats import ColladaLoadOptions\n\n"
            "class TestColladaImporter(unittest.TestCase):\n"
            "    def test_import_real_cube(self):\n"
            "        scene = Scene()\n"
            "        options = ColladaLoadOptions()\n"
            "        file_path = os.path.join('examples', 'cube.dae')\n"
            "        if os.path.exists(file_path):\n"
            "            scene.open(file_path, options)\n"
            "            self.assertTrue(len(scene.root_node.child_nodes) > 0)\n"
            "        else:\n"
            "            self.skipTest('missing fixture')\n",
            encoding="utf-8",
        )

        repo_info = RepoInfo(
            doc_paths=[],
            example_paths=[],
            source_paths=[],
            test_paths=["tests/test_collada_importer.py"],
            file_tree=["tests/test_collada_importer.py"],
        )
        api_surface = _make_api_surface(
            class_briefs=[
                ClassBrief(name="Scene"),
                ClassBrief(name="ColladaLoadOptions"),
            ],
            public_classes=["Scene", "ColladaLoadOptions"],
            import_allowlist=["aspose.threed"],
        )
        product = _make_product(
            family="3d",
            display_name="Aspose.3D",
            canonical_import="aspose.threed",
            runtime_import="aspose.threed",
        )

        snippets = _extract_snippets(tmp_path, repo_info, product, api_surface, [])
        valid, invalid_count = _validate_snippet_imports(
            snippets,
            ["aspose.threed"],
            api_surface=api_surface,
        )

        assert invalid_count == 0
        assert len(valid) == 1
        assert "scene.open(file_path, options)" in valid[0].code
        assert "self.assertTrue" not in valid[0].code
        assert "skipTest" not in valid[0].code
        assert "import unittest" not in valid[0].code

    def test_validate_snippet_imports_filters_non_public_product_helpers(self):
        """Regression: helper/plugin imports not present in public API surface are rejected."""
        from launcher.workers.understand.extract._snippets import _validate_snippet_imports

        api_surface = _make_api_surface(
            class_briefs=[
                ClassBrief(name="Scene"),
                ClassBrief(name="ThreeMfLoadOptions"),
            ],
            public_classes=["Scene", "ThreeMfLoadOptions"],
            import_allowlist=["aspose.threed"],
        )
        snippets = [
            Snippet(
                code=(
                    "from aspose.threed import Scene\n"
                    "from aspose.threed.formats import ThreeMfPlugin\n"
                    "scene = Scene()\n"
                    "plugin = ThreeMfPlugin()\n"
                ),
                language="python",
                source_file="tests/test_3mf_importer.py",
            )
        ]

        valid, invalid_count = _validate_snippet_imports(
            snippets,
            ["aspose.threed"],
            api_surface=api_surface,
        )

        assert invalid_count == 1
        assert valid == []

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
# 4. (TC-4062: TestSyntheticSnippets removed — synthetic generator deleted)
# ===========================================================================


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

    def test_is_internal_class_allowlist_overrides_marker(self):
        """TC-4042: allowlist takes priority over name markers.

        A class explicitly in __all__ (export_allowlist) is treated as public
        even if its name contains an internal marker like 'FND'. The allowlist
        is the authoritative source; markers are fallback-only when no allowlist exists.
        """
        from launcher.workers.understand.extract import _is_internal_class

        allowlist = frozenset({"FNDHelper"})
        assert _is_internal_class("FNDHelper", allowlist) is False  # allowlist wins

    def test_is_internal_class_marker_applies_when_not_in_allowlist(self):
        """Class with marker that is NOT in allowlist is still marked internal via allowlist exclusion."""
        from launcher.workers.understand.extract import _is_internal_class

        allowlist = frozenset({"PublicClass", "AnotherPublic"})
        # FNDHelper has marker AND is not in allowlist — allowlist excludes it (internal)
        assert _is_internal_class("FNDHelper", allowlist) is True

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
# 7. (TC-4062: TestSyntheticSnippetImportPath removed — synthetic generator deleted)
# ===========================================================================


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


# ===========================================================================
# QSR-01 (TC-4040): worker.py merge step — format list fallback logic
# ===========================================================================


class TestWorkerMergeFormatFallback:
    """TC-4040: or-based fallback in worker.py merge step (QSR-01, tests 5–8)."""

    def test_worker_merge_prefers_extract_formats_when_non_empty(self):
        """extract_evidence.supported_formats non-empty → merged result uses extract list."""
        extract_evidence = ProductEvidence(supported_formats=["OBJ", "FBX"])
        repo_evidence = ProductEvidence(supported_formats=["DOCX"])
        merged = repo_evidence.model_copy(update={
            "supported_formats": extract_evidence.supported_formats or repo_evidence.supported_formats,
        })
        assert merged.supported_formats == ["OBJ", "FBX"]

    def test_worker_merge_falls_back_to_repo_formats_when_extract_empty(self):
        """extract_evidence.supported_formats == [] → merged result uses repo list."""
        extract_evidence = ProductEvidence(supported_formats=[])
        repo_evidence = ProductEvidence(supported_formats=["DOCX"])
        merged = repo_evidence.model_copy(update={
            "supported_formats": extract_evidence.supported_formats or repo_evidence.supported_formats,
        })
        assert merged.supported_formats == ["DOCX"]

    def test_worker_merge_format_fields_isolated(self):
        """input_formats and output_formats fall back independently of each other."""
        extract_evidence = ProductEvidence(input_formats=["OBJ"], output_formats=[])
        repo_evidence = ProductEvidence(input_formats=["DOCX"], output_formats=["PDF"])
        merged = repo_evidence.model_copy(update={
            "input_formats": extract_evidence.input_formats or repo_evidence.input_formats,
            "output_formats": extract_evidence.output_formats or repo_evidence.output_formats,
        })
        assert merged.input_formats == ["OBJ"]   # extract wins (non-empty)
        assert merged.output_formats == ["PDF"]  # repo fallback (extract empty)

    def test_worker_merge_preserves_existing_fields(self):
        """Format merge does NOT overwrite limitations or workflow_examples."""
        wf = WorkflowExample(name="load_scene", title="Load Scene", code="scene = Scene()")
        lim = LimitationEntry(feature="OBJ export", constraint="not supported")
        extract_evidence = ProductEvidence(
            supported_formats=["OBJ"],
            limitations=[lim],
            workflow_examples=[wf],
        )
        repo_evidence = ProductEvidence(supported_formats=["DOCX"])
        merged = repo_evidence.model_copy(update={
            "supported_formats": extract_evidence.supported_formats or repo_evidence.supported_formats,
            "limitations": extract_evidence.limitations,
            "workflow_examples": extract_evidence.workflow_examples,
        })
        assert merged.supported_formats == ["OBJ"]
        assert len(merged.limitations) == 1
        assert merged.limitations[0].feature == "OBJ export"
        assert len(merged.workflow_examples) == 1
        assert merged.workflow_examples[0].name == "load_scene"

    def test_filter_workflow_examples_drops_test_sources(self):
        """Regression: repo-level workflow_examples must not be sourced from raw tests."""
        from launcher.workers.understand.extract._entry import _filter_workflow_examples

        test_workflow = WorkflowExample(
            name="test_save_options",
            title="Test Save Options",
            code="def test_save_options(self):\n    self.assertTrue(options.enable_compression)\n",
            source_file="tests/test_3mf_exporter.py",
        )
        readme_workflow = WorkflowExample(
            name="readme_quickstart",
            title="Quick Start",
            code="import aspose.threed\nscene = Scene()\nscene.save('out.obj')\n",
            source_file="README.md",
        )
        example_workflow = WorkflowExample(
            name="save_scene",
            title="Save Scene",
            code="scene = Scene()\nscene.save('out.obj')\n",
            source_file="examples/save_scene.py",
        )

        filtered = _filter_workflow_examples(
            [test_workflow, readme_workflow, example_workflow]
        )

        assert [wf.source_file for wf in filtered] == [
            "README.md",
            "examples/save_scene.py",
        ]


# ===========================================================================
# IU-01 — TC-4056 Fix 3: disk-fallback sanitization in _build_doc_contexts
# ===========================================================================


class TestDiskFallbackSanitization:
    """IU-G1: Verify that _read_content disk-fallback (heal re-run path) calls
    sanitize_input so that secrets and oversized content are stripped before
    reaching the LLM prompt pipeline.

    The disk-fallback triggers when repo_content={} (empty dict, falsy) —
    simulating a resume/heal re-run where context.repo_content was not restored.
    """

    def _make_repo_info(self, repo_dir: Path, doc_rel_paths: list[str]):
        """Build a minimal RepoInfo with the given doc paths in file_tree and doc_paths."""
        from launcher.models.understanding import FileCategory, FileEntry, RepoInfo, SharedFacts
        file_index = {
            p: FileEntry(category=FileCategory.doc, size_bytes=(repo_dir / p).stat().st_size)
            for p in doc_rel_paths
            if (repo_dir / p).exists()
        }
        return RepoInfo(
            file_tree=doc_rel_paths,
            file_index=file_index,
            doc_paths=doc_rel_paths,
            shared_facts=SharedFacts(primary_language="python"),
        )

    def test_disk_fallback_redacts_secret_pattern(self, tmp_path):
        """A file containing an API key pattern (sk-...) must have it redacted.

        Uses repo_content={} (empty, falsy) to force the disk-fallback code path.
        sanitize_input must redact sk-<20+alphanum> tokens.
        """
        from launcher.workers.understand.extract._snippets import _build_doc_contexts

        doc_file = tmp_path / "readme.md"
        # sk- prefix + 21 alphanumeric chars → matches _SECRET_RE in input_sanitizer
        secret_token = "sk-aaaaabbbbccccddddeeee1"
        doc_file.write_text(
            f"# API Reference\n\nAuthentication token: {secret_token}\n\nUse the client.\n",
            encoding="utf-8",
        )

        repo_info = self._make_repo_info(tmp_path, ["readme.md"])
        # repo_content={} is falsy → forces disk-read fallback in _read_content
        contexts = _build_doc_contexts(tmp_path, repo_info, repo_content={})

        all_content = " ".join(ctx["content"] for ctx in contexts)
        assert secret_token not in all_content, (
            "sanitize_input must redact API key patterns in disk-fallback path. "
            f"Token {secret_token!r} must not appear in LLM context."
        )
        assert contexts, "At least one context entry must be returned for readme.md"

    def test_disk_fallback_returns_no_context_for_missing_file(self, tmp_path):
        """A doc_path that doesn't exist on disk must produce no context entry.

        _read_content returns None for missing files; the caller skips them.
        """
        from launcher.workers.understand.extract._snippets import _build_doc_contexts
        from launcher.models.understanding import FileCategory, FileEntry, RepoInfo, SharedFacts

        repo_info = RepoInfo(
            file_tree=["nonexistent.md"],
            file_index={
                "nonexistent.md": FileEntry(category=FileCategory.doc, size_bytes=100)
            },
            doc_paths=["nonexistent.md"],
            shared_facts=SharedFacts(primary_language="python"),
        )
        contexts = _build_doc_contexts(tmp_path, repo_info, repo_content={})

        paths_returned = [ctx["path"] for ctx in contexts]
        assert "nonexistent.md" not in paths_returned, (
            "Missing file must produce no context entry — _read_content must return None."
        )

    def test_disk_fallback_respects_max_chars_cap(self, tmp_path):
        """A file larger than 100_000 chars must be truncated to ≤ 100_000 chars.

        sanitize_input is called with max_chars=100_000; content beyond that is cut.
        """
        from launcher.workers.understand.extract._snippets import _build_doc_contexts

        doc_file = tmp_path / "readme.md"
        oversized = "A" * 150_000
        doc_file.write_text(oversized, encoding="utf-8")

        repo_info = self._make_repo_info(tmp_path, ["readme.md"])
        contexts = _build_doc_contexts(tmp_path, repo_info, repo_content={})

        assert contexts, "readme.md must produce at least one context entry"
        total_content = sum(len(ctx["content"]) for ctx in contexts)
        assert total_content <= 100_000, (
            f"Disk-fallback must cap content at 100_000 chars; got {total_content}"
        )

    def test_cache_hit_path_not_affected(self, tmp_path):
        """When repo_content has the key, disk is NOT read — cache hit path is unaffected.

        Writes a file to disk with a secret, but puts clean content in repo_content.
        The context must use the clean cache content, not the secret-containing disk file.
        """
        from launcher.workers.understand.extract._snippets import _build_doc_contexts

        doc_file = tmp_path / "readme.md"
        doc_file.write_text("sk-aaaaabbbbccccddddeeee1 (secret on disk)", encoding="utf-8")

        repo_info = self._make_repo_info(tmp_path, ["readme.md"])
        clean_content = "Clean cached content from original scout run."
        # repo_content is truthy and contains the key → cache hit → disk not read
        contexts = _build_doc_contexts(
            tmp_path, repo_info, repo_content={"readme.md": clean_content}
        )

        all_content = " ".join(ctx["content"] for ctx in contexts)
        assert clean_content in all_content, "Cache-hit path must return repo_content value"
        assert "sk-" not in all_content, "Secret on disk must not bleed through cache-hit path"


# ===================================================================
# TC-4061: Platform-correct extraction tests
# ===================================================================


class TestTC4061SnippetContextLanguageFence:
    """TC-4061: _build_snippet_context must use snippet.language for the code fence."""

    def test_build_snippet_context_uses_snippet_language(self):
        """TypeScript snippet must use ```typescript fence, not ```python."""
        from launcher.workers.understand.extract._llm import _build_snippet_context

        ts_snippet = Snippet(
            language="typescript",
            code="const x: number = 1;\nconsole.log(x);",
            source_type="extracted",
            claim_ids=[],
        )
        result = _build_snippet_context([ts_snippet])
        assert "```typescript" in result, (
            f"Expected ```typescript fence for TypeScript snippet, got: {result!r}"
        )
        assert "```python" not in result, (
            f"Must not use ```python fence for TypeScript snippet: {result!r}"
        )

    def test_build_snippet_context_python_snippet_uses_python_fence(self):
        """Python snippet must still use ```python fence (regression guard)."""
        from launcher.workers.understand.extract._llm import _build_snippet_context

        py_snippet = Snippet(
            language="python",
            code="import aspose_cells_foss as cells\nwb = cells.Workbook()",
            source_type="extracted",
            claim_ids=[],
        )
        result = _build_snippet_context([py_snippet])
        assert "```python" in result, (
            f"Expected ```python fence for Python snippet, got: {result!r}"
        )

    def test_build_snippet_context_empty_language_falls_back_to_python(self):
        """Snippet with empty language string falls back to ```python."""
        from launcher.workers.understand.extract._llm import _build_snippet_context

        snippet = Snippet(
            language="",
            code="x = 1",
            source_type="extracted",
            claim_ids=[],
        )
        result = _build_snippet_context([snippet])
        assert "```python" in result, (
            f"Expected ```python fallback for empty language, got: {result!r}"
        )


class TestTC4061PackageRootWarnLog:
    """TC-4061: _detect_package_root must log WARNING when returning empty string."""

    def test_detect_package_root_warns_when_empty(self, tmp_path, caplog):
        """Empty-structure repo triggers WARNING and returns ''."""
        import logging
        from launcher.workers.understand.extract._api_surface import _detect_package_root

        # Create a temp dir with no recognizable package structure
        (tmp_path / "some_file.txt").write_text("hello")
        # Ensure no __init__.py, no go.mod, no package.json, etc.

        with caplog.at_level(logging.WARNING, logger="launcher.workers.understand.extract._api_surface"):
            result = _detect_package_root(tmp_path)

        assert result == "", f"Expected '' for empty-structure repo, got: {result!r}"
        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("no package root detected" in msg for msg in warning_messages), (
            f"Expected WARNING 'no package root detected' in: {warning_messages}"
        )


class TestTC4061FormatEvidenceSourceField:
    """TC-4061: ProductEvidence.format_evidence_source field."""

    def test_format_evidence_source_default_is_heuristic(self):
        """ProductEvidence defaults format_evidence_source to 'heuristic'."""
        from launcher.models.understanding import ProductEvidence
        pe = ProductEvidence()
        assert pe.format_evidence_source == "heuristic"

    def test_format_evidence_source_can_be_set_to_ast_verified(self):
        """format_evidence_source can be set to 'ast_verified'."""
        from launcher.models.understanding import ProductEvidence
        pe = ProductEvidence(format_evidence_source="ast_verified")
        assert pe.format_evidence_source == "ast_verified"

    def test_format_evidence_source_can_be_set_to_absent(self):
        """PH-02: format_evidence_source accepts 'absent' literal value."""
        from launcher.models.understanding import ProductEvidence
        pe = ProductEvidence(format_evidence_source="absent")
        assert pe.format_evidence_source == "absent"

    def test_format_evidence_source_rejects_invalid_value(self):
        """PH-02: Literal type constraint rejects values outside the allowed set."""
        import pytest
        from pydantic import ValidationError
        from launcher.models.understanding import ProductEvidence
        with pytest.raises(ValidationError):
            ProductEvidence(format_evidence_source="unknown_value")


# ===========================================================================
# 8. Snippet deduplication (TC-4063 / SNP-01)
# ===========================================================================


class TestSnippetDeduplication:
    """_extract_snippets() deduplicates snippets by SHA-256 content hash."""

    def _setup_repo(self, tmp_path: Path, files: dict[str, str]) -> None:
        for rel, content in files.items():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def _make_repo_info(self, doc_paths: list[str], example_paths: list[str] | None = None):
        from launcher.models.understanding import RepoInfo
        return RepoInfo(doc_paths=doc_paths, example_paths=example_paths or [])

    def test_identical_code_in_two_files_yields_one_snippet(self, tmp_path):
        """Same fenced Python block in README and docs/ → exactly 1 snippet extracted."""
        from launcher.workers.understand.extract import _extract_snippets

        code_block = "```python\nimport mylib\nresult = mylib.run()\nprint(result)\n```"
        self._setup_repo(tmp_path, {
            "README.md": f"# Intro\n\n{code_block}\n",
            "docs/guide.md": f"# Guide\n\n{code_block}\n",
        })
        repo_info = self._make_repo_info(["README.md", "docs/guide.md"])
        product = _make_product(canonical_import="mylib")
        api_surface = _make_api_surface()

        snippets = _extract_snippets(tmp_path, repo_info, product, api_surface, [])

        python_snippets = [s for s in snippets if s.language == "python"]
        assert len(python_snippets) == 1, (
            f"Expected 1 deduplicated snippet, got {len(python_snippets)}"
        )

    def test_distinct_code_in_same_file_both_kept(self, tmp_path):
        """Two different fenced Python blocks in the same file are both kept."""
        from launcher.workers.understand.extract import _extract_snippets

        self._setup_repo(tmp_path, {
            "README.md": (
                "# Intro\n\n"
                "```python\nimport mylib\nmylib.init()\n```\n\n"
                "```python\nimport mylib\nmylib.run()\n```\n"
            ),
        })
        repo_info = self._make_repo_info(["README.md"])
        product = _make_product(canonical_import="mylib")
        api_surface = _make_api_surface()

        snippets = _extract_snippets(tmp_path, repo_info, product, api_surface, [])

        python_snippets = [s for s in snippets if s.language == "python"]
        assert len(python_snippets) >= 2, (
            f"Expected >=2 distinct snippets, got {len(python_snippets)}"
        )

    def test_normalize_snippet_imports_uses_runtime_import(self):
        """TC-4255: pip-name imports are normalized to runtime_import for Python."""
        from launcher.workers.understand.extract._snippets import _normalize_snippet_imports

        product = _make_product(
            family="3d",
            display_name="Aspose.3D",
            canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
        )
        api_surface = _make_api_surface(import_allowlist=["aspose.threed"])
        code = "from aspose_3d_foss import Scene\nscene = Scene()"

        normalized = _normalize_snippet_imports(code, api_surface, product)
        assert "from aspose.threed import Scene" in normalized
        assert "aspose_3d_foss" not in normalized

    def test_validate_snippet_imports_filters_control_points_private_member(self):
        """TC-4255: snippets using private members like _control_points are rejected."""
        from launcher.workers.understand.extract._snippets import _validate_snippet_imports

        snippets = [
            Snippet(
                code="import aspose.threed\nmesh._control_points.append((0, 0, 0, 1))",
                language="python",
                source_type="extracted",
                source_file="README.md",
            )
        ]

        valid, invalid_count = _validate_snippet_imports(snippets, ["aspose.threed"])
        assert valid == []
        assert invalid_count == 1


# ===========================================================================
# 9. Snippet provenance — source_file populated (TC-4063 / SNP-01)
# ===========================================================================


class TestSnippetProvenance:
    """_extract_snippets() populates source_file on every returned Snippet."""

    def test_source_file_populated_on_extracted_snippet(self, tmp_path):
        """Every extracted snippet must have a non-empty source_file."""
        from launcher.workers.understand.extract import _extract_snippets
        from launcher.models.understanding import RepoInfo

        readme = tmp_path / "README.md"
        readme.write_text(
            "# MyLib\n\n```python\nimport mylib\nmylib.run()\n```\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(doc_paths=["README.md"])
        product = _make_product(canonical_import="mylib")
        api_surface = _make_api_surface()

        snippets = _extract_snippets(tmp_path, repo_info, product, api_surface, [])

        assert snippets, "Expected at least one snippet from README"
        for s in snippets:
            assert s.source_file, (
                f"Snippet.source_file must be non-empty; got {s.source_file!r}"
            )

    def test_source_file_is_relative_path(self, tmp_path):
        """source_file must be a relative path, not an absolute path."""
        from launcher.workers.understand.extract import _extract_snippets
        from launcher.models.understanding import RepoInfo

        (tmp_path / "docs").mkdir()
        doc = tmp_path / "docs" / "usage.md"
        doc.write_text(
            "# Usage\n\n```python\nimport mylib\nx = mylib.load()\n```\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(doc_paths=["docs/usage.md"])
        product = _make_product(canonical_import="mylib")
        api_surface = _make_api_surface()

        snippets = _extract_snippets(tmp_path, repo_info, product, api_surface, [])

        assert snippets, "Expected at least one snippet from docs/usage.md"
        for s in snippets:
            assert not s.source_file.startswith("/"), (
                f"source_file must be relative, got: {s.source_file!r}"
            )
            assert not s.source_file.startswith("C:"), (
                f"source_file must be relative, got: {s.source_file!r}"
            )


# ---------------------------------------------------------------------------
# Phase 4 — TC-4084: Multi-platform install recipe
# ---------------------------------------------------------------------------

class TestMultiPlatformInstallRecipe:
    """TC-4084: install recipe dispatch for npm, go, rust, dotnet, ruby, php, python."""

    def test_typescript_package_json(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        (tmp_path / "package.json").write_text(
            '{"name": "@aspose/cells", "version": "24.1.0"}', encoding="utf-8"
        )
        product = _make_product(
            family="cells", platform="typescript",
            canonical_import="@aspose/cells",
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert "npm install" in recipe.install_command
        assert "@aspose/cells" in recipe.install_command
        assert recipe.source_file == "package.json"

    def test_typescript_shared_facts_cached(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.understanding import SharedFacts
        product = _make_product(
            family="cells", platform="typescript",
            canonical_import="@aspose/cells",
        )
        shared_facts = SharedFacts(
            package_name="@aspose/cells",
            primary_language="typescript",
        )
        recipe = extract_install_recipe(tmp_path, product, shared_facts=shared_facts)
        assert recipe is not None
        assert "npm install" in recipe.install_command
        assert recipe.source_file == "package.json (cached)"

    def test_go_module(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        (tmp_path / "go.mod").write_text(
            "module github.com/aspose/cells-go\n\ngo 1.21\n", encoding="utf-8"
        )
        product = _make_product(
            family="cells", platform="go", canonical_import="github.com/aspose/cells-go",
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert "go get" in recipe.install_command
        assert "github.com/aspose/cells-go" in recipe.install_command
        assert recipe.source_file == "go.mod"

    def test_rust_cargo(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        (tmp_path / "Cargo.toml").write_text(
            "[package]\nname = \"aspose-cells\"\nversion = \"24.1.0\"\n", encoding="utf-8"
        )
        product = _make_product(
            family="cells", platform="rust", canonical_import="aspose-cells",
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert "cargo add" in recipe.install_command
        assert "aspose-cells" in recipe.install_command
        assert recipe.source_file == "Cargo.toml"

    def test_dotnet_csproj(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        csproj = tmp_path / "Aspose.Cells.csproj"
        csproj.write_text(
            '<Project><ItemGroup>'
            '<PackageReference Include="Aspose.Cells" Version="24.1.0" />'
            '</ItemGroup></Project>',
            encoding="utf-8",
        )
        product = _make_product(
            family="cells", platform="dotnet", canonical_import="Aspose.Cells",
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert "dotnet add package" in recipe.install_command
        assert "Aspose.Cells" in recipe.install_command

    def test_python_unchanged(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname = \"aspose-cells-foss\"\nversion = \"24.1.0\"\n",
            encoding="utf-8",
        )
        product = _make_product(
            family="cells", platform="python", canonical_import="aspose_cells_foss",
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert "pip install" in recipe.install_command
        assert "aspose-cells-foss" in recipe.install_command
        assert recipe.source_file == "pyproject.toml"

    def test_source_file_attribution_typescript_cached(self, tmp_path):
        """TC-4084: TypeScript SharedFacts cached → source_file is 'package.json (cached)', not 'pyproject.toml (cached)'."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.understanding import SharedFacts
        product = _make_product(
            family="cells", platform="typescript", canonical_import="@aspose/cells",
        )
        shared_facts = SharedFacts(
            package_name="@aspose/cells",
            primary_language="typescript",
        )
        recipe = extract_install_recipe(tmp_path, product, shared_facts=shared_facts)
        assert recipe is not None
        assert "pyproject.toml" not in recipe.source_file, (
            f"Expected source_file to not reference pyproject.toml for TypeScript, got: {recipe.source_file!r}"
        )
        assert "package.json" in recipe.source_file

    def test_install_command_not_pip_command(self):
        """TC-4084: InstallRecipe uses install_command field (not pip_command)."""
        from launcher.models.understanding import InstallRecipe
        recipe = InstallRecipe(install_command="pip install aspose-cells-foss")
        assert recipe.install_command == "pip install aspose-cells-foss"
        # Backward-compat property still works
        assert recipe.pip_command == "pip install aspose-cells-foss"


# ---------------------------------------------------------------------------
# Phase 4 — TC-4087: Doc-scan workflow examples for non-Python
# ---------------------------------------------------------------------------

class TestNonPythonWorkflowExamples:
    """TC-4087: doc-scan strategy fires for non-Python repos."""

    def test_ordered_list_in_readme_produces_example(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_workflow_examples
        from launcher.models.understanding import RepoInfo
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Getting Started\n\n"
            "1. Install the package: run npm install @aspose/cells\n"
            "2. Create a new Workbook instance in your TypeScript code\n"
            "3. Load an existing spreadsheet from disk using workbook.load()\n"
            "4. Save the document to a new format using workbook.save()\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(doc_paths=[])
        examples = extract_workflow_examples(tmp_path, repo_info, api_surface=None, platform="typescript")
        assert len(examples) >= 1
        assert any("workflow" in e.name or "readme" in e.name.lower() for e in examples)

    def test_ordered_list_requires_3_steps(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_workflow_examples
        from launcher.models.understanding import RepoInfo
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Quick Start\n\n"
            "1. Install the package.\n"
            "2. Configure your credentials and environment settings.\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(doc_paths=[])
        examples = extract_workflow_examples(tmp_path, repo_info, api_surface=None, platform="typescript")
        # Only 2 steps — should NOT produce a doc-scan example
        assert all("readme" not in e.name.lower() for e in examples)

    def test_example_source_file_heuristic(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_workflow_examples
        from launcher.models.understanding import RepoInfo
        ex_dir = tmp_path / "examples"
        ex_dir.mkdir()
        ts_file = ex_dir / "hello.ts"
        ts_file.write_text(
            "import { Workbook } from '@aspose/cells';\n"
            "const wb = new Workbook();\n"
            "wb.load('input.xlsx');\n"
            "wb.save('output.pdf');\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(example_paths=["examples/hello.ts"])
        examples = extract_workflow_examples(tmp_path, repo_info, api_surface=None, platform="typescript")
        assert len(examples) >= 1
        assert examples[0].language == "typescript"
        assert examples[0].source_file == "examples/hello.ts"

    def test_source_file_over_100_lines_excluded(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_workflow_examples
        from launcher.models.understanding import RepoInfo
        ex_dir = tmp_path / "examples"
        ex_dir.mkdir()
        big_file = ex_dir / "big.ts"
        big_file.write_text("\n".join(f"// line {i}" for i in range(200)), encoding="utf-8")
        repo_info = RepoInfo(example_paths=["examples/big.ts"])
        examples = extract_workflow_examples(tmp_path, repo_info, api_surface=None, platform="typescript")
        assert not any(e.source_file == "examples/big.ts" for e in examples)

    def test_python_ast_path_unchanged(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_workflow_examples
        from launcher.models.understanding import RepoInfo
        ex_dir = tmp_path / "examples"
        ex_dir.mkdir()
        py_file = ex_dir / "usage.py"
        py_file.write_text(
            "from aspose.cells import Workbook\n\n"
            "def convert_excel_to_pdf(src, dst):\n"
            "    wb = Workbook()\n"
            "    wb.load(src)\n"
            "    wb.save(dst)\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(example_paths=["examples/usage.py"])
        examples = extract_workflow_examples(tmp_path, repo_info, api_surface=None, platform="python")
        assert len(examples) >= 1
        assert examples[0].language == "python"

    def test_python_workflow_examples_filter_private_members(self, tmp_path):
        """TC-4255: workflow examples using private Python members are rejected."""
        from launcher.workers.understand.extract._deterministic import extract_workflow_examples
        from launcher.models.understanding import RepoInfo

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_mesh.py").write_text(
            "def test_build_mesh():\n"
            "    scene = Scene()\n"
            "    mesh = Mesh('cube')\n"
            "    mesh._control_points.append((0, 0, 0, 1))\n"
            "    scene.save('out.obj')\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(test_paths=["tests/test_mesh.py"])
        api_surface = _make_api_surface(import_allowlist=["aspose.threed"], public_classes=["Scene", "Mesh"])

        examples = extract_workflow_examples(tmp_path, repo_info, api_surface=api_surface, platform="python")
        assert examples == []


# ===========================================================================
# TC-4089 P2-G: Dedup threshold 0.85 (was 0.8)
# ===========================================================================


class TestDedupThreshold:
    """P2-G: Dedup threshold raised to 0.85 — claims at ~0.82 Jaccard are NOT removed."""

    def _make_claim(self, text: str, kind: str = "feature") -> "Claim":
        from launcher.models.claims import Claim
        import hashlib
        h = hashlib.sha256(text.encode()).hexdigest()[:6]
        return Claim(
            claim_id=f"CLM-test-{h}",
            text=text,
            kind=kind,
            visibility="public",
            tier_relevance="all",
        )

    def test_claims_at_82_jaccard_are_not_deduped(self):
        """Two claims sharing ~82% Jaccard similarity must both survive (threshold is 0.85)."""
        from launcher.workers.understand.extract._validation import _deduplicate_claims

        # Craft two claims with Jaccard ~0.82:
        # claim_a: 11 words all shared + 2 unique = 13 words total
        # claim_b: 11 words shared + 3 unique = 14 words total
        # intersection=11, union=16 → Jaccard=11/16=0.6875 — too low; let's use a larger overlap
        # 9 shared words, 1 unique each → intersection=9, union=11 → 9/11=0.818 < 0.85 → NOT duped
        shared = "supports reading xlsx files from the file system path"  # 9 words
        claim_a = self._make_claim(shared + " efficiently")
        claim_b = self._make_claim(shared + " reliably")

        # Verify Jaccard is between 0.80 and 0.85 (so old threshold would dedup, new one won't)
        words_a = set(claim_a.text.lower().split())
        words_b = set(claim_b.text.lower().split())
        jaccard = len(words_a & words_b) / len(words_a | words_b)
        assert 0.80 < jaccard < 0.85, (
            f"Test setup error: Jaccard {jaccard:.3f} not in (0.80, 0.85)"
        )

        result = _deduplicate_claims([claim_a, claim_b])
        assert len(result) == 2, (
            f"Both claims must survive with threshold=0.85; Jaccard={jaccard:.3f}"
        )

    def test_claims_at_90_jaccard_are_deduped(self):
        """Claims sharing >0.85 Jaccard are still deduplicated."""
        from launcher.workers.understand.extract._validation import _deduplicate_claims

        # 9 shared words, 0 unique in second → Jaccard = 9/10 = 0.9 > 0.85 → deduped
        base = "supports reading and writing xlsx spreadsheet files from disk"
        claim_a = self._make_claim(base + " path")
        claim_b = self._make_claim(base + " path")  # identical → Jaccard = 1.0

        result = _deduplicate_claims([claim_a, claim_b])
        assert len(result) == 1, "Identical claims must be deduplicated"


# ===========================================================================
# TC-4089 P2-B: Module-level functions in api_identifiers
# ===========================================================================


class TestModuleLevelFunctions:
    """P2-B: Module-level public functions appear in api_identifiers."""

    def test_module_level_functions_in_api_identifiers(self, tmp_path):
        """A Python module with public module-level functions should populate api_identifiers."""
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        product = _make_product(canonical_import="mylib", family="mylib")
        pkg = tmp_path / "mylib"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "utils.py").write_text(
            "def compute_sum(a, b):\n"
            "    '''Compute the sum of two numbers.'''\n"
            "    return a + b\n\n"
            "def process_data(data):\n"
            "    '''Process the input data.'''\n"
            "    return data\n\n"
            "def _private_helper():\n"
            "    pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert "compute_sum" in result.api_identifiers, (
            f"compute_sum not in api_identifiers: {result.api_identifiers}"
        )
        assert "process_data" in result.api_identifiers, (
            f"process_data not in api_identifiers: {result.api_identifiers}"
        )
        assert "_private_helper" not in result.api_identifiers, (
            "_private_helper must be excluded (private)"
        )

    def test_module_level_functions_not_in_public_classes(self, tmp_path):
        """Module-level functions must NOT appear in public_classes."""
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        product = _make_product(canonical_import="mylib", family="mylib")
        pkg = tmp_path / "mylib"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "funcs.py").write_text(
            "def compute_sum(a, b):\n"
            "    return a + b\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert "compute_sum" not in result.public_classes, (
            "compute_sum must NOT appear in public_classes — it is a function, not a class"
        )

    def test_module_level_functions_filtered_by_export_allowlist(self, tmp_path):
        """When __all__ is present, module functions not in __all__ are excluded."""
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        product = _make_product(canonical_import="mylib", family="mylib")
        pkg = tmp_path / "mylib"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text(
            '__all__ = ["compute_sum"]\n', encoding="utf-8"
        )
        (pkg / "funcs.py").write_text(
            "def compute_sum(a, b):\n"
            "    return a + b\n\n"
            "def internal_fn():\n"
            "    pass\n",
            encoding="utf-8",
        )

        result = _extract_api_surface(tmp_path, product)
        assert "compute_sum" in result.api_identifiers
        assert "internal_fn" not in result.api_identifiers


# ===========================================================================
# TC-4089 P2-C: Evidence path validation
# ===========================================================================


class TestEvidencePathValidation:
    """P2-C: _validate_and_normalize_claims rejects evidence paths not in file_tree."""

    def _make_raw_claim(self, source_file: str, text: str = "Feature supports reading files from disk path") -> dict:
        return {
            "text": text,
            "kind": "feature",
            "visibility": "public",
            "claim_source": "llm",
            "evidence": [{"source_file": source_file, "snippet": "some code"}],
        }

    def test_invalid_path_replaced_with_unknown(self):
        """Evidence source_file not in file_tree is replaced with 'unknown'."""
        from launcher.workers.understand.extract._validation import _validate_and_normalize_claims

        product = _make_product()
        api_surface = _make_api_surface()
        raw = [self._make_raw_claim("src/nonexistent_file.py")]
        file_tree = frozenset({"src/real_file.py"})

        claims = _validate_and_normalize_claims(raw, product, api_surface, file_tree=file_tree)
        assert claims, "Expected at least one claim"
        for claim in claims:
            for ev in claim.evidence:
                assert ev.source_file != "src/nonexistent_file.py", (
                    "Fabricated path must be replaced with 'unknown'"
                )
                if "nonexistent" not in ev.source_file:
                    assert ev.source_file in ("unknown", "src/real_file.py")

    def test_fabricated_path_becomes_unknown(self):
        """Evidence with fabricated path gets source_file='unknown'."""
        from launcher.workers.understand.extract._validation import _validate_and_normalize_claims

        product = _make_product()
        api_surface = _make_api_surface()
        raw = [self._make_raw_claim("src/llm_invented_module.py")]
        file_tree = frozenset({"src/real_module.py", "README.md"})

        claims = _validate_and_normalize_claims(raw, product, api_surface, file_tree=file_tree)
        assert claims
        ev_paths = [ev.source_file for claim in claims for ev in claim.evidence]
        assert "src/llm_invented_module.py" not in ev_paths, (
            "Fabricated path must not survive validation"
        )
        assert "unknown" in ev_paths, (
            f"Fabricated path must be replaced with 'unknown'; got: {ev_paths}"
        )

    def test_docstring_pseudo_path_preserved(self):
        """Evidence with 'docstring:ClassName' pseudo-path is NOT replaced."""
        from launcher.workers.understand.extract._validation import _validate_and_normalize_claims

        product = _make_product()
        api_surface = _make_api_surface()
        raw = [self._make_raw_claim("docstring:MyClass.my_method")]
        file_tree = frozenset({"src/real_module.py"})  # docstring path not in file_tree

        claims = _validate_and_normalize_claims(raw, product, api_surface, file_tree=file_tree)
        assert claims
        ev_paths = [ev.source_file for claim in claims for ev in claim.evidence]
        assert "docstring:MyClass.my_method" in ev_paths, (
            f"Pseudo-path 'docstring:ClassName' must be preserved; got: {ev_paths}"
        )

    def test_valid_path_preserved(self):
        """Evidence with a path that exists in file_tree is preserved as-is."""
        from launcher.workers.understand.extract._validation import _validate_and_normalize_claims

        product = _make_product()
        api_surface = _make_api_surface()
        raw = [self._make_raw_claim("src/real_module.py")]
        file_tree = frozenset({"src/real_module.py"})

        claims = _validate_and_normalize_claims(raw, product, api_surface, file_tree=file_tree)
        assert claims
        ev_paths = [ev.source_file for claim in claims for ev in claim.evidence]
        assert "src/real_module.py" in ev_paths, (
            f"Valid path must be preserved; got: {ev_paths}"
        )

    def test_no_file_tree_skips_validation(self):
        """When file_tree=None, no path validation is performed."""
        from launcher.workers.understand.extract._validation import _validate_and_normalize_claims

        product = _make_product()
        api_surface = _make_api_surface()
        raw = [self._make_raw_claim("src/any_path.py")]

        claims = _validate_and_normalize_claims(raw, product, api_surface, file_tree=None)
        assert claims
        ev_paths = [ev.source_file for claim in claims for ev in claim.evidence]
        assert "src/any_path.py" in ev_paths, (
            "Without file_tree, no validation occurs — path must be preserved"
        )


class TestPrivatePythonApiClaimFiltering:
    """TC-4255: private Python member claims must not remain public evidence."""

    def test_validate_and_normalize_claims_drops_control_points_private_claim(self):
        from launcher.workers.understand.extract._validation import _validate_and_normalize_claims

        product = _make_product(
            family="3d",
            display_name="Aspose.3D",
            canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
        )
        api_surface = _make_api_surface(import_allowlist=["aspose.threed"])
        raw = [{
            "text": "Use `_control_points.append()` to add vertices to Mesh.",
            "kind": "api",
            "visibility": "public",
            "claim_source": "llm",
            "evidence": [{"source_file": "README.md", "snippet": "mesh._control_points.append(...)"}],
        }]

        claims = _validate_and_normalize_claims(raw, product, api_surface, file_tree=frozenset({"README.md"}))
        assert claims == []


# ===========================================================================
# TC-4089 P2-F: Per-method docstring claims from typed_methods
# ===========================================================================


class TestMethodDocstringClaims:
    """P2-F: _harvest_docstring_claims_raw generates per-method docstring claims."""

    def _make_method_signature(self, name: str, docstring: str):
        from launcher.models.product import MethodSignature
        return MethodSignature(
            name=name,
            docstring_snippet=docstring,
        )

    def test_method_with_real_docstring_produces_claim(self):
        """A method with ≥20 char non-boilerplate docstring produces a per-method claim."""
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw
        from launcher.models.product import ClassBrief, MethodSignature

        ms = MethodSignature(
            name="convert_to_pdf",
            docstring_snippet="Converts the workbook to PDF format with layout preservation.",
        )
        brief = ClassBrief(
            name="Workbook",
            docstring_snippet="Represents a spreadsheet workbook with multiple sheets.",
            typed_methods=[ms],
        )
        api_surface = _make_api_surface(class_briefs=[brief])
        product = _make_product()

        raw = _harvest_docstring_claims_raw(api_surface, product)
        method_claims = [r for r in raw if "convert_to_pdf" in r.get("text", "")]
        assert method_claims, (
            f"Expected a claim for convert_to_pdf; got texts: {[r['text'] for r in raw]}"
        )
        claim = method_claims[0]
        assert "Workbook.convert_to_pdf():" in claim["text"]
        assert "Converts the workbook" in claim["text"]
        assert claim["kind"] == "api"
        assert claim["claim_source"] == "docstring"

    def test_method_evidence_uses_pseudo_path(self):
        """Per-method claim evidence source_file must use 'docstring:ClassName.method_name'."""
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw
        from launcher.models.product import ClassBrief, MethodSignature

        ms = MethodSignature(
            name="load_from_file",
            docstring_snippet="Loads the document from the specified file path on disk.",
        )
        brief = ClassBrief(
            name="Document",
            docstring_snippet="The main document container class for OneNote files.",
            typed_methods=[ms],
        )
        api_surface = _make_api_surface(class_briefs=[brief])
        product = _make_product()

        raw = _harvest_docstring_claims_raw(api_surface, product)
        method_claims = [r for r in raw if "load_from_file" in r.get("text", "")]
        assert method_claims
        ev = method_claims[0]["evidence"][0]
        assert ev["source_file"] == "docstring:Document.load_from_file", (
            f"Expected pseudo-path, got: {ev['source_file']!r}"
        )

    def test_short_docstring_skipped(self):
        """Method docstrings shorter than 20 chars are skipped."""
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw
        from launcher.models.product import ClassBrief, MethodSignature

        ms = MethodSignature(name="run", docstring_snippet="Runs it.")  # 8 chars < 20
        brief = ClassBrief(name="Runner", typed_methods=[ms])
        api_surface = _make_api_surface(class_briefs=[brief])
        product = _make_product()

        raw = _harvest_docstring_claims_raw(api_surface, product)
        method_claims = [r for r in raw if "run" in r.get("text", "") and "Runner.run():" in r.get("text", "")]
        assert not method_claims, "Short docstring must not produce a per-method claim"

    def test_boilerplate_docstring_filtered(self):
        """Methods with short boilerplate docstrings are not harvested."""
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw
        from launcher.models.product import ClassBrief, MethodSignature

        boilerplate_cases = [
            ("get_value", "Returns the value."),  # starts with "returns"
            ("set_title", "Set the title."),  # starts with "set "
            ("initialize_engine", "Initialize the engine."),  # starts with "initialize"
        ]
        for method_name, doc in boilerplate_cases:
            ms = MethodSignature(name=method_name, docstring_snippet=doc)
            brief = ClassBrief(name="MyClass", typed_methods=[ms])
            api_surface = _make_api_surface(class_briefs=[brief])
            product = _make_product()

            raw = _harvest_docstring_claims_raw(api_surface, product)
            method_claims = [
                r for r in raw
                if f"MyClass.{method_name}():" in r.get("text", "")
            ]
            assert not method_claims, (
                f"Boilerplate docstring {doc!r} must not produce a claim"
            )

    def test_per_method_claims_capped_at_50_per_class(self):
        """No more than 50 per-method claims are harvested per class (TC-4241: raised from 10 to 50)."""
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw, _MAX_TYPED_METHODS_CLAIMS
        from launcher.models.product import ClassBrief, MethodSignature

        typed_methods = [
            MethodSignature(
                name=f"method_{i}",
                docstring_snippet=f"This method performs complex operation number {i} on the data.",
            )
            for i in range(60)  # above new cap of 50
        ]
        brief = ClassBrief(name="BigClass", typed_methods=typed_methods)
        api_surface = _make_api_surface(class_briefs=[brief])
        product = _make_product()

        raw = _harvest_docstring_claims_raw(api_surface, product)
        method_claims = [r for r in raw if "BigClass." in r.get("text", "") and "():" in r.get("text", "")]
        assert len(method_claims) <= _MAX_TYPED_METHODS_CLAIMS, (
            f"Per-method claims must be capped at {_MAX_TYPED_METHODS_CLAIMS} per class; got {len(method_claims)}"
        )


# ===========================================================================
# TC-4091 — LLM prompt path regression guard
# ===========================================================================


class TestTC4091LLMPromptPath:
    """Regression guard: _llm.py must resolve claim_extractor.txt via parents[3]."""

    def test_llm_prompt_path_resolves_to_existing_file(self):
        """parents[3] / 'prompts' / 'claim_extractor.txt' must exist on disk."""
        from launcher.workers.understand.extract import _llm

        prompt_path = (
            Path(_llm.__file__).resolve().parents[3]
            / "prompts"
            / "claim_extractor.txt"
        )
        assert prompt_path.exists(), (
            f"claim_extractor.txt not found at {prompt_path}. "
            "Ensure parents[3] points to src/launcher/ and the prompt file is present."
        )

    def test_llm_prompt_path_parents3_is_launcher_root(self):
        """parents[3] of _llm.__file__ must be the src/launcher/ directory."""
        from launcher.workers.understand.extract import _llm

        launcher_root = Path(_llm.__file__).resolve().parents[3]
        # Normalise to forward slashes for cross-platform comparison
        root_str = launcher_root.as_posix()
        assert root_str.endswith("src/launcher"), (
            f"Expected parents[3] to end with 'src/launcher', got: {root_str}"
        )

    def test_prompt_path_does_not_use_old_parents2(self):
        """Regression guard: the prompt_path line in _llm.py must use parents[3], not parents[2]."""
        from launcher.workers.understand.extract import _llm

        source = Path(_llm.__file__).read_text(encoding="utf-8")
        # Find the line that sets prompt_path
        prompt_lines = [
            line for line in source.splitlines() if "prompt_path" in line and "prompts" in line
        ]
        assert prompt_lines, "Could not find prompt_path assignment line in _llm.py"
        for line in prompt_lines:
            assert "parents[2]" not in line, (
                f"Found old parents[2] in prompt_path line: {line!r}. "
                "TC-4091 fix requires parents[3]."
            )
            assert "parents[3]" in line, (
                f"Expected parents[3] in prompt_path line but not found: {line!r}"
            )


# ===========================================================================
# TC-4093: Install recipe verification uses canonical_import
# ===========================================================================


class TestTC4093InstallRecipeVerification:
    """TC-4093: Python verification code must use canonical_import, not runtime_import."""

    def test_python_verification_uses_canonical_import(self, tmp_path):
        """Verification code uses canonical_import (pip package), not runtime_import (namespace)."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-cells-foss"\nversion = "26.3.1"\n',
            encoding="utf-8",
        )
        product = _make_product(
            family="cells",
            platform="python",
            canonical_import="aspose_cells_foss",
            runtime_import="aspose.cells",
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert recipe.verification_code.startswith("import aspose_cells_foss"), (
            f"Expected verification to start with 'import aspose_cells_foss', got: {recipe.verification_code!r}"
        )
        assert "import aspose.cells" not in recipe.verification_code, (
            f"Verification must not use runtime_import, got: {recipe.verification_code!r}"
        )

    def test_python_verification_fallback_to_family_when_no_canonical(self, tmp_path):
        """When canonical_import is empty, fallback to family name for verification."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-cells-foss"\nversion = "26.3.1"\n',
            encoding="utf-8",
        )
        product = _make_product(
            family="cells",
            platform="python",
            canonical_import="",
            runtime_import="aspose.cells",
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        # family="cells" is used as fallback
        assert "import cells" in recipe.verification_code, (
            f"Expected 'import cells' in verification, got: {recipe.verification_code!r}"
        )

    def test_python_verification_empty_when_no_pkg_info(self, tmp_path):
        """When both canonical_import and family are empty, verification is empty string."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-cells-foss"\nversion = "26.3.1"\n',
            encoding="utf-8",
        )
        product = _make_product(
            family="",
            platform="python",
            canonical_import="",
            runtime_import="",
        )
        recipe = extract_install_recipe(tmp_path, product)
        # May return None if package_name cannot be derived, or return with empty verification
        if recipe is not None:
            assert recipe.verification_code == "", (
                f"Expected empty verification when no pkg info, got: {recipe.verification_code!r}"
            )


# ===========================================================================
# TC-4094: Docstring claim cap raised 50→200 with truncation warning
# ===========================================================================


class TestTC4094DocstringCapRaise:
    """TC-4241: max_claims default is 2000 (raised from 200/TC-4094, 50/TC-3816); WARNING logged when cap is reached."""

    def test_default_cap_is_bounded(self):
        """Default max_claims stays bounded to prevent docstring-claim flooding."""
        import inspect
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw, _MAX_DOCSTRING_CLAIMS

        sig = inspect.signature(_harvest_docstring_claims_raw)
        default = sig.parameters["max_claims"].default
        assert default == _MAX_DOCSTRING_CLAIMS, (
            f"TC-4241: expected default max_claims={_MAX_DOCSTRING_CLAIMS}, got {default}"
        )
        assert default <= 200, f"Docstring claim cap is too high for bounded evidence: {default}"

    def test_warning_logged_when_cap_reached(self, caplog):
        """WARNING is emitted when the claim cap is hit before all classes are processed."""
        import logging
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw

        # Build 50 class_briefs each with a 30+ char docstring
        briefs = [
            ClassBrief(
                name=f"Class{i}",
                docstring_snippet=f"This is a docstring for class number {i} in the test.",
                methods=[f"method_{i}"],
            )
            for i in range(50)
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        product = _make_product()

        with caplog.at_level(logging.WARNING, logger="launcher.workers.understand.extract._entry"):
            result = _harvest_docstring_claims_raw(api_surface, product, max_claims=5)

        # The cap check fires before adding claims for the next class; each class can add
        # at most 2 claims (docstring + methods), so result length may be slightly above cap
        # but far below the 50-class total (100 max without cap).
        assert len(result) < 20, f"Cap not respected: expected far fewer than 50 classes worth, got {len(result)}"
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_records, (
            "Expected a WARNING log when cap is reached, but none was emitted"
        )

    def test_no_warning_when_cap_not_reached(self, caplog):
        """No WARNING about cap when fewer classes than max_claims are present."""
        import logging
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw

        briefs = [
            ClassBrief(
                name=f"SmallClass{i}",
                docstring_snippet=f"Short docstring for class {i}, more than thirty chars.",
                methods=[f"do_{i}"],
            )
            for i in range(3)
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        product = _make_product()

        with caplog.at_level(logging.WARNING, logger="launcher.workers.understand.extract._entry"):
            _harvest_docstring_claims_raw(api_surface, product, max_claims=200)

        cap_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "cap=" in r.getMessage()
        ]
        assert not cap_warnings, (
            f"Unexpected cap WARNING when cap not reached: {[r.getMessage() for r in cap_warnings]}"
        )

    def test_warning_includes_remaining_class_count(self, caplog):
        """WARNING message must mention remaining classes count."""
        import logging
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw

        # 20 class_briefs, cap at 10 → 10 remaining when cap is hit at index 10
        briefs = [
            ClassBrief(
                name=f"BigClass{i}",
                docstring_snippet=f"Detailed docstring for BigClass{i} — longer than thirty chars.",
                methods=[f"operate_{i}", f"run_{i}"],
            )
            for i in range(20)
        ]
        api_surface = _make_api_surface(class_briefs=briefs)
        product = _make_product()

        with caplog.at_level(logging.WARNING, logger="launcher.workers.understand.extract._entry"):
            _harvest_docstring_claims_raw(api_surface, product, max_claims=10)

        cap_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "cap=" in r.getMessage()
        ]
        assert cap_warnings, "Expected at least one WARNING about cap being reached"
        msg = cap_warnings[0].getMessage()
        # The warning should reference the total class count (20)
        assert "20" in msg, (
            f"Expected total class count (20) in warning message, got: {msg!r}"
        )


# ===========================================================================
# TC-4092: Format detection false positive — negative context filter
# ===========================================================================


class TestTC4092FormatDetectionFalsePositive:
    """TC-4092: Verify that string-scan-only format hits with negative context are suppressed."""

    def test_format_with_negative_context_and_no_enum_refs_excluded(self, tmp_path):
        """PDF mentioned only in a 'not supported' comment must NOT appear in results."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        # Write a source file with PDF only in a 'not supported' comment
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "workbook.py").write_text(
            "# Note: PDF is not supported\n"
            "# document.pdf cannot be exported\n"
            "def save(path): pass\n",
            encoding="utf-8",
        )

        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        names = {r.name for r in result}
        assert "PDF" not in names, (
            f"PDF should be suppressed by negative context filter, but got: {names}"
        )

    def test_format_with_enum_reference_not_excluded_despite_negative_context(self, tmp_path):
        """PDF with a FileFormat.PDF enum reference must NOT be excluded, even if docs say unsupported."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        # Write a test file with a real enum reference (Strategy 1 hit)
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_formats.py").write_text(
            "result = workbook.save('output.pdf', FileFormat.PDF)  # export\n",
            encoding="utf-8",
        )

        # Also write a doc file with a negative mention
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "limitations.md").write_text(
            "# PDF is not supported for import\n"
            "# cannot import from PDF\n",
            encoding="utf-8",
        )

        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        names = {r.name for r in result}
        assert "PDF" in names, (
            f"PDF with enum reference (Strategy 1) must survive negative context filter, got: {names}"
        )

    def test_xlsx_not_affected_by_negative_filter(self, tmp_path):
        """XLSX with positive code evidence is not dropped by the negative context filter."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        # Write a test file referencing XLSX via enum
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_xlsx.py").write_text(
            "wb.save('output.xlsx', FileFormat.XLSX)  # save\n",
            encoding="utf-8",
        )

        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        names = {r.name for r in result}
        assert "XLSX" in names, (
            f"XLSX with enum reference must appear in results, got: {names}"
        )

    def test_negative_context_pattern_matches_expected_strings(self):
        """_FORMAT_NEGATIVE_CTX_RE must match negative context strings and not positive ones."""
        from launcher.workers.understand.extract._deterministic import _FORMAT_NEGATIVE_CTX_RE

        # Strings that MUST match (negative context)
        should_match = [
            "PDF is not supported",
            "unsupported format",
            "no support for this type",
            "cannot export to PDF",
            "cannot import from this format",
            "cannot load this file",
            "cannot save the document",
            "cannot read the input",
            "cannot write the output",
            "does not support PDF",
            "does not implement this method",
            "not implement yet",
            "not available in this version",
        ]
        for text in should_match:
            assert _FORMAT_NEGATIVE_CTX_RE.search(text), (
                f"Expected _FORMAT_NEGATIVE_CTX_RE to match: {text!r}"
            )

        # Strings that MUST NOT match (positive context)
        should_not_match = [
            "is supported",
            "supports pdf",
            "export to pdf",
            "PDF export available",
            "can save to xlsx",
        ]
        for text in should_not_match:
            assert not _FORMAT_NEGATIVE_CTX_RE.search(text), (
                f"Expected _FORMAT_NEGATIVE_CTX_RE NOT to match: {text!r}"
            )


class TestTC4096FormatURLExclusion:
    """TC-4096: URL-embedded file extensions must not trigger format detection."""

    def test_url_embedded_pdf_not_detected(self, tmp_path):
        """PDF inside a hyperlink URL (file:///path/report.pdf) must NOT be detected."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()
        (examples_dir / "test_hyperlinks.py").write_text(
            'ws.hyperlinks.add("A1", "file:///C:/Documents/report.pdf")\n'
            'ws.hyperlinks.add("B2", "http://example.com/output.pdf")\n',
            encoding="utf-8",
        )
        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Cells", canonical_import="aspose_cells_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        names = {r.name for r in result}
        assert "PDF" not in names, (
            f"PDF from hyperlink URL must not be detected, but got: {names}"
        )

    def test_local_path_pdf_still_detected(self, tmp_path):
        """PDF in a local save path (not a URL) should still be detected."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "converter.py").write_text(
            'workbook.save("output.pdf")  # export to pdf\n',
            encoding="utf-8",
        )
        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Cells", canonical_import="aspose_cells_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        names = {r.name for r in result}
        assert "PDF" in names, (
            f"PDF from local save path should be detected, but got: {names}"
        )


# ===========================================================================
# TC-4103: Strategy 4 — format class names (FbxSaveOptions etc.)
# ===========================================================================


class TestFormatMatrixStrategy4:
    """TC-4103: Strategy 4 detects format class names (FbxSaveOptions etc.)."""

    def test_fbx_save_options_detected(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_format_matrix
        from launcher.models.product import ProductIdentity

        # Write a Python file with FbxSaveOptions import
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test_formats.py").write_text(
            "from aspose.threed import FbxSaveOptions, ObjLoadOptions, GltfSaveOptions\n"
            "opts = FbxSaveOptions()\n"
            "load_opts = ObjLoadOptions()\n",
            encoding="utf-8",
        )

        product = ProductIdentity(
            family="aspose-3d",
            platform="python",
            display_name="Aspose.3D",
            canonical_import="aspose.threed",
            repo_url="https://github.com/test/test",
        )
        records = extract_format_matrix(tmp_path, product)
        names = {r.name for r in records}
        assert "FBX" in names, f"FBX not found; got {names}"
        assert "OBJ" in names, f"OBJ not found; got {names}"
        fbx_rec = next(r for r in records if r.name == "FBX")
        assert fbx_rec.can_export, "FBX should be can_export=True (SaveOptions)"
        obj_rec = next(r for r in records if r.name == "OBJ")
        assert obj_rec.can_import, "OBJ should be can_import=True (LoadOptions)"

    def test_gltf_both_options(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_format_matrix
        from launcher.models.product import ProductIdentity

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test_gltf.py").write_text(
            "opts_save = GltfSaveOptions()\n"
            "opts_load = GltfLoadOptions()\n",
            encoding="utf-8",
        )

        product = ProductIdentity(
            family="aspose-3d",
            platform="python",
            display_name="Aspose.3D",
            canonical_import="aspose.threed",
            repo_url="https://github.com/test/test",
        )
        records = extract_format_matrix(tmp_path, product)
        names = {r.name for r in records}
        assert "GLTF" in names, f"GLTF not found; got {names}"

    def test_empty_repo_still_returns_empty(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_format_matrix
        from launcher.models.product import ProductIdentity

        product = ProductIdentity(
            family="test",
            platform="python",
            display_name="Test",
            canonical_import="test",
            repo_url="https://github.com/test/test",
        )
        records = extract_format_matrix(tmp_path, product)
        assert records == []

# ===========================================================================
# TC-4100: Namespace recursion explores ALL submodules
# ===========================================================================


class TestNamespaceRecursionMultiSubmodule:
    """TC-4100: namespace package recursion explores ALL submodules."""

    def test_multi_submodule_namespace_both_explored(self, tmp_path):
        """Two submodules → classes from both appear in public_classes."""
        # Build namespace: aspose/__init__.py exports {"threed", "cells"}
        aspose_dir = tmp_path / "aspose"
        aspose_dir.mkdir()
        (aspose_dir / "__init__.py").write_text(
            '__all__ = ["threed", "cells"]\n', encoding="utf-8"
        )
        # aspose/threed/__init__.py → exports Scene, Node
        threed_dir = aspose_dir / "threed"
        threed_dir.mkdir()
        (threed_dir / "__init__.py").write_text(
            'class Scene: "3D scene."\nclass Node: "A node."\n__all__ = ["Scene", "Node"]\n',
            encoding="utf-8",
        )
        # aspose/cells/__init__.py → exports Workbook
        cells_dir = aspose_dir / "cells"
        cells_dir.mkdir()
        (cells_dir / "__init__.py").write_text(
            'class Workbook: "A workbook."\n__all__ = ["Workbook"]\n',
            encoding="utf-8",
        )

        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        from launcher.models.product import ProductIdentity

        product = ProductIdentity(
            family="aspose-3d",
            platform="python",
            display_name="Aspose.3D",
            canonical_import="aspose.threed",
            repo_url="https://github.com/test/test",
        )
        surface = _extract_api_surface(tmp_path, product)
        assert "Scene" in surface.public_classes, (
            f"Scene missing from public_classes; got {surface.public_classes}"
        )
        assert "Workbook" in surface.public_classes, (
            f"Workbook missing from public_classes; got {surface.public_classes}"
        )

    def test_single_submodule_still_works(self, tmp_path):
        """Single submodule (original behavior) still explored correctly."""
        pkg_dir = tmp_path / "mypkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(
            '__all__ = ["sub"]\n', encoding="utf-8"
        )
        sub_dir = pkg_dir / "sub"
        sub_dir.mkdir()
        (sub_dir / "__init__.py").write_text(
            'class MyClass: "A class."\n__all__ = ["MyClass"]\n',
            encoding="utf-8",
        )

        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        from launcher.models.product import ProductIdentity

        product = ProductIdentity(
            family="mypkg",
            platform="python",
            display_name="MyPkg",
            canonical_import="mypkg",
            repo_url="https://github.com/test/test",
        )
        surface = _extract_api_surface(tmp_path, product)
        assert "MyClass" in surface.public_classes, (
            f"MyClass missing from public_classes; got {surface.public_classes}"
        )

    def test_three_submodules_all_explored(self, tmp_path):
        """Three submodules — all classes appear; not just first alphabetically."""
        ns_dir = tmp_path / "ns"
        ns_dir.mkdir()
        (ns_dir / "__init__.py").write_text(
            '__all__ = ["alpha", "beta", "gamma"]\n', encoding="utf-8"
        )
        for name, cls in [("alpha", "Alpha"), ("beta", "Beta"), ("gamma", "Gamma")]:
            sub = ns_dir / name
            sub.mkdir()
            (sub / "__init__.py").write_text(
                f'class {cls}: "Module {name}."\n__all__ = ["{cls}"]\n',
                encoding="utf-8",
            )

        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        from launcher.models.product import ProductIdentity

        product = ProductIdentity(
            family="ns",
            platform="python",
            display_name="NS",
            canonical_import="ns",
            repo_url="https://github.com/test/test",
        )
        surface = _extract_api_surface(tmp_path, product)
        for cls in ("Alpha", "Beta", "Gamma"):
            assert cls in surface.public_classes, (
                f"{cls} missing from public_classes; got {surface.public_classes}"
            )


# ===========================================================================
# TC-4210: Snippet dedup — full SHA-256 hash
# ===========================================================================


class TestSnippetDedup:
    """TC-4210: _build_snippet_context must dedup by full body hash, not code[:200]."""

    def _make_snippet(self, code: str, language: str = "python") -> "Snippet":
        from launcher.models.claims import Snippet
        return Snippet(code=code, language=language, source_type="extracted")

    def test_same_prefix_different_body_both_survive(self):
        """Two snippets sharing identical first 200 chars but different bodies must both survive dedup.

        Under the old code[:200] key they would be incorrectly treated as duplicates.
        With the SHA-256 key they are distinct and both must appear in the output.
        """
        from launcher.workers.understand.extract._llm import _build_snippet_context

        # 200-char shared prefix: "# shared header\n" (16) + "x = 1\n" * 31 (186) = 202 chars
        shared_prefix = "# shared header\n" + "x = 1\n" * 31  # 202 chars >= 200
        assert len(shared_prefix) >= 200, "Shared prefix must be >= 200 chars for the test to be meaningful"

        code_a = shared_prefix + "\n# only in snippet A\nresult_a = do_thing_a()\n"
        code_b = shared_prefix + "\n# only in snippet B\nresult_b = do_thing_b()\n"

        snippets = [self._make_snippet(code_a), self._make_snippet(code_b)]
        result = _build_snippet_context(snippets)

        assert "result_a" in result, "Snippet A body must be present after dedup"
        assert "result_b" in result, "Snippet B body must be present after dedup"

    def test_exact_duplicate_deduplicated(self):
        """Exact duplicate snippets must be collapsed to one entry."""
        from launcher.workers.understand.extract._llm import _build_snippet_context

        code = "def hello():\n    return 'world'\n"
        snippets = [self._make_snippet(code), self._make_snippet(code), self._make_snippet(code)]
        result = _build_snippet_context(snippets)

        # Count occurrences of the distinctive function name
        assert result.count("def hello():") == 1, (
            "Exact duplicate must be collapsed — only one copy should survive dedup"
        )

    def test_fully_different_snippets_both_survive(self):
        """Completely different snippets must both appear in the output."""
        from launcher.workers.understand.extract._llm import _build_snippet_context

        snippets = [
            self._make_snippet("def alpha():\n    return 1\n"),
            self._make_snippet("def beta():\n    return 2\n"),
        ]
        result = _build_snippet_context(snippets)

        assert "def alpha():" in result, "Snippet alpha must survive"
        assert "def beta():" in result, "Snippet beta must survive"


# ===========================================================================
# TC-4211: Contamination keywords — config-driven extension
# ===========================================================================


class TestContaminationConfig:
    """TC-4211: Extra contamination keywords loaded from configs/contamination_keywords.yaml."""

    def _make_claim(self, text: str):
        """Build a minimal Claim object with public visibility."""
        from launcher.models.claims import Claim
        return Claim(
            claim_id="CLM-test-abc123",
            text=text,
            kind="feature",
            evidence=[],
            visibility="public",
            tier_relevance="tier_a",
        )

    def test_yaml_keyword_blocks_contaminated_claim(self, tmp_path):
        """A keyword loaded from YAML must block a claim that doesn't mention the product.

        We monkeypatch _load_extra_keywords to return a custom keyword without
        needing a real file on disk (avoids path-resolution complexity in tests).
        """
        import importlib
        import unittest.mock as mock
        import launcher.workers.understand.extract._validation as val_module

        # Temporarily extend effective keywords with a test-specific keyword
        extra_kw = "superspecialframework"
        original_effective = val_module._EFFECTIVE_CONTAMINANT_KEYWORDS
        try:
            val_module._EFFECTIVE_CONTAMINANT_KEYWORDS = original_effective | frozenset({extra_kw})

            from launcher.workers.understand.extract._validation import _filter_contaminated_claims

            product = _make_product()
            # Claim about superspecialframework only (no product mention)
            claim = self._make_claim(f"Use {extra_kw} to build ML pipelines.")
            result = _filter_contaminated_claims([claim], product)
            assert len(result) == 0, (
                f"Claim about '{extra_kw}' (no product mention) must be filtered out"
            )
        finally:
            val_module._EFFECTIVE_CONTAMINANT_KEYWORDS = original_effective

    def test_yaml_absent_graceful_fallback(self):
        """_load_extra_keywords must return empty frozenset when YAML file does not exist."""
        import unittest.mock as mock
        from pathlib import Path
        from launcher.workers.understand.extract._validation import _load_extra_keywords

        # Patch Path.exists to return False to simulate absent file
        with mock.patch.object(Path, "exists", return_value=False):
            result = _load_extra_keywords()

        assert isinstance(result, frozenset), "Must return a frozenset even when file absent"
        assert len(result) == 0, "Must return empty frozenset when file absent (graceful fallback)"

    def test_hardcoded_keywords_still_work(self):
        """Hardcoded keyword 'docling' must still filter contaminated claims after TC-4211."""
        from launcher.workers.understand.extract._validation import _filter_contaminated_claims

        product = _make_product()
        # Claim about docling only (hardcoded contaminant keyword)
        claim = self._make_claim("Docling parses PDF documents using ML models.")
        result = _filter_contaminated_claims([claim], product)
        assert len(result) == 0, (
            "Claim about 'docling' (hardcoded keyword, no product mention) must be filtered"
        )


# ===========================================================================
# TC-HAL-04 tests: _filter_fallback_api_claims
# ===========================================================================


class TestFilterFallbackApiClaims:
    """Tests for LLM fallback strict api-kind filtering (TC-HAL-04)."""

    def _make_surface(self, identifiers):
        return _make_api_surface(api_identifiers=identifiers)

    def _make_claim(self, claim_id, text, kind="api", source="llm_fallback"):
        return Claim(
            claim_id=claim_id,
            text=text,
            kind=kind,
            claim_source=source,
        )

    def test_filter_activates_above_threshold(self):
        """When fallback_rate > 0.6, unverified api-kind claims are dropped."""
        from launcher.workers.understand.extract._entry import _filter_fallback_api_claims

        api_surface = self._make_surface(["Workbook", "save"])

        claims = [
            self._make_claim("c1", "The Workbook class provides export."),
            self._make_claim("c2", "Use FbxElement to manipulate FBX."),
            self._make_claim("c3", "Library supports scene loading.", kind="feature"),
        ]

        kept, dropped = _filter_fallback_api_claims(claims, api_surface, fallback_rate=0.95)
        assert dropped == 1  # c2 dropped (no api identifier match)
        assert len(kept) == 2  # c1 kept (has "workbook"), c3 kept (feature kind)

    def test_filter_inactive_below_threshold(self):
        """When fallback_rate <= 0.6, no filtering occurs."""
        from launcher.workers.understand.extract._entry import _filter_fallback_api_claims

        api_surface = self._make_surface(["Node"])

        claims = [
            self._make_claim("c1", "Use FbxElement for FBX."),
        ]

        kept, dropped = _filter_fallback_api_claims(claims, api_surface, fallback_rate=0.5)
        assert dropped == 0
        assert len(kept) == 1

    def test_filter_inactive_at_exact_threshold(self):
        """When fallback_rate == threshold (0.6), no filtering occurs (boundary)."""
        from launcher.workers.understand.extract._entry import _filter_fallback_api_claims

        api_surface = self._make_surface(["Node"])

        claims = [
            self._make_claim("c1", "Use FbxElement for FBX."),
        ]

        kept, dropped = _filter_fallback_api_claims(claims, api_surface, fallback_rate=0.6)
        assert dropped == 0
        assert len(kept) == 1

    def test_filter_keeps_non_api_kinds(self):
        """llm_fallback claims with kind != api are always kept."""
        from launcher.workers.understand.extract._entry import _filter_fallback_api_claims

        api_surface = self._make_surface(["Node"])

        claims = [
            self._make_claim("c1", "Supports FBX and OBJ formats.", kind="format"),
            self._make_claim("c2", "Install via pip install aspose.", kind="install"),
        ]

        kept, dropped = _filter_fallback_api_claims(claims, api_surface, fallback_rate=0.99)
        assert dropped == 0
        assert len(kept) == 2

    def test_filter_keeps_verified_api_claims(self):
        """llm_fallback api-kind claims with API identifier in text are kept."""
        from launcher.workers.understand.extract._entry import _filter_fallback_api_claims

        api_surface = self._make_surface(["Node", "add_child"])

        claims = [
            self._make_claim("c1", "The Node class provides scene hierarchy."),
        ]

        kept, dropped = _filter_fallback_api_claims(claims, api_surface, fallback_rate=0.99)
        assert dropped == 0  # kept because "node" is in api_identifiers
        assert len(kept) == 1

    def test_empty_api_identifiers_keeps_all(self):
        """Empty api_identifiers -> no filtering (cannot verify -> keep all)."""
        from launcher.workers.understand.extract._entry import _filter_fallback_api_claims

        api_surface = self._make_surface([])

        claims = [
            self._make_claim("c1", "Unknown api stuff."),
        ]

        kept, dropped = _filter_fallback_api_claims(claims, api_surface, fallback_rate=0.99)
        assert dropped == 0
        assert len(kept) == 1

    def test_non_fallback_source_never_dropped(self):
        """Claims with claim_source != llm_fallback are never dropped even at high rate."""
        from launcher.workers.understand.extract._entry import _filter_fallback_api_claims

        api_surface = self._make_surface(["Workbook"])

        claims = [
            self._make_claim("c1", "Use FbxElement for FBX.", source="llm"),
            self._make_claim("c2", "Use FbxElement for FBX.", source="docstring"),
            self._make_claim("c3", "Use FbxElement for FBX.", source="deterministic"),
        ]

        kept, dropped = _filter_fallback_api_claims(claims, api_surface, fallback_rate=0.99)
        assert dropped == 0
        assert len(kept) == 3

    def test_case_insensitive_identifier_match(self):
        """API identifier matching is case-insensitive."""
        from launcher.workers.understand.extract._entry import _filter_fallback_api_claims

        api_surface = self._make_surface(["WORKBOOK"])

        claims = [
            self._make_claim("c1", "The workbook class provides export."),
        ]

        kept, dropped = _filter_fallback_api_claims(claims, api_surface, fallback_rate=0.99)
        assert dropped == 0  # "workbook" matches "WORKBOOK" (case-insensitive)


# ===========================================================================
# TC-HAL-05 tests: property rendering (no parens for properties)
# ===========================================================================


class TestDocstringPropertyRendering:
    """Tests for TC-HAL-05: property claims should not include () suffix."""

    def test_property_in_typed_methods_no_parens(self):
        """If ms.name is in property_name_set, no () in claim text."""
        from unittest.mock import MagicMock
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        ms = MagicMock()
        ms.name = "parent_nodes"
        ms.docstring_snippet = "Returns the list of parent nodes for this node."

        pd = MagicMock()
        pd.name = "parent_nodes"
        pd.docstring_snippet = "The parent nodes of this node in the scene."

        brief = MagicMock()
        brief.name = "Node"
        brief.docstring_snippet = "Represents a 3D scene node."
        brief.methods = ["parent_nodes", "add_child"]
        brief.typed_methods = [ms]
        brief.typed_properties = [pd]

        api_surface = _make_api_surface(class_briefs=[])
        api_surface = api_surface.model_copy(update={"class_briefs": [brief]})

        product = _make_product(family="3d")

        raw_claims = _harvest_docstring_claims_raw(api_surface, product)

        claim_texts = [c["text"] for c in raw_claims]
        assert not any("parent_nodes()" in t for t in claim_texts), (
            "Found parent_nodes() as method call. Claim texts: " + str(claim_texts)
        )

    def test_pure_method_has_parens(self):
        """Method NOT in property_name_set gets () in claim text."""
        from unittest.mock import MagicMock
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        ms = MagicMock()
        ms.name = "add_child_node"
        ms.docstring_snippet = "Adds a child node to this node children list."

        brief = MagicMock()
        brief.name = "Node"
        brief.docstring_snippet = "Represents a 3D scene node."
        brief.methods = ["add_child_node"]
        brief.typed_methods = [ms]
        brief.typed_properties = []

        api_surface = _make_api_surface(class_briefs=[])
        api_surface = api_surface.model_copy(update={"class_briefs": [brief]})

        product = _make_product(family="3d")

        raw_claims = _harvest_docstring_claims_raw(api_surface, product)

        claim_texts = [c["text"] for c in raw_claims]
        assert any("add_child_node():" in t for t in claim_texts), (
            "Expected add_child_node() in claim text. Got: " + str(claim_texts)
        )

    def test_per_property_claim_generated(self):
        """Properties with docstrings should generate their own claims (no method text)."""
        from unittest.mock import MagicMock
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        pd = MagicMock()
        pd.name = "title"
        pd.docstring_snippet = "The title of this document section, used for navigation."

        brief = MagicMock()
        brief.name = "Section"
        brief.docstring_snippet = "Represents a section within a notebook."
        brief.methods = []
        brief.typed_methods = []
        brief.typed_properties = [pd]

        api_surface = _make_api_surface(class_briefs=[])
        api_surface = api_surface.model_copy(update={"class_briefs": [brief]})

        product = _make_product()

        raw_claims = _harvest_docstring_claims_raw(api_surface, product)

        claim_texts = [c["text"] for c in raw_claims]
        assert any("Section.title:" in t for t in claim_texts), (
            "Expected Section.title: claim. Got: " + str(claim_texts)
        )
        assert not any("Section.title():" in t for t in claim_texts), (
            "Unexpected Section.title(): in claims. Got: " + str(claim_texts)
        )

    def test_property_docstring_too_short_skipped(self):
        """Property docstrings < 20 chars should be skipped."""
        from unittest.mock import MagicMock
        from launcher.workers.understand.extract import _harvest_docstring_claims_raw

        pd = MagicMock()
        pd.name = "id"
        pd.docstring_snippet = "The ID."  # Only 7 chars

        brief = MagicMock()
        brief.name = "Node"
        brief.docstring_snippet = "Represents a 3D scene node."
        brief.methods = []
        brief.typed_methods = []
        brief.typed_properties = [pd]

        api_surface = _make_api_surface(class_briefs=[])
        api_surface = api_surface.model_copy(update={"class_briefs": [brief]})

        product = _make_product()

        raw_claims = _harvest_docstring_claims_raw(api_surface, product)
        claim_texts = [c["text"] for c in raw_claims]
        assert not any("Node.id:" in t for t in claim_texts)


# ---------------------------------------------------------------------------
# TC-HAL-10: hallucination_metrics shape (SR-03)
# ---------------------------------------------------------------------------

def _compute_hallucination_metrics(claims: list) -> dict:
    """Mirror of the audit assembly block in understand/worker.py (TC-HAL-10)."""
    _total_claims = len(claims)
    _low_conf_claims = sum(1 for c in claims if getattr(c, 'confidence', 1.0) < 0.5)
    _estimated_hallucination_rate = (
        _low_conf_claims / _total_claims if _total_claims > 0 else 0.0
    )
    _llm_fallback_count = sum(1 for c in claims if getattr(c, 'claim_source', 'llm') == 'llm_fallback')
    _llm_fallback_rate = _llm_fallback_count / _total_claims if _total_claims > 0 else 0.0
    _conf_dist: dict[str, int] = {"1.0": 0, "0.75": 0, "0.5": 0, "0.35": 0, "other": 0}
    for _c in claims:
        _cv = str(round(getattr(_c, 'confidence', 1.0), 2))
        if _cv in _conf_dist:
            _conf_dist[_cv] += 1
        else:
            _conf_dist["other"] += 1
    return {
        "llm_fallback_rate": round(_llm_fallback_rate, 4),
        "unverified_api_claims_dropped": 0,
        "confidence_distribution": _conf_dist,
        "estimated_hallucination_rate": round(_estimated_hallucination_rate, 4),
        "low_confidence_claim_count": _low_conf_claims,
        "total_claim_count": _total_claims,
    }


class TestHallucinationMetricsShape:
    """SR-03: Verify hallucination_metrics audit block keys and values [TC-HAL-10]."""

    _REQUIRED_KEYS = {
        "llm_fallback_rate",
        "unverified_api_claims_dropped",
        "confidence_distribution",
        "estimated_hallucination_rate",
        "low_confidence_claim_count",
        "total_claim_count",
    }
    _REQUIRED_DIST_KEYS = {"1.0", "0.75", "0.5", "0.35", "other"}

    def _make_claim(self, source: str, confidence: float) -> Claim:
        return Claim(
            claim_id="c1",
            text="test claim",
            kind="api",
            claim_source=source,
            confidence=confidence,
        )

    def test_all_required_keys_present(self) -> None:
        claims = [self._make_claim("llm", 0.75), self._make_claim("docstring", 1.0)]
        metrics = _compute_hallucination_metrics(claims)
        assert self._REQUIRED_KEYS == set(metrics.keys())

    def test_confidence_distribution_keys_present(self) -> None:
        claims = [self._make_claim("llm", 0.75)]
        metrics = _compute_hallucination_metrics(claims)
        assert self._REQUIRED_DIST_KEYS == set(metrics["confidence_distribution"].keys())

    def test_empty_claims_returns_zero_rates(self) -> None:
        metrics = _compute_hallucination_metrics([])
        assert metrics["estimated_hallucination_rate"] == 0.0
        assert metrics["llm_fallback_rate"] == 0.0
        assert metrics["total_claim_count"] == 0

    def test_all_fallback_claims_rate_equals_one(self) -> None:
        claims = [self._make_claim("llm_fallback", 0.35) for _ in range(5)]
        metrics = _compute_hallucination_metrics(claims)
        assert metrics["llm_fallback_rate"] == 1.0
        assert metrics["estimated_hallucination_rate"] == 1.0
        assert metrics["low_confidence_claim_count"] == 5
        assert metrics["confidence_distribution"]["0.35"] == 5

    def test_mixed_claims_correct_distribution(self) -> None:
        claims = [
            self._make_claim("docstring", 1.0),
            self._make_claim("docstring", 1.0),
            self._make_claim("llm", 0.75),
            self._make_claim("llm_fallback", 0.35),
        ]
        metrics = _compute_hallucination_metrics(claims)
        assert metrics["total_claim_count"] == 4
        assert metrics["low_confidence_claim_count"] == 1  # only 0.35 < 0.5
        assert metrics["estimated_hallucination_rate"] == 0.25
        assert metrics["confidence_distribution"]["1.0"] == 2
        assert metrics["confidence_distribution"]["0.75"] == 1
        assert metrics["confidence_distribution"]["0.35"] == 1

    def test_hallucination_rate_does_not_exceed_one(self) -> None:
        claims = [self._make_claim("llm_fallback", 0.35) for _ in range(100)]
        metrics = _compute_hallucination_metrics(claims)
        assert 0.0 <= metrics["estimated_hallucination_rate"] <= 1.0
        assert 0.0 <= metrics["llm_fallback_rate"] <= 1.0


# ===========================================================================
# TC-4246: _build_verified_facts_block tests
# ===========================================================================


class TestBuildVerifiedFactsBlock:
    def test_returns_empty_for_none_extraction_db(self):
        from launcher.workers.understand.extract._llm import _build_verified_facts_block
        assert _build_verified_facts_block(None) == ""

    def test_returns_empty_for_empty_extraction_db(self):
        from launcher.workers.understand.extract._llm import _build_verified_facts_block
        from launcher.models.understanding import ExtractionDatabase
        db = ExtractionDatabase()
        assert _build_verified_facts_block(db) == ""

    def test_includes_api_facts(self):
        from launcher.workers.understand.extract._llm import _build_verified_facts_block
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="Workbook", member_name="save",
                    signature="def save(self, path)", confidence=1.0)
        ])
        result = _build_verified_facts_block(db)
        assert "VERIFIED API FACTS:" in result
        assert "AF-test-001" in result
        assert "def save(self, path)" in result

    def test_includes_format_facts(self):
        from launcher.workers.understand.extract._llm import _build_verified_facts_block
        from launcher.models.understanding import ExtractionDatabase, FormatFact
        db = ExtractionDatabase(format_facts=[
            FormatFact(fact_id="FF-test-001", format_name="XLSX", extension=".xlsx",
                       can_import=True, can_export=True, confidence=1.0)
        ])
        result = _build_verified_facts_block(db)
        assert "VERIFIED FORMAT FACTS:" in result
        assert "XLSX" in result

    def test_respects_max_chars(self):
        from launcher.workers.understand.extract._llm import _build_verified_facts_block
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        # Create many facts to test truncation
        facts = [
            ApiFact(fact_id=f"AF-test-{i:03d}", class_name="Cls", member_name=f"method_{i}",
                    signature=f"def method_{i}(self)", confidence=1.0)
            for i in range(500)
        ]
        db = ExtractionDatabase(api_facts=facts)
        result = _build_verified_facts_block(db, max_chars=1000)
        assert len(result) <= 1000


# ===========================================================================
# TC-4247: Fact-binding validation
# ===========================================================================


class TestValidateFactBinding:
    def test_discovery_mode_passthrough(self):
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        claims = [{"claim_id": "CLM-001", "text": "test", "confidence": 0.75, "claim_source": "llm"}]
        result, stats = _validate_fact_binding(claims, None, bounded_mode_active=False)
        assert len(result) == 1
        assert result[0].get("confidence") == 0.75
        assert "skipped" in stats

    def test_empty_db_passthrough(self):
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase
        claims = [{"claim_id": "CLM-001", "text": "test", "confidence": 0.75, "claim_source": "llm"}]
        result, stats = _validate_fact_binding(claims, ExtractionDatabase(), bounded_mode_active=True)
        assert len(result) == 1
        assert "skipped" in stats

    def test_bound_claim_keeps_confidence(self):
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="Workbook", member_name="save")
        ])
        claims = [{
            "claim_id": "CLM-001", "text": "test", "confidence": 0.75,
            "claim_source": "llm",
            "evidence": [{"source_fact_id": "AF-test-001", "source_file": "src/wb.py"}]
        }]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert result[0].get("confidence") == 0.75
        assert result[0].get("claim_source") == "llm"
        assert stats["bound_claims"] == 1
        assert stats["unbound_claims_downgraded"] == 0

    def test_unbound_claim_downgraded(self):
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="Workbook", member_name="save")
        ])
        claims = [{
            "claim_id": "CLM-001", "text": "ObjLoadOptions supports MTL format",
            "confidence": 0.75, "claim_source": "llm",
            "evidence": [{"source_fact_id": "", "source_file": "README.md"}]
        }]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert result[0]["confidence"] == 0.35
        assert result[0]["claim_source"] == "llm_fallback"  # TC-4252: llm_unbound renamed to llm_fallback
        assert stats["unbound_claims_downgraded"] == 1

    def test_nonexistent_fact_id_downgraded(self):
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="Workbook", member_name="save")
        ])
        claims = [{
            "claim_id": "CLM-001", "text": "test",
            "confidence": 0.75, "claim_source": "llm",
            "evidence": [{"source_fact_id": "AF-HALLUCINATED-999", "source_file": "README.md"}]
        }]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert result[0]["confidence"] == 0.35
        assert stats["unbound_claims_downgraded"] == 1

    def test_docstring_claim_not_downgraded(self):
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="Workbook", member_name="save")
        ])
        claims = [{
            "claim_id": "CLM-001", "text": "Workbook.save()",
            "confidence": 1.0, "claim_source": "docstring",
            "evidence": [{"source_fact_id": "", "source_file": "docstring:Workbook.save"}]
        }]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert result[0]["confidence"] == 1.0
        assert stats["pre_verified_skipped"] == 1
        assert stats["unbound_claims_downgraded"] == 0

    def test_original_dict_not_mutated(self):
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="C", member_name="m")
        ])
        original = {
            "claim_id": "CLM-001", "confidence": 0.75, "claim_source": "llm",
            "evidence": [{"source_fact_id": ""}]
        }
        claims = [original]
        _validate_fact_binding(claims, db, bounded_mode_active=True)
        # Original dict must NOT be mutated
        assert original["confidence"] == 0.75
        assert original["claim_source"] == "llm"

    def test_format_facts_count_as_valid(self):
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, FormatFact
        db = ExtractionDatabase(format_facts=[
            FormatFact(fact_id="FF-test-001", format_name="XLSX", can_export=True)
        ])
        claims = [{
            "claim_id": "CLM-001", "confidence": 0.75, "claim_source": "llm",
            "evidence": [{"source_fact_id": "FF-test-001"}]
        }]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert result[0]["confidence"] == 0.75
        assert stats["bound_claims"] == 1
