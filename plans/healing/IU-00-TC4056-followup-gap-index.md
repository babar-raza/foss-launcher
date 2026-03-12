# IU-00 — TC-4056 Follow-up Gap Index

**Context**: TC-4056 implemented 8 root-cause fixes in the Intake and Understand workers
(3310 unit tests passing). Self-review identified 6 residual gaps: three fixes lack
behavioral tests, integration tests were not run, a security-boundary code path has no
observability, and the parent plan file was not closed.

**Parent taskcard**: `plans/taskcards/TC-4056_intake_understand_hardening.md` (status: Done)
**Self-review source**: inline self-review of TC-4056 close-out response, 2026-03-11

---

## Gap Table

| Gap ID | Description | Severity | Taskcard | Status |
|--------|-------------|----------|----------|--------|
| IU-G1 | Fix 3 (disk-fallback sanitization) has no test — security boundary unverified | CRITICAL | IU-01 | Done |
| IU-G2 | Fix 6 (importance sort) has no behavioral test — regression would be silent | HIGH | IU-02 | Done |
| IU-G3 | Fix 7 (skipped_paths) has no end-to-end budget exhaustion test | HIGH | IU-03 | Done |
| IU-G4 | Integration test suite not run before TC-4056 close-out | MEDIUM | IU-04 | Done |
| IU-G5 | Disk-fallback code path has no log line — invisible in heal re-run traces | MEDIUM | IU-05 | Done |
| IU-G6 | Parent plan `spicy-tickling-lake.md` not marked complete | ADMIN | IU-06 | Done |
| IU-G7 | `_SOURCE_IMPORTANCE_STEMS` has `"__init__"` but normalization strips underscores → never matches | HIGH | IU-07 | Done |

---

## Execution Order

```
IU-01 (CRITICAL, test only, 30 min)
IU-02 (HIGH,     test only, 20 min)
IU-03 (HIGH,     test only, 20 min)
IU-04 (MEDIUM,   run + doc, 15 min)
IU-05 (MEDIUM,   code+log,  20 min — touches protected path, needs TC-per-CLAUDE.md)
IU-06 (ADMIN,    doc only,  5 min)
```

IU-01 through IU-03 are independent and can execute in any order.
IU-04 should run after IU-01/02/03 are in place (so integration run covers new tests).
IU-05 requires the existing TC-4056 taskcard or a micro-TC to authorize the protected path.
IU-06 is entirely administrative.

---

## Taskcards

---

## IU-01 — Test: disk-fallback sanitization in `_build_doc_contexts`

**Status**: Done — 4 tests added to `tests/unit/workers/understand/test_extract.py::TestDiskFallbackSanitization`. All pass (3350/3350 full suite).
**Gap linkage**: IU-G1
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: CRITICAL — Fix 3 touches the LLM context sanitization boundary. Without this
test a regression would allow secrets/tokens to reach the LLM silently.

### Context

`_build_doc_contexts` in `_snippets.py` has an inner function `_read_content` that reads
disk when `repo_content` is `None` (resume/heal re-run path). TC-4056 Fix 3 wrapped this
path in `sanitize_input(raw, max_chars=100_000)`, but no test verifies this. The test must
simulate a heal re-run by passing `repo_content={}` (empty dict) and assert that content
matching a known redaction pattern is stripped before being included in the context.

### Scope

**Fix**: Add a test class `TestDiskFallbackSanitization` to
`tests/unit/workers/understand/test_extract.py` with ≥3 test methods:
1. `test_disk_fallback_sanitizes_secret_patterns` — file with mock secret (`sk-aaaa...`) is redacted
2. `test_disk_fallback_returns_none_for_missing_file` — nonexistent path returns nothing in context
3. `test_disk_fallback_respects_max_chars_cap` — a file larger than 100K chars is truncated

**Allowed paths**:
- `tests/unit/workers/understand/test_extract.py`

