# TC-4306 Evidence — .NET csproj Selection and API Extraction

## Test Run Summary

**Full suite (PYTHONHASHSEED=0):**
```
4740 passed, 65 skipped, 3 xfailed, 2 xpassed in 114.68s
```
Zero failures. All pre-existing tests pass. 12 new tests added (2 in test_scout_facts.py, 10 in test_dotnet_adapter.py).

## Targeted Test Run (TC-4306 tests only)

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_facts.py tests/unit/workers/understand/test_dotnet_adapter.py -v

============================= test session starts =============================
collected 34 items

tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_empty_repo PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_detects_python_language PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_detects_java_language PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_detects_build_systems PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_detects_multiple_build_systems PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_has_tests PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_no_tests PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_manifest_declared_testpaths_count_as_tests PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_has_ci PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_has_docs_folder PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_has_examples_folder PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_parses_pyproject_toml PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_parses_setup_cfg PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_pyproject_takes_precedence PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_missing_pyproject_falls_back PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_package_json_extracts_description_deps_scripts PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_cargo_toml_extracts_description_deps PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_pom_xml_extracts_description_deps PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_csproj_extracts_description_deps PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_gemspec_extracts_description_deps PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_platform_priority_java_uses_pom PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_platform_priority_python_unchanged PASSED
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_dotnet_build_system_detected PASSED          [NEW TC-4306]
tests/unit/workers/test_scout_facts.py::TestExtractSharedFacts::test_multi_csproj_selects_library_project PASSED  [NEW TC-4306]
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterTypedMethods::test_extract_class_details_returns_method_details PASSED
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterTypedMethods::test_method_has_parameter_info PASSED
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterTypedMethods::test_enum_class_extracted PASSED
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterTypedMethods::test_uses_csharp_language_explicitly PASSED
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterTypedMethods::test_fallback_when_ts_analyzer_raises PASSED
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterPackageRoot::test_detect_package_root_multi_project PASSED  [NEW TC-4306]
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterPackageRoot::test_detect_package_root_single_csproj PASSED  [NEW TC-4306]
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterPackageRoot::test_detect_package_root_no_csproj_fallback PASSED  [NEW TC-4306]
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterPackageRoot::test_build_import_allowlist_all_namespaces PASSED  [NEW TC-4306]
tests/unit/workers/understand/test_dotnet_adapter.py::TestDotNetAdapterPackageRoot::test_build_import_allowlist_excludes_foreign_namespaces PASSED  [NEW TC-4306]

34 passed in 1.84s
```

## Bug Found During Implementation

**Critical Bug:** The `is_test` check in both `_select_main_csproj()` and `detect_package_root()` used
the full absolute path to detect test projects. This caused both `.csproj` files to be flagged as
`is_test=True` when `tmp_path` contained "test" in its name (e.g., pytest's
`test_detect_package_root_multi0` tmp dir).

**Fix:** Changed both functions to compute the path relative to `repo_dir` (or the common ancestor
of all csproj files) before checking for "test" in path segments. This ensures only project-internal
directory names (e.g., `tests/`, `test/`) are used for filtering.
