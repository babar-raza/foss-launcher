"""TC-3100 / TC-3150: Unit tests for W2 Quality Uplift.

Tests cover:
- Phase 1A: __init__.py re-export symbol extraction
- Phase 1B: Module-level function_details extraction
- Phase 1C: Constructor default parameter values
- Phase 1D: Method start_line in method_details
- Phase 1B propagation: build_api_inventory function_details
- Phase 2A: Excerpt hash computation and normalization
- Phase 2B: Context line range for citations
- Phase 3A: Capability extraction from README and docstrings
- Phase 3B: Workflow extraction from example files
- Phase 3C: Example coverage metric
- Phase 1B/1C consumers: _format_api_symbols_block rendering
- Determinism: Identical output on repeated runs
TC-3150 additions:
- TestSymbolKind: explicit kind field on classes/methods/functions
- TestDocstringSnippet: docstring_snippet on method_details/function_details
- TestFirstSentence: _first_sentence() helper
- TestSetupCfgParser: parse_setup_cfg()
- TestTypescriptExtraction: analyze_typescript_file()
- TestGoExtraction: analyze_go_file() + parse_go_mod()
- TestConversionPairs: _extract_conversion_pairs_deterministic()
- TestInputOutputFormats: _extract_input_output_formats()
- TestLimitationsInRepoTruth: _extract_limitation_summary() via build_repo_truth()
- TestEvidencePointers: evidence field on capabilities
- TestApiIndex: build_api_index()
"""

import json
import hashlib

import pytest
from pathlib import Path

