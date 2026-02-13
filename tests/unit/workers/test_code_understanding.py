"""Unit tests for TC-1410: LLM-powered code understanding.

Tests cover:
- Offline fallback (AST-only profiles)
- LLM path with mocked responses
- Empty API surface handling
- File identification and truncation
- Schema version and metadata

Spec: specs/07_code_analysis_and_enrichment.md
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.launch.workers.w2_facts_builder.code_understanding import (
    _build_offline_understanding,
    _identify_public_api_files,
    _parse_llm_response,
    _supplement_stub_usage,
    _truncate_source,
    build_code_understanding,
)


@pytest.fixture
def sample_code_analysis():
    """Minimal code_analysis dict mimicking code_analyzer output."""
    return {
        "api_surface": {
            "classes": ["DataProcessor", "Config", "Result"],
            "functions": ["DataProcessor.run", "DataProcessor.load", "Config.from_file"],
            "modules": ["mylib.core"],
        },
        "code_structure": {
            "source_roots": ["src/"],
            "public_entrypoints": ["__init__.py"],
            "package_names": ["my-library"],
        },
        "constants": {
            "version": "1.0.0",
            "supported_formats": ["CSV", "JSON"],
        },
        "positioning": {
            "tagline": "My Library for Python",
            "short_description": "A Python library for data processing.",
        },
        "metadata": {
            "files_analyzed": 10,
            "parsing_failures": 0,
        },
    }


@pytest.fixture
def repo_with_source(tmp_path):
    """Create a temp repo with Python source files."""
    src_dir = tmp_path / "src" / "mylib" / "core"
    src_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text(
        '"""My Library for Python."""\n'
        "from .processor import DataProcessor\n"
        "from .config import Config\n"
    )

    (src_dir / "processor.py").write_text(
        "class DataProcessor:\n"
        '    """Processes input data and produces results."""\n'
        "\n"
        "    @staticmethod\n"
        "    def load(path: str) -> 'DataProcessor':\n"
        '        """Load data from a file."""\n'
        "        pass\n"
        "\n"
        "    def run(self, output_path: str) -> None:\n"
        '        """Run the processing pipeline."""\n'
        "        pass\n"
        "\n"
        "    @property\n"
        "    def results(self):\n"
        '        """List of processing results."""\n'
        "        return []\n"
    )

    (src_dir / "config.py").write_text(
        "class Config:\n"
        '    """Configuration for the data processor."""\n'
        "\n"
        "    @classmethod\n"
        "    def from_file(cls, path: str) -> 'Config':\n"
        '        """Load config from a YAML or JSON file."""\n'
        "        return cls()\n"
    )

    return tmp_path


class TestTruncateSource:
    """Test source content truncation."""

    def test_short_content_unchanged(self):
        content = "class Foo:\n    pass\n"
        assert _truncate_source(content) == content

    def test_long_content_truncated(self):
        content = "x = 1\n" * 1000  # ~6000 chars
        result = _truncate_source(content, max_chars=100)
        assert len(result) <= 120  # some slack for truncation marker
        assert result.endswith("# ... (truncated)")

    def test_truncation_at_line_boundary(self):
        content = "a" * 50 + "\n" + "b" * 50 + "\n" + "c" * 50 + "\n"
        result = _truncate_source(content, max_chars=80)
        # Should cut at a newline, not mid-line
        assert "# ... (truncated)" in result


class TestIdentifyPublicApiFiles:
    """Test public API file identification."""

    def test_finds_source_files(self, repo_with_source, sample_code_analysis):
        files = _identify_public_api_files(sample_code_analysis, repo_with_source)
        paths = [str(f.relative_to(repo_with_source)) for f in files]
        # Should find the processor.py file (has DataProcessor class)
        assert any("processor" in p for p in paths)

    def test_skips_test_directories(self, tmp_path, sample_code_analysis):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_proc.py").write_text("class DataProcessor:\n    pass\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "proc.py").write_text("class DataProcessor:\n    pass\n")

        files = _identify_public_api_files(sample_code_analysis, tmp_path)
        paths = [str(f.relative_to(tmp_path)) for f in files]
        assert not any("tests" in p for p in paths)

    def test_empty_repo(self, tmp_path, sample_code_analysis):
        files = _identify_public_api_files(sample_code_analysis, tmp_path)
        assert files == []


class TestParseLlmResponse:
    """Test LLM response parsing."""

    def test_plain_json(self):
        content = '{"product_summary": "A library", "core_concepts": []}'
        result = _parse_llm_response(content)
        assert result["product_summary"] == "A library"

    def test_json_with_fences(self):
        content = '```json\n{"product_summary": "A library"}\n```'
        result = _parse_llm_response(content)
        assert result["product_summary"] == "A library"

    def test_invalid_json_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _parse_llm_response("not json")


class TestBuildOfflineUnderstanding:
    """Test offline (AST-only) code understanding."""

    def test_produces_valid_structure(self, sample_code_analysis, tmp_path):
        result = _build_offline_understanding(
            sample_code_analysis, "TestProduct", tmp_path
        )

        assert result["schema_version"] == "1.0.0"
        assert result["product_name"] == "TestProduct"
        assert isinstance(result["product_summary"], str)
        assert len(result["product_summary"]) > 0
        assert isinstance(result["core_concepts"], list)
        assert isinstance(result["class_profiles"], list)
        assert isinstance(result["usage_workflows"], list)
        assert result["metadata"]["source"] == "offline_ast"

    def test_class_profiles_from_ast(self, sample_code_analysis, tmp_path):
        result = _build_offline_understanding(
            sample_code_analysis, "TestProduct", tmp_path
        )

        class_names = [cp["name"] for cp in result["class_profiles"]]
        assert "DataProcessor" in class_names
        assert "Config" in class_names

    def test_methods_grouped_by_class(self, sample_code_analysis, tmp_path):
        result = _build_offline_understanding(
            sample_code_analysis, "TestProduct", tmp_path
        )

        proc_profile = next(
            cp for cp in result["class_profiles"] if cp["name"] == "DataProcessor"
        )
        method_names = [m["name"] for m in proc_profile["key_methods"]]
        assert "run" in method_names or "load" in method_names

    def test_empty_api_surface(self, tmp_path):
        code_analysis = {
            "api_surface": {"classes": [], "functions": [], "modules": []},
            "constants": {},
            "positioning": {},
        }
        result = _build_offline_understanding(code_analysis, "EmptyLib", tmp_path)
        assert result["class_profiles"] == []
        assert result["core_concepts"] == []


class TestBuildCodeUnderstanding:
    """Test main build_code_understanding function."""

    def test_empty_api_returns_minimal(self, tmp_path):
        code_analysis = {
            "api_surface": {"classes": [], "functions": [], "modules": []},
            "constants": {},
            "positioning": {},
            "metadata": {"files_analyzed": 0, "parsing_failures": 0},
        }

        result = build_code_understanding(
            code_analysis, tmp_path, "EmptyLib", llm_client=None
        )

        assert result["schema_version"] == "1.0.0"
        assert result["metadata"]["source"] == "empty"
        assert result["class_profiles"] == []

    def test_offline_without_llm(self, sample_code_analysis, repo_with_source):
        result = build_code_understanding(
            sample_code_analysis, repo_with_source, "TestProduct", llm_client=None
        )

        assert result["schema_version"] == "1.0.0"
        assert result["metadata"]["source"] == "offline_ast"
        assert len(result["class_profiles"]) > 0

    def test_llm_path_success(self, sample_code_analysis, repo_with_source):
        """Test LLM path with mocked client. Testing: mocked"""
        mock_client = MagicMock()
        mock_client.model = "test-model"
        mock_client.chat_completion.return_value = {
            "content": json.dumps({
                "product_summary": "A library for data processing",
                "core_concepts": [
                    {
                        "concept": "DataProcessor",
                        "explanation": "Entry point for processing pipelines",
                        "api": ["DataProcessor"],
                        "level": "beginner",
                    }
                ],
                "class_profiles": [
                    {
                        "name": "DataProcessor",
                        "module": "mylib.core",
                        "purpose": "Processes input data",
                        "key_methods": [
                            {
                                "name": "load",
                                "signature": "load(path: str) -> DataProcessor",
                                "purpose": "Load data from a file",
                                "example": "proc = DataProcessor.load('data.csv')",
                            }
                        ],
                        "relationships": ["Config"],
                        "typical_usage": "proc = DataProcessor.load('data.csv')",
                    }
                ],
                "usage_workflows": [],
                "api_relationships": {"DataProcessor": ["Config"]},
            }),
            "usage": {"total_tokens": 500},
        }

        result = build_code_understanding(
            sample_code_analysis, repo_with_source, "TestProduct", llm_client=mock_client
        )

        assert result["metadata"]["source"] == "llm"
        assert result["product_summary"] == "A library for data processing"
        assert len(result["class_profiles"]) == 1
        assert result["class_profiles"][0]["name"] == "DataProcessor"
        mock_client.chat_completion.assert_called_once()

    def test_llm_failure_falls_back_to_offline(self, sample_code_analysis, repo_with_source):
        """Test that LLM failure gracefully falls back to offline. Testing: mocked"""
        mock_client = MagicMock()
        mock_client.model = "test-model"
        mock_client.chat_completion.side_effect = Exception("LLM unavailable")

        result = build_code_understanding(
            sample_code_analysis, repo_with_source, "TestProduct", llm_client=mock_client
        )

        assert result["metadata"]["source"] == "offline_ast"
        assert len(result["class_profiles"]) > 0

    def test_llm_invalid_json_falls_back(self, sample_code_analysis, repo_with_source):
        """Test that invalid LLM JSON falls back to offline. Testing: mocked"""
        mock_client = MagicMock()
        mock_client.model = "test-model"
        mock_client.chat_completion.return_value = {
            "content": "this is not valid json at all",
            "usage": {},
        }

        result = build_code_understanding(
            sample_code_analysis, repo_with_source, "TestProduct", llm_client=mock_client
        )

        assert result["metadata"]["source"] == "offline_ast"


class TestEnrichedOfflineUnderstanding:
    """TC-1503: Tests for enriched offline code understanding with docstrings/signatures."""

    @pytest.fixture
    def enriched_code_analysis(self):
        """Code analysis with enriched dict-format classes (TC-1501 output)."""
        return {
            "api_surface": {
                "classes": [
                    {
                        "name": "DataProcessor",
                        "docstring": "Processes input data and produces results.",
                        "bases": ["BaseProcessor"],
                        "module": "processor",
                        "methods": ["load", "run", "save"],
                        "method_details": [
                            {
                                "name": "load",
                                "signature": "load(path: str)",
                                "docstring": "Load data from a file.",
                                "return_type": "DataProcessor",
                            },
                            {
                                "name": "run",
                                "signature": "run()",
                                "docstring": "Run the processing pipeline.",
                                "return_type": "",
                            },
                            {
                                "name": "save",
                                "signature": "save(output_path: str)",
                                "docstring": "Save processed data to disk.",
                                "return_type": "",
                            },
                        ],
                    },
                    {
                        "name": "Config",
                        "docstring": "Configuration for the data processor.",
                        "bases": [],
                        "module": "config",
                        "methods": ["from_file"],
                        "method_details": [
                            {
                                "name": "from_file",
                                "signature": "from_file(path: str)",
                                "docstring": "Load config from a YAML or JSON file.",
                                "return_type": "Config",
                            },
                        ],
                    },
                ],
                "functions": ["DataProcessor.load", "DataProcessor.run", "DataProcessor.save", "Config.from_file"],
                "modules": ["mylib.core"],
            },
            "constants": {
                "version": "1.0.0",
                "supported_formats": ["CSV", "JSON"],
            },
            "positioning": {
                "tagline": "My Library for Python",
                "short_description": "A Python library for data processing.",
            },
        }

    def test_offline_uses_docstrings_for_purpose(self, enriched_code_analysis, tmp_path):
        """Verify docstrings flow into class purpose."""
        result = _build_offline_understanding(enriched_code_analysis, "TestProduct", tmp_path)
        proc_profile = next(cp for cp in result["class_profiles"] if cp["name"] == "DataProcessor")
        assert "Processes input data" in proc_profile["purpose"]

    def test_offline_uses_bases_for_relationships(self, enriched_code_analysis, tmp_path):
        """Verify base classes populate relationships."""
        result = _build_offline_understanding(enriched_code_analysis, "TestProduct", tmp_path)
        proc_profile = next(cp for cp in result["class_profiles"] if cp["name"] == "DataProcessor")
        assert "BaseProcessor" in proc_profile["relationships"]

    def test_offline_generates_code_examples(self, enriched_code_analysis, tmp_path):
        """Verify typical_usage is generated from method names."""
        result = _build_offline_understanding(enriched_code_analysis, "TestProduct", tmp_path)
        proc_profile = next(cp for cp in result["class_profiles"] if cp["name"] == "DataProcessor")
        assert proc_profile["typical_usage"] != ""
        assert "DataProcessor()" in proc_profile["typical_usage"]

    def test_offline_generates_basic_usage_workflow(self, enriched_code_analysis, tmp_path):
        """Verify load/save pattern generates a Basic Usage workflow."""
        result = _build_offline_understanding(enriched_code_analysis, "TestProduct", tmp_path)
        workflow_names = [w["name"] for w in result["usage_workflows"]]
        assert "Basic Usage" in workflow_names
        basic = next(w for w in result["usage_workflows"] if w["name"] == "Basic Usage")
        assert len(basic["steps"]) >= 2
        assert "DataProcessor" in basic["api_involved"]

    def test_offline_api_relationships_from_bases(self, enriched_code_analysis, tmp_path):
        """Verify api_relationships built from base classes."""
        result = _build_offline_understanding(enriched_code_analysis, "TestProduct", tmp_path)
        assert "DataProcessor" in result["api_relationships"]
        assert "BaseProcessor" in result["api_relationships"]["DataProcessor"]

    def test_offline_method_details_in_key_methods(self, enriched_code_analysis, tmp_path):
        """Verify method signatures and docstrings appear in key_methods."""
        result = _build_offline_understanding(enriched_code_analysis, "TestProduct", tmp_path)
        proc_profile = next(cp for cp in result["class_profiles"] if cp["name"] == "DataProcessor")
        load_method = next(m for m in proc_profile["key_methods"] if m["name"] == "load")
        assert "path" in load_method["signature"]
        assert "Load data" in load_method["purpose"]


class TestTC1513SupplementStubUsage:
    """TC-1513: Tests for _supplement_stub_usage post-LLM safety net."""

    def test_stub_usage_replaced(self):
        """Stub typical_usage is replaced with AST-generated code."""
        result = {
            "class_profiles": [
                {
                    "name": "Scene",
                    "key_methods": [],
                    "typical_usage": "# See source code for full usage",
                },
            ],
        }
        code_analysis = {
            "api_surface": {
                "classes": [
                    {"name": "Scene", "methods": ["open", "save", "render", "_internal"]},
                ],
            },
        }

        _supplement_stub_usage(result, code_analysis)

        usage = result["class_profiles"][0]["typical_usage"]
        assert "obj = Scene()" in usage
        assert "obj.open()" in usage
        assert "obj.save()" in usage
        assert "obj.render()" in usage
        assert "_internal" not in usage  # private methods excluded

    def test_supplement_uses_key_methods(self):
        """When code_analysis has no methods, uses LLM's key_methods."""
        result = {
            "class_profiles": [
                {
                    "name": "Mesh",
                    "key_methods": [
                        {"name": "create_polygon", "purpose": "Create a polygon"},
                        {"name": "triangulate", "purpose": "Triangulate mesh"},
                    ],
                    "typical_usage": "",  # empty = should be supplemented
                },
            ],
        }
        code_analysis = {
            "api_surface": {
                "classes": [],  # no AST data
            },
        }

        _supplement_stub_usage(result, code_analysis)

        usage = result["class_profiles"][0]["typical_usage"]
        assert "obj = Mesh()" in usage
        assert "obj.create_polygon()" in usage
        assert "obj.triangulate()" in usage

    def test_real_usage_not_overwritten(self):
        """Real typical_usage is preserved, not overwritten."""
        real_code = "scene = Scene()\nscene.open('test.fbx')\nscene.save('out.obj')"
        result = {
            "class_profiles": [
                {
                    "name": "Scene",
                    "key_methods": [{"name": "open"}, {"name": "save"}],
                    "typical_usage": real_code,
                },
            ],
        }
        code_analysis = {
            "api_surface": {
                "classes": [
                    {"name": "Scene", "methods": ["open", "save"]},
                ],
            },
        }

        _supplement_stub_usage(result, code_analysis)

        assert result["class_profiles"][0]["typical_usage"] == real_code


