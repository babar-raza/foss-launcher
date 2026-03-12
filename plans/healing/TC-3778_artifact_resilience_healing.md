# TC-3778 Artifact Resilience — Healing Plan

## Context

Self-review of TC-3778 (Evaluate worker artifact resilience) identified 6 concrete gaps that prevent the implementation from being production-grade. The core feature works (per-page + summary artifacts written to disk), but there are correctness bugs, missing test coverage, dead code, and an unguarded crash path.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | Per-page artifacts stale after permalink collision re-grading | Bug/Critical | SR-01 |
| G-02 | Missing-file pages (grade F) never get artifacts written | Bug/Medium | SR-01 |
| G-03 | `eval_pages_dir.mkdir()` unguarded — can crash the worker | Bug/Medium | SR-02 |
| G-04 | `RunLayout.evaluation_dir` property added but never referenced (dead code) | Cleanup/Low | SR-02 |
| G-05 | `_safe_slug` has no isolated unit tests (path traversal, empty, unicode) | Test gap/Medium | SR-03 |
| G-06 | No test for write-failure graceful degradation or collision artifact correctness | Test gap/Medium | SR-03 |

---

## Taskcard SR-01 — Fix stale/missing per-page artifacts

**Status**: Done
**Gap linkage**: G-01, G-02
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
- Move per-page artifact writes from inside the per-page loop to a dedicated write pass AFTER the permalink collision check. This ensures collision-downgraded pages have correct grades on disk.
- Also write artifacts for missing-file pages (which currently skip via `continue` before the write call).

**Allowed paths**:
- `src/launcher/workers/evaluate/worker.py`
- `tests/unit/workers/test_evaluate.py`

**Forbidden**: any other file/path

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` — all pass
- **Tests**:
  - Existing `TestPermalinkCollision::test_slug_collision_detected` still passes
  - New test: after permalink collision, the on-disk `.eval.json` for colliding pages has `grade: "F"` and a `permalink` finding with `severity: "critical"`
  - New test: missing-file pages produce a `.eval.json` artifact with `grade: "F"` and `check: "file_missing"`
- **Config respected end-to-end**: N/A
- **No mock data in production paths**: Confirmed

### Deliverables

1. Modified `src/launcher/workers/evaluate/worker.py`:
   - Remove `_write_page_artifact(context, page_eval)` from inside the per-page loop (line 112)
   - Add a write-all loop after the permalink collision block (after current line 131):
     ```python
     # Write per-page evaluation artifacts (after collision re-grading)
     for page_eval in page_evals:
         _write_page_artifact(context, page_eval)
     ```
2. Modified `tests/unit/workers/test_evaluate.py`:
   - New test `test_collision_artifact_has_correct_grade` in `TestEvaluateArtifacts`
   - New test `test_missing_file_page_artifact_written` in `TestEvaluateArtifacts`

### Hard rules

- Keep public signatures unchanged
- No network in tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync

### Review dimensions — what 5/5 means for SR-01

| Dimension | 5/5 Definition |
|-----------|----------------|
| Correctness | On-disk artifacts always match in-memory PageEvaluation after all post-processing |
| Thoroughness | Every code path (normal, missing-file, collision) produces an artifact |
| Test Quality | Tests assert JSON content correctness, not just file existence |
| Robustness | Write failures are still non-fatal after the move |
| Minimality | Only the write location changes; no other logic modified |

### Runbook

```bash
# 1. Edit worker.py: remove line 111-112, add write loop after line 131
# 2. Add 2 new tests to test_evaluate.py
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 5. Verify collision artifact content manually
# python -c "import json; d=json.load(open('...')); assert d['grade']=='F'"
```

---

## Taskcard SR-02 — Guard mkdir and wire RunLayout.evaluation_dir

**Status**: Done
**Gap linkage**: G-03, G-04
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
- Wrap `eval_pages_dir.mkdir(parents=True, exist_ok=True)` in try/except with warning log. On failure, set a flag to skip artifact writes (worker continues normally).
- Replace hardcoded `context.run_dir / "evaluation"` paths in `worker.py` with usage of `RunLayout.evaluation_dir` — or remove the dead property if RunLayout shouldn't own this. Decision: **use it**, since it was added for this purpose and matches `content_bundle_dir` pattern.

**Allowed paths**:
- `src/launcher/workers/evaluate/worker.py`
- `src/launcher/io/run_layout.py`
- `tests/unit/workers/test_evaluate.py`

**Forbidden**: any other file/path

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py tests/unit/io/ -v` — all pass
- **Tests**:
  - New test: when `evaluation/pages/` directory cannot be created (e.g., parent is a file), worker still returns a valid `EvaluationReport` and logs a warning
  - Existing artifact tests still pass
