# TC-3784 False Permalink Collision Fix — Healing Plan

## Context

Self-review of TC-3784 (fix false permalink collision detection and artifact overwrite) identified 7 gaps that prevent the implementation from being fully production-grade. The core fix is correct — collision detection now groups by `content_path or slug`, and `PageEvaluation` carries `content_path`. However, a downstream consumer (`verify_healing.py`) is now broken, test coverage has holes, an artifact filename collision vector exists, a stale docstring is misleading, and there's no same-content_path collision test to prove the positive path still works.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-07 | `verify_healing.py` uses `_safe_slug(page_eval.slug)` — broken for pages with `content_path` | Bug/High | SR-04 |
| G-08 | No test for same `content_path` collision (positive path) | Test gap/Medium | SR-05 |
| G-09 | No test for missing-file page with `content_path` set (artifact filename check) | Test gap/Medium | SR-05 |
| G-10 | `_safe_slug` can produce colliding filenames from distinct `content_path` values (e.g. `a/b_c` vs `a_b/c`) | Robustness/Low | SR-06 |
| G-11 | `run_layout.py` docstring says `pages/{slug}.eval.json` — now incorrect | Docs/Low | SR-04 |
| G-12 | Collision message says "path" but key may be a slug when `content_path` is empty | Consistency/Low | SR-04 |
| G-13 | No backward-compat deserialization test for `PageEvaluation` JSON without `content_path` | Test gap/Low | SR-05 |

---

## Taskcard SR-04 — Fix downstream consumers and consistency issues

**Status**: Done
**Gap linkage**: G-07, G-11, G-12
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
1. Update `verify_healing.py` lines 107 and 136 to use `_safe_slug(page_eval.content_path or page_eval.slug)` instead of `_safe_slug(page_eval.slug)`, matching the worker's new artifact naming.
2. Update `run_layout.py` docstring line 7 from `pages/{slug}.eval.json` to `pages/{content_path_or_slug}.eval.json` to reflect the new naming convention.
3. Update collision finding message to be key-agnostic: use `"Permalink collision: '{path_key}' used by {n} pages"` (drop the word "path" which is misleading when the key is a bare slug).

**Allowed paths**:
- `scripts/verify_healing.py`
- `src/launcher/io/run_layout.py` (docstring only)
- `src/launcher/workers/evaluate/worker.py` (message string only)

**Forbidden**: any other file/path

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/verify_healing.py runs/pilot_cells_20260306T195001` — all gaps PASS (no MISSING artifacts for `_index` pages)
- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` — all pass (111+)
- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — full suite passes (1416+)
- **Config respected end-to-end**: `verify_healing.py` artifact lookup matches worker artifact write logic
- **No mock data in production paths**: N/A (script-only changes)

### Deliverables

1. Modified `scripts/verify_healing.py` — 2 lines changed (107, 136): `_safe_slug(page_eval.slug)` → `_safe_slug(page_eval.content_path or page_eval.slug)` and `_safe_slug(p.slug)` → `_safe_slug(p.content_path or p.slug)`
2. Modified `src/launcher/io/run_layout.py` — docstring line 7 updated
3. Modified `src/launcher/workers/evaluate/worker.py` — collision message string (1 line)

### Hard rules

- Keep public signatures unchanged
- No network in offline tests
- No new deps
- Keep code/docs/tests in sync — the docstring must match the actual behavior

### Review dimensions — what 5/5 looks like

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | All 3 downstream references updated, no remaining stale slug-based lookups |
| Consistency | Message format, docstring, and script all use the same `content_path or slug` pattern |
| Production grading | `verify_healing.py` runs successfully against real pilot data |
| Correctness | Artifact lookup matches artifact write for all pages (with and without `content_path`) |
| Minimality | Only message string, docstring, and 2 script lines touched |
| Integration | Script, docstring, and worker are now aligned on naming convention |
| Observability | Collision message is unambiguous whether key is a path or slug |

### Now (runbook)

```bash
# 1. Edit verify_healing.py line 107
#    _safe_slug(page_eval.slug) → _safe_slug(page_eval.content_path or page_eval.slug)
# 2. Edit verify_healing.py line 136
#    _safe_slug(p.slug) → _safe_slug(p.content_path or p.slug)
# 3. Edit run_layout.py docstring line 7
#    pages/{slug}.eval.json → pages/{content_path_or_slug}.eval.json
# 4. Edit worker.py collision message
#    "Permalink collision: path '{path_key}'" → "Permalink collision: '{path_key}'"
# 5. Validate
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 6. (Optional) Run against pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/verify_healing.py runs/pilot_cells_20260306T195001
```

---

## Taskcard SR-05 — Close test coverage gaps

**Status**: Done
**Gap linkage**: G-08, G-09, G-13
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
1. Add `test_same_content_path_collision_detected` — two pages with identical `content_path` values are flagged as collisions (positive path proof).
2. Add `test_missing_file_with_content_path_artifact` — a missing-file page with `content_path` set produces an artifact named after the `content_path`, not the slug.
3. Add `test_backward_compat_deserialization` — a `PageEvaluation` JSON dict without `content_path` field deserializes successfully with `content_path=""`.

**Allowed paths**:
- `tests/unit/workers/test_evaluate.py`

**Forbidden**: any other file/path

### Acceptance checks

- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` — 114+ tests pass (3 new)
- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — full suite passes
- **No mock data in production paths**: Tests use `tmp_path` only
- **Deterministic runs**: All new tests are deterministic (no randomness, no LLM)

### Deliverables

1. `test_same_content_path_collision_detected` in `TestPermalinkCollision`:
   - 2 pages with `slug="_index"`, `content_path="docs.aspose.org/cells/_index"` (identical)
   - Assert 2 permalink findings with severity "critical"

2. `test_missing_file_with_content_path_artifact` in `TestEvaluateArtifacts`:
   - 1 page with `slug="_index"`, `content_path="docs.aspose.org/cells/_index"`, missing md file
   - Assert `content_path` propagated to `PageEvaluation`
   - Assert artifact file is `docs_aspose_org_cells__index.eval.json` (not `_index.eval.json`)

3. `test_backward_compat_deserialization` in `TestPermalinkCollision` or new class:
   - Deserialize `{"slug": "test", "grade": "A", "findings": [], "check_results": {}}` (no `content_path`)
   - Assert `page_eval.content_path == ""`

### Hard rules

- No network in offline tests
- No new deps
- Deterministic (PYTHONHASHSEED=0)
- Tests cover both happy path and regression/failure path

### Review dimensions — what 5/5 looks like

| Dimension | 5/5 criteria |
|-----------|-------------|
| Testability | Every code path introduced by TC-3784 has at least one dedicated test |
| Coverage | Positive collision (same content_path), negative collision (different content_path), missing-file with content_path, backward compat |
| Robustness | Backward-compat test proves old serialized data still works |
| Correctness | Same-content_path test proves real collisions are still detected |
| Minimality | Only test file touched, 3 focused test methods |
| Thoroughness | Missing-file branch with content_path explicitly verified (was uncovered) |

### Now (runbook)

```bash
# 1. Add 3 test methods to test_evaluate.py
# 2. Validate
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard SR-06 — Guard against `_safe_slug` filename collisions

**Status**: Done
**Gap linkage**: G-10
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
The `_safe_slug` function replaces all non-alphanumeric characters (including `/` and `_`) with `_`. This means two distinct `content_path` values can map to the same safe string:
- `a/b_c` → `a_b_c`
- `a_b/c` → `a_b_c`

This creates a silent artifact overwrite. The fix is to use a separator character that distinguishes path separators from literal underscores. Replace `/` with `--` (double dash) before the general sanitization, so that path structure is preserved:
- `a/b_c` → `a--b_c`
- `a_b/c` → `a_b--c`

Alternatively, if the content_path is a dotted subdomain path like `docs.aspose.org/cells/_index`, the dots and slashes already create enough distinction. The risk is theoretical but real for generated paths.

**Allowed paths**:
- `src/launcher/workers/evaluate/worker.py` (`_safe_slug` function only)
- `tests/unit/workers/test_evaluate.py` (new test in `TestSafeSlug`)

**Forbidden**: any other file/path

### Acceptance checks

- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestSafeSlug -v` — all pass including new collision test
- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — full suite passes
- **No mock data in production paths**: N/A
- **Deterministic runs**: `_safe_slug` is pure function, fully deterministic

### Deliverables

1. Modified `_safe_slug` in `worker.py`:
   ```python
   def _safe_slug(slug: str) -> str:
       """Sanitize slug for safe use as a filename."""
       # Preserve path structure: replace / with -- before general sanitization
       result = slug.replace("/", "--")
       result = re.sub(r"[^a-zA-Z0-9_-]", "_", result) or "unknown"
       return result
   ```

2. New test `test_distinct_paths_produce_distinct_slugs` in `TestSafeSlug`:
   ```python
   def test_distinct_paths_produce_distinct_slugs(self):
       assert _safe_slug("a/b_c") != _safe_slug("a_b/c")
   ```

3. Updated existing `test_slashes` to match new behavior:
   ```python
   def test_slashes(self):
       result = _safe_slug("a/b/c")
       assert "/" not in result
       assert result == "a--b--c"
   ```

### Hard rules

- Keep public signature of `_safe_slug` unchanged (input: str, output: str)
- Update all call sites if behavior changes — but `_safe_slug` is only called internally, no external consumers
- No new deps
- Deterministic

### Review dimensions — what 5/5 looks like

| Dimension | 5/5 criteria |
|-----------|-------------|
| Robustness | No two distinct `content_path` values can silently map to the same filename |
| Correctness | Existing slug-based filenames (no `/`) are unaffected by the change |
| Minimality | 1-line change to `_safe_slug`, 1 new test, 1 updated test assertion |
| Performance | No performance impact — single string replace + regex |
| Integration | All artifact lookups (`verify_healing.py`, tests) use `_safe_slug` consistently |
| Testability | Collision case has a dedicated unit test proving distinctness |

### Now (runbook)

```bash
# 1. Edit _safe_slug in worker.py — add slug.replace("/", "--") before regex
# 2. Update test_slashes expected value from "a_b_c" to "a--b--c"
# 3. Add test_distinct_paths_produce_distinct_slugs
# 4. Validate
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestSafeSlug -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

### Risk note

Changing `_safe_slug` output format means existing on-disk artifacts (from previous pilot runs) will have different filenames than what `verify_healing.py` now expects. This is acceptable because:
- Pilot runs are ephemeral (re-runnable)
- No production deployment references these filenames
- The fix prevents a real data-loss bug (silent overwrite)

If backward compat with existing artifacts is required, an alternative is to only apply the `replace("/", "--")` when `content_path` is used (not bare slug). But this adds complexity for marginal benefit.

---

## Dependency order

```
SR-04 (fix verify_healing.py + consistency) — independent, do first
SR-05 (test coverage) — independent, can parallel with SR-04
SR-06 (_safe_slug collision guard) — should be done AFTER SR-04 and SR-05 because it changes _safe_slug output format, requiring test assertion updates
```

## Execution estimate

| Taskcard | Files | Lines changed | Risk |
|----------|-------|---------------|------|
| SR-04 | 3 | ~6 | Low — string changes only |
| SR-05 | 1 | ~45 | Low — new tests only |
| SR-06 | 2 | ~8 | Medium — changes _safe_slug output format |