class TestUseCaseExtraction:
    """Test use case and real-world applications extraction for TC-1618."""

    def test_llm_response_with_use_cases(self):
        """Test parsing LLM response with use_cases array.

        TC-1618: LLM responses should include use_cases for marketing content.
        """
        from src.launch.workers.w2_facts_builder.code_understanding import (
            _parse_llm_response,
        )

        llm_response = """
{
    "product_summary": "A library for 3D file processing",
    "core_concepts": [],
    "class_profiles": [],
    "usage_workflows": [],
    "api_relationships": {},
    "use_cases": [
        {
            "scenario": "CAD file conversion",
            "description": "Convert CAD files between formats for design workflows",
            "benefit": "Automate format conversion",
            "example_domain": "Architecture"
        },
        {
            "scenario": "Game asset pipeline",
            "description": "Transform game assets from DCC tools to runtime formats",
            "benefit": "Streamline content pipelines",
            "example_domain": "Game development"
        }
    ],
    "real_world_applications": []
}
"""

        result = _parse_llm_response(llm_response)

        # Should have use_cases key
        assert "use_cases" in result
        assert len(result["use_cases"]) == 2

        # First use case
        uc1 = result["use_cases"][0]
        assert uc1["scenario"] == "CAD file conversion"
        assert "Convert CAD files" in uc1["description"]
        assert uc1["benefit"] == "Automate format conversion"
        assert uc1["example_domain"] == "Architecture"

    def test_llm_response_with_real_world_applications(self):
        """Test parsing LLM response with real_world_applications array.

        TC-1618: LLM responses should include industry-specific applications.
        """
        from src.launch.workers.w2_facts_builder.code_understanding import (
            _parse_llm_response,
        )

        llm_response = """
{
    "product_summary": "A library for 3D processing",
    "core_concepts": [],
    "class_profiles": [],
    "usage_workflows": [],
    "api_relationships": {},
    "use_cases": [],
    "real_world_applications": [
        {
            "industry": "Architecture",
            "use_case": "Building information modeling",
            "value_proposition": "Convert BIM models for visualization"
        },
        {
            "industry": "Manufacturing",
            "use_case": "Product design collaboration",
            "value_proposition": "Share designs across CAD systems"
        }
    ]
}
"""

        result = _parse_llm_response(llm_response)

        # Should have real_world_applications key
        assert "real_world_applications" in result
        assert len(result["real_world_applications"]) == 2

        # First application
        app1 = result["real_world_applications"][0]
        assert app1["industry"] == "Architecture"
        assert "Building information modeling" in app1["use_case"]
        assert "Convert BIM models" in app1["value_proposition"]