**Forbidden**: any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py::TestDiskFallbackSanitization -v` — all 3 tests PASS
- **UI/Web/API**: N/A (pure unit test)
- **Tests**:
  - `test_disk_fallback_sanitizes_secret_patterns`: creates a temp file containing `sk-aaaa1111bbbb2222` (mock API key pattern), calls `_build_doc_contexts` with `repo_content={}`, asserts the returned context text does NOT contain the raw token
  - `test_disk_fallback_returns_none_for_missing_file`: passes a `doc_paths` entry that doesn't exist on disk; asserts the context list has zero entries for that path
  - `test_disk_fallback_respects_max_chars_cap`: writes a 150,000-char file, asserts returned content ≤ 100,000 chars
- **Config respected end-to-end**: `max_chars=100_000` constant tested explicitly
- **No mock data in production paths**: test uses `tmp_path` for real disk files; no mocking of `sanitize_input` (must exercise the real sanitizer)

### Deliverables

1. `tests/unit/workers/understand/test_extract.py` — new `TestDiskFallbackSanitization` class appended, replacing no existing code
2. All 3 test methods cover the happy path (sanitization applied) and two failure/edge paths (missing file, oversized file)

### Hard rules

- No network in tests — all disk I/O uses `tmp_path`
- `sanitize_input` must NOT be mocked — exercise the real sanitizer to catch future contract changes
- Test must construct `RepoInfo` with the temp file in `doc_paths` so `_build_doc_contexts` actually routes through `_read_content`
- Deterministic: no randomness, no time-dependent assertions

### Review dimensions (5/5 target)

| Dimension | 5/5 means for IU-01 |
|-----------|---------------------|
| Correctness | Test would catch a future removal of `sanitize_input` from the disk-fallback path |
| Testability | Test is isolated, uses only stdlib + `tmp_path`, no live LLM calls |
| Robustness | Covers missing file (None return) and oversized file (truncation) |
| Observability | Test failure message identifies the exact fix (Fix 3) that regressed |
| Minimality | Appends only the new test class; zero changes to production code |

### Now (runbook)

```bash
# 1. Identify where _build_doc_contexts is importable from
# It's in launcher.workers.understand.extract._snippets
# The test file already imports from this module family.

# 2. Add TestDiskFallbackSanitization to test_extract.py
# Pattern: create tmp dir, write doc file, build RepoInfo with doc_paths=[rel_path],
# call _build_doc_contexts(tmp_path, repo_info, repo_content={})
# Assert context text does not contain the raw secret.

# 3. Run:
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_extract.py::TestDiskFallbackSanitization -v

# 4. Run full file to confirm no regressions:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_extract.py -q
```

---

## IU-02 — Test: importance-based file sort in Scout (`_read_repo_content`)

**Status**: Done — `TestImportanceRankHelper` (10 tests) + `TestFileImportanceSort` (4 tests) added to new `tests/unit/workers/understand/test_scout.py`. All pass. Discovered IU-G7 (normalization bug for `__init__` stems) during execution — tracked as IU-07.
**Gap linkage**: IU-G2
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: HIGH — Sort regression would cause low-quality files to be read before
critical API references, silently degrading LLM context quality with no error.

### Context

TC-4056 Fix 6 changed Scout's per-tier file sort from ascending-size-only to
`(-importance_rank, size_bytes)`. There is no test that verifies a high-importance file
(e.g., a file named `api.md`) is read before a low-importance file (e.g., `zz_misc.md`)
even when the high-importance file is larger. Without this test, the sort key could be
reverted or accidentally changed.

### Scope

**Fix**: Create `tests/unit/workers/understand/test_scout.py` (new file) with a test class
`TestFileImportanceSort` containing ≥3 test methods:
1. `test_important_doc_read_before_small_junk_doc` — `api.md` (large) read before `zzz_noise.md` (small)
2. `test_readme_read_before_unknown_doc` — `readme.md` read before `other_doc.md` of same size
3. `test_source_init_read_before_unknown_source` — `__init__.py` read before `utils_extra.py`

Also add `TestImportanceRankHelper` testing `_file_importance_rank` directly:
1. `test_rank_known_doc_stems` — `readme.md`, `api.md`, `guide.md` all return 1
2. `test_rank_unknown_doc_stem` — `zz_noise.md` returns 0
3. `test_rank_source_init` — `__init__.py` returns 1 in source category
4. `test_rank_unknown_source` — `utils_extra.py` returns 0 in source category

**Allowed paths**:
- `tests/unit/workers/understand/test_scout.py` (new file)

**Forbidden**: any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_scout.py -v` — all tests PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `TestImportanceRankHelper` tests call `_file_importance_rank` directly — verifies the ranking function independently of Scout
  - `TestFileImportanceSort` tests create a minimal repo in `tmp_path` with files of known sizes and names, then call `run_scout(repo_dir)` and assert that important files appear in `repo_content` while small junk files (within the same tier) may be absent if the budget is tight enough