from src.launch.workers.w2_facts_builder.code_analyzer import (
    _extract_modules_from_init,
    analyze_python_file,
    build_api_inventory,
    build_repo_truth,
    # TC-3150 additions
    _first_sentence,
    parse_setup_cfg,
    analyze_typescript_file,
    analyze_go_file,
    parse_go_mod,
    build_api_index,
    _extract_conversion_pairs_deterministic,
    _extract_input_output_formats,
    _extract_limitation_summary,
)
from src.launch.workers.w2_facts_builder.extract_claims import (
    _enrich_citations_with_excerpts,
)
from src.launch.workers.w5_section_writer.multi_pass import (
    _format_api_symbols_block,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _class_names(classes):
    """Helper to extract class names from class dicts or strings."""
    return [c["name"] if isinstance(c, dict) else c for c in classes]


def _make_code_analysis(classes=None, functions=None, modules=None,
                        function_details=None, constants=None):
    """Build a minimal code_analysis dict matching analyze_repository_code shape."""
    return {
        "api_surface": {
            "classes": classes or [],
            "functions": functions or [],
            "modules": modules or [],
            "function_details": function_details or [],
        },
        "code_structure": {
            "source_roots": ["src/"],
            "public_entrypoints": ["__init__.py"],
            "package_names": ["testpkg"],
        },
        "constants": constants or {},
        "metadata": {},
    }


# ===========================================================================
# Phase 1A: __init__.py re-export symbol extraction
# ===========================================================================


class TestInitReExportSymbols:
    """Phase 1A: _extract_modules_from_init extracts individual imported symbols."""

    def test_from_import_extracts_individual_symbols(self, tmp_path):
        """from .scene import Scene, SceneOptions should yield both symbol names."""
        init = tmp_path / "__init__.py"
        init.write_text("from .scene import Scene, SceneOptions\n")

        result = _extract_modules_from_init(init)
        assert "Scene" in result
        assert "SceneOptions" in result
        # The module stem 'scene' is also added (from node.module)
        assert "scene" in result

    def test_star_imports_are_skipped(self, tmp_path):
        """from .x import * should not add '*' to the result."""
        init = tmp_path / "__init__.py"
        init.write_text("from .utils import *\n")

        result = _extract_modules_from_init(init)
        assert "*" not in result
        # The module stem 'utils' is still captured from node.module
        assert "utils" in result

    def test_all_takes_priority(self, tmp_path):
        """__all__ = [...] should be used exclusively (Strategy 1)."""
        init = tmp_path / "__init__.py"
        init.write_text(
            '__all__ = ["Alpha", "Beta"]\n'
            "from .gamma import Gamma\n"
        )

        result = _extract_modules_from_init(init)
        assert result == ["Alpha", "Beta"]
        # Gamma is NOT in result because __all__ takes priority
        assert "Gamma" not in result

    def test_multiple_from_imports(self, tmp_path):
        """Multiple from-imports combine their symbols."""
        init = tmp_path / "__init__.py"
        init.write_text(
            "from .scene import Scene\n"
            "from .mesh import Mesh, MeshBuilder\n"
        )

        result = _extract_modules_from_init(init)
        assert "Scene" in result
        assert "Mesh" in result
        assert "MeshBuilder" in result

    def test_empty_init_returns_empty(self, tmp_path):
        """An empty __init__.py yields an empty list."""
        init = tmp_path / "__init__.py"
        init.write_text("")

        result = _extract_modules_from_init(init)
        assert result == []


# ===========================================================================
# Phase 1B: Module-level function_details
# ===========================================================================


class TestModuleFunctionDetails:
    """Phase 1B: analyze_python_file returns function_details for module-level functions."""

    def test_function_details_extracted(self, tmp_path):
        """Public module-level function should appear in function_details."""
        src = tmp_path / "convert.py"
        src.write_text(
            'def convert(path: str, fmt: str = "json") -> bool:\n'
            '    """Convert a file to the given format."""\n'
            "    return True\n"
        )

        result = analyze_python_file(src)
        fd = result["function_details"]
        assert len(fd) == 1
        entry = fd[0]
        assert entry["name"] == "convert"
        assert "path: str" in entry["signature"]
        assert "fmt: str" in entry["signature"]
        assert entry["return_type"] == "bool"
        assert entry["docstring"] == "Convert a file to the given format."
        assert entry["start_line"] == 1

    def test_private_functions_excluded_from_details(self, tmp_path):
        """Private functions (_helper) should NOT appear in function_details."""
        src = tmp_path / "helpers.py"
        src.write_text(
            "def public_func() -> None:\n"
            "    pass\n"
            "\n"
            "def _private_helper() -> None:\n"
            "    pass\n"
        )

        result = analyze_python_file(src)
        names = [fd["name"] for fd in result["function_details"]]
        assert "public_func" in names
        assert "_private_helper" not in names

    def test_multiple_functions_all_captured(self, tmp_path):
        """All public module-level functions are captured."""
        src = tmp_path / "multi.py"
        src.write_text(
            "def alpha() -> int:\n    return 1\n\n"
            "def beta(x: float) -> float:\n    return x * 2\n\n"
            "def gamma() -> str:\n    return 'ok'\n"
        )

        result = analyze_python_file(src)
        names = sorted(fd["name"] for fd in result["function_details"])
        assert names == ["alpha", "beta", "gamma"]

    def test_function_without_annotations(self, tmp_path):
        """Function without type annotations still captured with empty return_type."""
        src = tmp_path / "bare.py"
        src.write_text("def simple(x):\n    pass\n")

        result = analyze_python_file(src)
        fd = result["function_details"]
        assert len(fd) == 1
        assert fd[0]["name"] == "simple"
        assert fd[0]["return_type"] == ""


# ===========================================================================
# Phase 1C: Constructor default parameter values
# ===========================================================================


class TestDefaultParameterValues:
    """Phase 1C: Constructor parameters include default values."""

    def test_defaults_extracted(self, tmp_path):
        """Constructor defaults appear in param dicts."""
        src = tmp_path / "options.py"
        src.write_text(
            "class Options:\n"
            '    def __init__(self, path: str = ".", mode: int = 0, verbose: bool = False):\n'
            "        pass\n"
        )

        result = analyze_python_file(src)
        cls = result["classes"][0]
        ctor = cls["constructor"]
        assert ctor is not None
        params = ctor["parameters"]
        assert len(params) == 3

        by_name = {p["name"]: p for p in params}
        assert by_name["path"]["default"] == "'.'", (
            f"Expected quoted string default, got {by_name['path']['default']!r}"
        )
        assert by_name["mode"]["default"] == "0"
        assert by_name["verbose"]["default"] == "False"

    def test_params_without_defaults_have_empty_string(self, tmp_path):
        """Parameters without defaults should have default == ''."""
        src = tmp_path / "scene.py"
        src.write_text(
            "class Scene:\n"
            "    def __init__(self, name: str, width: int = 800):\n"
            "        pass\n"
        )

        result = analyze_python_file(src)
        ctor = result["classes"][0]["constructor"]
        params = ctor["parameters"]
        by_name = {p["name"]: p for p in params}
        assert by_name["name"]["default"] == ""
        assert by_name["width"]["default"] == "800"

    def test_no_init_means_no_constructor(self, tmp_path):
        """Class without __init__ should have constructor = None."""
        src = tmp_path / "simple.py"
        src.write_text(
            "class Empty:\n"
            "    pass\n"
        )

        result = analyze_python_file(src)
        cls = result["classes"][0]
        assert cls["constructor"] is None

    def test_annotations_preserved(self, tmp_path):
        """Annotations are also captured alongside defaults."""
        src = tmp_path / "typed.py"
        src.write_text(
            "class Typed:\n"
            "    def __init__(self, rate: float = 0.5):\n"
            "        pass\n"
        )

        result = analyze_python_file(src)
        params = result["classes"][0]["constructor"]["parameters"]
        assert params[0]["annotation"] == "float"
        assert params[0]["default"] == "0.5"


# ===========================================================================
# Phase 1D: Method start_line in method_details
# ===========================================================================


class TestMethodStartLine:
    """Phase 1D: method_details entries have start_line."""

    def test_start_line_matches_source(self, tmp_path):
        """Method start_line should correspond to the actual line in the file."""
        src = tmp_path / "widget.py"
        # Line 1: class Widget:
        # Line 2:     def render(self):
        # Line 3:         pass
        # Line 4: (blank)
        # Line 5:     def update(self, data):
        # Line 6:         pass
        src.write_text(
            "class Widget:\n"
            "    def render(self):\n"
            "        pass\n"
            "\n"
            "    def update(self, data):\n"
            "        pass\n"
        )

        result = analyze_python_file(src)
        cls = result["classes"][0]
        by_name = {m["name"]: m for m in cls["method_details"]}

        assert by_name["render"]["start_line"] == 2
        assert by_name["update"]["start_line"] == 5

    def test_start_line_present_in_every_method(self, tmp_path):
        """Every method_details entry must have a 'start_line' key."""
        src = tmp_path / "api.py"
        src.write_text(
            "class Api:\n"
            "    def get(self):\n"
            "        pass\n"
            "    def post(self, body):\n"
            "        pass\n"
            "    def delete(self, id):\n"
            "        pass\n"
        )

        result = analyze_python_file(src)
        for md in result["classes"][0]["method_details"]:
            assert "start_line" in md, f"start_line missing from {md['name']}"
            assert isinstance(md["start_line"], int)
            assert md["start_line"] > 0


# ===========================================================================
# Phase 1B propagation: build_api_inventory carries function_details
# ===========================================================================


class TestBuildApiInventoryFunctionDetails:
    """Phase 1B propagation: build_api_inventory propagates function_details."""

    def test_function_details_in_inventory(self, tmp_path):
        """function_details from code_analysis should appear in the inventory output."""
        fd_entry = {
            "name": "convert",
            "signature": "convert(path: str, fmt: str)",
            "docstring": "Convert a file.",
            "return_type": "bool",
            "start_line": 10,
        }
        ca = _make_code_analysis(function_details=[fd_entry])

        inventory = build_api_inventory(
            code_analysis=ca,
            repo_dir=tmp_path,
            source_roots=["src/"],
        )

        assert "function_details" in inventory
        assert len(inventory["function_details"]) == 1
        assert inventory["function_details"][0]["name"] == "convert"

    def test_empty_function_details_propagated(self, tmp_path):
        """Empty function_details should still be present as an empty list."""
        ca = _make_code_analysis()

        inventory = build_api_inventory(
            code_analysis=ca,
            repo_dir=tmp_path,
            source_roots=["src/"],
        )

        assert inventory["function_details"] == []


# ===========================================================================
# Phase 2A: Excerpt hash computation
# ===========================================================================


class TestExcerptHash:
    """Phase 2A: Excerpt hash computation in _enrich_citations_with_excerpts."""

    def test_excerpt_hash_is_16_hex_chars(self, tmp_path):
        """Excerpt hash should be exactly 16 hex characters."""
        # Create a file to cite
        source = tmp_path / "readme.txt"
        source.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\n")

        claims = [{
            "claim_id": "test-001",
            "citations": [{
                "path": "readme.txt",
                "start_line": 2,
                "end_line": 3,
            }],
        }]

        _enrich_citations_with_excerpts(claims, tmp_path)

        excerpt_hash = claims[0]["citations"][0]["excerpt_hash"]
        assert len(excerpt_hash) == 16
        assert all(c in "0123456789abcdef" for c in excerpt_hash)

    def test_deterministic_hash(self, tmp_path):
        """Same content should produce the same hash."""
        source = tmp_path / "data.txt"
        source.write_text("Hello World\nLine two\n")

        claims_a = [{
            "claim_id": "a",
            "citations": [{"path": "data.txt", "start_line": 1, "end_line": 1}],
        }]
        claims_b = [{
            "claim_id": "b",
            "citations": [{"path": "data.txt", "start_line": 1, "end_line": 1}],
        }]

        _enrich_citations_with_excerpts(claims_a, tmp_path)
        _enrich_citations_with_excerpts(claims_b, tmp_path)

        assert claims_a[0]["citations"][0]["excerpt_hash"] == (
            claims_b[0]["citations"][0]["excerpt_hash"]
        )

    def test_different_content_different_hash(self, tmp_path):
        """Different content should produce different hashes."""
        file_a = tmp_path / "a.txt"
        file_a.write_text("Alpha content here\n")
        file_b = tmp_path / "b.txt"
        file_b.write_text("Completely different text\n")

        claims_a = [{
            "claim_id": "a",
            "citations": [{"path": "a.txt", "start_line": 1, "end_line": 1}],
        }]
        claims_b = [{
            "claim_id": "b",
            "citations": [{"path": "b.txt", "start_line": 1, "end_line": 1}],
        }]

        _enrich_citations_with_excerpts(claims_a, tmp_path)
        _enrich_citations_with_excerpts(claims_b, tmp_path)

        assert claims_a[0]["citations"][0]["excerpt_hash"] != (
            claims_b[0]["citations"][0]["excerpt_hash"]
        )

    def test_empty_citation_yields_empty_hash(self, tmp_path):
        """Citation without path or start_line gets empty excerpt_hash."""
        claims = [{
            "claim_id": "empty",
            "citations": [{"path": "", "start_line": 0, "end_line": 0}],
        }]

        _enrich_citations_with_excerpts(claims, tmp_path)
        assert claims[0]["citations"][0]["excerpt_hash"] == ""


# ===========================================================================
# Phase 2A: Excerpt hash normalization
# ===========================================================================


class TestExcerptHashNormalization:
    """Phase 2A: Hash normalization (case + whitespace insensitive)."""

    def test_case_and_whitespace_normalization(self, tmp_path):
        """Two excerpts differing only by case and whitespace should hash the same."""
        # We test normalization by computing the hash manually
        # using the same algorithm as _enrich_citations_with_excerpts.
        excerpt_a = "Hello World"
        excerpt_b = "hello  world"

        norm_a = " ".join(excerpt_a.lower().split())
        norm_b = " ".join(excerpt_b.lower().split())

        hash_a = hashlib.sha256(norm_a.encode("utf-8")).hexdigest()[:16]
        hash_b = hashlib.sha256(norm_b.encode("utf-8")).hexdigest()[:16]

        assert hash_a == hash_b, (
            f"Normalized hashes should match: {hash_a} vs {hash_b}"
        )

    def test_different_words_different_hash(self, tmp_path):
        """Substantially different texts should not normalize to the same hash."""
        excerpt_a = "Create a new document"
        excerpt_b = "Delete an old file"

        norm_a = " ".join(excerpt_a.lower().split())
        norm_b = " ".join(excerpt_b.lower().split())

        hash_a = hashlib.sha256(norm_a.encode("utf-8")).hexdigest()[:16]
        hash_b = hashlib.sha256(norm_b.encode("utf-8")).hexdigest()[:16]

        assert hash_a != hash_b


# ===========================================================================
# Phase 2B: Context line range
# ===========================================================================


class TestContextLineRange:
    """Phase 2B: context_start_line and context_end_line on citations."""

    def test_context_range_mid_file(self, tmp_path):
        """Claim citing line 10 -> context_start_line = 7, context_end_line = 13."""
        source = tmp_path / "code.py"
        source.write_text("\n".join(f"line {i}" for i in range(1, 21)) + "\n")

        claims = [{
            "claim_id": "mid",
            "citations": [{"path": "code.py", "start_line": 10, "end_line": 10}],
        }]

        _enrich_citations_with_excerpts(claims, tmp_path)
        cit = claims[0]["citations"][0]
        assert cit["context_start_line"] == 7   # max(1, 10-3)
        assert cit["context_end_line"] == 13    # 10+3

    def test_context_range_clamped_at_top(self, tmp_path):
        """Claim citing line 1 -> context_start_line clamped to 1."""
        source = tmp_path / "top.py"
        source.write_text("first line\nsecond line\nthird line\nfourth line\n")

        claims = [{
            "claim_id": "top",
            "citations": [{"path": "top.py", "start_line": 1, "end_line": 1}],
        }]

        _enrich_citations_with_excerpts(claims, tmp_path)
        cit = claims[0]["citations"][0]
        assert cit["context_start_line"] == 1  # max(1, 1-3) = 1
        assert cit["context_end_line"] == 4    # 1+3

    def test_empty_citation_context_zeros(self, tmp_path):
        """Empty citation -> both context lines = 0."""
        claims = [{
            "claim_id": "empty",
            "citations": [{"path": "", "start_line": 0, "end_line": 0}],
        }]

        _enrich_citations_with_excerpts(claims, tmp_path)
        cit = claims[0]["citations"][0]
        assert cit["context_start_line"] == 0
        assert cit["context_end_line"] == 0

    def test_context_range_with_multi_line_citation(self, tmp_path):
        """Citation spanning lines 5-8 -> context extends +-3 from boundaries."""
        source = tmp_path / "multi.py"
        source.write_text("\n".join(f"L{i}" for i in range(1, 21)) + "\n")

        claims = [{
            "claim_id": "span",
            "citations": [{"path": "multi.py", "start_line": 5, "end_line": 8}],
        }]

        _enrich_citations_with_excerpts(claims, tmp_path)
        cit = claims[0]["citations"][0]
        assert cit["context_start_line"] == 2   # max(1, 5-3)
        assert cit["context_end_line"] == 11    # 8+3


# ===========================================================================
# Phase 3A: Capability extraction from README
# ===========================================================================


class TestCapabilitiesFromReadme:
    """Phase 3A: Capability extraction from README features sections."""

    def test_readme_features_bullet_points(self, tmp_path):
        """Bullet points under ## Features are extracted with source='readme'."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "# My Library\n"
            "\n"
            "## Features\n"
            "\n"
            "- Convert documents to PDF\n"
            "- Merge multiple files\n"
            "- Extract text content\n"
            "\n"
            "## Installation\n"
            "pip install mylib\n"
        )

        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, ["src/"])

        caps = result["capabilities"]["values"]
        texts = [c["text"] for c in caps]
        assert "Convert documents to PDF" in texts
        assert "Merge multiple files" in texts
        assert "Extract text content" in texts
        for cap in caps:
            assert cap["source"] == "readme"

    def test_key_features_heading_also_matched(self, tmp_path):
        """## Key Features heading is also recognized."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Lib\n"
            "\n"
            "## Key Features\n"
            "\n"
            "- Fast processing\n"
            "- Low memory usage\n"
        )

        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, ["src/"])

        caps = result["capabilities"]["values"]
        texts = [c["text"] for c in caps]
        assert "Fast processing" in texts
        assert "Low memory usage" in texts

    def test_no_readme_empty_capabilities(self, tmp_path):
        """Missing README yields empty capabilities from readme source."""
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, ["src/"])

        caps = result["capabilities"]["values"]
        # No readme means no readme-sourced capabilities (could still have docstring ones)
        readme_caps = [c for c in caps if c["source"] == "readme"]
        assert readme_caps == []


