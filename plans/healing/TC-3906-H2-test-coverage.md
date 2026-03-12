---
id: TC-3906-H2
title: "Write comprehensive tests for snapshot_manifest, phase_promoter, ir_regenerate"
status: Done
priority: P0 / Critical
owner: unassigned
updated: "2026-03-09"
tags: [snapshot, testing, coverage]
depends_on: [TC-3906-H1, TC-3906-H5]
allowed_paths:
  - plans/healing/TC-3906-H2-test-coverage.md
  - tests/unit/deploy/test_snapshot_manifest.py
  - tests/unit/deploy/test_phase_promoter.py
  - tests/unit/shared/test_ir_regenerate.py
---

# TC-3906-H2 — Comprehensive test coverage for TC-3906 new modules

## Status: Done

## Gap linkage

- **G-3906-02**: TC-3906 shipped zero new tests. All three new modules
  (`snapshot_manifest.py`, `phase_promoter.py`, `ir_regenerate.py`) are untested.
  The majority tracking bug (G-3906-01) would have been caught immediately by a test.
  The `_PHASE_FILES` correctness, path construction invariant, and corrupt-manifest
  recovery are all unverified.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

Create three test files covering all public functions and critical paths.

**`tests/unit/deploy/test_snapshot_manifest.py`** — Tests for `SnapshotManifest`, `SnapshotIREntry`,
`load_snapshot_manifest`, `save_snapshot_manifest`:

Required test cases:
1. `test_empty_manifest_defaults` — `SnapshotManifest()` has expected defaults.
2. `test_save_and_load_roundtrip` — Write manifest via `save_snapshot_manifest`, reload via
   `load_snapshot_manifest`, assert fields match (PYTHONHASHSEED=0, `tmp_path`).
3. `test_load_missing_file_returns_empty` — File does not exist → returns `SnapshotManifest()`.
4. `test_load_corrupt_file_backs_up_and_returns_empty` — Write invalid JSON, call load →
   returns empty, `.json.bak` created, original no longer exists.
5. `test_save_validates_schema` — Inject a valid manifest, save → no exception. Inject an
   invalid object (e.g., `grade="Z"`), save → raises (schema validation).
6. `test_snapshot_ir_entry_sha256_pattern` — Entry with invalid sha256 (not 64 hex chars)
   fails `SnapshotManifest.model_validate`.

**`tests/unit/deploy/test_phase_promoter.py`** — Tests for `promote_phase_snapshots`:

Required test cases:
1. `test_promote_happy_path` — Build `tmp_path` run_dir with `evaluation_report.json` (grade A)
   and matching `content_bundle/pages/{content_path}.ir.json`. Call `promote_phase_snapshots`.
   Assert: IR file exists at `snapshots/{content_path}.ir.json`; `snapshot_manifest.json`
   written; `report.ir_promoted == 1`.
2. `test_grade_below_min_skipped` — Grade D, min_grade=C → `ir_skipped_grade_low == 1`,
   no IR file in snapshots.
3. `test_sha256_dedup_skips_unchanged` — Promote same IR twice → second call:
   `ir_skipped_same_hash == 1`, no overwrite.
4. `test_incumbent_grade_blocks_demotion` — Promote grade A, then grade B → second call:
   `ir_skipped_no_improvement == 1`, incumbent grade A retained.
5. `test_missing_ir_file_skipped` — `evaluation_report.json` references slug with no `.ir.json`
   in content_bundle → `ir_skipped_missing_ir == 1`, no crash.
6. `test_majority_accumulates_across_calls` — Two calls for same run, 3 slots each →
   `manifest.run_ir_counts[run_id] == 6`, `majority_run_id == run_id`.