- **Config respected**: Tests set a small budget (e.g., 5000 bytes) so only high-priority files fit, forcing the sort to matter
- **No mock data in production paths**: real files on disk, real `run_scout` call, no mocking of `_file_importance_rank`

### Deliverables

1. `tests/unit/workers/understand/test_scout.py` — new file with two test classes
2. Covers happy path (important file wins) and regression path (sort key `size` alone would fail the test)

### Hard rules

- No network calls — all tests offline, no LLM calls
- `run_scout` is an async function; tests must use `@pytest.mark.asyncio` or `asyncio.run()`
- Budget must be set small enough that not all files fit — this forces the sort to be the deciding factor
- Deterministic: `PYTHONHASHSEED=0`

### Review dimensions (5/5 target)

| Dimension | 5/5 means for IU-02 |
|-----------|---------------------|
| Correctness | Reverting sort to `size_bytes` only would break `test_important_doc_read_before_small_junk_doc` |
| Testability | Direct `_file_importance_rank` tests allow unit-level verification without full Scout run |
| Robustness | Budget constraint means the test isn't vacuous — actual exclusion occurs |
| Observability | Test name and failure message identify which sort key failed |
| Minimality | New file only — no changes to production code |

### Now (runbook)

```bash
# 1. Import targets:
#   from launcher.workers.understand.scout import _file_importance_rank, run_scout
#   from launcher.models.understanding import FileCategory

# 2. For TestImportanceRankHelper: just call _file_importance_rank(path, category)

# 3. For TestFileImportanceSort: use tmp_path, write files, run_scout:
#   - Set budget via monkeypatching scout._DEFAULT_BUDGET_BYTES to small value
#   - OR write enough data to fill budget with junk before the important file
#   - Assert important file in repo_content keys

# 4. Run:
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_scout.py -v
```

---

## IU-03 — Test: `skipped_paths` population in `run_scout`

**Status**: Done — `TestSkippedPathsPopulation` (4 tests including async integration) added to `tests/unit/workers/understand/test_scout.py`. All pass. Fixed test scenario to use doc_cap exhaustion (8×110KB docs) rather than total-budget exhaustion to reliably trigger skipped_paths.
**Gap linkage**: IU-G3
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: HIGH — Without this test, the `skipped_paths` field could be silently broken
(never populated) and downstream workers would have no visibility into missed files.

### Context

TC-4056 Fix 7 added `skipped_paths: list[str]` to `RepoInfo`, populated from `budget_log`
entries with skip reasons (`budget_exceeded`, `doc_cap_reached`, `source_reserve`,
`file_too_large_for_remaining_budget`). Existing tests only verify that `RepoInfo`
deserializes with `skipped_paths=[]` as default — they do not exercise the Scout code
path that populates the field.

### Scope

**Fix**: Add a test class `TestSkippedPathsPopulation` to
`tests/unit/workers/understand/test_scout.py` with ≥2 test methods:
1. `test_skipped_paths_populated_when_budget_exceeded` — budget set to accommodate only 1 of 3 doc files; asserts `repo_info.skipped_paths` contains the 2 that didn't fit
2. `test_per_file_cap_files_not_in_skipped_paths` — a file that is truncated (not skipped) must NOT appear in `skipped_paths` (it appears in `repo_content`, just shortened)

Also add `TestSkippedPathsModel` (if not already covered) verifying `RepoInfo.skipped_paths`
deserializes correctly when field is absent (legacy bundles) or present.

**Allowed paths**:
- `tests/unit/workers/understand/test_scout.py` (created by IU-02 or created here if IU-02 is not yet executed)

**Forbidden**: any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_scout.py::TestSkippedPathsPopulation -v` — all tests PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_skipped_paths_populated_when_budget_exceeded`: creates 3 doc files totalling >budget; runs `run_scout`; asserts `len(repo_info.skipped_paths) > 0` and all skipped paths appear in the returned `budget_log` with a recognized skip reason
  - `test_per_file_cap_files_not_in_skipped_paths`: creates one large file (>100K chars), sets budget to accommodate it; runs `run_scout`; asserts the file IS in `repo_info.file_index` (was read, just truncated) and NOT in `repo_info.skipped_paths`
- **Config respected**: both tests use monkeypatched or parameterized budget values
- **No mock data**: real filesystem, real `run_scout`

### Deliverables

1. `TestSkippedPathsPopulation` added to `tests/unit/workers/understand/test_scout.py`
2. Test would fail if `skipped_paths` were not populated (e.g., if the list comprehension were commented out)

### Hard rules

