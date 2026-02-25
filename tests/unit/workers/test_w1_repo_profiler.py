"""Tests for TC-2437 + TC-2448: W1 repo profiler."""
from __future__ import annotations
import pytest
from launch.workers.w1_repo_scout.repo_profiler import (
    SOURCE_TYPE_WEIGHTS,
    _compute_api_signals,
    _compute_build_signals,
    _compute_confidence_and_warnings,
    _compute_docs_signals,
    _compute_examples_signals,
    _compute_formats_signals,
    _compute_language_breakdown,
    build_repo_profile_artifact,
    compute_api_surface,
    compute_docs_depth,
    score_citation_quality,
)


class TestComputeDocsDepth:
    def test_compute_docs_depth_empty(self):
        assert compute_docs_depth([], []) == 0

    def test_compute_docs_depth_with_files(self):
        assert compute_docs_depth(["a", "b"], ["c"]) == 3

    def test_compute_docs_depth_only_docs(self):
        assert compute_docs_depth(["readme.md", "guide.md", "api.md"], []) == 3

    def test_compute_docs_depth_only_examples(self):
        assert compute_docs_depth([], ["ex1.py", "ex2.py"]) == 2

    def test_compute_docs_depth_large_counts(self):
        docs = [f"doc_{i}.md" for i in range(60)]
        examples = [f"ex_{i}.py" for i in range(15)]
        assert compute_docs_depth(docs, examples) == 75


class TestComputeApiSurface:
    def test_compute_api_surface_excludes_test_files(self):
        paths = ["test_foo.py", "foo.py", "spec_bar.py", "baz.cs"]
        result = compute_api_surface(paths)
        assert result == 2

    def test_compute_api_surface_excludes_non_api_extensions(self):
        paths = ["readme.txt", "docs.md", "notes.yaml"]
        assert compute_api_surface(paths) == 0

    def test_compute_api_surface_includes_all_api_extensions(self):
        paths = ["module.py", "Module.cs", "Main.java", "index.ts", "main.go", "lib.rs"]
        assert compute_api_surface(paths) == 6

    def test_compute_api_surface_excludes_mock_files(self):
        paths = ["mock_service.py", "fixture_data.py", "real_service.py"]
        assert compute_api_surface(paths) == 1

    def test_compute_api_surface_empty(self):
        assert compute_api_surface([]) == 0

    def test_compute_api_surface_case_insensitive_test_marker(self):
        paths = ["TEST_utils.py", "SPEC_runner.py", "Helper.py"]
        assert compute_api_surface(paths) == 1


class TestScoreCitationQuality:
    def test_score_citation_quality_empty_returns_zero(self):
        assert score_citation_quality([], SOURCE_TYPE_WEIGHTS) == 0.0

    def test_score_citation_quality_readme_weight(self):
        citations = [{"source_type": "readme"}]
        assert score_citation_quality(citations, SOURCE_TYPE_WEIGHTS) == 0.6

    def test_score_citation_quality_api_doc_weight(self):
        citations = [{"source_type": "api_doc"}]
        assert score_citation_quality(citations, SOURCE_TYPE_WEIGHTS) == 0.9

    def test_score_citation_quality_returns_max_weight(self):
        citations = [
            {"source_type": "readme"},
            {"source_type": "api_doc"},
            {"source_type": "generic_doc"},
        ]
        assert score_citation_quality(citations, SOURCE_TYPE_WEIGHTS) == 0.9

    def test_score_citation_quality_infers_from_path(self):
        citations = ["examples/foo.py"]
        result = score_citation_quality(citations, SOURCE_TYPE_WEIGHTS)
        assert result == 0.85

    def test_score_citation_quality_infers_readme_from_path(self):
        citations = ["docs/README.md"]
        result = score_citation_quality(citations, SOURCE_TYPE_WEIGHTS)
        assert result == 0.6

    def test_score_citation_quality_unknown_source_type(self):
        citations = [{"source_type": "unknown"}]
        assert score_citation_quality(citations, SOURCE_TYPE_WEIGHTS) == 0.3

    def test_score_citation_quality_missing_source_type_key(self):
        citations = [{"file": "something.py"}]
        result = score_citation_quality(citations, SOURCE_TYPE_WEIGHTS)
        assert result == 0.3


# ---------------------------------------------------------------------------
# TC-2448: New signal helper tests
# ---------------------------------------------------------------------------