- **Config respected end-to-end**: N/A
- **No mock data in production paths**: Confirmed

### Deliverables

1. Modified `src/launcher/workers/evaluate/worker.py`:
   - Import `RunLayout` or construct path from a layout instance, OR use a constant derived from the layout pattern
   - Wrap mkdir in try/except; set `_artifacts_enabled = True/False` flag
   - Guard `_write_page_artifact` and `_write_summary_artifact` calls with the flag
2. Modified `tests/unit/workers/test_evaluate.py`:
   - New test verifying graceful degradation when directory creation fails
3. `src/launcher/io/run_layout.py` — no changes needed (property already exists and will now be referenced)

### Hard rules

- Keep public signatures unchanged
- No network in tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync

### Review dimensions — what 5/5 means for SR-02

| Dimension | 5/5 Definition |
|-----------|----------------|
| Robustness | Worker never crashes due to artifact directory issues |
| Integration | RunLayout.evaluation_dir is referenced, not dead code |
| Observability | Warning log emitted with exc_info on mkdir failure |
| Minimality | Only the mkdir guard and path wiring change |
| Maintainability | Single source of truth for the evaluation directory path |

### Runbook

```bash
# 1. Edit worker.py: wrap mkdir, add flag, guard writes, use RunLayout path
# 2. Add degradation test to test_evaluate.py
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 5. Grep for hardcoded "evaluation" paths to confirm none remain
# grep -rn '"evaluation' src/launcher/workers/evaluate/worker.py
```

---

## Taskcard SR-03 — Add missing test coverage for _safe_slug and write failures

**Status**: Done
**Gap linkage**: G-05, G-06
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
- Add isolated unit tests for `_safe_slug` covering: normal slug, path traversal (`../../etc/passwd`), empty string, slashes, unicode characters, very long slugs.
- Add a test verifying that when `context.store.write_json` raises an exception, the worker still returns a valid `EvaluationReport` (graceful degradation).

**Allowed paths**:
- `tests/unit/workers/test_evaluate.py`

**Forbidden**: any other file/path

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestSafeSlug -v` — all pass
- **Tests**:
  - `test_normal_slug` — `"getting-started"` passes through unchanged
  - `test_path_traversal` — `"../../etc/passwd"` has no `..`, no `/`
  - `test_empty_slug` — `""` returns `"unknown"`
  - `test_slashes` — `"a/b/c"` has no `/`
  - `test_unicode` — `"page-\u00e9"` sanitized to safe chars
  - `test_long_slug` — 500-char slug doesn't crash, produces valid filename
  - `test_write_failure_graceful` — monkeypatch `store.write_json` to raise; worker still returns `EvaluationReport`
- **Config respected end-to-end**: N/A
- **No mock data in production paths**: Confirmed

### Deliverables

1. Modified `tests/unit/workers/test_evaluate.py`:
   - New import: `from launcher.workers.evaluate.worker import _safe_slug`
   - New class `TestSafeSlug` with 6 tests
   - New test `test_write_failure_graceful` in `TestEvaluateArtifacts`

### Hard rules

- Keep public signatures unchanged
- No network in tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync

### Review dimensions — what 5/5 means for SR-03

| Dimension | 5/5 Definition |
|-----------|----------------|
| Test Quality | Every edge case of `_safe_slug` has a dedicated assertion |
| Robustness | Write failure path proven to degrade gracefully via test |
| Coverage | `_safe_slug` has 100% branch coverage; write failure path exercised |
| Correctness | Tests verify exact output strings, not just "no crash" |
| Minimality | Test-only changes; no production code modified |

### Runbook

```bash
# 1. Add TestSafeSlug class and write-failure test to test_evaluate.py
# 2. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestSafeSlug -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestEvaluateArtifacts -v
# 3. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