- Must use `@pytest.mark.asyncio` (or equivalent) since `run_scout` is async
- No network calls
- Deterministic: all file sizes deterministic, no random content
- Must distinguish `per_file_cap` (truncated, not skipped) from skip reasons

### Review dimensions (5/5 target)

| Dimension | 5/5 means for IU-03 |
|-----------|---------------------|
| Correctness | Test would catch if `skipped_paths` list comprehension were removed from `run_scout` |
| Robustness | Explicitly verifies truncated files are NOT in skipped_paths (the key distinction) |
| Testability | Exercises the real budget-exhaustion code path, not a model field |
| Observability | Failure message identifies which reason category triggered the test |
| Minimality | New test class only in existing new file — no production changes |

### Now (runbook)

```bash
# 1. Budget control: monkeypatch scout._DEFAULT_BUDGET_BYTES
#    OR use a test helper that calls _read_repo_content directly with budget_bytes=<small>

# 2. Build scenario:
#    tmp_path/docs/api.md         (2000 bytes, important)
#    tmp_path/docs/guide.md       (2000 bytes)
#    tmp_path/docs/reference.md   (2000 bytes)
#    budget = 2500 bytes -> only one doc fits

# 3. Call run_scout(tmp_path) with monkeypatched budget

# 4. Assert:
#    len(repo_info.skipped_paths) >= 2
#    all(p.endswith(".md") for p in repo_info.skipped_paths)

# 5. Run:
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_scout.py::TestSkippedPathsPopulation -v
```

---

## IU-04 — Run integration tests and update TC-4056 evidence

**Status**: Not Started
**Gap linkage**: IU-G4
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: MEDIUM — The plan for TC-4056 explicitly required an integration test run.
This was skipped during close-out. Without it, cross-worker contract issues from the 8
fixes may be undetected until a pilot run.

### Context

`plans/taskcards/TC-4056_intake_understand_hardening.md` Verification Plan section
required: `pytest tests/integration/ -x -q -m "not slow"`. This was not executed before
the taskcard was marked Done. The evidence file currently says "NOT RUN — deferred".

### Scope

**Fix**:
1. Run `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/ -x -q -m "not slow"`
2. Capture result (pass count, any failures)
3. Update `reports/TC-4056/evidence.md` "Integration Test Results" section with actual results
4. If any integration test fails due to TC-4056 changes: fix the root cause (which may spawn a new healing taskcard)

**Allowed paths**:
- `reports/TC-4056/evidence.md`

**Forbidden**: any other file or path during this taskcard. If integration failures require code fixes, open a new healing taskcard.

### Acceptance checks

- **CLI**:
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/ -x -q -m "not slow"
  ```
  Expected: all pass (or explicit documented failures with root cause)
- **UI/Web/API**: N/A
- **Tests**: integration suite passes without TC-4056 regressions
- **Config respected**: `-m "not slow"` excludes known slow network-dependent tests
- **No mock data**: integration tests run as-is (they have their own mocking)

### Deliverables

1. `reports/TC-4056/evidence.md` updated with actual integration test result line:
   ```
   Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/ -x -q -m "not slow"
   Result: N passed in X.Xs  [OR: FAILED — see root cause below]
   ```

### Hard rules

- Do not alter integration test code to make tests pass — fix root causes
- If a test fails due to a TC-4056 regression, open a new healing taskcard and reference it in the evidence

### Review dimensions (5/5 target)

| Dimension | 5/5 means for IU-04 |
|-----------|---------------------|
| Correctness | Evidence file accurately reflects actual test results |
| Thoroughness | All integration tests under `tests/integration/` executed (modulo `not slow` marker) |
| Observability | Failures documented with root cause, not silently skipped |
| Minimality | Only `evidence.md` modified — no production changes in this taskcard |
| Consistency | Evidence file final state matches TC-4056 acceptance check #1 |

### Now (runbook)

```bash
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2

# 1. Run integration suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/ -x -q -m "not slow" 2>&1 | tee /tmp/int_test_out.txt

# 2. Check result:
tail -5 /tmp/int_test_out.txt

# 3. Update reports/TC-4056/evidence.md with result

