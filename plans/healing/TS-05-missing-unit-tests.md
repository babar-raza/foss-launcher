# TS-05 — Comprehensive Unit Tests for HC-01, HC-03, HC-04

## Context

The HC healing sprint implemented 6 taskcards but only wrote 3 dedicated
tests (thread safety, regex hardening, structlog). Three taskcards have
ZERO dedicated unit tests:

- HC-01: `_build_import_allowlist()` with TreeSitter export extraction
- HC-03: `section_validator.py` multi-language import normalization
- HC-04: `discover_source_files` / `discover_manifests` / `extract_code_limitations`

These changes are integration-tested only through the full suite. A regression
in any of these paths would go undetected until a downstream failure.

## Status: Done

## Gap linkage

| Gap ID | Description |
|--------|-------------|
| G-09 | No dedicated unit tests for HC-01, HC-03, HC-04 |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Write targeted unit tests covering each changed function. All tests use
synthetic fixtures (tmp_path / inline code strings), no real repos.

**Tests for HC-01** (`_build_import_allowlist` with TreeSitter):

```
test_allowlist_python_uses_init_not_treesitter
  - Create __init__.py with __all__ = ["Workbook"]
  - Assert "Workbook" in allowlist
  - Assert TreeSitter NOT called (Python path)

test_allowlist_java_uses_treesitter_exports
  - Create Java file with `public class Workbook`
  - Assert "Workbook" in allowlist

test_allowlist_csharp_uses_treesitter_exports
  - Create C# file with `public class Document`
  - Assert "Document" in allowlist

test_allowlist_fallback_to_regex_when_treesitter_unavailable
  - Create Java file with `package com.aspose.cells;`
  - Mock TreeSitter ImportError
  - Assert "com.aspose.cells" in allowlist (regex fallback)

test_allowlist_empty_lang_tag_python_repo
  - Create __init__.py
  - product.lang_tag = ""
  - Assert Python __init__ path is used, not TreeSitter
```

**Tests for HC-03** (`section_validator` multi-lang normalization):

```
test_section_validator_normalizes_java_imports
  - Code block with `import com.aspose.cells`
  - canonical_import = "com.aspose.cells_foss"
  - Assert normalized in output

test_section_validator_skips_python_for_ts_normalize
  - Code block with language="python"
  - Assert _normalize_imports called, NOT ts_normalize

test_section_validator_graceful_when_ts_unavailable
  - language="java", mock ImportError
  - Assert no crash, content unchanged
```

**Tests for HC-04** (`discover_source_files`, `discover_manifests`, `extract_code_limitations`):

```
test_discover_source_files_finds_java
  - Create tmp_path/src/Foo.java
  - Assert Foo.java in results

test_discover_source_files_finds_rust
  - Create tmp_path/src/lib.rs
  - Assert lib.rs in results

test_discover_source_files_excludes_shell_sql
  - Create tmp_path/script.sh, tmp_path/query.sql
  - Assert NEITHER in results (after TS-04 fix)

test_discover_manifests_finds_pom_xml
  - Create tmp_path/pom.xml
  - Assert pom.xml in results

test_discover_manifests_finds_build_gradle
  - Create tmp_path/build.gradle
  - Assert build.gradle in results

test_extract_code_limitations_finds_java_todo
  - Create tmp_path/src/Foo.java with `// TODO: implement save`
  - Assert limitation claim extracted (after TS-03 fix)

test_extract_code_limitations_finds_python_todo
  - Create tmp_path/src/foo.py with `# TODO: fix parser`
  - Assert limitation claim extracted (regression test)
```

### Allowed paths

- `tests/unit/shared/test_ts_healing.py` (extend existing)
- `tests/unit/workers/test_understand.py` (extend existing — allowlist tests)
- `tests/unit/workers/test_generate.py` (extend existing — section validator tests)

### Forbidden

Any other file or path.

## Acceptance checks

- **Tests**: All new tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_healing.py tests/unit/workers/test_understand.py tests/unit/workers/test_generate.py -v -k "test_allowlist or test_section_validator_normal or test_discover or test_extract_code_limitations"` — 0 failures
- **Tests**: Full suite: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x` — 0 failures
- **Coverage**: At least 15 new test functions total
- No mock data in production paths
- No network in offline tests

## Deliverables

- New/updated test functions in existing test files
- Each changed function has >= 2 dedicated tests (happy path + failure/edge)
- No TODOs, no stubs

## Hard rules

- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps (use pytest fixtures, tmp_path, monkeypatch)
- All fixtures use synthetic code (no real repo data)
- Keep code/docs/tests in sync
- Tests must work on Windows 11 (use pathlib, not hardcoded `/`)
- Tests depend on TS-03 and TS-04 being completed first (for discover/limitation changes)

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | Every changed function has >= 2 tests (happy + edge/failure) |
| Correctness | Tests prove the fix works, not just that it doesn't crash |
| Test quality | Tests are fast (<1s each), deterministic, isolated (tmp_path) |
| Coverage | 15+ new test functions covering all 3 HCs |
| Robustness | Failure path tests: ImportError, empty repo, missing files |
| Maintainability | Tests in existing test files, not scattered new files |
| Minimality | Only test files changed |

## Now (runbook)

```bash
# 1. Add allowlist tests to test_understand.py
#    (depends on TS-02 being applied first for correct allowlist logic)

# 2. Add section_validator tests to test_generate.py

# 3. Add discover/limitation tests to test_ts_healing.py
#    (depends on TS-03 and TS-04 being applied first)

# 4. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_healing.py tests/unit/workers/test_understand.py tests/unit/workers/test_generate.py -v -k "test_allowlist or test_section_validator_normal or test_discover or test_extract_code_limitations"

# 5. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x

# 6. Count new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --collect-only -q 2>&1 | tail -1
# Expected: >= 15 more than current count (1523)
```