# ===========================================================================
# Phase 3A: Capability extraction from docstrings
# ===========================================================================


class TestCapabilitiesFromDocstrings:
    """Phase 3A: Capability extraction from class docstrings."""

    def test_first_sentence_extracted(self, tmp_path):
        """First sentence of class docstring is extracted with source='docstring'."""
        ca = _make_code_analysis(classes=[
            {
                "name": "Converter",
                "docstring": "Converts documents between formats. Supports PDF and DOCX.",
                "bases": [],
                "module": "mylib.converter",
                "methods": [],
                "method_details": [],
                "properties": [],
                "constructor": None,
                "class_constants": [],
                "source_file": "converter.py",
                "start_line": 1,
            },
        ])

        result = build_repo_truth(tmp_path, {}, ca, ["src/"])
        caps = result["capabilities"]["values"]
        doc_caps = [c for c in caps if c["source"].startswith("docstring")]
        assert len(doc_caps) >= 1
        # First sentence up to first ". " boundary
        assert doc_caps[0]["text"] == "Converts documents between formats."

    def test_empty_docstring_not_extracted(self, tmp_path):
        """Class with empty docstring should not produce a capability."""
        ca = _make_code_analysis(classes=[
            {
                "name": "Bare",
                "docstring": "",
                "bases": [],
                "module": "mylib",
                "methods": [],
                "method_details": [],
                "properties": [],
                "constructor": None,
                "class_constants": [],
                "source_file": "bare.py",
                "start_line": 1,
            },
        ])

        result = build_repo_truth(tmp_path, {}, ca, ["src/"])
        caps = result["capabilities"]["values"]
        doc_caps = [c for c in caps if c["source"].startswith("docstring")]
        assert doc_caps == []


