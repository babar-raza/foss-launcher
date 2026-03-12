# PH-00 — Platform Hardening: Post-TC-4060/TC-4061 Self-Review Gap Index

**Source**: AG-020 self-review of TC-4060 (Intake Hardening) + TC-4061 (Understand Hardening)
**Date**: 2026-03-11
**Severity legend**: 🔴 Critical | 🟠 Significant | 🟡 Minor

---

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|:--------:|-------------|----------|
| G-01 | 🔴 | `_write_cache_timestamp` unguarded — OSError propagates through a successful clone | [PH-01](#ph-01) |
| G-02 | 🔴 | `format_evidence_source` has no write site — always `"heuristic"` in production (dead code) | [PH-02](#ph-02) |
| G-03 | 🟠 | `files_estimated` cap is 200 in code but taskcard spec said 100 | [PH-03](#ph-03) |
| G-04 | 🟠 | `_detect_package_root` WARNING fires even for adapter-dispatched repos (noise, misleading) | [PH-04](#ph-04) |
| G-05 | 🟡 | `_generate_synthetic_snippets` docstring missing Python-only constraint (checklist item 13 falsely marked done) | [PH-05](#ph-05) |
| G-06 | 🟡 | `config_generator._derive_canonical_import` reads `families.yaml` on every call — no caching, hurts batch mode | [PH-06](#ph-06) |

---

## Taskcards

---

<a name="ph-01"></a>
## PH-01 — Guard `_write_cache_timestamp` Against OSError

**Status**: Done
**Gap linkage**: G-01
**Checklist**: [x] OSError guard logs WARNING [x] success path no WARNING [x] 2 tests pass
**Role**: Senior engineer. Drop-in, production-ready.

### Context

`_write_cache_timestamp` in `src/launcher/workers/intake/clone.py` calls
`ts_marker.write_text(...)` with no error handling. If the disk is full or the
cache directory has restricted permissions after the clone succeeds, this raises
`OSError` and propagates up through `clone_repo_cached`, failing the entire Intake
pipeline — despite the clone having completed successfully. The timestamp is a
non-critical diagnostic: its failure must never abort a good clone.

### Scope

**Fix**: Wrap the `write_text` call in `_write_cache_timestamp` with `try/except OSError`
and log a WARNING on failure. Pipeline continues without interruption.

**Allowed paths**:
- `src/launcher/workers/intake/clone.py`
- `tests/unit/workers/test_clone.py`

**Forbidden**: any other path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_clone.py -v --tb=short` — all pass including new tests
- **UI/Web/API**: N/A
- **Tests**:
  - New: `test_clone_timestamp_write_failure_does_not_abort_clone` — mock `write_text` to raise `OSError`; assert clone still returns `(repo_dir, sha, is_fresh)` successfully and a WARNING was logged
  - New: `test_clone_timestamp_write_failure_logs_warning` — same setup; assert `caplog` contains `"Could not write .clone_timestamp"`
  - Regression: all existing `TestCloneTimestamp` tests still pass
- **Config respected end-to-end**: `force_refresh=True` path also guarded (write is called on the fresh clone)
- **No mock data in production paths**: tests must use `tmp_path` fixture, not hardcoded dirs

### Deliverables

1. **`src/launcher/workers/intake/clone.py`** — `_write_cache_timestamp` function wrapped:
   ```python
   def _write_cache_timestamp(cache_dir: Path) -> None:
       """Write ISO UTC timestamp marker for stale-cache detection.

       TC-4060: Written alongside .clone_sha on fresh clone.
       Failure is non-fatal — a WARNING is logged and the pipeline continues.
       Without this marker, _log_cache_age silently skips age logging (acceptable).
       """
       ts_marker = cache_dir / _CLONE_TIMESTAMP_MARKER
       try:
           ts_marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
       except OSError as exc:
           logger.warning(
               "[Clone] Could not write .clone_timestamp to %s: %s — "
               "stale cache age detection disabled for this clone.",
               cache_dir, exc,
           )
   ```
2. **`tests/unit/workers/test_clone.py`** — 2 new tests covering the error path (OSError guard) and the WARNING message format.

### Hard rules

- Keep `clone_repo_cached` public signature unchanged — no new parameters
- No network calls in tests — all clone operations must be mocked or use `tmp_path`
- `_log_cache_age` must continue to work (silently skip) when `.clone_timestamp` is absent (pre-existing behavior)
- Guard must not swallow genuine logic errors — only `OSError` is caught, not bare `Exception`
- Deterministic: `PYTHONHASHSEED=0` required

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Robustness | OSError on timestamp write never propagates to caller |
| Testability | Both happy-path and OSError-path covered with real assertions |
| Observability | WARNING message includes `cache_dir` and the original exception |
| Minimality | Single try/except block; no restructuring of surrounding code |
| Correctness | Clone return value unchanged; stale detection gracefully degrades |

### Now (runbook)

```bash
# 1. Edit clone.py: wrap _write_cache_timestamp body in try/except OSError
# 2. Verify existing tests still pass
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_clone.py -v --tb=short

# 3. Add 2 new tests to test_clone.py
# 4. Run targeted + full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_clone.py tests/unit/workers/test_intake.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

<a name="ph-02"></a>
## PH-02 — Add Write Site + Literal Type for `format_evidence_source`

**Status**: Done
**Checklist**: [x] Literal type on field [x] write site in worker.py [x] schema enum constraint [x] 3 new tests pass (absent, ast_verified, rejection) [x] existing tests unchanged
**Gap linkage**: G-02
**Role**: Senior engineer. Drop-in, production-ready.

### Context

`ProductEvidence.format_evidence_source` was added in TC-4061 with a default of
`"heuristic"` and a JSON schema entry, but no production code ever sets it to
`"ast_verified"` or `"absent"`. In every real run the field is always `"heuristic"`,
making it dead documentation masquerading as a signal. Additionally, the field
accepts any `str`, so invalid values (e.g. `"verified"`, `"llm"`) pass silently.

Two independent fixes:
1. **Type tightening**: change `str` → `Literal["ast_verified", "heuristic", "absent"]`
2. **Write site**: set the correct value in `_extract_product_evidence` based on what
   `build_repo_truth` actually found.

### Scope

**Fix**:
- In `understanding.py`: change field type to `Literal["ast_verified", "heuristic", "absent"]`
- In `worker.py` (Understand): after assembling `ProductEvidence`, set `format_evidence_source`
  based on the actual evidence: `"ast_verified"` when formats came from AST analysis
  (i.e. `not _evidence_failed and bool(pe.supported_formats or pe.input_formats or pe.output_formats)`),
  `"absent"` when no formats found at all, `"heuristic"` otherwise.

**Allowed paths**:
- `src/launcher/models/understanding.py`
- `src/launcher/workers/understand/worker.py`
- `specs/schemas/understanding_bundle.schema.json`
- `tests/unit/workers/test_understand.py`
- `tests/unit/workers/understand/test_extract.py`

**Forbidden**: any other path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/unit/workers/understand/test_extract.py -v --tb=short`
- **UI/Web/API**: N/A
- **Tests**:
  - New: `test_format_evidence_source_is_ast_verified_when_formats_present` — build a bundle where `_extract_product_evidence` returns formats; assert `product_evidence.format_evidence_source == "ast_verified"`
  - New: `test_format_evidence_source_is_absent_when_no_formats` — empty `supported_formats`/`input_formats`/`output_formats`; assert `"absent"`
  - New: `test_format_evidence_source_rejects_invalid_value` — `ProductEvidence(format_evidence_source="invalid")` raises `ValidationError`
  - Regression: `test_format_evidence_source_default_is_heuristic` still passes (default unchanged)
- **Config respected end-to-end**: value must appear in `understanding_bundle.json` artifact when written
- **No mock data in production paths**: use `tmp_path` for `_extract_product_evidence` tests

### Deliverables

1. **`src/launcher/models/understanding.py`** — field change:
   ```python
   from typing import Literal

   format_evidence_source: Literal["ast_verified", "heuristic", "absent"] = Field(
       default="heuristic",
       description=(
           "TC-4061: How format lists (supported_formats, input_formats, output_formats) "
           "were populated. 'ast_verified' = extracted from source AST and verified; "
           "'heuristic' = regex/pattern matching with uncertain coverage; "
           "'absent' = no formats found in the repository."
       ),
   )
   ```
2. **`src/launcher/workers/understand/worker.py`** — add write site after `ProductEvidence` assembly:
   ```python
   # TC-4061 PH-02: Set format_evidence_source based on actual extraction outcome
   _has_formats = bool(
       _product_evidence.supported_formats
       or _product_evidence.input_formats
       or _product_evidence.output_formats
   )
   if not _has_formats:
       _fmt_src: Literal["ast_verified", "heuristic", "absent"] = "absent"
   elif not _evidence_failed:
       _fmt_src = "ast_verified"
   else:
       _fmt_src = "heuristic"
   _product_evidence = _product_evidence.model_copy(update={"format_evidence_source": _fmt_src})
   ```
3. **`specs/schemas/understanding_bundle.schema.json`** — tighten field definition:
   ```json
   "format_evidence_source": {
     "type": "string",
     "enum": ["ast_verified", "heuristic", "absent"],
     "description": "TC-4061: Provenance of format lists. 'ast_verified' | 'heuristic' | 'absent'.",
     "default": "heuristic"
   }
   ```
4. **`tests/unit/workers/test_understand.py`** and **`tests/unit/workers/understand/test_extract.py`** — 3 new tests covering all 3 values and the validation rejection.

### Hard rules

- `Literal` type must be imported from `typing` (Python 3.8+ compatible; already 3.13 in this project)
- `model_copy(update=...)` pattern is already used in the codebase — do not use `__dict__` mutation
- The `_evidence_failed` boolean already exists in `worker.py`; use it, do not re-derive
- Schema `"enum"` addition is backward-compatible (new bundles valid; old bundles with `"heuristic"` still valid)
- No new dependencies

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | `format_evidence_source` reflects actual extraction outcome in every run |
| Robustness | `Literal` type rejects invalid values at model validation (not silently) |
| Observability | Field value visible in `understanding_bundle.json` artifact |
| Integration fit | Uses existing `model_copy` + `_evidence_failed` patterns |
| Minimality | Two targeted edits (model + worker); no restructuring |

### Now (runbook)

```bash
# 1. Update understanding.py: Literal type on format_evidence_source
# 2. Update worker.py: add _fmt_src derivation + model_copy after ProductEvidence assembly
# 3. Update understanding_bundle.schema.json: add enum constraint
# 4. Add 3 tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py::TestTC4061FormatEvidenceSourceField -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/unit/workers/understand/ -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

<a name="ph-03"></a>
## PH-03 — Fix `files_estimated` Cap: 200 → 100 (Spec Alignment)

**Status**: Done
**Checklist**: [x] cap changed to 100 [x] docstring updated [x] test_files_estimated_capped_at_100 passes [x] 67 intake tests pass
**Gap linkage**: G-03
**Role**: Senior engineer. Drop-in, production-ready.

### Context

TC-4060 taskcard Step 4 specifies: _"count of top-level files (non-recursive, cap at 100
to stay fast)"_. The implementation uses `min(len(children), 200)`. Evidence.md silently
accepts 200 without noting the discrepancy. This is a spec deviation that needs correction
and a test that pins the cap value.

### Scope

**Fix**: Change `min(len(children), 200)` to `min(len(children), 100)` in `_build_repo_signals`
in `worker.py` (Intake). Update the relevant test assertions and test name.

**Allowed paths**:
- `src/launcher/workers/intake/worker.py`
- `tests/unit/workers/test_intake.py`

**Forbidden**: any other path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py::TestBuildRepoSignals -v --tb=short`
- **UI/Web/API**: N/A
- **Tests**:
  - New/updated: `test_files_estimated_cap_is_100` — create a `tmp_path` with 150 files; assert `files_estimated == 100` (not 150, not 200)
  - Regression: `test_large_dir_signals` (if named differently) must assert ≤100, not ≤200
  - Existing tests that assert specific `files_estimated` values must be updated to match new cap
- **Config respected end-to-end**: `intake_bundle.json` must show `files_estimated ≤ 100`
- **No mock data in production paths**: use `tmp_path` with real file creation

### Deliverables

1. **`src/launcher/workers/intake/worker.py`** — one-line change in `_build_repo_signals`:
   ```python
   # Before:
   files_estimated = min(len(children), 200)
   # After:
   files_estimated = min(len(children), 100)  # TC-4060 Step 4: non-recursive, cap at 100
   ```
2. **`tests/unit/workers/test_intake.py`** — add `test_files_estimated_cap_is_100`; update any existing assertion that relied on 200.

### Hard rules

- This is a purely internal constant change — no API surface changes
- Do not change `_STALE_CACHE_DAYS = 7` or any other constant
- `_build_repo_signals` docstring must be updated to say "capped at 100" instead of any prior value
- Deterministic: `PYTHONHASHSEED=0`

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Cap value matches spec exactly (100) |
| Spec alignment | `_build_repo_signals` docstring agrees with implementation |
| Testability | Test creates >100 files and asserts exactly 100 |
| Minimality | Single constant change + docstring update + 1 test |
| Evidence | Next evidence.md run will show correct value |

### Now (runbook)

```bash
# 1. Edit worker.py (Intake): min(..., 100)
# 2. Update _build_repo_signals docstring: "capped at 100"
# 3. Add/update test
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py::TestBuildRepoSignals -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

<a name="ph-04"></a>
## PH-04 — Suppress `_detect_package_root` WARNING for Adapter-Dispatched Repos

**Status**: Not Started
**Gap linkage**: G-04
**Role**: Senior engineer. Drop-in, production-ready.

### Context

`_detect_package_root` logs a WARNING when it returns `""`. This is correct for
the fallback code path (no adapter). However, `_extract_api_surface` bypasses
`_detect_package_root` entirely when an `adapter` is provided — the adapter's
`detect_package_root()` is called instead. The WARNING is therefore irrelevant for
C++, Java, Go, and .NET repos that use adapters, and would appear misleadingly in
their logs when `_detect_package_root` is called directly (e.g. in tests or future
tooling).

Fix: add a `suppress_warning: bool = False` parameter (or equivalently, an
`_adapter_dispatched` kwarg) so callers can suppress the WARNING when the fallback
path is expected. The WARNING fires by default, maintaining the new behavior for the
case the WARNING is needed.

**Alternative** (simpler): add a module-level docstring note clarifying the function
is the fallback path and that callers using adapters should not call it. Only add the
parameter if the function is actually called directly in non-test code for adapter repos.

After investigation, the correct fix is the simpler documentation-only approach if
`_detect_package_root` is never called for adapter repos in production; and the
parameter approach if it could be.

### Scope

**Fix**: Investigate call graph. If `_detect_package_root` is never called for
adapter-dispatched repos in production, add a clear docstring note. If it can be
called for adapter repos (unlikely but possible in custom adapters that call `super()`),
add `suppress_warning: bool = False`.

**Allowed paths**:
- `src/launcher/workers/understand/extract/_api_surface.py`
- `tests/unit/workers/understand/test_extract.py`

**Forbidden**: any other path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py::TestTC4061PackageRootWarnLog -v --tb=short`
- **UI/Web/API**: N/A
- **Tests**:
  - Existing: `test_detect_package_root_warns_when_empty` still passes
  - New: `test_detect_package_root_no_warning_when_suppressed` — if parameter added, call with `suppress_warning=True`, assert no WARNING emitted
  - New: `test_extract_api_surface_no_spurious_warning_with_adapter` — call `_extract_api_surface` with a mock adapter; assert `_detect_package_root` WARNING does NOT appear in logs
- **Config respected**: WARNING only appears when appropriate (fallback path, no adapter)
- **No mock data**: use `tmp_path` with controlled structure

### Deliverables

1. **`src/launcher/workers/understand/extract/_api_surface.py`** — either:
   - (Option A: docstring-only) Update `_detect_package_root` docstring: _"This function is the no-adapter fallback. `_extract_api_surface` bypasses this function when an adapter is provided. Only call this for repos where no adapter is registered."_
   - (Option B: parameter) Add `suppress_warning: bool = False`:
     ```python
     def _detect_package_root(repo_dir: Path, *, suppress_warning: bool = False) -> str:
         ...
         if not suppress_warning:
             logger.warning(...)
         return ""
     ```
2. **`tests/unit/workers/understand/test_extract.py`** — tests for the chosen approach.

### Hard rules

- Do not change the default behavior — WARNING fires when appropriate
- If Option B (parameter) chosen: all existing call sites must be audited and updated
- Do not suppress the WARNING for the no-adapter fallback path — only for adapter-dispatched calls
- No new dependencies

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Observability | WARNING fires when meaningful; suppressed when expected |
| Correctness | No false positives in adapter-dispatched repo logs |
| Minimality | Docstring or single parameter; no restructuring |
| Testability | Suppression behavior tested directly |
| Robustness | Default behavior preserved (opt-in suppression only) |

### Now (runbook)

```bash
# 1. Read _extract_api_surface: confirm adapter path never calls _detect_package_root
grep -n "_detect_package_root" src/launcher/workers/understand/extract/_api_surface.py

# 2. Choose Option A or B based on audit
# 3. Apply change + tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py::TestTC4061PackageRootWarnLog -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

<a name="ph-05"></a>
## PH-05 — Update `_generate_synthetic_snippets` Docstring (Python-Only Constraint)

**Status**: Not Started
**Gap linkage**: G-05
**Role**: Senior engineer. Drop-in, production-ready.

### Context

TC-4061 checklist item 13 was marked `[x]` ("Docstrings/comments updated for all
changed code paths") but `_generate_synthetic_snippets` was not updated. Its docstring
makes no mention of the Python-only constraint added by TC-4061. A future engineer
encountering the function will not know it generates Python AST syntax and cannot be
called for non-Python platforms. The call-site gate in `_entry.py` is the only
protection — but it has an inline comment, not a function-level guarantee.

### Scope

**Fix**: Update the `_generate_synthetic_snippets` docstring to explicitly state:
(a) the function generates Python-syntax code, (b) it must only be called for Python
repos, (c) the call site in `_entry.py` enforces this gate.

**Allowed paths**:
- `src/launcher/workers/understand/extract/_entry.py`

**Forbidden**: any other path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q --tb=short` — all pass (docstring-only change, no behavioral impact)
- **UI/Web/API**: N/A
- **Tests**: No new behavioral tests needed — this is purely a docstring update. Verify no test asserts on docstring text.
- **Config respected end-to-end**: N/A
- **No mock data**: N/A

### Deliverables

1. **`src/launcher/workers/understand/extract/_entry.py`** — updated `_generate_synthetic_snippets` docstring:
   ```python
   def _generate_synthetic_snippets(
       api_surface: ApiSurface,
       product: ProductIdentity,
       claims: list[Claim],
       max_snippets: int = 20,
   ) -> list[Snippet]:
       """Generate template-based code snippets from ClassBrief data.

       **Python-only**: This function generates Python-syntax code using Python import
       statements (``import {module}``) and validates syntax with ``ast.parse()``.
       It must NOT be called for non-Python platforms (TypeScript, Go, Java, .NET, etc.)
       as the output would be syntactically wrong for those languages.

       Call-site gate in ``_entry.py`` enforces this: only called when
       ``product.platform in ("python", "")``. Do not call this function directly
       for non-Python repos.

       No LLM involved — pure deterministic synthesis from API surface.
       Only generates for classes that have >= 2 safe (no-required-arg) methods.
       Each snippet is validated with ast.parse() before inclusion.

       TC-4056 Fix 8: Only include methods that have no required positional arguments
       (i.e., only self). Methods like load(path: str) or save(path) with required args
       are skipped — generating obj.load() with no args creates semantically wrong evidence.
       TC-4061: Python-only synthesis. Guarded at call site in _entry.py.
       """
   ```

### Hard rules

- Docstring only — zero behavioral changes
- Do not reformat the function body or adjust indentation
- Python-only constraint must be explicit (not implied)
- Must run `tests/` regression to confirm no behavioral side-effects

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Maintainability | Future engineers cannot miss the Python-only constraint |
| Correctness | Docstring accurately describes behavior (Python AST validation) |
| Spec alignment | Checklist item 13 legitimately satisfied |
| Minimality | Docstring update only; zero code change |
| Consistency | Matches TC-4061 inline comment in `_entry.py` |

### Now (runbook)

```bash
# 1. Edit _entry.py: update _generate_synthetic_snippets docstring
# 2. Verify zero behavioral impact
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

<a name="ph-06"></a>
## PH-06 — Cache `families.yaml` Reads in `config_generator._derive_canonical_import`

**Status**: Not Started
**Gap linkage**: G-06
**Role**: Senior engineer. Drop-in, production-ready.

### Context

`config_generator._derive_canonical_import` accepts a `families_yaml_path` argument
and calls `families_yaml_path.read_text()` + `yaml.safe_load()` on every invocation.
In batch mode (`org_scanner` processing 100+ GitHub repos), this results in 100+
identical disk reads and YAML parses of the same file — a ~5–50ms cost per call that
compounds to seconds for large orgs. The Intake worker already implements a module-level
`_families_cache` for the same file. The config generator should do the same.

### Scope

**Fix**: Add a module-level `_config_gen_families_cache: dict | None = None` in
`config_generator.py`. Add `_load_families_for_config_gen(path)` that reads once
and caches. Add `_clear_config_gen_families_cache()` for test isolation.
Wire `_derive_canonical_import` to use the cache.

**Allowed paths**:
- `src/launcher/intake/config_generator.py`
- `tests/unit/intake/test_config_generator.py`

**Forbidden**: any other path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_config_generator.py -v --tb=short`
- **UI/Web/API**: N/A
- **Tests**:
  - New: `test_derive_canonical_import_reads_families_yaml_only_once` — call `_derive_canonical_import` 5× with the same `families_yaml_path`; assert `yaml.safe_load` called exactly once (mock it)
  - New: `test_clear_config_gen_families_cache_resets_state` — call, clear, call again; assert 2 reads
  - Regression: all existing `TestDeriveCanonicalImport` tests still pass
- **Config respected**: cache is per-process, keyed on file path (if multiple YAML paths used, cache them separately or invalidate on path change)
- **No mock data in production paths**: tests may mock `yaml.safe_load`; production path uses real YAML

### Deliverables

1. **`src/launcher/intake/config_generator.py`** — add cache infrastructure:
   ```python
   # Module-level cache for families.yaml — one read per process lifetime per path.
   # Mirrors the pattern used in workers/intake/worker.py (_families_cache).
   _config_gen_families_cache: dict[str, dict] = {}  # key: str(path) → parsed YAML

   def _load_families_for_config_gen(families_yaml_path: Path) -> dict:
       """Load and cache families.yaml for config_generator. One parse per process per path."""
       key = str(families_yaml_path.resolve())
       if key in _config_gen_families_cache:
           return _config_gen_families_cache[key]
       try:
           data = yaml.safe_load(families_yaml_path.read_text(encoding="utf-8")) or {}
       except Exception:
           data = {}
       _config_gen_families_cache[key] = data
       return data

   def _clear_config_gen_families_cache() -> None:
       """Reset cache. Used in tests for isolation between test cases."""
       _config_gen_families_cache.clear()
   ```
2. Wire `_derive_canonical_import` to call `_load_families_for_config_gen(families_yaml_path)` instead of reading inline.
3. **`tests/unit/intake/test_config_generator.py`** — 2 new tests (cache hit, cache reset) + ensure `_clear_config_gen_families_cache()` is called in test teardown/fixtures.

### Hard rules

- Cache keyed by resolved path string — prevents path aliasing bugs (`.` vs absolute)
- Cache is NOT shared with Intake worker's `_families_cache` — separate module scope
- `_clear_config_gen_families_cache()` must be called in test fixtures to prevent cross-test contamination
- No new dependencies (no `functools.lru_cache` — the existing `_families_cache` pattern is a plain dict for explicitness and testability)
- Keep existing `_derive_canonical_import` public signature unchanged

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Performance | 100 calls → 1 disk read (not 100) |
| Testability | `yaml.safe_load` call count assertable via mock |
| Robustness | Cache miss on parse failure returns `{}` (same behavior as uncached) |
| Consistency | Same pattern as `_families_cache` in Intake worker |
| Minimality | New helper + wire-up only; no change to external API |

### Now (runbook)

```bash
# 1. Add _config_gen_families_cache + _load_families_for_config_gen + _clear_... to config_generator.py
# 2. Wire _derive_canonical_import to use _load_families_for_config_gen
# 3. Add 2 tests + ensure test isolation
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_config_generator.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```