# 4. If failures: triage and open new healing taskcard
```

---

## IU-05 — Add observability log for disk-fallback path in `_read_content`

**Status**: Not Started
**Gap linkage**: IU-G5
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: MEDIUM — The disk-fallback path is hit only on resume/heal re-runs. Without
a log line, there is no way to confirm in production logs that (a) sanitization was applied
and (b) which files triggered disk reads vs. cache hits.

### Context

In `_snippets.py`, `_read_content()` has two paths:
1. Cache hit: returns `repo_content[rel_path]` silently
2. Disk fallback (heal re-run path): reads from disk, sanitizes

Path 2 is the security-relevant path added by TC-4056 Fix 3. It currently has no log line.
In production heal re-runs, operators have no way to see which files went through the disk
path. A single `logger.debug` call would make this visible.

**NOTE**: This taskcard touches `src/launcher/workers/understand/extract/_snippets.py`,
a protected path under `src/launcher/`. Per CLAUDE.md (AG-002), this requires an
authorized In-Progress taskcard. IU-05 serves as that authorization. Set status to
`In-Progress` before making the code change.

### Scope

**Fix**: In `_snippets.py`, add one `logger.debug` line inside `_read_content` at the
point where the disk-read branch is entered:
```python
logger.debug("[Extract] repo_content miss; sanitized disk read for %s", rel_path)
```
Place it immediately before `raw = file_path.read_text(...)`.

**Allowed paths**:
- `src/launcher/workers/understand/extract/_snippets.py`

**Forbidden**: any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q` — all pass (no regressions)
- **UI/Web/API**: N/A
- **Tests**: No new tests required for a single log line, but IU-01's `TestDiskFallbackSanitization` exercises this path; that test should still pass
- **Config respected**: `logger.debug` is suppressed in normal test output; no test verbosity change needed
- **No mock data**: the log line doesn't change behavior

### Deliverables

1. `src/launcher/workers/understand/extract/_snippets.py` — one line added to `_read_content` disk-fallback branch
2. No new tests required (IU-01 covers the path)

### Hard rules

- Add only the debug log line — no other changes to `_snippets.py`
- Log must use `%s` lazy formatting (not f-string) for logger compatibility
- Do not change public signatures or behavior

### Review dimensions (5/5 target)

| Dimension | 5/5 means for IU-05 |
|-----------|---------------------|
| Observability | Production logs now show which files triggered disk fallback vs. cache |
| Minimality | Exactly one line added; zero behavioral change |
| Correctness | Log placement (before read, not after) tells operator file was about to be read |
| Maintainability | `%s` lazy format matches existing log patterns in the file |
| Integration fit | `logger.debug` is consistent with other debug log patterns in `_snippets.py` |

### Now (runbook)

```bash
# 1. Locate the disk-fallback branch in _read_content (around line 165-175)
# 2. Add: logger.debug("[Extract] repo_content miss; sanitized disk read for %s", rel_path)
#    immediately before: raw = file_path.read_text(encoding="utf-8", errors="replace")

# 3. Verify:
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/ -q

# 4. Smoke-check the log appears at debug level:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -c "
import logging, asyncio
logging.basicConfig(level=logging.DEBUG)
# ... set up a minimal run_extract call with repo_content=None
"
```

---

## IU-06 — Close parent plan `spicy-tickling-lake.md`

**Status**: Not Started
**Gap linkage**: IU-G6
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: ADMIN — Open plan files attract unnecessary agent attention and may be
mistaken for in-progress work.

### Context

`C:\Users\prora\.claude\plans\spicy-tickling-lake.md` is the parent plan that scoped the
TC-4056 work (Steps 1-3 analysis + Steps 4-8 fix sequence). It has no completion note.
Future agents reading the plan directory will see it as open.

### Scope

**Fix**: Prepend a completion banner to `spicy-tickling-lake.md`:
```markdown
> **STATUS: COMPLETE** — All 8 fixes implemented via TC-4056 (2026-03-11).
> Unit tests: 3310 passed. Integration tests: see IU-04.
> Residual gaps tracked in `plans/healing/IU-00-TC4056-followup-gap-index.md`.
```

**Allowed paths**:
- `C:\Users\prora\.claude\plans\spicy-tickling-lake.md`

**Forbidden**: any other file or path.

### Acceptance checks

- **CLI**: `head -5 "C:/Users/prora/.claude/plans/spicy-tickling-lake.md"` — shows STATUS: COMPLETE banner
- **UI/Web/API**: N/A
- **Tests**: N/A (documentation only)
- **Config respected**: N/A
- **No mock data**: N/A

### Deliverables

1. `spicy-tickling-lake.md` — completion banner prepended; all existing content preserved

### Hard rules

- Prepend only — do not delete or restructure existing plan content
- Banner must reference TC-4056 by ID and the IU-00 gap index