# ===========================================================================
# Phase 3B: Workflow extraction from example files
# ===========================================================================


class TestWorkflowsFromExamples:
    """Phase 3B: Workflow extraction from example directories."""

    def test_example_importing_known_class(self, tmp_path):
        """Example file importing a known class creates a workflow entry."""
        # Create examples directory
        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()
        example_file = examples_dir / "demo_convert.py"
        example_file.write_text(
            "from mylib import Converter\n"
            "\n"
            "c = Converter()\n"
            "c.run()\n"
        )

        ca = _make_code_analysis(classes=[
            {
                "name": "Converter",
                "docstring": "Converter class.",
                "bases": [],
                "module": "mylib",
                "methods": ["run"],
                "method_details": [],
                "properties": [],
                "constructor": None,
                "class_constants": [],
                "source_file": "mylib/converter.py",
                "start_line": 1,
            },
        ])

        result = build_repo_truth(tmp_path, {}, ca, ["src/"])
        wfs = result["workflows"]["values"]
        assert len(wfs) == 1
        assert wfs[0]["name"] == "demo_convert"
        assert "Converter" in wfs[0]["api_classes_used"]
        assert wfs[0]["source_file"] == "examples/demo_convert.py"

    def test_multiple_examples_multiple_workflows(self, tmp_path):
        """Multiple example files produce multiple workflow entries."""
        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()

        (examples_dir / "ex_alpha.py").write_text("from lib import Alpha\n")
        (examples_dir / "ex_beta.py").write_text("from lib import Beta\n")

        ca = _make_code_analysis(classes=[
            {"name": "Alpha", "docstring": "", "bases": [], "module": "lib",
             "methods": [], "method_details": [], "properties": [],
             "constructor": None, "class_constants": [],
             "source_file": "alpha.py", "start_line": 1},
            {"name": "Beta", "docstring": "", "bases": [], "module": "lib",
             "methods": [], "method_details": [], "properties": [],
             "constructor": None, "class_constants": [],
             "source_file": "beta.py", "start_line": 1},
        ])

        result = build_repo_truth(tmp_path, {}, ca, ["src/"])
        wfs = result["workflows"]["values"]
        names = sorted(w["name"] for w in wfs)
        assert names == ["ex_alpha", "ex_beta"]

    def test_example_without_known_imports_excluded(self, tmp_path):
        """Example files that don't import known classes are excluded."""
        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()
        (examples_dir / "unrelated.py").write_text("import os\nprint('hello')\n")

        ca = _make_code_analysis(classes=[
            {"name": "Converter", "docstring": "", "bases": [], "module": "lib",
             "methods": [], "method_details": [], "properties": [],
             "constructor": None, "class_constants": [],
             "source_file": "converter.py", "start_line": 1},
        ])

        result = build_repo_truth(tmp_path, {}, ca, ["src/"])
        wfs = result["workflows"]["values"]
        assert wfs == []


# ===========================================================================
# Phase 3C: Example coverage metric
# ===========================================================================


class TestExampleCoverage:
    """Phase 3C: Example coverage metric computation."""

    def test_partial_coverage_ratio(self, tmp_path):
        """5 classes, 3 with examples -> coverage ratio = 0.6."""
        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()
        # Example imports 3 of 5 classes
        (examples_dir / "demo.py").write_text(
            "from lib import Alpha, Beta, Gamma\n"
        )

        classes = []
        for name in ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]:
            classes.append({
                "name": name, "docstring": "", "bases": [],
                "module": "lib", "methods": [], "method_details": [],
                "properties": [], "constructor": None, "class_constants": [],
                "source_file": f"{name.lower()}.py", "start_line": 1,
            })

        ca = _make_code_analysis(classes=classes)
        result = build_repo_truth(tmp_path, {}, ca, ["src/"])

        cov = result["example_coverage"]
        assert cov["ratio"] == 0.6
        assert cov["classes_with_examples"] == 3
        assert cov["total_api_classes"] == 5

    def test_full_coverage(self, tmp_path):
        """All classes covered -> ratio = 1.0."""
        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()
        (examples_dir / "all.py").write_text("from lib import Foo, Bar\n")

        classes = [
            {"name": "Foo", "docstring": "", "bases": [], "module": "lib",
             "methods": [], "method_details": [], "properties": [],
             "constructor": None, "class_constants": [],
             "source_file": "foo.py", "start_line": 1},
            {"name": "Bar", "docstring": "", "bases": [], "module": "lib",
             "methods": [], "method_details": [], "properties": [],
             "constructor": None, "class_constants": [],
             "source_file": "bar.py", "start_line": 1},
        ]

        ca = _make_code_analysis(classes=classes)
        result = build_repo_truth(tmp_path, {}, ca, ["src/"])

        assert result["example_coverage"]["ratio"] == 1.0

    def test_zero_classes_zero_ratio(self, tmp_path):
        """Zero API classes -> ratio = 0.0 (avoids division by zero)."""
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, ["src/"])

        assert result["example_coverage"]["ratio"] == 0.0
        assert result["example_coverage"]["total_api_classes"] == 0


# ===========================================================================
# Phase 3B/3C: No examples directory
# ===========================================================================


class TestNoExamplesDir:
    """Phase 3B/3C: Graceful handling when no examples directory exists."""

    def test_no_examples_empty_workflows(self, tmp_path):
        """Missing examples/ dir -> workflows empty."""
        classes = [
            {"name": "Cls", "docstring": "", "bases": [], "module": "lib",
             "methods": [], "method_details": [], "properties": [],
             "constructor": None, "class_constants": [],
             "source_file": "cls.py", "start_line": 1},
        ]
        ca = _make_code_analysis(classes=classes)
        result = build_repo_truth(tmp_path, {}, ca, ["src/"])

        assert result["workflows"]["values"] == []

    def test_no_examples_zero_coverage(self, tmp_path):
        """Missing examples/ dir -> coverage ratio = 0.0."""
        classes = [
            {"name": "Cls", "docstring": "", "bases": [], "module": "lib",
             "methods": [], "method_details": [], "properties": [],
             "constructor": None, "class_constants": [],
             "source_file": "cls.py", "start_line": 1},
        ]
        ca = _make_code_analysis(classes=classes)
        result = build_repo_truth(tmp_path, {}, ca, ["src/"])

        assert result["example_coverage"]["ratio"] == 0.0