class TestDocsSignals:
    def _call(self, paths, doc_entrypoints=None, doc_details=None, docs_depth=0):
        return _compute_docs_signals(
            paths,
            doc_entrypoints or [],
            doc_details or [],
            docs_depth,
        )

    def test_has_readme_detected(self):
        result = self._call(["README.md", "src/main.py"])
        assert result["has_readme"] is True

    def test_has_readme_case_insensitive(self):
        result = self._call(["readme.rst", "src/lib.py"])
        assert result["has_readme"] is True

    def test_has_readme_subdirectory(self):
        result = self._call(["subdir/README.md"])
        assert result["has_readme"] is True

    def test_no_readme_detected(self):
        result = self._call(["docs/guide.md", "src/main.py"])
        assert result["has_readme"] is False

    def test_has_docs_folder_detected(self):
        result = self._call(["docs/guide.md", "src/main.py"])
        assert result["has_docs_folder"] is True

    def test_has_docs_folder_nested(self):
        result = self._call(["project/docs/api.md"])
        assert result["has_docs_folder"] is True

    def test_no_docs_folder(self):
        result = self._call(["README.md", "src/main.py"])
        assert result["has_docs_folder"] is False

    def test_markdown_file_count(self):
        paths = ["README.md", "docs/guide.md", "docs/api.markdown", "src/main.py"]
        result = self._call(paths)
        assert result["markdown_file_count"] == 3

    def test_markdown_count_zero(self):
        result = self._call(["src/main.py", "setup.py"])
        assert result["markdown_file_count"] == 0

    def test_readme_size_from_details(self):
        details = [
            {"path": "README.md", "doc_type": "readme", "file_size_bytes": 4200},
            {"path": "docs/guide.md", "doc_type": "guide", "file_size_bytes": 1000},
        ]
        result = self._call(["README.md"], doc_details=details)
        assert result["readme_size_bytes"] == 4200

    def test_readme_size_zero_when_no_details(self):
        result = self._call(["README.md"])
        assert result["readme_size_bytes"] == 0

    def test_docs_depth_score_propagated(self):
        result = self._call(["README.md"], docs_depth=42)
        assert result["docs_depth_score"] == 42


class TestExamplesSignals:
    def _call(self, paths, example_paths=None):
        return _compute_examples_signals(paths, example_paths or [])

    def test_has_examples_folder(self):
        result = self._call(["examples/hello.py", "src/main.py"])
        assert result["has_examples_folder"] is True

    def test_has_samples_folder(self):
        result = self._call(["samples/demo.py"])
        assert result["has_examples_folder"] is True

    def test_nested_examples_folder(self):
        result = self._call(["project/examples/foo.py"])
        assert result["has_examples_folder"] is True

    def test_no_examples_folder(self):
        result = self._call(["src/main.py", "docs/guide.md"])
        assert result["has_examples_folder"] is False

    def test_example_file_count(self):
        result = self._call([], ["ex1.py", "ex2.cs", "ex3.py"])
        assert result["example_file_count"] == 3

    def test_code_extensions_sorted(self):
        result = self._call([], ["examples/hello.py", "examples/convert.cs"])
        assert result["code_extensions"] == [".cs", ".py"]

    def test_code_extensions_empty_when_no_examples(self):
        result = self._call([])
        assert result["code_extensions"] == []

    def test_code_extensions_deduplicated(self):
        result = self._call([], ["a.py", "b.py", "c.py"])
        assert result["code_extensions"] == [".py"]


class TestApiSignals:
    def _call(self, paths, api_surface=0):
        return _compute_api_signals(paths, api_surface)

    def test_has_type_stubs(self):
        result = self._call(["src/module.pyi", "src/module.py"])
        assert result["has_type_stubs"] is True

    def test_no_type_stubs(self):
        result = self._call(["src/module.py", "docs/guide.md"])
        assert result["has_type_stubs"] is False

    def test_has_openapi_spec_yaml(self):
        result = self._call(["docs/openapi.yaml"])
        assert result["has_openapi_spec"] is True

    def test_has_openapi_spec_json(self):
        result = self._call(["api/swagger.json"])
        assert result["has_openapi_spec"] is True

    def test_no_openapi_spec(self):
        result = self._call(["src/main.py", "docs/guide.md"])
        assert result["has_openapi_spec"] is False

    def test_has_api_docs_folder(self):
        result = self._call(["api/reference.md"])
        assert result["has_api_docs_folder"] is True

    def test_has_apidocs_folder(self):
        result = self._call(["project/apidocs/index.html"])
        assert result["has_api_docs_folder"] is True

    def test_no_api_docs_folder(self):
        result = self._call(["src/main.py", "docs/guide.md"])
        assert result["has_api_docs_folder"] is False

    def test_api_surface_count_propagated(self):
        result = self._call(["src/main.py"], api_surface=7)
        assert result["api_surface_count"] == 7

    def test_empty_paths(self):
        result = self._call([])
        assert result["has_type_stubs"] is False
        assert result["has_openapi_spec"] is False
        assert result["has_api_docs_folder"] is False