7. `test_phase_jsons_written_when_majority_won` — Run A wins 5 slots. Assert
   `phase_store/cells/python/understand.json` exists (from run's `understanding_bundle.json`).
8. `test_dry_run_writes_nothing` — `dry_run=True` → no files written to snapshots or
   phase_store, but report is populated correctly.
9. `test_missing_eval_report_returns_empty_report` — No `evaluation_report.json` → returns
   `PhasePromotionReport` with all zeros, no crash.
10. `test_path_depth_preserved` — content_path with subdirectory (`kb.aspose.org/cells/python/developer-guide/slug`) →
    IR promoted to `snapshots/kb.aspose.org/cells/python/developer-guide/slug.ir.json`.

**`tests/unit/shared/test_ir_regenerate.py`** — Tests for `regenerate_from_snapshots`:

Required test cases:
1. `test_regenerate_happy_path` — Create `snapshots/{content_path}.ir.json` with a valid
   minimal `PageIR`. Call `regenerate_from_snapshots(snapshots_dir, output_dir)`. Assert
   `output_dir/{content_path}.md` exists and contains expected YAML frontmatter.
2. `test_path_preserved_verbatim` — IR at `snapshots/kb.aspose.org/cells/python/developer-guide/slug.ir.json`
   → output at `output_dir/kb.aspose.org/cells/python/developer-guide/slug.md`.
3. `test_missing_snapshots_dir_returns_empty` — Non-existent `snapshots_dir` → returns `[]`,
   no crash.
4. `test_corrupt_ir_file_skipped` — One IR file with invalid JSON, one valid →
   `len(written) == 1`, no crash.
5. `test_frontmatter_error_skipped` — IR with missing required frontmatter key → skipped,
   remaining pages written.
6. `test_snapshot_manifest_json_not_processed` — Place `snapshot_manifest.json` in snapshots dir
   (note: it won't match `*.ir.json` glob, but confirm it's not in output).
7. `test_returns_list_of_written_paths` — Return value contains absolute paths of written files.

### Path construction to assert in tests:

```python
# Phase promoter invariant:
assert (snapshots_dir / (content_path + ".ir.json")).exists()

# ir_regenerate invariant:
rel = ir_file.relative_to(snapshots_dir)
assert (output_dir / rel.with_suffix(".md")).exists()
```

### Allowed paths:
- `plans/healing/TC-3906-H2-test-coverage.md`
- `tests/unit/deploy/test_snapshot_manifest.py`
- `tests/unit/deploy/test_phase_promoter.py`
- `tests/unit/shared/test_ir_regenerate.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/deploy/test_snapshot_manifest.py \
    tests/unit/deploy/test_phase_promoter.py \
    tests/unit/shared/test_ir_regenerate.py \
    -v --tb=short
```
All new tests pass. Full suite ≥ 3183 passed (no regressions).

### UI/Web/API:
N/A.

### Tests:
- ≥10 tests in `test_phase_promoter.py`
- ≥6 tests in `test_snapshot_manifest.py`
- ≥7 tests in `test_ir_regenerate.py`
- All tests use `tmp_path` fixture, no network, no real filesystem side effects outside `tmp_path`
- `PYTHONHASHSEED=0` enforced via `pytest.ini` or CLI flag

### Config respected end-to-end:
- `min_grade` parameter exercised at C, A, and F boundaries
- `dry_run=True` path separately tested

### No mock data in production paths:
- `render_page` and `sha256_file` called on real (tmp_path) files in tests — no mocking
- Only `_update_phase_store` may be optionally mocked in majority-tracking unit tests to
  avoid filesystem overhead

## Deliverables

1. **`tests/unit/deploy/test_snapshot_manifest.py`** — New file, 6 tests. No stubs, no TODOs.
2. **`tests/unit/deploy/test_phase_promoter.py`** — New file, 10 tests. No stubs, no TODOs.
   Must build minimal but valid `evaluation_report.json` and `*.ir.json` fixtures in `tmp_path`.
3. **`tests/unit/shared/test_ir_regenerate.py`** — New file, 7 tests. No stubs, no TODOs.
   Must use a minimal valid `PageIR` fixture with required frontmatter fields.

Full file replacements — no stubs, no TODOs.
If contracts/schemas change: tests must import from corrected `snapshot_manifest.py` after TC-3906-H1 lands.

## Hard rules

- No network in tests: `render_page` operates on local PageIR structs; `sha256_file` on `tmp_path` files.
- Deterministic: `PYTHONHASHSEED=0` on all runs.
- No new deps beyond `pytest` and `pytest-tmp-path` (already present).
- Minimal valid `PageIR` fixture: must include all `_REQUIRED_FM_KEYS` from `ir_renderer.py`
  (`title`, `slug`, `type`, `url`, `weight`, `family`, `platform`, `page_role`).
- Tests must pass after TC-3906-H1 fix is applied (depend on corrected model).

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Testability | All 3 test files run independently; each test is ≤ 30 lines; all use `tmp_path` |
| Correctness | Path invariant `snapshots_dir/(content_path+".ir.json")` asserted in phase_promoter tests |
| Thoroughness | Happy path + grade-filter + SHA-dedup + missing-file + dry-run + corrupt-manifest |
| Robustness | Error paths (corrupt IR, missing IR, missing eval) tested without crashing |
| Production grading | Tests catch the G-3906-01 majority tracking bug if fix is reverted |

## Now (runbook)

```bash
# 1. Check existing test structure to determine test dir conventions
ls tests/unit/

# 2. Read minimal valid PageIR fields from ir_renderer.py
grep "_REQUIRED_FM_KEYS" src/launcher/shared/ir_renderer.py

# 3. Read EvaluationReport + PageEvaluation models for fixture construction
grep -n "class EvaluationReport\|class PageEvaluation" src/launcher/models/evaluation.py

# 4. Write test_snapshot_manifest.py (6 tests)

# 5. Write test_phase_promoter.py (10 tests)

# 6. Write test_ir_regenerate.py (7 tests)

# 7. Run all three files
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/deploy/test_snapshot_manifest.py \
    tests/unit/deploy/test_phase_promoter.py \
    tests/unit/shared/test_ir_regenerate.py \
    -v --tb=short

# 8. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3
```