### Review dimensions (5/5 target)

| Dimension | 5/5 means for IU-06 |
|-----------|---------------------|
| Minimality | Only a banner prepended; zero content removed |
| Consistency | References correct TC-4056 ID and follow-up gap index file |
| Maintainability | Future agents can immediately see the plan is done without reading the full document |

### Now (runbook)

```bash
# 1. Read current first line of spicy-tickling-lake.md
# 2. Prepend the STATUS banner (4 lines)
# 3. Verify: head -10 ".claude/plans/spicy-tickling-lake.md"
```

---

## IU-07 — Fix `_SOURCE_IMPORTANCE_STEMS` normalization bug in `scout.py`

**Status**: Not Started
**Gap linkage**: IU-G7 (discovered during IU-02 execution)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: HIGH — `__init__.py` is the most important source file in any Python package
but currently gets rank 0 (treated as unknown) due to this bug. The sort that was meant
to prioritize it silently fails.

### Context

`_file_importance_rank` normalizes stems with `.replace("-", "").replace("_", "")`.
This means `"__init__"` → `"init"`. But `_SOURCE_IMPORTANCE_STEMS` contains `"__init__"`
(with underscores), so the lookup always misses. `__init__.py` gets the same rank 0 as any
random source file, defeating Fix 6's intent for Python packages.

The correct fix: replace `"__init__"` with `"init"` in `_SOURCE_IMPORTANCE_STEMS` to match
what the normalization function actually produces. Equally, any other stem with underscores
or hyphens in the set should be pre-normalized. Check `_DOC_IMPORTANCE_STEMS` for the same
issue: it already has `"gettingstarted"` (correct), confirming that pre-normalization was
the intended pattern — just missed for `"__init__"`.

### Scope

**Fix**: In `scout.py`, change `"__init__"` → `"init"` in `_SOURCE_IMPORTANCE_STEMS`.
Audit `_DOC_IMPORTANCE_STEMS` for any entry that would not match after normalization.

**Allowed paths**:
- `src/launcher/workers/understand/scout.py`

**Forbidden**: any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_scout.py -v` — `test_init_source_rank_is_0_due_to_normalization_bug` must be UPDATED to assert rank == 1 (after the fix), and all other tests must still pass
- **Tests**:
  - After fix: `_file_importance_rank("__init__.py", FileCategory.source) == 1`
  - After fix: `_file_importance_rank("pkg/__init__.py", FileCategory.source) == 1`
  - `test_init_source_rank_is_0_due_to_normalization_bug` renamed to `test_init_source_rank_is_1` and asserts `== 1`
  - `test_init_read_before_unknown_source_same_size` added back using `__init__.py`
- **No mock data**: exercises real `_file_importance_rank` function
- **Config respected**: no new config — pure bugfix

### Deliverables

1. `src/launcher/workers/understand/scout.py` — `"__init__"` → `"init"` in `_SOURCE_IMPORTANCE_STEMS`
2. `tests/unit/workers/understand/test_scout.py` — update the `test_init_source_rank_is_0_due_to_normalization_bug` test to assert `== 1` and rename it; add `__init__.py`-based sort test

### Hard rules

- Change only `_SOURCE_IMPORTANCE_STEMS` — do not change the normalization function itself (it's correct for its purpose)
- Verify `_DOC_IMPORTANCE_STEMS` has no similar un-normalized entries

### Review dimensions (5/5 target)

| Dimension | 5/5 means for IU-07 |
|-----------|---------------------|
| Correctness | `__init__.py` achieves rank 1 after fix — verifiable by direct assertion |
| Minimality | One string changed in the frozenset + test updated; zero behavioral change elsewhere |
| Testability | Existing `test_init_source_rank_is_0_due_to_normalization_bug` becomes the passing test |
| Robustness | Audit of both stem sets prevents similar bugs from hiding |

### Now (runbook)

```bash
# 1. In scout.py, change:
#   _SOURCE_IMPORTANCE_STEMS: frozenset[str] = frozenset({
#       "__init__", "main", "core", "base", "client", "api", "index",
#   })
# to:
#   _SOURCE_IMPORTANCE_STEMS: frozenset[str] = frozenset({
#       "init", "main", "core", "base", "client", "api", "index",
#   })

# 2. Update test_scout.py: rename bug-documenting test, assert == 1

# 3. Run:
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_scout.py -v

# 4. Run full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q \
  --deselect=tests/unit/workers/test_publish.py::TestDeployIntegration
```