class TestBuildSignals:
    def _call(self, paths, build_systems=None):
        return _compute_build_signals(paths, build_systems or [])

    def test_detected_manifests_pyproject(self):
        result = self._call(["pyproject.toml", "src/main.py"])
        assert "pyproject.toml" in result["detected_manifests"]

    def test_detected_manifests_package_json(self):
        result = self._call(["package.json", "index.js"])
        assert "package.json" in result["detected_manifests"]

    def test_detected_manifests_sorted(self):
        result = self._call(["pyproject.toml", "Makefile", "requirements.txt"])
        assert result["detected_manifests"] == sorted(result["detected_manifests"])

    def test_no_manifests_found(self):
        result = self._call(["src/main.py", "README.md"])
        assert result["detected_manifests"] == []

    def test_has_ci_github_actions(self):
        result = self._call([".github/workflows/ci.yml"])
        assert result["has_ci"] is True

    def test_has_ci_travis(self):
        result = self._call([".travis.yml"])
        assert result["has_ci"] is True

    def test_has_ci_circleci(self):
        result = self._call([".circleci/config.yml"])
        assert result["has_ci"] is True

    def test_no_ci(self):
        result = self._call(["src/main.py", "README.md"])
        assert result["has_ci"] is False

    def test_build_systems_propagated(self):
        result = self._call([], build_systems=["msbuild", "cmake"])
        assert result["build_systems"] == ["msbuild", "cmake"]


class TestFormatsSignals:
    def _call(self, paths):
        return _compute_formats_signals(paths)

    def test_domain_extensions_extracted(self):
        result = self._call(["model.fbx", "scene.obj", "src/main.py"])
        assert ".fbx" in result["domain_extensions"]
        assert ".obj" in result["domain_extensions"]

    def test_code_extensions_excluded(self):
        result = self._call(["src/main.py", "lib.cs"])
        assert ".py" not in result["domain_extensions"]
        assert ".cs" not in result["domain_extensions"]

    def test_doc_extensions_excluded(self):
        result = self._call(["README.md", "config.yaml", "data.json"])
        assert ".md" not in result["domain_extensions"]
        assert ".yaml" not in result["domain_extensions"]
        assert ".json" not in result["domain_extensions"]

    def test_binary_asset_count(self):
        result = self._call(["model.fbx", "scene.obj", "texture.fbx"])
        assert result["binary_asset_count"] == 3

    def test_domain_extensions_sorted(self):
        result = self._call(["b.xyz", "a.abc", "c.fbx"])
        assert result["domain_extensions"] == sorted(result["domain_extensions"])

    def test_empty_paths(self):
        result = self._call([])
        assert result["binary_asset_count"] == 0
        assert result["domain_extensions"] == []


class TestLanguageBreakdown:
    def test_counts_by_extension(self):
        paths = ["a.py", "b.py", "c.cs"]
        result = _compute_language_breakdown(paths)
        assert result["py"] == 2
        assert result["cs"] == 1

    def test_empty_paths(self):
        assert _compute_language_breakdown([]) == {}

    def test_no_extension_skipped(self):
        result = _compute_language_breakdown(["Makefile", "Dockerfile"])
        assert result == {}

    def test_top_15_limit(self):
        paths = [f"file_{i}.ext{i}" for i in range(20)]
        result = _compute_language_breakdown(paths)
        assert len(result) <= 15