# ===========================================================================
# Phase 1B consumer: _format_api_symbols_block with function_details
# ===========================================================================


class TestFormatApiSymbolsBlockWithFunctions:
    """Phase 1B consumer: _format_api_symbols_block renders function_details."""

    def test_module_functions_section_rendered(self):
        """Output should contain 'Module functions:' section."""
        inventory = {
            "classes": [{"name": "Cls", "import_path": "pkg.Cls", "methods": ["run"]}],
            "function_details": [
                {
                    "name": "convert",
                    "signature": "convert(path: str, fmt: str)",
                    "return_type": "bool",
                },
            ],
            "public_surface": {
                "classes": ["pkg.Cls"],
                "functions": [],
                "confidence": "high",
                "source": "__all__",
            },
        }

        block = _format_api_symbols_block(inventory)
        assert "Module functions:" in block

    def test_function_signatures_rendered(self):
        """Function signatures should appear in the output."""
        inventory = {
            "classes": [{"name": "Cls", "import_path": "pkg.Cls", "methods": []}],
            "function_details": [
                {
                    "name": "convert",
                    "signature": "convert(path: str, fmt: str)",
                    "return_type": "bool",
                },
                {
                    "name": "validate",
                    "signature": "validate(data: dict)",
                    "return_type": "",
                },
            ],
            "public_surface": {
                "classes": ["pkg.Cls"],
                "functions": [],
                "confidence": "high",
                "source": "__all__",
            },
        }

        block = _format_api_symbols_block(inventory)
        assert "convert(path: str, fmt: str)" in block
        assert "-> bool" in block
        assert "validate(data: dict)" in block

    def test_no_function_details_no_section(self):
        """No function_details -> no 'Module functions:' section."""
        inventory = {
            "classes": [{"name": "Cls", "import_path": "pkg.Cls", "methods": ["run"]}],
            "function_details": [],
            "public_surface": {
                "classes": ["pkg.Cls"],
                "functions": [],
                "confidence": "high",
                "source": "__all__",
            },
        }

        block = _format_api_symbols_block(inventory)
        assert "Module functions:" not in block


# ===========================================================================
# Phase 1C consumer: _format_api_symbols_block with defaults
# ===========================================================================


class TestFormatApiSymbolsBlockWithDefaults:
    """Phase 1C consumer: _format_api_symbols_block renders constructor defaults."""

    def test_default_values_in_constructor(self):
        """Output should contain '= defaultvalue' patterns for constructor params."""
        inventory = {
            "classes": [{
                "name": "Options",
                "import_path": "pkg.Options",
                "methods": [],
                "constructor": {
                    "parameters": [
                        {"name": "path", "annotation": "str", "default": "'.'"},
                        {"name": "mode", "annotation": "int", "default": "0"},
                    ],
                },
            }],
            "function_details": [],
            "public_surface": {
                "classes": ["pkg.Options"],
                "functions": [],
                "confidence": "high",
                "source": "__all__",
            },
        }

        block = _format_api_symbols_block(inventory)
        assert "path: str = '.'" in block
        assert "mode: int = 0" in block

    def test_param_without_default(self):
        """Params without default should NOT show '=' in the output."""
        inventory = {
            "classes": [{
                "name": "Scene",
                "import_path": "pkg.Scene",
                "methods": [],
                "constructor": {
                    "parameters": [
                        {"name": "name", "annotation": "str", "default": ""},
                    ],
                },
            }],
            "function_details": [],
            "public_surface": {
                "classes": ["pkg.Scene"],
                "functions": [],
                "confidence": "high",
                "source": "__all__",
            },
        }

        block = _format_api_symbols_block(inventory)
        # Should have "name: str" but NOT "name: str ="
        assert "name: str" in block
        assert "name: str =" not in block

    def test_constructor_with_annotation_only(self):
        """Param with annotation but no default renders correctly."""
        inventory = {
            "classes": [{
                "name": "Builder",
                "import_path": "pkg.Builder",
                "methods": ["build"],
                "constructor": {
                    "parameters": [
                        {"name": "config", "annotation": "dict", "default": ""},
                        {"name": "verbose", "annotation": "bool", "default": "True"},
                    ],
                },
            }],
            "function_details": [],
            "public_surface": {
                "classes": ["pkg.Builder"],
                "functions": [],
                "confidence": "high",
                "source": "__all__",
            },
        }

        block = _format_api_symbols_block(inventory)
        assert "config: dict" in block
        assert "verbose: bool = True" in block


# ===========================================================================
# Determinism
# ===========================================================================


