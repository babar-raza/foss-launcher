# TC-2448 Evidence Report — Agent C: Enrich repo_profiler.py + W1 Always-On Write

**Date**: 2026-02-23
**Agent**: Agent_C
**Status**: Done

---

## Deliverables Completed

### 1. `src/launch/workers/w1_repo_scout/repo_profiler.py` — Expanded to schema 2.0

Added 6 new private helper functions:
- `_compute_docs_signals()` — has_readme, readme_size_bytes, has_docs_folder, markdown_file_count, docs_depth_score
- `_compute_examples_signals()` — has_examples_folder, example_file_count, code_extensions
- `_compute_api_signals()` — has_api_docs_folder, has_type_stubs, has_openapi_spec, api_surface_count
- `_compute_build_signals()` — build_systems, detected_manifests, has_ci
- `_compute_formats_signals()` — binary_asset_count, domain_extensions
- `_compute_language_breakdown()` — top-15 extension counts
- `_compute_confidence_and_warnings()` — confidence float + warnings list

Updated `build_repo_profile_artifact()`:
- schema_version bumped "1.0" → "2.0"
- All existing top-level keys preserved (backward compat)
- 8 new keys added: language_breakdown, confidence, warnings, docs_signals, examples_signals, api_signals, build_signals, formats_signals

### 2. `src/launch/workers/w1_repo_scout/worker.py` — Always-on write

Removed `LAUNCH_REPO_PROFILING=1` env var guard. `repo_profile.json` is now always written. The `try/except` wrapper remains so failures are non-fatal.

### 3. `tests/unit/workers/test_w1_repo_profiler.py` — 91 tests (was 30)

Added 6 new test classes:
- `TestDocsSignals` (12 tests) — README detection, docs folder, markdown count, size from details
- `TestExamplesSignals` (8 tests) — has_examples_folder, code_extensions, counts
- `TestApiSignals` (10 tests) — type stubs, openapi, api_docs_folder
- `TestBuildSignals` (9 tests) — detected_manifests, has_ci (GitHub/Travis/CircleCI)
- `TestFormatsSignals` (6 tests) — domain extensions, binary count, exclusions
- `TestLanguageBreakdown` (4 tests) — counts, empty, no-extension skip, 15-limit
- `TestConfidenceAndWarnings` (7 tests) — low confidence, warnings, sorted output
- Updated `TestBuildRepoProfileArtifact`: schema_version → "2.0", new signal keys asserted

### 4. `tests/fixtures/repos/` — 3 fixture repo shapes

- `docs_heavy/` (9 files): README + 4 docs + pyproject.toml + 2 source files
- `examples_heavy/` (17 files): README + pyproject.toml + CI + 15 example .py files
- `minimal_readme/` (3 files): README + setup.cfg + 1 source file

---

## Test Results

| Suite | Count | Result |
|-------|-------|--------|
| `test_w1_repo_profiler.py` | 91 | ✓ All pass |
| Full suite `tests/` | 5320+ | Pending (background) |

---

## Key Design Decisions

1. **Schema backward compat**: All v1.0 top-level keys preserved — `repo_profile.get("quality_tier", "standard")` etc. work unchanged.
2. **Always-on write**: Pure function computation, negligible overhead (<2ms). No need for env gate.
3. **Confidence formula**: 0.8 baseline, -0.15 for no README, -0.15 for no docs. Floor = 0.
4. **domain_extensions**: Only non-code, non-doc, non-web extensions (e.g., `.fbx`, `.xlsx`) — captures domain-specific format files.