class TestConfidenceAndWarnings:
    def _call(self, paths, doc_entrypoints=None, example_paths=None):
        return _compute_confidence_and_warnings(
            paths,
            doc_entrypoints or [],
            example_paths or [],
        )

    def test_no_paths_gives_very_low_confidence(self):
        confidence, warnings = self._call([])
        assert confidence < 0.3
        assert "no_paths" in warnings

    def test_no_readme_docks_confidence(self):
        paths = ["docs/guide.md", "src/main.py"]
        c_with_readme, _ = self._call(["README.md"] + paths)
        c_without_readme, warnings = self._call(paths)
        assert c_without_readme < c_with_readme
        assert "no_readme" in warnings

    def test_no_docs_adds_warning(self):
        _, warnings = self._call(["README.md"], doc_entrypoints=[])
        assert "no_docs" in warnings

    def test_no_examples_adds_warning(self):
        _, warnings = self._call(["README.md"], example_paths=[])
        assert "no_examples" in warnings

    def test_rich_inventory_high_confidence(self):
        paths = ["README.md"] + [f"docs/doc_{i}.md" for i in range(10)] + \
                [f"examples/ex_{i}.py" for i in range(5)]
        doc_entrypoints = [f"docs/doc_{i}.md" for i in range(10)]
        example_paths = [f"examples/ex_{i}.py" for i in range(5)]
        confidence, warnings = self._call(paths, doc_entrypoints, example_paths)
        assert confidence >= 0.7
        # Should not have no_readme or no_docs warnings
        assert "no_readme" not in warnings
        assert "no_docs" not in warnings

    def test_warnings_are_sorted(self):
        _, warnings = self._call([])
        assert warnings == sorted(warnings)

    def test_confidence_clamped_to_one(self):
        paths = ["README.md"] + [f"file_{i}.py" for i in range(50)]
        confidence, _ = self._call(paths, ["README.md"] * 10, ["ex.py"] * 10)
        assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# Updated TestBuildRepoProfileArtifact (schema 2.0)
# ---------------------------------------------------------------------------