class TestDeterminism:
    """Test that running extraction twice produces identical output."""

    def test_analyze_python_file_deterministic(self, tmp_path):
        """Two runs of analyze_python_file on the same file produce identical JSON."""
        src = tmp_path / "deterministic.py"
        src.write_text(
            "class Alpha:\n"
            '    """Alpha class."""\n'
            "    def compute(self, x: int) -> int:\n"
            "        return x * 2\n"
            "\n"
            "class Beta:\n"
            '    """Beta class."""\n'
            "    def __init__(self, name: str = 'default'):\n"
            "        self.name = name\n"
            "\n"
            "    def show(self) -> str:\n"
            "        return self.name\n"
            "\n"
            "def helper(data: list) -> int:\n"
            "    return len(data)\n"
            "\n"
            "CONSTANT = 42\n"
        )

        r1 = analyze_python_file(src)
        r2 = analyze_python_file(src)

        j1 = json.dumps(r1, sort_keys=True)
        j2 = json.dumps(r2, sort_keys=True)
        assert j1 == j2, "analyze_python_file should be deterministic"

    def test_build_repo_truth_deterministic(self, tmp_path):
        """Two runs of build_repo_truth on the same inputs produce identical JSON."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Test\n\n## Features\n\n- Feature A\n- Feature B\n"
        )

        ca = _make_code_analysis(classes=[
            {"name": "Cls", "docstring": "A useful class.", "bases": [],
             "module": "lib", "methods": [], "method_details": [],
             "properties": [], "constructor": None, "class_constants": [],
             "source_file": "cls.py", "start_line": 1},
        ])

        r1 = build_repo_truth(tmp_path, {}, ca, ["src/"])
        r2 = build_repo_truth(tmp_path, {}, ca, ["src/"])

        j1 = json.dumps(r1, sort_keys=True)
        j2 = json.dumps(r2, sort_keys=True)
        assert j1 == j2, "build_repo_truth should be deterministic"


# ===========================================================================
# TC-3150: _first_sentence() helper
# ===========================================================================

class TestFirstSentence:
    """TC-3150: _first_sentence() helper extracts first sentence from docstrings."""

    def test_basic_extraction(self):
        text = "Load a 3D scene from file. Additional details follow."
        assert _first_sentence(text) == "Load a 3D scene from file."

    def test_max_len_truncation(self):
        long = "A" * 150
        result = _first_sentence(long, max_len=50)
        assert len(result) <= 50

    def test_empty_string(self):
        assert _first_sentence("") == ""

    def test_single_line_no_period(self):
        assert _first_sentence("No period here", max_len=100) == "No period here"

    def test_multiline_uses_first_line(self):
        text = "First line summary.\nSecond line detail."
        assert _first_sentence(text) == "First line summary."


# ===========================================================================
# TC-3150: kind field on symbol records
# ===========================================================================

class TestSymbolKind:
    """TC-3150: analyze_python_file emits explicit kind field on classes/methods/functions."""

    def test_class_has_kind_field(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text("class MyClass:\n    pass\n")
        result = analyze_python_file(src)
        classes = result.get("classes", [])
        assert any(c.get("kind") == "class" for c in classes if isinstance(c, dict))

    def test_method_kind_is_method(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class MyClass:\n"
            "    def do_work(self): pass\n"
        )
        result = analyze_python_file(src)
        classes = result.get("classes", [])
        assert classes
        md = classes[0].get("method_details", [])
        assert any(m.get("kind") == "method" for m in md)

    def test_classmethod_kind(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class MyClass:\n"
            "    @classmethod\n"
            "    def from_file(cls, path): pass\n"
        )
        result = analyze_python_file(src)
        classes = result.get("classes", [])
        assert classes
        md = classes[0].get("method_details", [])
        from_file = next((m for m in md if m.get("name") == "from_file"), None)
        assert from_file is not None, "from_file method should be in method_details"
        assert from_file.get("kind") == "classmethod"

    def test_staticmethod_kind(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class MyClass:\n"
            "    @staticmethod\n"
            "    def create(): pass\n"
        )
        result = analyze_python_file(src)
        classes = result.get("classes", [])
        assert classes
        md = classes[0].get("method_details", [])
        create = next((m for m in md if m.get("name") == "create"), None)
        assert create is not None
        assert create.get("kind") == "staticmethod"

    def test_property_kind_in_method_details(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class MyClass:\n"
            "    @property\n"
            "    def name(self): return ''\n"
        )
        result = analyze_python_file(src)
        classes = result.get("classes", [])
        assert classes
        md = classes[0].get("method_details", [])
        name_m = next((m for m in md if m.get("name") == "name"), None)
        assert name_m is not None
        assert name_m.get("kind") == "property"

    def test_function_kind_is_function(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text("def load(path: str): pass\n")
        result = analyze_python_file(src)
        fd = result.get("function_details", [])
        assert any(f.get("kind") == "function" for f in fd)

    def test_kind_propagated_through_build_api_inventory(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text("class Scene:\n    def open(self): pass\n")
        code_analysis = {
            "api_surface": {"classes": analyze_python_file(src).get("classes", []),
                            "functions": [], "modules": []},
            "code_structure": {"source_roots": [""], "public_entrypoints": [], "package_names": ["testpkg"]},
            "constants": {}, "metadata": {},
        }
        inv = build_api_inventory(code_analysis, tmp_path, [""])
        cls = next((c for c in inv.get("classes", []) if c.get("name") == "Scene"), None)
        assert cls is not None
        assert cls.get("kind") == "class"


# ===========================================================================
# TC-3150: docstring_snippet on method_details and function_details
# ===========================================================================

class TestDocstringSnippet:
    """TC-3150: analyze_python_file emits docstring_snippet on method/function details."""

    def test_method_has_docstring_snippet(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class MyClass:\n"
            "    def load(self):\n"
            "        \"\"\"Load a 3D scene from file. Returns the scene.\"\"\"\n"
            "        pass\n"
        )
        result = analyze_python_file(src)
        md = result.get("classes", [{}])[0].get("method_details", [])
        load = next((m for m in md if m["name"] == "load"), None)
        assert load is not None
        snippet = load.get("docstring_snippet", "")
        assert snippet == "Load a 3D scene from file."

    def test_method_snippet_empty_for_no_docstring(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text("class MyClass:\n    def run(self): pass\n")
        result = analyze_python_file(src)
        md = result.get("classes", [{}])[0].get("method_details", [])
        run = next((m for m in md if m["name"] == "run"), None)
        assert run is not None
        assert run.get("docstring_snippet", "") == ""

    def test_function_has_docstring_snippet(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "def create(path: str):\n"
            "    \"\"\"Create a new document. Returns Document.\"\"\"\n"
            "    pass\n"
        )
        result = analyze_python_file(src)
        fd = result.get("function_details", [])
        fn = next((f for f in fd if f["name"] == "create"), None)
        assert fn is not None
        assert fn.get("docstring_snippet") == "Create a new document."

    def test_snippet_capped_at_80_chars(self, tmp_path):
        long_doc = "A" * 100
        src = tmp_path / "mod.py"
        src.write_text(f"def run():\n    \"\"\"{long_doc}\"\"\"\n    pass\n")
        result = analyze_python_file(src)
        fd = result.get("function_details", [])
        fn = next((f for f in fd if f["name"] == "run"), None)
        assert fn is not None
        assert len(fn.get("docstring_snippet", "")) <= 80


# ===========================================================================
# TC-3150: parse_setup_cfg()
# ===========================================================================

class TestSetupCfgParser:
    """TC-3150: parse_setup_cfg() extracts metadata, dependencies, and entrypoints."""

    def test_extracts_metadata(self, tmp_path):
        cfg = tmp_path / "setup.cfg"
        cfg.write_text(
            "[metadata]\n"
            "name = my-package\n"
            "version = 1.2.3\n"
            "description = A useful library\n"
        )
        result = parse_setup_cfg(cfg)
        assert result.get("name") == "my-package"
        assert result.get("version") == "1.2.3"
        assert result.get("description") == "A useful library"

    def test_extracts_python_requires_and_deps(self, tmp_path):
        cfg = tmp_path / "setup.cfg"
        cfg.write_text(
            "[metadata]\nname = pkg\n"
            "[options]\n"
            "python_requires = >=3.8\n"
            "install_requires =\n"
            "    numpy>=1.20\n"
            "    pillow\n"
        )
        result = parse_setup_cfg(cfg)
        assert result.get("python_requires") == ">=3.8"
        deps = result.get("dependencies", [])
        assert "numpy>=1.20" in deps
        assert "pillow" in deps

    def test_extracts_entrypoints(self, tmp_path):
        cfg = tmp_path / "setup.cfg"
        cfg.write_text(
            "[metadata]\nname = pkg\n"
            "[options.entry_points]\n"
            "console_scripts =\n"
            "    my-tool = mypkg.cli:main\n"
        )
        result = parse_setup_cfg(cfg)
        assert "my-tool" in result.get("entrypoints", [])

    def test_missing_sections_return_empty(self, tmp_path):
        cfg = tmp_path / "setup.cfg"
        cfg.write_text("[metadata]\nname = pkg\n")
        result = parse_setup_cfg(cfg)
        assert result.get("dependencies", []) == []
        assert result.get("entrypoints", []) == []

    def test_nonexistent_file_returns_empty(self, tmp_path):
        result = parse_setup_cfg(tmp_path / "nonexistent.cfg")
        assert result == {}


# ===========================================================================
# TC-3150: TypeScript extraction
# ===========================================================================

class TestTypescriptExtraction:
    """TC-3150: analyze_typescript_file() extracts exported symbols from .ts files."""

    def test_export_class(self, tmp_path):
        ts = tmp_path / "mod.ts"
        ts.write_text("export class Workbook { save() {} }\n")
        result = analyze_typescript_file(ts)
        names = [c["name"] for c in result.get("classes", [])]
        assert "Workbook" in names

    def test_export_function(self, tmp_path):
        ts = tmp_path / "mod.ts"
        ts.write_text("export function createWorkbook(path: string): Workbook {}\n")
        result = analyze_typescript_file(ts)
        assert "createWorkbook" in result.get("functions", [])

    def test_export_interface_and_type(self, tmp_path):
        ts = tmp_path / "mod.ts"
        ts.write_text(
            "export interface SaveOptions { format: string; }\n"
            "export type FileFormat = 'xlsx' | 'csv';\n"
        )
        result = analyze_typescript_file(ts)
        names = {c["name"]: c["kind"] for c in result.get("classes", [])}
        assert names.get("SaveOptions") == "interface"
        assert names.get("FileFormat") == "type"

    def test_non_exported_not_extracted(self, tmp_path):
        ts = tmp_path / "mod.ts"
        ts.write_text(
            "class InternalHelper { }\n"
            "function internalFn() {}\n"
        )
        result = analyze_typescript_file(ts)
        names = [c["name"] for c in result.get("classes", [])]
        assert "InternalHelper" not in names
        assert "internalFn" not in result.get("functions", [])

    def test_kind_field_on_class(self, tmp_path):
        ts = tmp_path / "mod.ts"
        ts.write_text("export class MyClass {}\n")
        result = analyze_typescript_file(ts)
        cls = next((c for c in result.get("classes", []) if c["name"] == "MyClass"), None)
        assert cls is not None
        assert cls.get("kind") == "class"


# ===========================================================================
# TC-3150: Go extraction
# ===========================================================================

class TestGoExtraction:
    """TC-3150: analyze_go_file() + parse_go_mod() extract Go symbols."""

    def test_exported_struct_types(self, tmp_path):
        go = tmp_path / "scene.go"
        go.write_text(
            "package threed\n"
            "type Scene struct {\n"
            "    nodes []Node\n"
            "}\n"
            "type internalHelper struct {}\n"
        )
        result = analyze_go_file(go)
        names = [c["name"] for c in result.get("classes", [])]
        assert "Scene" in names
        assert "internalHelper" not in names

    def test_exported_functions(self, tmp_path):
        go = tmp_path / "factory.go"
        go.write_text(
            "package threed\n"
            "func NewScene() *Scene { return nil }\n"
            "func internalInit() {}\n"
        )
        result = analyze_go_file(go)
        assert "NewScene" in result.get("functions", [])
        assert "internalInit" not in result.get("functions", [])

    def test_exported_methods(self, tmp_path):
        go = tmp_path / "scene.go"
        go.write_text(
            "package threed\n"
            "func (s *Scene) Open(path string) error { return nil }\n"
            "func (s *Scene) internalSetup() {}\n"
        )
        result = analyze_go_file(go)
        assert "Open" in result.get("functions", [])
        assert "internalSetup" not in result.get("functions", [])

    def test_parse_go_mod(self, tmp_path):
        gomod = tmp_path / "go.mod"
        gomod.write_text(
            "module github.com/aspose/threed\n\ngo 1.21\n"
        )
        result = parse_go_mod(gomod)
        assert result.get("name") == "threed"
        assert result.get("module_path") == "github.com/aspose/threed"
        assert result.get("go_version") == "1.21"


# ===========================================================================
# TC-3150: Conversion pairs
# ===========================================================================

class TestConversionPairs:
    """TC-3150: _extract_conversion_pairs_deterministic() finds format pairs."""

    def test_filename_pattern_obj_to_stl(self, tmp_path):
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "convert_OBJ_TO_STL.py").write_text("pass")
        ca = _make_code_analysis()
        pairs = _extract_conversion_pairs_deterministic(tmp_path, ca, ["OBJ", "STL"])
        found = [(p["source"], p["target"]) for p in pairs]
        assert ("OBJ", "STL") in found

    def test_empty_when_no_formats(self, tmp_path):
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "convert_obj_to_stl.py").write_text("pass")
        ca = _make_code_analysis()
        pairs = _extract_conversion_pairs_deterministic(tmp_path, ca, [])
        assert pairs == []

    def test_deterministic_ordering(self, tmp_path):
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "convert_PDF_TO_DOCX.py").write_text("pass")
        (examples / "convert_OBJ_TO_STL.py").write_text("pass")
        ca = _make_code_analysis()
        r1 = _extract_conversion_pairs_deterministic(tmp_path, ca, ["OBJ", "STL", "PDF", "DOCX"])
        r2 = _extract_conversion_pairs_deterministic(tmp_path, ca, ["OBJ", "STL", "PDF", "DOCX"])
        assert r1 == r2
        # Pairs should be sorted by (source, target)
        keys = [(p["source"], p["target"]) for p in r1]
        assert keys == sorted(keys)


# ===========================================================================
# TC-3150: Input/output format distinction
# ===========================================================================

class TestInputOutputFormats:
    """TC-3150: _extract_input_output_formats() splits formats by direction."""

    def test_load_options_class_yields_input(self):
        ca = _make_code_analysis(classes=[
            {"name": "OBJLoadOptions", "methods": [], "method_details": [],
             "properties": [], "constructor": None, "class_constants": [],
             "docstring": "", "bases": [], "module": "", "source_file": "", "start_line": 1},
        ])
        input_fmts, _ = _extract_input_output_formats(ca, ["OBJ", "STL"])
        assert "OBJ" in input_fmts

    def test_save_options_class_yields_output(self):
        ca = _make_code_analysis(classes=[
            {"name": "STLSaveOptions", "methods": [], "method_details": [],
             "properties": [], "constructor": None, "class_constants": [],
             "docstring": "", "bases": [], "module": "", "source_file": "", "start_line": 1},
        ])
        _, output_fmts = _extract_input_output_formats(ca, ["OBJ", "STL"])
        assert "STL" in output_fmts

    def test_bidirectional_fallback_when_no_signal(self):
        """When no LoadOptions/SaveOptions classes found, both lists equal supported_formats."""
        ca = _make_code_analysis(classes=[
            {"name": "Scene", "methods": [], "method_details": [],
             "properties": [], "constructor": None, "class_constants": [],
             "docstring": "", "bases": [], "module": "", "source_file": "", "start_line": 1},
        ])
        input_fmts, output_fmts = _extract_input_output_formats(ca, ["OBJ", "STL"])
        assert sorted(input_fmts) == ["OBJ", "STL"]
        assert sorted(output_fmts) == ["OBJ", "STL"]


# ===========================================================================
# TC-3150: Limitations in repo_truth
# ===========================================================================

class TestLimitationsInRepoTruth:
    """TC-3150: build_repo_truth() includes limitations from source code."""

    def test_limitations_key_present(self, tmp_path):
        """build_repo_truth always has 'limitations' key, even if empty."""
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, [])
        assert "limitations" in result
        assert "values" in result["limitations"]

    def test_not_implemented_error_extracted(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class Renderer:\n"
            "    def render_ray(self):\n"
            "        raise NotImplementedError('render_ray is not supported')\n"
        )
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, [])
        texts = [lim["text"] for lim in result["limitations"]["values"]]
        assert any("render_ray" in t or "not supported" in t for t in texts)

    def test_limitations_are_deduplicated(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class A:\n"
            "    def x(self):\n"
            "        raise NotImplementedError('same message')\n"
            "class B:\n"
            "    def y(self):\n"
            "        raise NotImplementedError('same message')\n"
        )
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, [])
        texts = [lim["text"] for lim in result["limitations"]["values"]]
        # Deduplicated: each unique text appears only once
        assert len(texts) == len(set(t.lower() for t in texts))


# ===========================================================================
# TC-3150: Evidence pointers on capabilities
# ===========================================================================

class TestEvidencePointers:
    """TC-3150: _extract_capabilities() adds evidence {file, line} pointers."""

    def test_readme_capability_has_evidence(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "# My Library\n\n"
            "## Features\n\n"
            "- Load 3D meshes from OBJ files\n"
            "- Export to STL format\n"
        )
        from src.launch.workers.w2_facts_builder.code_analyzer import _extract_capabilities
        ca = _make_code_analysis()
        caps = _extract_capabilities(tmp_path, ca)
        readme_caps = [c for c in caps if c.get("source") == "readme"]
        assert readme_caps, "Should have README-sourced capabilities"
        for cap in readme_caps:
            ev = cap.get("evidence")
            assert ev is not None, f"Capability '{cap['text']}' missing evidence"
            assert "file" in ev
            assert ev.get("line", 0) > 0

    def test_docstring_capability_has_evidence(self, tmp_path):
        src = tmp_path / "scene.py"
        src.write_text(
            "class Scene:\n"
            "    \"\"\"Represents a 3D scene with meshes and lights.\"\"\"\n"
            "    pass\n"
        )
        from src.launch.workers.w2_facts_builder.code_analyzer import _extract_capabilities
        ca = {
            "api_surface": {
                "classes": [analyze_python_file(src, repo_dir=tmp_path).get("classes", [{}])[0]],
                "functions": [], "modules": [],
            },
            "code_structure": {"source_roots": [""], "public_entrypoints": [], "package_names": []},
            "constants": {}, "metadata": {},
        }
        caps = _extract_capabilities(tmp_path, ca)
        doc_caps = [c for c in caps if "docstring" in c.get("source", "")]
        assert doc_caps, "Should have docstring-sourced capabilities"
        for cap in doc_caps:
            ev = cap.get("evidence")
            assert ev is not None, f"Docstring capability '{cap['text']}' missing evidence"
            assert "file" in ev

    def test_repo_truth_capabilities_have_evidence(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            "## Features\n\n- Convert files to PDF\n"
        )
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, [])
        caps = result.get("capabilities", {}).get("values", [])
        for cap in caps:
            if cap.get("source") == "readme":
                assert "evidence" in cap, f"README capability '{cap['text']}' missing evidence"
                break


# ===========================================================================
# TC-3150: Compact API index
# ===========================================================================

class TestApiIndex:
    """TC-3150: build_api_index() creates compact index from api_inventory."""

    def _make_inventory(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text(
            "class Scene:\n"
            "    \"\"\"Represents a 3D scene. Can hold meshes.\"\"\"\n"
            "    def open(self, path: str): pass\n"
            "    def save(self, path: str): pass\n"
            "    @property\n"
            "    def name(self): return ''\n"
            "\n"
            "def load_scene(path: str):\n"
            "    \"\"\"Load a scene from disk. Returns Scene.\"\"\"\n"
            "    pass\n"
        )
        py_result = analyze_python_file(src, repo_dir=tmp_path)
        code_analysis = {
            "api_surface": {
                "classes": py_result.get("classes", []),
                "functions": py_result.get("functions", []),
                "modules": [],
                "function_details": py_result.get("function_details", []),
            },
            "code_structure": {"source_roots": [""], "public_entrypoints": [], "package_names": ["testpkg"]},
            "constants": {}, "metadata": {},
        }
        inv = build_api_inventory(code_analysis, tmp_path, [""])
        inv["package_name"] = "testpkg"
        return inv

    def test_compact_index_structure(self, tmp_path):
        inv = self._make_inventory(tmp_path)
        idx = build_api_index(inv)
        assert "package_name" in idx
        assert "class_index" in idx
        assert "function_index" in idx
        assert "symbol_count" in idx

    def test_class_index_has_counts(self, tmp_path):
        inv = self._make_inventory(tmp_path)
        idx = build_api_index(inv)
        cls_entries = idx.get("class_index", [])
        assert cls_entries
        scene = next((c for c in cls_entries if c["name"] == "Scene"), None)
        assert scene is not None
        assert scene["method_count"] >= 2  # open + save
        assert scene["property_count"] >= 1  # name

    def test_docstring_snippet_in_class_index(self, tmp_path):
        inv = self._make_inventory(tmp_path)
        idx = build_api_index(inv)
        scene = next((c for c in idx.get("class_index", []) if c["name"] == "Scene"), None)
        assert scene is not None
        snippet = scene.get("docstring_snippet", "")
        assert snippet == "Represents a 3D scene."

    def test_symbol_count_matches_totals(self, tmp_path):
        inv = self._make_inventory(tmp_path)
        idx = build_api_index(inv)
        expected = len(idx["class_index"]) + len(idx["function_index"])
        assert idx["symbol_count"] == expected

    def test_deterministic_output(self, tmp_path):
        inv = self._make_inventory(tmp_path)
        idx1 = build_api_index(inv)
        idx2 = build_api_index(inv)
        assert json.dumps(idx1, sort_keys=True) == json.dumps(idx2, sort_keys=True)


# ===========================================================================
# TC-3150: repo_truth new fields present
# ===========================================================================

class TestRepoTruthNewFields:
    """TC-3150: build_repo_truth() includes all new TC-3150 fields."""

    def test_input_formats_field_present(self, tmp_path):
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, [])
        assert "input_formats" in result
        assert "values" in result["input_formats"]

    def test_output_formats_field_present(self, tmp_path):
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, [])
        assert "output_formats" in result
        assert "values" in result["output_formats"]

    def test_conversion_pairs_field_present(self, tmp_path):
        ca = _make_code_analysis()
        result = build_repo_truth(tmp_path, {}, ca, [])
        assert "conversion_pairs" in result
        assert "values" in result["conversion_pairs"]

    def test_new_fields_deterministic(self, tmp_path):
        """Verify new repo_truth fields are deterministic across two runs."""
        ca = _make_code_analysis()
        r1 = build_repo_truth(tmp_path, {}, ca, [])
        r2 = build_repo_truth(tmp_path, {}, ca, [])
        assert json.dumps(r1.get("input_formats"), sort_keys=True) == json.dumps(r2.get("input_formats"), sort_keys=True)
        assert json.dumps(r1.get("conversion_pairs"), sort_keys=True) == json.dumps(r2.get("conversion_pairs"), sort_keys=True)