class TestBuildRepoProfileArtifact:
    def _rich_inventory(self):
        return {
            "paths": [f"src/module_{i}.py" for i in range(20)],
            "doc_entrypoints": [f"docs/doc_{i}.md" for i in range(45)],
            "example_paths": [f"examples/ex_{i}.py" for i in range(11)],
            "repo_profile": {
                "primary_languages": ["Python", "C#"],
                "build_systems": ["setuptools"],
            },
        }

    def test_build_repo_profile_quality_tier_rich(self):
        inv = self._rich_inventory()
        result = build_repo_profile_artifact(inv)
        assert result["quality_tier"] == "rich"

    def test_build_repo_profile_quality_tier_standard(self):
        inv = {
            "paths": [],
            "doc_entrypoints": [f"doc_{i}.md" for i in range(13)],
            "example_paths": ["ex1.py", "ex2.py"],
            "repo_profile": {},
        }
        result = build_repo_profile_artifact(inv)
        assert result["quality_tier"] == "standard"

    def test_build_repo_profile_quality_tier_standard_via_examples(self):
        inv = {
            "paths": [],
            "doc_entrypoints": ["a.md", "b.md", "c.md"],
            "example_paths": ["e1.py", "e2.py", "e3.py", "e4.py"],
            "repo_profile": {},
        }
        result = build_repo_profile_artifact(inv)
        assert result["quality_tier"] == "standard"

    def test_build_repo_profile_quality_tier_minimal(self):
        inv = {
            "paths": [],
            "doc_entrypoints": ["a.md", "b.md", "c.md"],
            "example_paths": ["ex1.py", "ex2.py"],
            "repo_profile": {},
        }
        result = build_repo_profile_artifact(inv)
        assert result["quality_tier"] == "minimal"

    def test_build_repo_profile_deterministic(self):
        inv = self._rich_inventory()
        r1 = build_repo_profile_artifact(inv)
        r2 = build_repo_profile_artifact(inv)
        assert r1 == r2

    def test_build_repo_profile_schema_version_is_2(self):
        result = build_repo_profile_artifact({})
        assert result["schema_version"] == "2.0"

    def test_build_repo_profile_empty_inventory_has_signal_keys(self):
        result = build_repo_profile_artifact({})
        assert result["docs_depth"] == 0
        assert result["examples_count"] == 0
        assert result["api_surface"] == 0
        assert result["languages"] == []
        assert result["build_systems"] == []
        assert result["quality_tier"] == "minimal"
        assert "docs_signals" in result
        assert "examples_signals" in result
        assert "api_signals" in result
        assert "build_signals" in result
        assert "formats_signals" in result
        assert "confidence" in result
        assert "warnings" in result
        assert "language_breakdown" in result

    def test_build_repo_profile_languages_sorted(self):
        inv = {"repo_profile": {"primary_languages": ["Python", "C#", "Java"]}}
        result = build_repo_profile_artifact(inv)
        assert result["languages"] == sorted(["Python", "C#", "Java"])

    def test_build_repo_profile_build_systems_sorted(self):
        inv = {"repo_profile": {"build_systems": ["msbuild", "cmake", "bazel"]}}
        result = build_repo_profile_artifact(inv)
        assert result["build_systems"] == sorted(["msbuild", "cmake", "bazel"])

    def test_build_repo_profile_source_type_weights_present(self):
        result = build_repo_profile_artifact({})
        assert "source_type_weights" in result
        assert isinstance(result["source_type_weights"], dict)
        assert result["source_type_weights"]["api_doc"] == 0.9

    def test_build_repo_profile_api_surface_computed(self):
        inv = {
            "paths": ["src/foo.py", "test_foo.py", "src/bar.cs"],
            "doc_entrypoints": [],
            "example_paths": [],
            "repo_profile": {},
        }
        result = build_repo_profile_artifact(inv)
        assert result["api_surface"] == 2

    def test_build_repo_profile_docs_depth_sum(self):
        inv = {
            "doc_entrypoints": ["a.md", "b.md"],
            "example_paths": ["ex.py"],
        }
        result = build_repo_profile_artifact(inv)
        assert result["docs_depth"] == 3
        assert result["examples_count"] == 1

    def test_build_repo_profile_docs_signals_populated(self):
        inv = {
            "paths": ["README.md", "docs/guide.md", "src/main.py"],
            "doc_entrypoints": ["README.md", "docs/guide.md"],
            "example_paths": [],
            "repo_profile": {},
        }
        result = build_repo_profile_artifact(inv)
        ds = result["docs_signals"]
        assert ds["has_readme"] is True
        assert ds["has_docs_folder"] is True
        assert ds["markdown_file_count"] == 2

    def test_build_repo_profile_examples_signals_populated(self):
        inv = {
            "paths": ["examples/hello.py", "examples/convert.cs"],
            "doc_entrypoints": [],
            "example_paths": ["examples/hello.py", "examples/convert.cs"],
            "repo_profile": {},
        }
        result = build_repo_profile_artifact(inv)
        es = result["examples_signals"]
        assert es["has_examples_folder"] is True
        assert es["example_file_count"] == 2
        assert ".cs" in es["code_extensions"]
        assert ".py" in es["code_extensions"]

    def test_build_repo_profile_language_breakdown_populated(self):
        inv = {
            "paths": ["a.py", "b.py", "c.cs"],
            "doc_entrypoints": [],
            "example_paths": [],
            "repo_profile": {},
        }
        result = build_repo_profile_artifact(inv)
        lb = result["language_breakdown"]
        assert lb["py"] == 2
        assert lb["cs"] == 1

    def test_three_shapes_quality_tiers(self):
        """Verify the 3 fixture-shaped inventories produce expected quality tiers."""
        # docs_heavy: 6 docs + 0 examples → docs_depth=6, examples=0 → minimal
        docs_heavy = {
            "paths": ["README.md", "docs/a.md", "docs/b.md", "docs/c.md",
                      "docs/d.md", "docs/e.md", "pyproject.toml", "src/x.py"],
            "doc_entrypoints": ["README.md", "docs/a.md", "docs/b.md",
                                "docs/c.md", "docs/d.md", "docs/e.md"],
            "example_paths": [],
            "repo_profile": {"primary_languages": ["Python"], "build_systems": ["setuptools"]},
        }
        # examples_heavy: 1 doc + 15 examples → docs_depth=16, examples=15 → standard
        examples_heavy = {
            "paths": ["README.md"] + [f"examples/ex_{i}.py" for i in range(15)],
            "doc_entrypoints": ["README.md"],
            "example_paths": [f"examples/ex_{i}.py" for i in range(15)],
            "repo_profile": {"primary_languages": ["Python"], "build_systems": ["setuptools"]},
        }
        # minimal: 1 doc + 0 examples → minimal
        minimal = {
            "paths": ["README.md", "src/main.py"],
            "doc_entrypoints": ["README.md"],
            "example_paths": [],
            "repo_profile": {"primary_languages": ["Python"], "build_systems": []},
        }
        r_docs = build_repo_profile_artifact(docs_heavy)
        r_ex = build_repo_profile_artifact(examples_heavy)
        r_min = build_repo_profile_artifact(minimal)

        assert r_docs["quality_tier"] == "minimal"   # 6 docs only — below threshold
        assert r_ex["quality_tier"] == "standard"    # 16 docs_depth > 10
        assert r_min["quality_tier"] == "minimal"    # 1 doc, no examples
